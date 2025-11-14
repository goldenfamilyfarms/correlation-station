"""-*- coding: utf-8 -*-

ServiceDeviceOnboarder Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of ServiceDeviceOnboarder plans

"""

import sys

from copy import deepcopy

sys.path.append("model-definitions")
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan
from scripts.networkservice.update_site_state import UpdateSiteState


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    ServiceProvisioner.
    """

    SERVICE_TYPE_LOOKUP = {
        "EVP": "EVPL",
        "EVPL": "EVPL",
        "EPL": "EPL",
        "EP": "EPL",
        "IP": "IP",
        "EP-LAN": "EP-LAN",
        "EVP-LAN": "EVP-LAN",
        "RPHY": "RPHY",
    }

    COS_LOOKUP = {
        "PE": {
            "NONE": "SERVICEPORT_UNCLASSIFIED_COS",
            "BRONZE": "SERVICEPORT_BRONZE_COS",
            "SILVER": "SERVICEPORT_SILVER_COS",
            "GOLD": "SERVICEPORT_GOLD_COS",
        },
        "CPE": {"NONE": "PBIT-0", "BRONZE": "PBIT-1", "SILVER": "PBIT-3", "GOLD": "PBIT-5"},
        "PE-CPE": {
            "SERVICEPORT_UNCLASSIFIED_COS": "PBIT-0",
            "SERVICEPORT_BRONZE_COS": "PBIT-1",
            "SERVICEPORT_SILVER_COS": "PBIT-3",
            "SERVICEPORT_GOLD_COS": "PBIT-5",
        },
    }
    CONNECTION_TYPE_LOOKUP = {"pointToPoint": "Point-To-Point", "Point to Point": "Point-To-Point"}

    PE_SPECIFIC_RESOURCE_TYPES = {
        "FIA": "charter.resourceTypes.ServiceProvisioner_FIA",
        "VOICE": "charter.resourceTypes.ServiceProvisioner_FIA",
        "ELAN": "charter.resourceTypes.ServiceProvisioner_ELAN",
    }

    PROVISION_SLM_SERVICES = ["CTBH 4G"]

    def process(self):
        self.logger.info("Properties: {}".format(self.properties))
        circuit_details_id = self.properties["circuit_details_id"]
        self.context = self.properties["context"]
        stage = self.properties["stage"]
        service_resource_type = self.BUILT_IN_MEF_TEST_SERVICE_TYPE
        update_site_state = UpdateSiteState(self)
        if stage == "PRODUCTION":
            service_resource_type = self.BUILT_IN_MEF_PRODUCTION_SERVICE_TYPE

        circuit_details = self.get_resource(circuit_details_id)
        self.leg_identifier = circuit_details['label'].split("-")[-1].strip(".cd")
        self.is_multileg_circuit = True if self.leg_identifier in ["PRIMARY", "SECONDARY"] else False
        self.network_service_id = self.properties.get("network_service_resource_id")
        service_type = circuit_details["properties"]["serviceType"]
        network_service = self.bpo.resources.get(self.network_service_id)

        pe_provisioned = False
        # if service_type in PE_SPECIFIC_RESOURCE_TYPES, pe_provisioned is set to True
        if self.context == "PE" and self.PE_SPECIFIC_RESOURCE_TYPES.get(service_type):
            # this calls service fia provisioner
            self.create_pe_provisioner_resource(service_type)
            pe_provisioned = True
        self.logger.info("PE Provisioned: {}".format(pe_provisioned))

        # DETERMINE WHICH DEVICES SHOULD BE UPDATED BASED ON CONTEXT
        device_list, cpe_update_list, pe_list, pe_rtr_list = self.determine_devices_to_update_by_context(
            circuit_details
        )

        # Updating Service Details becuase FIA or ELAN Provisioners could have updated it by now
        circuit_details = self.get_resource(circuit_details_id)
        evc_service_type = circuit_details["properties"]["service"][0]["data"]["evc"][0]["serviceType"]
        self.logger.info(f"+++ circuit_details: {circuit_details}")
        self.logger.info(f"+++ evc_service_type:{evc_service_type}")

        # Checking PE state if it was FIA or ELAN
        if len(pe_list) > 0 and pe_provisioned:
            pe_state = self.is_node_provisioned(circuit_details, pe_list[0])
            self.logger.info(pe_state)
            if pe_provisioned is True and pe_state != "True":
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"PE device {pe_list[0]} provisioned by {service_type} provisioner but circuit details shows provisoned state {pe_state}",
                )
                self.categorized_error = msg
                self.exit_error(msg)
        # DETERMINE WHICH DEVICES SHOULD BE UPDATED BASED ON
        # IF THEY HAVE BEEN PROVISIONED BEFORE AND IF THEY ARE INSTALLED
        device_update_list = self.determine_devices_to_update(
            device_list, circuit_details, evc_service_type, pe_rtr_list
        )
        if len(device_update_list) == 0:
            self.logger.info("There are no devices to update associated with this service.")
            return

        original_device_update_list = deepcopy(device_update_list)
        # if there are more than one devices in update_list for non-ELINE, just keep the first device
        if self.context == "PE":
            if not service_type == "ELINE":
                device_update_list = [device_update_list[0]]

        # GET THE MEF CIRCUIT FOR THE CIRCUIT ID IF THERE IS ONE, MODEL IF NONE
        mef_service = self.get_mef_service(service_type, circuit_details, service_resource_type)
        if mef_service is None:
            mef_service = self.get_mef_service_properties_from_details(circuit_details, self.context, circuit_details_id)
        # NOW BUILD THE MEF MODEL FOR THE SERVICE BASED ON WHAT IS REQ
        self.add_mef_service_endpoints(mef_service, circuit_details, device_update_list)
        self.logger.debug("MEF Service: " + str(mef_service))

        # NOW CREATE OR UPDATE MEF SERVICE
        if self.is_mef_service_created(mef_service):
            self.logger.info("updating mef service")
            self.update_mef_service(mef_service)
        else:
            self.logger.info("creating mef service")
            self.create_mef_service(mef_service, service_resource_type, network_service["id"])

        # UPDATE CPE STATES IN NETWORKSERVICE
        self.logger.debug("CPE Update list: " + str(cpe_update_list))
        for cpe in cpe_update_list:
            update_site_state.update_site_state_by_network_service(network_service, cpe, "ACTIVATING-INITIATED")

        self.update_circuit_details_devices_provisioned(circuit_details_id, original_device_update_list)

        self.circuit_id = self.resource["properties"]["circuit_id"]
        self.circuit_details_id = self.resource["properties"]["circuit_details_id"]

    def get_mef_service(self, service_type, circuit_details, service_resource_type):
        mef_service = None
        if service_type != "ELAN":
            if "evcId" in circuit_details["properties"]["service"][0]["data"]["evc"][0].keys():
                try:
                    user_label = circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"][0][
                        "userLabel"
                    ]
                    if self.is_multileg_circuit:
                        user_label = user_label.replace(user_label.split(":")[0], user_label.split(":")[0] + "-" + self.leg_identifier)
                    evcId = circuit_details["properties"]["service"][0]["data"]["evc"][0]["evcId"]
                    mef_service = self.get_resource_by_type_and_properties(
                        service_resource_type,
                        {"userLabel": user_label, "evcId": evcId},
                        no_fail=True,
                    )
                except Exception as err:
                    msg = self.error_formatter(
                        self.PROCESS_ERROR_TYPE,
                        self.RESOURCE_GET_SUBCATEGORY,
                        f"Error collecting MEF Services from BPO for Label: {user_label} & Resource Type: {service_resource_type}. Error: {str(err)}",
                    )
                    self.categorized_error = msg
                    raise Exception(msg)
            else:
                # Its an FIA service
                try:
                    mef_service = self.get_resource_by_type_and_label(
                        service_resource_type,
                        circuit_details["properties"]["serviceName"] + ".mef_service",
                        no_fail=True,
                    )
                except Exception:
                    msg = self.error_formatter(
                        self.PROCESS_ERROR_TYPE,
                        self.RESOURCE_GET_SUBCATEGORY,
                        f"Error collecting MEF Services from BPO for Label: {circuit_details['properties']['serviceName'] + '.mef_service'} & Resource Type: {service_resource_type}.",
                    )
                    self.categorized_error = msg
                    raise Exception(msg)
            self.logger.debug("MEF Service Found: " + str(mef_service))
        return mef_service

    def add_mef_service_endpoints(self, mef_service, circuit_details, device_update_list):
        mef_service["properties"]["endPoints"] = (
            [
                self.get_mef_endpoint_from_details(circuit_details, device_update_list[0]),
                self.get_mef_endpoint_from_details(circuit_details, device_update_list[-1]),
            ]
            if len(device_update_list) == 2
            else [self.get_mef_endpoint_from_details(circuit_details, device_update_list[0])]
        )

    def is_mef_service_created(self, mef_service):
        return "id" in mef_service.keys()

    def update_mef_service(self, mef_service):
        if "cosNames" in mef_service["properties"].keys():
            new_cos_name = self.get_new_cos_name(mef_service)
            mef_service["properties"]["cosNames"] = new_cos_name
        self.logger.info("MEF Service to update: " + str(mef_service))
        try:
            self.bpo.resources.patch(mef_service["id"], {"properties": mef_service["properties"]})
            self.await_differences_cleared_collect_timing(
                "CPE MEF Update", mef_service["id"], interval=10.0, tmax=1200.0
            )
        except Exception as ex:
            self.logger.exception(ex)
            raise Exception("Failure in adding CPE to service.  Error: " + str(ex))

    def create_mef_service(self, mef_service, service_resource_type, network_service_id):
        product = self.get_built_in_product(service_resource_type)
        mef_service["productId"] = product["id"]
        # CREATION
        try:
            self.bpo.resources.create(network_service_id, mef_service, wait_time=600)
        except Exception as ex:
            self.logger.exception(ex)
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_CREATE_SUBCATEGORY,
                f"Failure creating PE to PE service for mef service: {mef_service}.  Error: {str(ex)}",
            )
            self.categorized_error = msg
            raise Exception(msg)

    def determine_devices_to_update(self, device_list, circuit_details, evc_service_type, pe_rtr_list):
        device_update_list = []
        for device in device_list:
            self.logger.info(device)
            if not self.is_node_provisioned(circuit_details, device) == "True":
                if evc_service_type != "RPHY" or device not in pe_rtr_list:
                    device_update_list.append(device)

        self.logger.info("Devices to be Updated are %s " % str(device_update_list))
        return device_update_list

    def create_pe_provisioner_resource(self, service_type):
        pe_resource = None
        pe_provisioner_obj = {
            "label": self.properties["circuit_id"] + "-" + service_type + "-Provisioner",
            "productId": self.get_built_in_product(self.PE_SPECIFIC_RESOURCE_TYPES.get(service_type))["id"],
            "properties": self.properties,
        }
        try:
            self.logger.info("Creating PE Provisioner resource: {}".format(pe_provisioner_obj))
            pe_resource = self.bpo.resources.create(self.network_service_id, pe_provisioner_obj, wait_time=600.0)
        except RuntimeError as e:
            if pe_resource:
                self.logger.info(
                    "Upon Failure Resource Status for %s - Resource Type: %s, Resource Label: %s, Orch State: %s"
                    % (
                        pe_resource.resource_id,
                        pe_resource.resource["resourceTypeId"],
                        pe_resource.resource["label"],
                        pe_resource.resource["orchState"],
                    )
                )
            else:
                resourceType_id = self.PE_SPECIFIC_RESOURCE_TYPES.get(service_type)
                label = pe_provisioner_obj["label"]
                self.logger.info(
                    "Upon Failure Resource Status for Resource Type: %s, Resource Label: %s" % (resourceType_id, label)
                )
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_CREATE_SUBCATEGORY,
                f"Failed at service provisioner for PE with reason {str(e)}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

    def determine_devices_to_update_by_context(self, circuit_details):
        device_list = []
        cpe_update_list = []
        pe_list = []
        pe_rtr_list = []
        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)
        for spoke in spoke_list:
            ordered_list = self.get_ordered_topology(spoke)
            for node in ordered_list:
                for device, values in node.items():
                    if self.context == "CPE":
                        if self.is_handoff_device(values):
                            if (
                                self.get_node_bpo_state(circuit_details, device)
                                == self.BPO_STATES["AVAILABLE"]["state"]
                            ):
                                device_list.append(device)
                                cpe_update_list.append(device)
                    if self.context == "PE" or self.context == "ALL":
                        if not values["Role"] == "CPE":
                            if not self.is_handoff_device(values):
                                # do not add duplicate (in locally switched PE, PE appears twice in topology)
                                if device not in device_list:
                                    device_list.append(device)
                                if device not in pe_list:
                                    pe_list.append(device)
                                    # Create list of actual PE Routers as pe_list includes QFX AGGs
                                    if values["Role"] == "PE":
                                        pe_rtr_list.append(device)
        return device_list, cpe_update_list, pe_list, pe_rtr_list

    def is_a_side_for_host(self, circuit_details_props, hostname):
        """returns True if the host is on the "A" side of the service

        Returns False if Z Side
        """
        return_value = True
        z_side = circuit_details_props.get("z_side")
        if z_side and z_side["pe"]["hostname"] == hostname or z_side["cpe"]["hostname"] == hostname:
            return_value = False

        return return_value

    def get_mef_endpoint_from_details(self, circuit_details, device_info):
        """returns the MEF end point for the device_info"""

        device_role = self.get_node_role(circuit_details, device_info)
        client_neighbor = str(self.get_node_property(circuit_details, device_info, "Client Neighbor"))
        if self.is_handoff_device({"Role": device_role, "Client Neighbor": client_neighbor}):
            mef_ep = self.get_mef_cpe_endpoint(circuit_details, device_info)
        else:
            mef_ep = self.get_mef_pe_endpoint(circuit_details, device_info)

        return mef_ep

    def get_mef_pe_endpoint(self, circuit_details, device_info):
        """returns the MEF PE end point for the device_info"""

        return_value = {
            "role": "root",
            "adminState": True,
            "uniId": device_info + "-" + self.get_node_client_interface(circuit_details, device_info),
            "userLabel": self.get_node_client_interface_description(circuit_details, device_info),
            "sVlan": (
                0
                if circuit_details["properties"]["service"][0]["data"]["evc"][0]["sVlan"].lower() == "untagged"
                else int(circuit_details["properties"]["service"][0]["data"]["evc"][0]["sVlan"])
            ),
        }

        ceVlans = self.get_cvlans_for_uni_ep(circuit_details, return_value["uniId"])
        if ceVlans:
            return_value["CEvlans"] = []
            for cevlan in ceVlans:
                value = {"vid": str(cevlan)}
                return_value["CEvlans"].append(value)

        self.logger.info("Required PE endpoint is %s" % str(return_value))

        return return_value

    def get_mef_cpe_endpoint(self, circuit_details, device_info):
        """returns the MEF CPE end point for the device_info"""

        req_ep = self.get_required_endpoint(device_info, circuit_details)
        opt_ep_keys = [
            "sourceMacAddressLlimitTimeInterval",
            "colorIdentifier",
            "cosIdentifier",
            "eecIdentifier",
            "subscriberMegMipEnabled",
            "testMegEnabled",
            "sourceMacAddressLimit",
            "ceVlans",
            "sVlanOperation",
        ]

        return_value = {
            "role": req_ep.get("Role", "root"),
            "adminState": req_ep["adminState"],
            "uniId": req_ep["uniId"],
            "userLabel": self.get_node_client_interface_description(circuit_details, device_info),
            "sVlan": 0 if req_ep["sVlan"].lower() == "untagged" else int(req_ep["sVlan"]),
        }

        for key in opt_ep_keys:
            if key in req_ep.keys():
                if key == "ceVlans":
                    return_value["CEvlans"] = []
                    for cevlan in req_ep[key]:
                        # Converting cevlan to string to match type of mef template
                        value = {"vid": str(cevlan)}
                        return_value["CEvlans"].append(value)
                else:
                    return_value[key] = req_ep[key]

        self.logger.info("Required CPE endpoint is %s" % str(return_value))

        return return_value

    def get_required_endpoint(self, device_name, circuit_details):
        """
        returns the required service endpoint
        for the device
        """

        req_ep = None
        for service in circuit_details["properties"]["service"]:
            for evc in service["data"]["evc"]:
                for ep in evc["endPoints"]:
                    if device_name == self.get_node_port_name_from_uuid(ep["uniId"])[0]:
                        req_ep = ep

        if req_ep is None:
            msg = self.error_formatter(
                self.PROCESS_ERROR_TYPE,
                self.RESOURCE_GET_SUBCATEGORY,
                f"Unable to find desired EndPoint for device: {device_name}",
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return req_ep

    def get_policer_name(self, vendor, bw_profile):
        """returns the MEF Service properties

        From the Circuit_details provided
        """

        bw_list = self.get_bandwidth_int_and_units(bw_profile)
        packet_bw_id = str(bw_list[0]) + str(bw_list[1])
        bp_profile = self.get_packet_bw_profile_by_id(packet_bw_id, vendor)
        if bp_profile:
            return bp_profile["properties"]["name"]

        return None

    def get_mef_service_properties_from_details(self, cd, context, circuit_details_id):
        """returns the MEF Service properties

        From the Circuit_details provided
        """
        details = cd["properties"]
        # for now i expect one element only, may need to change it later on
        evc = details["service"][0]["data"]["evc"][0]
        optional_keys = [
            "evc-ingress-bwp",
            "evc-egress-bwp",
            "evcId",
            "unicastFrameDelivery",
            "multicastFrameDelivery",
            "ceVlanIdPreservation",
            "ceVlanPcpPreservation",
            "maxNumOfEvcEndPoint",
            "broadcastFrameDelivery",
            "ceVlanDeiPreservation",
            "maxFrameSize",
        ]

        properties = {
            "circuit_details_id": circuit_details_id,
            "svcType": self.SERVICE_TYPE_LOOKUP[evc["serviceType"]],
            "adminState": evc["adminState"],
            "maxNumOfEvcEndPoint": evc["maxNumOfEvcEndPoint"],
            "path_finder_product_id": self.get_built_in_product(self.BUILT_IN_PATH_FINDER_TYPE)["id"],
            "status": {"operationalState": True, "serviceState": "as"},
            "connectionType": self.CONNECTION_TYPE_LOOKUP[evc["connectionType"]],
            "userLabel": self.get_service_userLabel(cd),
        }
        for key in optional_keys:
            if key in optional_keys:
                if key in evc.keys():
                    properties[key] = evc[key]

        if "cosNames" in evc.keys():
            evc["cosNames"][0]["name"] = self.COS_LOOKUP[context][evc["cosNames"][0]["name"]]
            properties["cosNames"] = evc["cosNames"]

        if self.is_multileg_circuit:
            properties["userLabel"] = properties["userLabel"].replace(properties["userLabel"].split(":")[0], properties["userLabel"].split(":")[0] + "-" + self.leg_identifier)

        return_value = {"label": details["circuit_id"] + ".mef_service", "properties": properties}

        return return_value

    def get_new_cos_name(self, mef_service):
        """converts cos name to required pbit
        when moving from pe to cpe context
        """

        return_value = mef_service["properties"]["cosNames"]
        cos_name = mef_service["properties"]["cosNames"][0]["name"]
        if cos_name in self.COS_LOOKUP["PE-CPE"].keys():
            new_cos_name = self.COS_LOOKUP["PE-CPE"][cos_name]
            mef_service["properties"]["cosNames"][0]["name"] = new_cos_name
            return_value = mef_service["properties"]["cosNames"]

        return return_value

    def update_circuit_details_devices_provisioned(self, circuit_details_id, original_device_update_list):
        circuit_details = self.bpo.resources.get(circuit_details_id)
        self.logger.info("original_device_update_list: %s" % original_device_update_list)
        cd_label = circuit_details["label"]
        for device in original_device_update_list:
            self.logger.info("The DEVICE is: %s" % device)
            circuit_details = self.update_node_prop_value(device, circuit_details_id, "Provisioned", "True")
            # from this point, circuit_details is None as update_node_prop_value does not return anything
        try:
            self.await_differences_cleared_collect_timing(cd_label, circuit_details_id, interval=5.0)
        except Exception as ex:
            self.logger.info("Circuit %s failed update with error: %s" % (circuit_details_id, str(ex)))
