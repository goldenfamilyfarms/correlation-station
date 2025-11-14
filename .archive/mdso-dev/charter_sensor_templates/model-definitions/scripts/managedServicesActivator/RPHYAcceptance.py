from scripts.common_plan import CommonPlan
import sys
sys.path.append('model-definitions')


class Activate(CommonPlan):
    """
    Payload example =
    {
        'cid': CID,
        'rpd': x:0,
        'cmtsipAddress': IP,
        'chanel_numbers' : [list of ON channels to validate]
        'service_groups': [list of service groups to validate]
    }
    """
    SUPPORTED_MODELS = [
        "FSP 150-XG116PRO",
        "FSP 150-XG116PROH",
        "FSP 150-XG118PRO (SH)",
        "FSP 150CC-GE114/114S",
        "FSP 150-GE114PRO-C",
        "ETX-220A",
        "ETX203AX/2SFP/2UTP2SFP",
        "ETX-203AX/GE30/2SFP/4UTP",
        "RAD ETX-2I-10G/4SFPP/4SFP4UTP",
        "ETX-2I-10G/4SFPP/4SFP4UTP",
        "ETX-2I-10G/4SFPP/24SFP",
        "ETX-2I-10G-B/8.5/8SFPP",
        "ETX-2I-10G-B/19/8SFPP",
    ]

    def process(self):
        """
        RPHY Acceptance and Compliance Steps
        a- RPD is online and Locked.
        b- Check Channel lineups. Local + Regional are required. verify/validate usin step 3
        c- check Min/Max Buffer levels (more than 0, excel step 2.12)
        d- check desription. Check locking time > 60 minutes. Section to check MAC under "notes" but probably not do that.
        """
        self.cmtsIpAddress = self.resource['properties']['cmtsipAddress']
        self.cid = self.properties["cid"]
        self.rpd = self.properties["rpd"]
        self.channels = self.properties['channel_numbers']
        self.service_groups = self.properties['service_groups']
        flagged_issues = []
        try:
            msg = "Getting Network Function"
            self.logger.info(msg)
            nf = self.get_network_function_by_host(self.cmtsIpAddress)
            if not nf:
                try:
                    product = 'charter.resourceTypes.DeviceOnboarder'
                    self.onboard_device(product, self.cmtsIpAddress, "HARMONIC", "vCMTS", "MANAGED_SERVICES_ACTIVATION")
                    nf = self.get_network_function_by_host(self.cmtsIpAddress)
                    if not nf:
                        self.exit_error("No network function found for hostname {}".format(self.cmtsIpAddress))

                    self.await_active_collect_timing([nf['id']])
                except Exception as e:
                    self.status_messages("Unable to Onboard device {} due to:{}".format(self.cmtsIpAddress, e))
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
        except Exception as e:
            self.status_messages(f"Other issue while onboarding: {e}", parent="rphy_acceptance_status")

        """
        Confirm Channel Online and Clock shows Locked
        """
        # Confirm channel is online and locked
        self.status_messages("Checking RPD status and Clock", parent="rphy_acceptance_status")
        # Abort to ensure it starts at executive mode
        self.execute_ra_command_file(self.nf_res_id, 'abort-config.json', {'rpd': self.rpd})
        rpd_result = self.execute_ra_command_file(self.nf_res_id, 'get-rpd.json', {'rpd': self.rpd}).json()['result']
        if "not found" in rpd_result:
            self.update_status_and_exit("RPD not online, exiting")
        else:
            status = rpd_result.split('\n')[3].split()[4]
            clock = rpd_result.split('\n')[3].split()[5]
            if status != 'online' or clock != 'locked':
                self.update_status_and_exit(f"RPD not online or locked. \n status: {status} , clock: {clock} ")

        self.status_messages('Checking Channel Status', parent="rphy_acceptance_status")
        channel_result = self.execute_ra_command_file(self.nf_res_id, 'get-rpd-video-channel.json', {'rpd': self.rpd}).json()['result']
        if self.validate_response(channel_result):
            self.logger.info(f"Execute get-rpd-video-channel.json result - {channel_result}")
            # Parse result and remove blanks
            channel_list = list(filter(None, channel_result.split("\r\r\n")[3::]))
            # Grab only all configured channels and groups
            svcs_list = []
            for sg in channel_list:
                svcs_list.append(
                    {
                        'Service_group': sg.split()[1],
                        'RF_Channel': sg.split()[0].split('/')[-1],
                        'Status': sg.split()[2]
                    }
                )
            self.logger.info(f"CONFIGURED SVCS: {svcs_list}")
            # Find Channels that are off when they should be on
            down_channels, free_channels = [], []
            for item in svcs_list:
                if item['Status'].lower() != 'up':
                    if item['RF_Channel'] in self.channels and item["Service_group"] in self.service_groups:
                        down_channels.append(item['RF_Channel'])
                else:
                    if item['RF_Channel'] not in self.channels:
                        free_channels.append(item['RF_Channel'])

            channels = [channel.split()[0].split("/")[-1] for channel in channel_list]
            exp_channels = ['67', '68']
            missing_channels = [c for c in self.channels if str(c) not in channels and str(c) not in exp_channels]

            # Find missing service groups
            self.logger.info(f"Execute get-channel-service-groups.json result - {channel_result}")
            channel_sg_result = self.execute_ra_command_file(self.nf_res_id, 'get-channel-service-groups.json', {'rpd': self.rpd}).json()['result']
            channel_sg_result = list(filter(None, channel_sg_result.split('\r\n')))
            ds_rf_sgs = [x.split('cable service-group')[1].strip() for x in channel_sg_result]

            missing_groups = [g for g in self.service_groups if g not in ds_rf_sgs]

            if missing_groups:
                msg = f"Missing Service Groups Found: {missing_groups}"
                flagged_issues.append(msg)
            if down_channels:
                msg = f"Channels down when they should be up: {down_channels}"
                flagged_issues.append(msg)
            if missing_channels:
                msg = f"Channels ordered but not configured: {missing_channels}"
                flagged_issues.append(msg)
            if free_channels:
                msg = f"Channels on customer didn't order: {free_channels}"
                flagged_issues.append(msg)
        else:
            flagged_issues.append('No Channel Status Found')

        """
        Confirm min and max buffer levels
        """
        self.status_messages('Checking Buffer Levels', parent="rphy_acceptance_status")
        buffer_response = self.execute_ra_command_file(self.nf_res_id, 'get-channel-counters.json', {'rpd': self.rpd}).json()['result']
        if self.validate_response(buffer_response):
            buffer_list = list(filter(None, buffer_response.split("\r\r\n")))[1:-2]
            self.logger.info(f"Execute get-channel-counters.json result - {buffer_list}")
            flagged_channels = []
            for channel in buffer_list:
                if channel.split()[-1] == 0 or channel.split()[-2] == 0:
                    flagged_channels.append(
                        {
                            'Channel': channel.split()[0],
                            'Min Buffer': channel.split()[-2],
                            'Max Buffer': channel.split()[-1]
                        }
                    )
            if flagged_channels:
                msg = f"0% Buffers found: {str(flagged_channels)}"
                self.logger.info(f"Buffer issues found: {str(flagged_channels)}")
                flagged_issues.append(msg)
        else:
            flagged_issues.append('No Channel Buffers Found')

        """
        Validate Description, GCP Online Status and Locking Time > 60 min
        """
        self.status_messages('Checking RPD Description, Status and Locking Time', parent="rphy_acceptance_status")
        verbose_response = self.execute_ra_command_file(self.nf_res_id, 'get-rpd-verbose.json', {'rpd': self.rpd}).json()['result']
        self.logger.info(f"Execute get-rpd-verbose.json result - {verbose_response}")
        verbose_response = list(filter(None, verbose_response.split('\r\r\n')))
        locking_time = verbose_response[-1].split()[-1]
        gcp_status = verbose_response[6].split()[-1].lower()
        description = verbose_response[3].split(" : ")[1]

        if 'h' not in locking_time:
            flagged_issues.append(f"Locking time < 60m. Time: {locking_time}")
        if self.cid not in description:
            flagged_issues.append("CID not in description")
        if gcp_status != "online":
            flagged_issues.append("GCP Connection Status not online)")

        # Updating final message
        if flagged_issues:
            self.logger.info(f"Flagged Issues found, patching the following: {flagged_issues}")
            self.bpo.resources.patch_observed(
                self.resource['id'], {"properties": {"report": flagged_issues}}
            )

        """
        Attempt Log into CPE.
        """
        self.status_messages('Attempting to log into CPE', parent="rphy_acceptance_status")
        self.cpeIpAddress = self.resource['properties']['CPE']['ipAddress']
        self.cpeVendor = self.resource['properties']['CPE']['vendor']
        self.cpeModel = self.resource['properties']['CPE']['model']

        cpe_fail = False
        if self.cpeVendor.upper() in ["RAD", "ADVA"] and self.cpeModel in self.SUPPORTED_MODELS:
            try:
                msg = "Getting Network Function"
                self.logger.info(msg)
                nf = self.get_network_function_by_host(self.cpeIpAddress)
                if not nf:
                    try:
                        product = 'charter.resourceTypes.DeviceOnboarder'
                        self.onboard_device(product, self.cpeIpAddress, self.cpeVendor, self.cpeModel, "NETWORK_SERVICE_ACTIVATION")
                        nf = self.get_network_function_by_host(self.cpeIpAddress)
                        self.await_active_collect_timing([nf['id']])
                    except Exception as e:
                        self.status_messages("Unable to Onboard device {} due to:{}".format(self.cpeIpAddress, e), parent="rphy_acceptance_status")
                        cpe_fail = True
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
                                "reason": "Could not access CPE: {}".format(network_function_resource["reason"]),
                            },
                        )
                if cpe_fail == False:
                    # Poll NF after onboarding or
                    nf = self.get_network_function_by_host(self.cpeIpAddress)
                    if nf["properties"]["communicationState"] == "AVAILABLE":
                        self.logger.info("Login to CPE successful ")
                    else:
                        self.logger.info(f"Error Accessing CPE with vendor: {self.cpeVendor} ip: {self.cpeIpAddress}")
                        flagged_issues.append("Could not log into CPE")
                        self.bpo.resources.patch_observed(
                            self.resource['id'], {"properties": {"report": flagged_issues}}
                        )

                    self.status_messages('Attempting to log into CPE', parent="rphy_acceptance_status")
            except Exception as e:
                self.status_messages(f"Other issue while onboarding: {e}")
        else:
            self.status_messages(f'Unsupported CPE, skipping CPE check. Model: {self.cpeModel}, Vendor: {self.cpeVendor}', parent="rphy_acceptance_status")
        self.status_messages('Acceptance complete', parent="rphy_acceptance_status")

    def validate_response(self, response, exit=False):
        if "No Data Found" in response:
            return False
        else:
            return True

    def onboard_device(self, product, ipAddress, vendor, model, operation=None):
        device_onboarder_details = {
            "label": self.resource['label'] + product,
            "productId": self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)["id"],
            "properties": {
                "device_vendor": vendor,
                "device_ip": ipAddress,
                "device_model": model,
                "session_profile": "sensor",
                "device_already_active": False,
                "operation": operation
            }
        }
        a = self.bpo.resources.create(self.resource_id, device_onboarder_details)
        self.logger.info(f"AAAAA \n : {a}")

    def update_status_and_exit(self, msg):
        """Update status_message and exit_error message.

        PARAMETERS
        ----------
            msg : str
                Message to deliver
        """
        self.bpo.resources.patch_observed(self.resource['id'], {"properties": {"rphy_acceptance_status": msg}})
        self.logger.info(f"UPDATE WAS CALLED. {self.resource['id']} , msg")
        self.exit_error(msg)


class Terminate(CommonPlan):
    pass
