import time
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.deviceconfiguration.cli_cutthrough import CliCutthrough


class Activate(CommonPlan, CliCutthrough):
    """
    Checking Operation Type
    Validate Supported Device Model
    Checking Existing Resources
    Onboard device
    Step 1:
        Verify RPD# not in use
        Verify channel# not in use (granite)
        Configure RPD
    Step 2:
        configure Down Stream on ds-rf port
    Step 3:
        Gather CLU info from CLU Database (Work In Progres)
        Configure Service Group / Chanel Line Up

    """

    def process(self):
        self.ipAddress = self.resource['properties']['cmtsipAddress']
        self.operationType = self.resource['properties']['operationType']

        # Check operation type
        self.log_status_message('Checking Operation Type')
        self.vendor = self.resource['properties']['device_type']
        if self.operationType != "New":
            err = "Operation " + self.operationType + " is not supported."
            err_msg = "Failed Step {}: {}".format("Operation Type Check", err)
            self.update_status_and_exit(err_msg)

        try:
            msg = "Getting Network Function"
            self.logger.info(msg)
            nf = self.get_network_function_by_host(self.ipAddress)
            if not nf:
                try:
                    product = 'charter.resourceTypes.DeviceOnboarder'
                    self.onboard_cmts(product, "MANAGED_SERVICES_ACTIVATION")
                    nf = self.get_network_function_by_host(self.ipAddress)
                    if not nf:
                        self.exit_error("No network function found for hostname {}".format(self.ipAddress))

                    self.await_active_collect_timing([nf['id']])
                except Exception as e:
                    msg = f"Unable to Onboard device {self.ipAddress} due to:{e}"
                    self.log_status_message(msg)
            elif nf['properties']['communicationState'] != "AVAILABLE":
                self.bpo.market.post("/resources/{}/resync".format(nf["id"]))
                self.logger.info("*****************RESYNC*********************")
                try:
                    self.get_resource_await_orchstate(
                        resource_id=nf["id"],
                        orchstates={"active"},
                        timeout=330,
                        poll_interval=10,
                    )
                    self.logger.info("awaiting orchstate active")
                except Exception:
                    self.logger.exception("resource failed to reach active orchstate")
                    network_function_resource = self.bpo.resources.get(nf["id"])
                    self.bpo.resources.patch_observed(
                        self.resource["id"],
                        data={
                            "reason": "Could not onboard the CMTS: {}".format(network_function_resource["reason"]),
                        },
                    )
            self.nf_res_id = nf['providerResourceId']
        except Exception as ex:
            err_msg = "Failed to find network function with reason: {}".format(ex)
            self.update_status_and_exit(err_msg)
        self.log_status_message('Checking Existing Resources')
        self.vecima = self.resource['properties']['device_type'].lower() == 'vecima'
        self.rpd = self.resource['properties']['rpd']
        # Start with abort in case of stuck session from previous error
        self.execute_ra_command_file(self.nf_res_id, 'abort-config.json')
        curr_rpd = self.execute_ra_command_file(self.nf_res_id, 'get-rpd.json', {"rpd": self.rpd}).json()['result']
        # Enable in Prod. RPD must not have any configurations on it to avoid outage before configuring.
        if "not found" not in curr_rpd:  # remove not after testing
            self.update_status_and_exit("Existing RPD found, do not continue")
        self.log_status_message('Adding RPD and Turning Channels Up')
        try:
            self.create_payloads()
            res = self.execute_ra_command_file(self.nf_res_id, 'config-mode.json')
            if 'Entering configuration mode terminal' not in res.json()['result']:
                self.update_status_and_exit('Failed to enter configuration mode')
            self.try_ra_command('add-rpd.json', self.rpd_payload)
            self.try_ra_command('set-channels.json', self.channel_payload)
            self.try_ra_command('turn-channels-up.json', self.channels_up_payload)

            for service in self.service_payloads:  # maybe remove if we dont' receive service packages
                self.try_ra_command('set-service.json', self.service_payloads[service])
            for service in self.service_port_payloads:
                self.try_ra_command('set-service-port.json', self.service_port_payloads[service])
            commit_result = self.execute_ra_command_file(self.nf_res_id, 'commit-write.json').json()['result']
        except Exception as ex:
            err_msg = "Failed: Configuring RPD - Reason: {}".format(ex)
            self.update_status_and_exit(err_msg)
        if "Successfully" not in commit_result:
            self.update_status_and_exit('Config failed to save with reason: {res}'.format(res=commit_result))
        # Looped check for Pebble successfully pulling an IP address. Default 30s

        self.log_status_message('Verifying Configuration')
        try:
            check1 = self.check_channels()
            self.logger.info(f"CHECK1 {check1}")
            check2 = self.check_rpd()
            self.logger.info(f"CHECK2 {check2}")
            check3 = self.check_services()
            self.logger.info(f"CHECK3 {check3}")
            if not check1 or not check2 or not check3:
                self.update_status_and_exit('Configuration not saved correctly')
        except Exception as ex:
            self.update_status_and_exit('Checking final config failed: {}.'.format(ex))
        self.logger.info("configuration saved correctly")
        self.log_status_message('Configuration Saved Correctly')

    def log_status_message(self, msg, parent="rphy_activation"):
        self.status_messages(msg, parent=parent)

    def onboard_cmts(self, product, operation=None):
        rphy_onboarder_details = {
            "label": self.resource['label'] + product,
            "productId": self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)["id"],
            "properties": {
                "device_vendor": "HARMONIC",
                "device_ip": self.ipAddress,
                "device_model": "vCMTS",
                "session_profile": "default",
                "device_already_active": False,
                "operation": operation
            }
        }
        self.bpo.resources.create(self.resource_id, rphy_onboarder_details)

    def check_no_existing_rpd(self, rpd):
        # Enable in Prod. RPD must not have any configurations on it to avoid outage before configuring.
        if "not found" not in rpd:  # remove not after testing
            self.update_status_and_exit("Existing RPD found, do not continue")

    def wait_for_online(self, timer, interval=10):
        online = False
        try:
            for _ in range(timer):
                rpd = self.execute_ra_command_file(self.nf_res_id, 'get-rpd.json', {"rpd": self.rpd}).json()['result'].split('\n')
                if len(rpd) > 2:
                    if rpd[3].split()[4] == 'online':
                        online = True
                        break
                time.sleep(interval)
        except Exception as ex:
            err_msg = "RPD online check failed: {}".format(ex)
            self.update_status_and_exit(err_msg)
        if not online:
            self.update_status_and_exit('Timeout while waiting for rpd to come back online after restart')

    def create_payloads(self):
        # Get primary clock and gateway ip from device
        try:
            self.primary_clock_ip = self.execute_ra_command_file(self.nf_res_id, 'get-primary-clock-ip.json').json()['result'].split()[4]
            self.gateway_ip = self.execute_ra_command_file(self.nf_res_id, 'get-gateway-ip.json').json()['result'].split()[3].split('/')[0]
        except Exception as ex:
            self.update_status_and_exit("Failed to get primary clock and gateway ip with reason:{}".format(ex))
        if len(self.primary_clock_ip.split('.')) != 4 or len(self.gateway_ip.split('.')) != 4:
            self.update_status_and_exit('Failed to get primary/gateway ip')

        self.rpd_payload = {
            "rpd": self.rpd,
            "mac_address": self.resource['properties']['mac_address'],
            "description": self.resource['properties']['rpd_des'],
        }

        if self.vecima:
            rpd_light_level = 13.4
            self.rpd_payload["primary_ip"] = self.primary_clock_ip
            self.rpd_payload["gateway_ip"] = self.gateway_ip
        else:
            rpd_light_level = 38.0
            self.rpd_payload["async"] = True

        self.channel_payload = {
            "rpd": self.rpd,
            "rpd_light_level": rpd_light_level,
            "signal_type": self.resource['properties']['signal_type']
        }
        # Create payload for add-rpd.json command

        self.service_payloads, self.svc_group = {}, {}
        self.service_port_payloads = {}
        self.services_data = self.properties['service_group_data']
        for data in self.services_data:
            self.svc_group[data.pop("name")] = data

        for service in self.svc_group:
            s = self.execute_ra_command_file(self.nf_res_id, 'get-service.json', {"group_name": service})
            if "element does not exist" in s.json()['result']:
                payload = {
                    "group_name": service,
                    "dst_address": self.svc_group[service]['dst_address'],
                    "src_address": self.svc_group[service]['src_address'],
                    "port": self.svc_group[service]["session_port"],
                    "down_channels": self.svc_group[service]['channels'],
                    'ds_rf_port': self.rpd + '/0'
                }
                self.service_payloads[service] = payload
            else:
                payload = {
                    "group_name": service,
                    'ds_rf_port': self.rpd + '/0'
                }
                self.service_port_payloads[service] = payload

        self.channels = set(self.resource['properties']['channels'])
        channels_up = ""
        for channel in self.channels:
            channels_up += "down-channel {channel} \n admin-state up \n ".format(channel=channel)
        self.channels_up_payload = {
            "rpd": self.rpd,
            "channels": channels_up
        }

    def get_private_data(self):
        defaults = self.bpo.resources.get(
            self.get_resources_by_type_and_label(
                "charter.resourceTypes.rphy_fw", "default", no_fail=True)[0]["id"], obfuscate=False)
        return defaults["properties"]

    def check_rpd(self):
        status = False
        rpd_conf = self.execute_ra_command_file(self.nf_res_id, 'show-run-rpd.json', {"rpd": self.rpd}).json()['result'].split('\n')
        self.logger.info(f"MAC_ADDRESS_PAUL: {self.rpd_payload}, \n RPD_RESULT: {rpd_conf}")
        mac = self.rpd_payload.get('mac_address').replace(":", "")
        reformatted_mac = mac[:4] + "." + mac[4:8] + "." + mac[8:]
        if "mac-address" in rpd_conf[1]:
            if rpd_conf[1].strip().split()[-1] == reformatted_mac:
                status = True
        if "description" in rpd_conf[2]:
            if rpd_conf[2].strip().split()[-1] == self.rpd_payload['description']:
                status = True
        #  removing ptp check for now
        # ptp_result = self.execute_ra_command_file(self.nf_res_id, 'get-rpd-ptp.json', {"rpd": self.rpd}).json()['result'].split('\n')
        # ip_line = ptp_result[1].split()
        # self.logger.info(f"IP_LINE: {ip_line}")
        # if ip_line[3] != self.rpd_payload.get('primary_ip') or ip_line[5] != self.rpd_payload.get('gateway_ip'):
        #     return False
        return status

    def check_channels(self):
        channel_result = self.execute_ra_command_file(self.nf_res_id, 'get-channels.json', {"rpd": self.rpd}).json()['result'].split('\n')
        if float(channel_result[2].split()[1]) != self.channel_payload.get('rpd_light_level'):
            self.update_status_and_exit('rpd light level not saved.')
        if channel_result[-5].split()[1] != self.channel_payload.get('signal_type'):
            self.update_status_and_exit('signal type not saved')
        for i in range(len(channel_result)):
            if 'down-channel' in channel_result[i] and int(channel_result[i].split()[1]) in self.channels \
                    and channel_result[i + 1].split()[1] != 'up':
                self.update_status_and_exit('Some channels not turned up correctly.')
        return True

    def try_ra_command(self, config_file, payload=None):
        res = self.execute_ra_command_file(self.nf_res_id, config_file, payload).json()['result']
        if res:
            replace = ['-', '^', '\n', '\r']
            for char in replace:
                res = res.replace(char, '')
            self.update_status_and_exit("Failed step: {step} with reason: {res}".format(step=config_file.split('.')[0], res=res))

    def check_services(self):
        self.logger.info(f"SVC_GROUP: {self.svc_group}")
        for service in self.svc_group:
            s = self.execute_ra_command_file(self.nf_res_id, 'get-service.json', {"group_name": service}).json()['result'].split()
            if (self.rpd + "/0") not in s:
                self.update_status_and_exit('Service {service} not saved correctly.'.format(service=service))
        return True

    def update_status_and_exit(self, msg):
        """Update status_message and exit_error message.

        PARAMETERS
        ----------
            msg : str
                Message to deliver
        """
        self.bpo.resources.patch_observed(self.resource['id'], {"properties": {"activation_error": msg}})
        self.logger.info(f"UPDATE WAS CALLED. {self.resource['id']} , msg")
        self.exit_error(msg)


class Terminate(CommonPlan):
    pass
