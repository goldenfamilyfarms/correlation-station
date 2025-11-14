import time
from datetime import datetime
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.deviceconfiguration.cli_cutthrough import CliCutthrough


class Activate(CommonPlan, CliCutthrough):
    """
    Checking Operation Type
    Onboard device
    Check Firmware of given RPD
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
        msg = 'Checking Operation Type'
        self.status_messages(msg, parent="rphy_fw_upgrade")
        self.vendor = self.resource['properties']['vendor'].lower()
        if self.operationType != "New":
            err = "Operation " + self.operationType + " is not supported."
            err_msg = "Failed Step {}: {}".format(msg, err)
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
                    self.status_messages("Unable to Onboard device {} due to:{}".format(self.ipAddress, e))
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
        msg = 'Checking Existing Resources'
        self.status_messages(msg, parent="rphy_fw_upgrade")
        self.vecima = self.resource['properties']['vendor'].lower() == 'vecima'
        self.rpd = self.resource['properties']['rpd']
        # Start with abort in case of stuck session from previous error
        self.execute_ra_command_file(self.nf_res_id, 'abort-config.json')
        curr_rpd = self.execute_ra_command_file(self.nf_res_id, 'get-rpd.json', {"rpd": self.rpd}).json()['result']
        # Enable in Prod. RPD must not have any configurations on it to avoid outage before configuring.
        if "not found" in curr_rpd:  # remove not after testing
            self.update_status_and_exit("RPD Not online, cannot proceed with upgrade")

        msg = 'Checking RPD for Firmware'
        self.status_messages(msg, parent="rphy_fw_upgrade")
        try:
            self.fw_updated = False
            self.check_firmware()
            if self.fw_updated:
                msg = 'FW Upgrade complete. Waiting 8 minutes for it to reboot and 15 for it to return Online'
                self.status_messages(msg, parent="rphy_fw_upgrade")
                time.sleep(480)
                online = False
                online = self.wait_for_online(900, 20)
                if not online:
                    self.update_status_and_exit('Timeout while waiting for rpd to come back online after restart')

                self.logger.info("Upgrade completed saved correctly")
                msg = 'Upgrade completed saved correctly"'
                self.status_messages(msg, parent="rphy_fw_upgrade")
            else:
                msg = "Installation is already in progress. nothing to do."
                self.status_messages(msg, parent="rphy_fw_upgrade")
        except Exception as ex:
            err_msg = "Failed: {} - Reason: {}".format(msg, ex)
            self.update_status_and_exit(ex)

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
        return online

    def check_firmware(self):
        res = self.execute_ra_command_file(self.nf_res_id, "get-rpd.json", {"rpd": self.rpd}).json()['result']
        fw = res.split('\n')[3].split()[3]
        self.logger.info(f"FW IS: {fw}")
        approved_firmware = self.get_private_data()["firmware"]["vecima"] if self.vecima else self.get_private_data()["firmware"]["harmonic"]
        if fw not in approved_firmware:
            self.update_firmware(approved_firmware)

    def update_firmware(self, approved_firmware):
        firmware_url = f"http://50.84.225.95/files/tftp/firmware/{self.vendor}/automation/{approved_firmware}"
        fw_update = self.execute_ra_command_file(self.nf_res_id, "update-firmware.json", {"rpd": self.rpd, "firmware_url": firmware_url}).json()["result"]
        start_timer = datetime.now()
        if "installation in progress" in fw_update:
            download_complete = False
            try:
                for i in range(0, 900, 20):
                    response = self.execute_ra_command_file(self.nf_res_id, 'get-upgrade-status.json', {"rpd": self.rpd}).json()['result']
                    if "upgrade successful" in response.lower():
                        self.fw_updated = True
                        download_complete = True
                        duration = (datetime.now() - start_timer).seconds
                        self.logger.info(f"\nFirmware download completed in {duration} seconds, waiting 8 minutes for reset to finish\n")
                        break
                    time.sleep(20)
                if download_complete == False:
                    msg = f"RPD Upgrade failed or exceeded 15 minutes. Last Status:{response}"
                    self.update_status_and_exit(msg)
            except Exception as ex:
                err_msg = "RPD upgrade check failed: {}".format(ex)
                self.update_status_and_exit(err_msg)
        elif "installation already in progress" in fw_update:
            self.logger.info("Installation already in progress. Nothing to do")

    def get_private_data(self):
        defaults = self.bpo.resources.get(
            self.get_resources_by_type_and_label(
                "charter.resourceTypes.rphy_fw", "default", no_fail=True)[0]["id"], obfuscate=False)
        return defaults["properties"]

    def update_status_and_exit(self, msg):
        """Update status_message and exit_error message.

        PARAMETERS
        ----------
            msg : str
                Message to deliver
        """
        self.bpo.resources.patch_observed(self.resource['id'], {"properties": {"rphy_fw_upgrade": msg}})
        self.logger.info(f"UPDATE WAS CALLED. {self.resource['id']} , msg")
        self.exit_error(msg)


class Terminate(CommonPlan):
    pass
