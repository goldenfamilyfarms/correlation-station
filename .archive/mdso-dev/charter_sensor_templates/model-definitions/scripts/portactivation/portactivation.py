import json
import time
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
import datetime
import calendar
import re
from ra_plugins.ra_cutthrough import RaCutThrough


class Activate(CommonPlan):
    """
    Get the Network function/ Device from BPO
    If the device is in market:
        Find the given TPE-
        If the TPE resource is present:
            return status as- "ready to configure (with device id and port id)"
        else:
            return status as - "Port isn't present on the device. Please check the device (with device id)"
    else:
        return status as - "Device not present (with device id)"

    If expiry time is set to 0 this means the port will remain up and a resource scheduler will still be invoked
    resource removal time is the time that will be used for the resource scheduler.
    """

    def process(self):
        # GET the resource its properties from the market as only the resource_id is passed i.
        resource_id = self.params["resourceId"]
        resource = self.bpo.resources.get(resource_id)
        properties = resource["properties"]
        expiry_time = properties["terminationTime"]
        resource_removal_time = 30

        # Pull out relative properties & set defaults
        device_name = properties["deviceName"]
        port_name = properties["portname"].lower()

        port_activation_resources = self.check_port_activation_resources(device_name, port_name)
        status = port_activation_resources["status"]
        self.logger.info(
            "Existing port activation resource for %s_%s (if any): %s"
            % (device_name, port_name, port_activation_resources)
        )

        # resync network function if its found
        self.resync_network_function(device_name)

        if "already available" in status:
            output = {"status": status}
            if expiry_time == 0:
                # Create Resource Scheduler Instance
                self.create_scheduler_resource(resource_id, resource, resource_removal_time)
            else:
                # Create Resource Scheduler Instance
                self.create_scheduler_resource(resource_id, resource, expiry_time)
            self.logger.info("Output: " + json.dumps(output))
            return output

        # get TPE resource
        tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
        self.logger.info("First TPE under Activate: %s" % tpe)

        # getting the status and check the status value
        if "status" in tpe:
            status = tpe["status"]

            # If the status is "Device not present " then add/onboard the device
            if "Device not present" in status:
                device_onboard_result = self.addDevice(resource_id)
                tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
                if "Device deployed successfully" in device_onboard_result:
                    self.logger.info("TPE under successful deploy in Activate: %s" % tpe)
                    if "properties" in tpe:
                        status = "Ready to configure"
                    else:
                        status = "Port not present on the device - PA Onboard"
                elif "Device deployment was unsuccessful" in device_onboard_result:
                    self.logger.info("TPE under unsuccessful onboarding in Activate: %s" % tpe)
                    status = "Device onboarding was unsuccessful"
        else:
            status = "Ready to configure"

        if expiry_time == 0:
            # Create Resource Scheduler Instance
            self.create_scheduler_resource(resource_id, resource, resource_removal_time)
        else:
            # Create Resource Scheduler Instance
            self.create_scheduler_resource(resource_id, resource, expiry_time)

        output = {"status": status}
        self.logger.info("Output: " + json.dumps(output))
        return output

    def create_scheduler_resource(self, resource_id, resource, expiry_time):
        # Create Resource Scheduler Instance
        current_time = datetime.datetime.now()
        termination_time = current_time + datetime.timedelta(minutes=expiry_time)
        scheduler_product = self.get_built_in_product(self.BUILT_IN_RESOURCE_SCHEDULER_TYPE)
        scheduler_label = resource["label"] + ".terminate"
        scheduler_object = {
            "label": scheduler_label,
            "productId": scheduler_product["id"],
            "properties": {
                "termination_resource_id": resource_id,
                "termination_time": {
                    "year": termination_time.year,
                    "month": calendar.month_name[termination_time.month][0:3],
                    "day": termination_time.day,
                    "hour": termination_time.hour,
                    "minute": termination_time.minute,
                },
            },
        }
        self.bpo.resources.create(self.params["resourceId"], scheduler_object)

    # ADD DEVICE: run connectivity check, on-board the device and check for comm state
    def addDevice(self, resource_id):
        resource = self.bpo.resources.get(resource_id)
        properties = resource["properties"]
        device_name = properties["deviceName"]
        created_onboarded_res = []
        devices_deployed = {}
        vendor_name = properties["vendor"].upper()
        onboard_product = self.get_built_in_product(self.BUILT_IN_DEVICE_ONBOARDER_TYPE)

        label = device_name + ".device_onboarder"
        devices_deployed[device_name] = False
        onboard_details = {
            "label": label,
            "productId": onboard_product["id"],
            "properties": {
                "device_ip": device_name,
                "device_name": device_name.split(".")[0],
                "device_vendor": vendor_name,
                "device_already_active": True,
            },
        }
        self.logger.debug("On-boarding device: " + device_name)
        device_res = self.add("Resource", "/resources", onboard_details)
        created_onboarded_res.append(device_res)
        # NOW WAIT FOR THEM ALL TO FINISH
        for resp in created_onboarded_res:
            resp_id = resp["id"]
            # Wait for relationships to be built
            try:
                self.await_resource_states_collect_timing("Waiting for " + resp_id, resp_id, interval=5, tmax=300)
                devices_deployed[resp["properties"]["device_ip"]] = True
            except Exception:
                try:
                    r = self.bpo.resources.get(resp_id)
                    if r is not None:
                        devices_deployed[resp["properties"]["device_ip"]] = r["orchState"] == "active"
                except Exception as ex:
                    devices_deployed[resp["properties"]["device_ip"]] = True
                    self.logger.debug("On-boarder %s already on-boarding so no need to check." % resp_id)
                    self.logger.debug("Exception: " + str(ex))

                # NO NEED TO KEEP THE ONBOARDER AROUND, ITS JOB IS DONE
                self.delete_resource(resp_id)

        self.logger.debug("Devices Deployed: " + json.dumps(devices_deployed, indent=4))
        output = {"status": "Device deployment was unsuccessful"}

        for deployment_success in devices_deployed.values():
            # If the device attempting to be deployed is successful, it will break the loop
            if deployment_success is True:
                output = {"status": "Device deployed successfully"}
                break

        self.logger.info("Output: " + json.dumps(output))

        return output


class PortActivationOperation(CommonPlan):
    def check_port_state(self, resource_id, state, interval, tmax):
        """check weather the given port state has been change on the device,
        Wait till the port state changed on the device
        :param resource_id: resource ID
        :param state: port state
        :interval: interval to send get request
        :tmax: maximun time for wait
        :type resource_id: str
        :type state: str
        :type interval: int
        :type tmax:int
        """
        t0 = time.time()
        offset = 2.0
        time.sleep(offset)
        resource = self.bpo.resources.get(resource_id)
        properties = resource["properties"]
        device_name = properties["deviceName"]
        port_name = properties["portname"].lower()
        adminstate = ""

        device_port = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
        self.logger.info("Initial TPE under PortActivationOperation: %s" % device_port)
        self.bpo.market.post("/resources/{}/resync".format(device_port["id"]))
        self.logger.info("***************************ResyncNF********************************")
        time.sleep(5)

        while True:
            # get TPE resource
            tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
            self.logger.info("TPE under check_port_state: %s" % tpe)

            # Reaching to network function for port status
            try:
                get_admin_state = self.execute_ra_command_file(
                    tpe["properties"]["device"], "get-interface.json", parameters={"name": port_name}, headers=None
                )
            except Exception as e:
                raise Exception(
                    "An error occurred while attempting to get the admin state.  Details: %s  |  TPE: %s" % (e, tpe)
                )

            self.logger.info("admin_state data from executed RA command: %s" % get_admin_state.text)
            self.logger.info("**********GET ADMIN STATUS **************** ")
            get_admin_state = get_admin_state.json()["result"]
            self.logger.info("Returned interface results: %s" % get_admin_state)
            adminstate = get_admin_state["interface-information"]["physical-interface"]["admin-status"]["#text"]

            self.logger.info("Reqdstate: %s" % (state))
            self.logger.info("Admin State: %s" % (adminstate))
            if adminstate == state:
                break

            remaining = (t0 + tmax) - time.time()
            if remaining < 0:
                raise Exception("Timed out while waiting for port adminstate change to be in %s" % (state))
            self.logger.info(
                "Waiting %s seconds for port adminstate change to be in state %s (remaining time %s)"
                % (interval, state, remaining)
            )
            time.sleep(interval)
        self.logger.info("Port adminstate successfully changed to %s" % (state))

    def deactivate_port(self, tpe, port_name, reqdstate, properties, resource_id):
        # pull full port config
        eligibility = properties["deactivate_eligible"]
        if tpe.get("properties"):
            get_deactivate_status = self.execute_ra_command_file(
                tpe["properties"]["device"], "get-interface-config.json", parameters={"name": port_name}, headers=None
            )
        elif tpe.get("status"):
            if "is not MDSO reachable" in tpe.get("status"):
                raise Exception(
                    "Device is not MDSO reachable, preventing the TPE from being returned.  |  "
                    "Device information: %s" % tpe
                )
            else:
                raise Exception(
                    "TPE is unable to return the proper information to turn %s to %s state.  |  "
                    "TPE: %s" % (port_name, reqdstate, tpe)
                )
        else:
            raise Exception(
                "TPE does not contain the necessary information required to run the get-interface-config "
                "ra command file.  |  TPE: %s  |  Device properties: %s" % (tpe, properties)
            )

        get_deactivate_status = get_deactivate_status.json()["result"]
        # if statement to check for reqdstate and cutthrough to apply 'deactivate interface' which turns the light on
        if eligibility is not True:
            properties["status"] = "Port not eligible for Activation"
            self.bpo.resources.patch(resource_id, {"properties": properties})
            raise Exception("Port not eligible for Activation")
        if reqdstate == "up":
            properties["wasPortActivated"] = True
            self.bpo.resources.patch(resource_id, {"properties": properties})
            self.execute_ra_command_file(
                tpe["properties"]["device"],
                "deactivate-interface.json",
                parameters={"param": "enable", "interface": port_name, "commit": True},
                headers=None,
            )
            time.sleep(5)
            self.logger.info("******************ENABLING PORT WITH DEACTIVATE******************")
        else:
            # else cutthrough to apply 'activate interface' which enables the existing config i.e. DISABLEIF
            self.execute_ra_command_file(
                tpe["properties"]["device"],
                "activate-interface.json",
                parameters={"param": "enable", "interface": port_name, "commit": True},
                headers=None,
            )
            time.sleep(5)
            self.logger.info("******************DISABLING PORT WITH ACTIVATE******************")

    def get_interface_optic_levels(self, tpe, port_name, admin_state, retries=6):
        """
        Checking Light levels on the interface. If the admin state of the port is up,
        it will try multiple times to give the device the opportunirty to update the value.
        Some Junipers are slow to display light levels.
        """
        interface_optic_levels = self.execute_ra_command_file(
            tpe["properties"]["device"], "show-interface-dom.json", parameters={"name": port_name}, headers=None
        )
        optic_levels = interface_optic_levels.json()["result"]
        tx_optic_levels = optic_levels["tx-signal-avg-optical-power"]

        if self.port_is_up_with_no_light_levels(admin_state, tx_optic_levels):
            while retries:
                retries -= 1
                time.sleep(10)
                interface_optic_levels = self.get_interface_optic_levels(tpe, port_name, admin_state, 0)
                optic_levels = interface_optic_levels.json()["result"]
                tx_optic_levels = optic_levels["tx-signal-avg-optical-power"]
                if not self.port_is_up_with_no_light_levels(admin_state, tx_optic_levels):
                    break

        return interface_optic_levels

    def port_is_up_with_no_light_levels(self, admin_state, tx_optic_levels):
        return admin_state == "up" and tx_optic_levels == "- InfdBm"


class Terminate(PortActivationOperation):
    """
    Get on this resource- check  the flag wasPortActivated

    If wasPortActivated is True:
        do a set on the given TPE i.e set adminState of the TPE resource to disable

    If expiry time is set to 0 the resource will still get deleted, but the port will remain up
    """

    def process(self):
        resource_id = self.params["resourceId"]
        resource = self.bpo.resources.get(resource_id)
        properties = resource["properties"]
        device_name = properties["deviceName"]
        port_name = properties["portname"].lower()
        tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
        self.logger.info("Initial TPE under Terminate: %s" % tpe)
        reqdstate = "down"
        expiry_time = properties["terminationTime"]
        if expiry_time != 0 and "wasPortActivated" in properties:
            self.deactivate_port(tpe, port_name, reqdstate, properties, resource_id)
        else:
            resource_id = self.params["resourceId"]
            resource = self.bpo.resources.get(resource_id)
            properties = resource["properties"]
            device_name = properties["deviceName"]
            port_name = properties["portname"].lower()

            self.logger.info("====== RESOURCE (in Class Terminate): =====")
            self.logger.info(resource)

            # resync network function
            self.resync_network_function(device_name)

            # Get device's network function
            device = self.get_network_function_by_host_or_ip(device_name, device_name)
            self.logger.info("====== DEVICE (in Class Terminate): =====")
            self.logger.info("Device: %s" % device)

            # Check if device is an MX converted to EDNA, set disabling apply group
            is_edna = False
            if device["properties"]["deviceVersion"][:9].upper() == "JUNIPERMX":
                is_edna = self.check_is_edna(device["providerResourceId"])
            disablr = "TP_DISABLEIF" if is_edna else "DISABLEIF"
            self.logger.info("Is this an MX that has convered to EDNA? %s" % is_edna)
            self.logger.info("The apply-group for disabling interfaces on this device is: %s" % disablr)

            # get TPE resource
            tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
            self.logger.info("Second TPE under Terminate: %s" % tpe)

            if "properties" in tpe:
                # get the existing adminstate of the port
                # admin_state = tpe["properties"]["data"]["attributes"]["layerTerminations"][0]["adminState"]

                if "wasPortActivated" in properties and properties["wasPortActivated"] is True:
                    apply_groups = tpe["properties"]["data"]["attributes"]["additionalAttributes"]["apply-groups"]
                    if disablr not in apply_groups:
                        if (
                            properties["terminationTime"] != 0
                        ):  # If resource created with 0 termination time - it remains up permanently
                            apply_groups.append(disablr)
                    tpe["properties"]["data"]["attributes"]["additionalAttributes"]["apply-groups"] = apply_groups

                    # choice of new or old to remove from port
                    dummy_descriptions = ["CPE:PEND - Light Test:::", "PEND - Light Test:CPE:::"]
                    self.logger.info("BEFORE TPE resource: %s" % tpe)
                    self.logger.info(
                        "===BEFORE====== tpe-props-data-attrs-ulabl: %s"
                        % tpe["properties"]["data"]["attributes"]["userLabel"]
                    )

                    if tpe["properties"]["data"]["attributes"]["userLabel"] in dummy_descriptions:
                        tpe["properties"]["data"]["attributes"]["userLabel"] = ""

                    # if tpe['properties']['data']['attributes']['userLabel'] == "CPE:PEND - Light Test:::":
                    # tpe['properties']['data']['attributes']['userLabel'] = ""
                    # patch TPE resource
                    is_discovered = tpe["discovered"]

                    if is_discovered is True:
                        self.bpo.resources.patch(tpe["id"], {"discovered": False})

                    self.bpo.resources.patch(tpe["id"], {"properties": tpe["properties"]})
                    self.logger.info("AFTER TPE resource: %s" % tpe)
                    self.logger.info(
                        "===AFTER====== tpe-props-data-attrs-ulabl: %s"
                        % tpe["properties"]["data"]["attributes"]["userLabel"]
                    )

                    if is_discovered is False:
                        self.bpo.resources.patch(tpe["id"], {"discovered": True})

                    if properties["terminationTime"] != 0:
                        self.check_port_state(resource_id, state="down", interval=5, tmax=300)
                    else:
                        self.check_port_state(resource_id, state="up", interval=5, tmax=300)

                    output = {"status": "Successfully triggered patch operation for port status"}
                    self.logger.info("Output: " + json.dumps(output))
                    return output
            else:
                output = {"status": "Port not present on the device - PA Terminate"}
                return output


class GetPortStatus(PortActivationOperation):
    """
    Get on this resource- find the status

    If the status is "ready to configure":
        do a get on this TPE and get the operationalState and adminState of the TPE resource
    else:
        return - "port not present based on the status"
    """

    def process(self):
        resource_id = self.params["resourceId"]
        resource = self.bpo.resources.get(resource_id)
        properties = resource["properties"]
        device_name = properties["deviceName"]
        port_name = properties["portname"].lower()
        status = properties["status"]
        self.logger.info("Given port properties: %s" % properties)

        if status == "Ready to configure":
            # get TPE resource
            tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
            self.logger.debug("GetPortStatus TPE: %s\n" % tpe)

            try:
                # get the existing adminstate of the port
                get_admin_state = self.execute_ra_command_file(
                    tpe["properties"]["device"], "get-interface.json", parameters={"name": port_name}, headers=None
                )
            except Exception as e:
                self.logger.info("Error raised while getting admin_state via ra_command: %s  | TPE: %s " % (e, tpe))
                raise Exception("Error raised while getting admin_state via ra_command: %s  | TPE: %s " % (e, tpe))

            # self.logger.info("admin_state data from executed RA command in GetPortStatus: %s" % get_admin_state.text)
            self.logger.info("**********GET ADMIN STATUS **************** ")
            get_admin_state = get_admin_state.json()["result"]
            admin_state = get_admin_state["interface-information"]["physical-interface"]["admin-status"]["#text"]
            oper_state = get_admin_state["interface-information"]["physical-interface"]["oper-status"]

            # check if first operation; no existing
            operations = self.bpo.resources.get_operations(resource_id)
            self.logger.info("OPERATION GET ****** %s" % operations)
            num_of_operations = len(operations["items"])

            if admin_state == "up" and num_of_operations <= 1:
                properties["deactivate_eligible"] = False
            else:
                if "deactivate_eligible" not in properties:
                    properties["deactivate_eligible"] = True

            self.bpo.resources.patch(resource_id, {"properties": properties})

            # get the optical light optical power levels of the port
            self.logger.info("**********GET OPTICAL POWER LEVELS **************** ")
            time.sleep(10)
            get_interface_dom = self.get_interface_optic_levels(tpe, port_name, admin_state)
            self.logger.info("show-interface-dom results: %s" % get_interface_dom.text)
            get_interface_dom = get_interface_dom.json()["result"]
            portRxAvgOpticalPower = get_interface_dom["rx-signal-avg-optical-power"]
            portTxAvgOpticalPower = get_interface_dom["tx-signal-avg-optical-power"]

            # get the port SFP properties
            self.logger.info("********** GET PORT SFP properties **************** ")
            # finding fpc-slot, pic-slot and port-slot from the port_name variable
            # support for Junos
            try:
                # fpp : fpc|pic|port-slot
                port_fpp = port_name.split("-", 1)[1]
                self.logger.info("********** FINDING fpc-slot, pic-slot and port-slot VALUES **************** ")
                fpc_slot = port_fpp.split("/", 2)[0]
                pic_slot = port_fpp.split("/", 2)[1]
                port_slot = port_fpp.split("/", 2)[2]
            except Exception as ex:
                self.logger.exception(ex)
                raise Exception(ex)

            get_port_sfp_props = self.execute_ra_command_file(
                tpe["properties"]["device"],
                "show-interface-sfp-props.json",
                parameters={"fpc-slot": fpc_slot, "pic-slot": pic_slot, "port-slot": port_slot},
                headers=None,
            )
            get_port_sfp_props = get_port_sfp_props.json()["result"]

            if get_port_sfp_props != {}:
                portSFPvendorPartNumber = get_port_sfp_props["sfp-vendor-part-number"]
                portSFPvendorName = get_port_sfp_props["sfp-vendor-name"]
                portSFPwavelength = get_port_sfp_props["sfp-wavelength"]
            else:
                portSFPvendorPartNumber = " N/A "
                portSFPvendorName = " N/A "
                portSFPwavelength = " N/A "

            # Output results
            output = {
                "status": "Port Status Retrieved",
                "adminstate": admin_state,
                "operstate": oper_state,
                "portRxAvgOpticalPower": portRxAvgOpticalPower,
                "portTxAvgOpticalPower": portTxAvgOpticalPower,
                "portSFPvendorPartNumber": portSFPvendorPartNumber,
                "portSFPvendorName": portSFPvendorName,
                "portSFPwavelength": portSFPwavelength,
            }
            self.logger.info("Output: " + json.dumps(output))
        else:
            output = {"status": "Resource not in Ready to configure state, hence operation can not be executed"}
            self.logger.info("Output: " + json.dumps(output))
        return output


class SetPortStatus(PortActivationOperation):
    """
    Get on this resource- find the status

    If the status is "ready to configure":
        do a set on the given TPE i.e set adminState of the TPE resourc

    else:
        return - "return based on the status"
    """

    def process(self):
        resource_id = self.params["resourceId"]
        resource = self.bpo.resources.get(resource_id)
        properties = resource["properties"]
        device_name = properties["deviceName"]
        port_name = properties["portname"].lower()
        tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
        operation = self.bpo.resources.get_operation(resource_id, self.params["operationId"])
        inputs = operation["inputs"]
        reqdstate = inputs["reqdstate"].lower()
        expiry_time = properties["terminationTime"]
        current_time = datetime.datetime.now()
        delta_time = current_time + datetime.timedelta(minutes=-65)
        # Create a current timestamp minus 65 minutes in iso format
        iso_time = delta_time.isoformat()[:19]
        resource_create_time = resource["createdAt"]
        created_time = resource_create_time[:19]
        self.logger.info("Initial SetPortStatus TPE: %s" % tpe)
        self.logger.info("====== Created: %s Delta: %s =====" % (created_time, iso_time))

        """"
        Comparing iso_time(current time - 65 minutes) to the creation time of the resource
        This is to prevent Port Activation from executing an operation on a resource
        that is older than 65 minutes
        """
        if created_time < iso_time:
            properties["status"] = "Port Activation Resource is old"
            self.bpo.resources.patch(resource_id, {"properties": properties})
            raise Exception("Port Activation Resource is old")

        if expiry_time != 0:
            self.deactivate_port(tpe, port_name, reqdstate, properties, resource_id)
        else:
            # added RaCutThrough
            self.cutthrough = RaCutThrough()
            status = properties["status"]
            device_brand = resource["properties"]["vendor"]

            # this condition is to check slax for juniper devices
            # all others will get the new description standard by default
            if device_brand.upper() == "JUNIPER":
                new_description_standard_apply = self.description_standard_decision(device_name)

                # condition to determine which interface description standard if description has to be added.
                if new_description_standard_apply:
                    tempDescription = "PEND - Light Test:CPE:::"
                else:
                    tempDescription = "CPE:PEND - Light Test:::"
            else:
                tempDescription = "PEND - Light Test:CPE:::"

            self.logger.info("====== RESOURCE (in Class SetPortStatus): =====")
            self.logger.info(resource)

            # Get device's network function
            device = self.get_network_function_by_host_or_ip(device_name, device_name)
            self.logger.info("====== DEVICE (in Class SetPortStatus): =====")
            self.logger.info(device)

            # Check if device is an MX converted to EDNA, set disabling apply group
            is_edna = False
            if device["properties"]["deviceVersion"][:9].upper() == "JUNIPERMX":
                device_prid = device["providerResourceId"]
                is_edna = self.check_is_edna(device_prid)
            disablr = "TP_DISABLEIF" if is_edna else "DISABLEIF"
            self.logger.info("Is this an MX that has converted to EDNA? %s" % is_edna)
            self.logger.info("The apply-group for disabling interfaces on this device is: %s" % disablr)

            if status == "Ready to configure":
                # get TPE resource
                tpe = self.get_tpe_by_name_and_host_return_errors(device_name, port_name)
                self.logger.info("SetPortStatus TPE under Ready to configure: %s" % tpe)

                if "properties" in tpe:
                    # get the existing adminstate of the port
                    get_admin_state = self.execute_ra_command_file(
                        tpe["properties"]["device"], "get-interface.json", parameters={"name": port_name}, headers=None
                    )
                    # self.logger.info("admin_state data from executed RA command in SetPortStatus: %s" % get_admin_state.text)
                    self.logger.info("**********GET ADMIN STATUS **************** ")
                    get_admin_state = get_admin_state.json()["result"]
                    admin_state = get_admin_state["interface-information"]["physical-interface"]["admin-status"]["#text"]

                    if reqdstate == "up":
                        if admin_state == "up":
                            output = {"status": "Port already in enabled state"}
                            self.logger.info("Output: " + str(output))
                            return output
                        else:
                            properties["wasPortActivated"] = True
                            self.bpo.resources.patch(resource_id, {"properties": properties})
                            apply_groups = tpe["properties"]["data"]["attributes"]["additionalAttributes"][
                                "apply-groups"
                            ]
                            if disablr in apply_groups:
                                apply_groups.remove(disablr)

                            tpe["properties"]["data"]["attributes"]["additionalAttributes"][
                                "apply-groups"
                            ] = apply_groups
                        # Setting temp port desctiption if there is none set on the interface
                        if tpe["properties"]["data"]["attributes"]["userLabel"] == "":
                            tpe["properties"]["data"]["attributes"]["userLabel"] = tempDescription

                    elif reqdstate == "down":
                        if admin_state == "down":
                            output = {"status": "Port already in disabled state"}
                            self.logger.info("Output: " + str(output))
                            return output
                        else:
                            if "wasPortActivated" in properties and properties["wasPortActivated"] is True:
                                apply_groups = tpe["properties"]["data"]["attributes"]["additionalAttributes"][
                                    "apply-groups"
                                ]
                                if disablr not in apply_groups:
                                    apply_groups.append(disablr)
                                tpe["properties"]["data"]["attributes"]["additionalAttributes"][
                                    "apply-groups"
                                ] = apply_groups
                            else:
                                output = {
                                    "status": "Operation not supported, port was not activated through Port Activation resource"
                                }
                                self.logger.info("Output: " + str(output))
                                return output

                    # patch TPE resource
                    is_discovered = tpe["discovered"]
                    self.bpo.resources.patch(tpe["id"], {"discovered": False})

                    # attempt to pass properties
                    self.logger.info(
                        "Attempting Apply Group + Interface Description Pass with the following structure:"
                    )
                    self.logger.info(tpe)
                    self.bpo.resources.patch(tpe["id"], {"properties": tpe["properties"]})

                    if is_discovered is True:
                        self.bpo.resources.patch(tpe["id"], {"discovered": True})

                    # check for disable and removes it from the port
                    if reqdstate == "up":
                        self.remove_disable(tpe, port_name)

                    # Check port state after resource patch
                    self.check_port_state(resource_id, state=reqdstate, interval=10, tmax=120)

                    output = {"status": "Successfully triggered patch operation for adminstate change"}
                    self.logger.info("Output: " + str(output))
            else:
                output = {"status": "Resource not in Ready to configure state, hence operation can not be executed"}
            self.logger.info("Output: " + str(output))

            return output

    def remove_disable(self, tpe, port_name):
        # removes disable if found on the port
        self.logger.info("***************************GET DISABLE STATUS*********************************")
        # pull full port config
        get_disable_status = self.execute_ra_command_file(
            tpe["properties"]["device"], "get-interface-config.json", parameters={"name": port_name}, headers=None
        )
        get_disable_status = get_disable_status.json()["result"]
        # if statement to check for disable on the port config and remove it if found
        if "disable" in get_disable_status["configuration"]["interfaces"][port_name]:
            self.execute_ra_command_file(
                tpe["properties"]["device"],
                "set-physical-interface-params.json",
                parameters={"param": "enable", "interface": port_name, "commit": True},
                headers=None,
            )
            self.logger.info("***************************REMOVED disable*********************************")

    def check_device_slax_version(self, slax_script_data, evi_slax_version):
        """this is to parse the netconf gathered data for the version of the slax script
        and compares it to the evi_slax_version and determines which description standard
        to follow for specific device and returns True or False

        returns:
            True or False
        """
        pattern = re.compile(r'\$sanity = "(.*?)";')
        matches = pattern.findall(slax_script_data)
        version = float(matches[0].replace("v", ""))
        self.logger.info("The current device slax script version on device: %s" % str(version))

        if version >= evi_slax_version:
            return True
        else:
            return False

    def description_standard_decision(self, fqdn):
        """makes a decision as to what description standard to apply to PE and AGG juniper device
        maybe MTU if needed currently commented out

        arguments:
            circuit_details, node 'uuid' / tid
        returns:
            boolean
        """
        # todo resolved node role by using the juniper model as the tell

        # method from common_plan.py to gather the device resource id
        device_resource = self.get_network_function_by_host(fqdn)
        self.logger.info("Device resource: %s" % device_resource)

        try:
            # condition to determine the node_role based on device
            if device_resource["properties"]["deviceVersion"][:9] == "JuniperMX":
                node_role = "PE"
            elif device_resource["properties"]["deviceVersion"][:9] == "JuniperQF":
                node_role = "AGG"
            elif device_resource["properties"]["deviceVersion"][:9] == "JuniperEX":
                node_role = "MTU"
            else:
                node_role = ""
        except Exception as e:
            raise Exception(
                "Error encountered while determing node role.  Details: %s  | device_resource: %s"
                % (e, device_resource)
            )

        self.logger.info("node_role is: %s " % (node_role))

        if node_role == "AGG":
            # slax script version that checks for latest description standards
            evi_slax_version = 1.4
            slax_json = "is_slax_qfx_version.json"

        self.logger.info("The device fqdn: %s device_resource_id: %s " % (fqdn, device_resource["providerResourceId"]))

        # check PE for EDNA slax script and if true it changes the values evi_slax_version and slax_json attributes
        if node_role == "PE":
            # slax script version that checks for latest description standards
            evi_slax_version = 2.44
            slax_json = "is_slax_pe_version.json"

            try:
                is_edna_slax = self.check_is_edna(device_resource["providerResourceId"])
                if is_edna_slax:
                    slax_json = "is_slax_edna_version.json"
            except Exception as e:
                self.logger.info("this is the exception raised while trying to find if is_edna: %s " % str(e))

        # Default to True if device not onboard yet
        new_description_standard_apply = True

        try:
            # racutthrough to gather slax data to parse for version
            slax_script_data = self.cutthrough.execute_ra_command_file(
                device_resource["providerResourceId"], slax_json, headers=None
            ).json()["result"]
            self.logger.info("The is the slax script data: %s " % str(slax_script_data))

            # returns True or False to determine new or old description standard
            new_description_standard_apply = self.check_device_slax_version(str(slax_script_data), evi_slax_version)
            self.logger.info("new_description_standard_apply: %s " % (new_description_standard_apply))

            return new_description_standard_apply
        except Exception as e:
            self.logger.info("this is the exception raised while trying to find the slax script: %s " % str(e))
            # made this True for testing purposes
            return new_description_standard_apply
