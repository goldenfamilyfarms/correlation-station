""" -*- coding: utf-8 -*-

PE config validator plans

Versions:
   0.1 July 27, 2018
       Initial check in of NetworkServiceCheck plans

"""

import json
import sys

sys.path.append("model-definitions")
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


# added BusinessLogic class to the Activate class parameters
class Activate(CompleteAndTerminatePlan):
    """
    This module will perform config pre-checks on PE devices and will
    fail if there are potential conflicts in configurationpresnet on device
    and circuit being built.
    """

    def process(self):
        # added this as to inherit Businesslogic class
        circuit_details_id = self.properties["circuit_details_id"]
        self.circuit_details = self.get_resource(circuit_details_id)
        self.logger.debug("circuit_details in pedeviceconfigvalidator: " + str(self.circuit_details))
        svlan = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["sVlan"]

        spoke_list = self.create_device_dict_from_circuit_details(self.circuit_details)
        self.logger.debug("spoke_list in pedeviceconfigvalidator: " + str(spoke_list))
        device_list = []
        index = 0
        for spoke in spoke_list:
            for device, device_info in spoke.items():
                if device in device_list:
                    index += 1
                if device_info["Role"] == "PE":
                    self.logger.debug("PE device found in pedeviceconfigvalidator: " + str(device))

                    nf = self.get_network_function_by_host_or_ip(device_info["FQDN"], device_info["Management IP"])
                    self.logger.debug("Network function of role PE found in pedeviceconfigvalidator: " + str(nf))

                    if "juniper" in nf["resourceTypeId"]:
                        device_prid = nf["providerResourceId"]
                        self.execute_ra_command_file(device_prid, "open-private-config.json")

                    if nf is None:
                        msg = "No PE device found for host name %s" % device
                        self.categorized_error = (
                            self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                        )
                        self.exit_error(msg)
                    else:
                        if not nf["orchState"] == "active":
                            msg = "NF %s is not active state, failing service" % device_info["Host Name"]
                            self.categorized_error = (
                                self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                            )
                            self.exit_error(msg)

                        device_prid = nf["providerResourceId"]
                        device_pid = nf["productId"]

                        package = nf["resourceTypeId"].split(".")[0]
                        plugin_rt = "charter.resourceTypes.CiscoPeConfigValidator"
                        plugin_product = self.get_plugin_product(package, plugin_rt)

                        # Cisco PE Validation
                        if plugin_product is not None:
                            plugin_properties = {
                                "node_id": nf["id"],
                                "pe_port": device_info["Client Interface"],
                                "description": device_info["Client Interface Description"],
                            }
                            if self.circuit_details["properties"]["topology"][0]["data"]["node"][0]["ownedNodeEdgePoint"][0]["name"][1]["value"] != "ENNI":
                                plugin_properties["client_neighbour_ip"] = self.get_node_management_ip(self.circuit_details, device_info["Client Neighbor"])

                            plugin_object = {
                                "label": self.circuit_details["properties"]["circuit_id"] + ".pe_config_validator",
                                "resourceTypeId": plugin_rt,
                                "productId": plugin_product,
                                "properties": plugin_properties,
                            }

                            plugin_resource = self.bpo.resources.create(self.resource["id"], plugin_object)
                            if plugin_resource.resource["orchState"] == "active":
                                self.bpo.relationships.delete_by_source_and_target(
                                    self.resource["id"], plugin_resource.resource_id
                                )
                                self.bpo.resources.delete(plugin_resource.resource_id)
                        # Nokia PE Validation
                        elif "nokia" in nf["resourceTypeId"]:
                            evcid = self.circuit_details["properties"]["service"][0]["data"]["evc"][0].get("evcId")
                            core_mgmt_ip = self.get_opposite_side_core_mgmt_ip(device_info)
                            # Confirm that SDP matching opposite PE mgmt ip is configured on device
                            sdp = self.execute_ra_command_file(
                                device_prid, "show-service-sdp.json", parameters={"ip": core_mgmt_ip}, headers=None
                            ).json()["result"]
                            if not sdp["SdpId"]:
                                msg = f"No SDP found for core device: {core_mgmt_ip}"
                                self.categorized_error = (
                                    self.ERROR_CATEGORY["NETWORK"].format(msg) if self.ERROR_CATEGORY.get("NETWORK") else ""
                                )
                                self.exit_error(msg)
                            # Confirm that EVCID is not already configured for another service on device
                            service_details = self.execute_ra_command_file(
                                device_prid, "show-service-using.json", parameters={"evcid": evcid}, headers=None
                            ).json()["result"]
                            if service_details["ServiceId"] == evcid:
                                msg = f"Service with EVCID: {evcid} already provisioned on device: {device_info['FQDN']}"
                                self.categorized_error = (
                                    self.ERROR_CATEGORY["NETWORK"].format(msg) if self.ERROR_CATEGORY.get("NETWORK") else ""
                                )
                                self.exit_error(msg)
                            # Confirm that intended SAP is not already configured on device
                            sap_details = self.execute_ra_command_file(
                                device_prid, "show-service-sap-using.json", parameters={"'port_id'": device_info["Client Interface"] + ":" + svlan}, headers=None
                            ).json()["result"]
                            if sap_details["PortId"] == device_info["Client Interface"] + ":" + svlan:
                                msg = f"SAP: {sap_details['PortId']} already provisioned on device: {device_info['FQDN']}"
                                self.categorized_error = (
                                    self.ERROR_CATEGORY["NETWORK"].format(msg) if self.ERROR_CATEGORY.get("NETWORK") else ""
                                )
                                self.exit_error(msg)

                        # Juniper PE Validation
                        else:
                            if self.circuit_details["properties"]["serviceType"] == "FIA":
                                self.domain_id = self.bpo.market.get("/products/%s" % device_pid)["domainId"]
                                ipv4_res = self.execute_ra_command_file(
                                    device_prid,
                                    "get-fre.json",
                                    parameters={"data.id": "RIB::GlobalRouter"},
                                    headers=None,
                                )
                                ipv6_res = self.execute_ra_command_file(
                                    device_prid, "get-fre.json", parameters={"data.id": "RIB::inet6.0"}, headers=None
                                )

                                if ipv4_res.json()["result"]:
                                    ipv4_res = ipv4_res.json()["result"]
                                    self.logger.debug(
                                        "Ipv4 Global Router resource is %s" % json.dumps(ipv4_res, indent=4)
                                    )
                                    dest_ips = self.circuit_details["properties"]["service"][0]["data"]["fia"][0][
                                        "endPoints"
                                    ][0].get("lanIpv4Addresses", [])
                                    for ip in dest_ips:
                                        if self.ip_already_exist(ip, ipv4_res):
                                            msg = "Route for IP %s already exists on device " % ip
                                            self.categorized_error = (
                                                self.ERROR_CATEGORY["NETWORK"].format(msg)
                                                if self.ERROR_CATEGORY.get("NETWORK")
                                                else ""
                                            )
                                            self.exit_error(msg)
                                if ipv6_res.json()["result"]:
                                    ipv6_res = ipv6_res.json()["result"]
                                    self.logger.debug("Ipv6 inet6.0 resource is %s" % json.dumps(ipv6_res, indent=4))
                                    dest_ips = self.circuit_details["properties"]["service"][0]["data"]["fia"][0][
                                        "endPoints"
                                    ][0].get("lanIpv6Addresses", [])
                                    for ip in dest_ips:
                                        if self.ip_already_exist(ip, ipv6_res):
                                            msg = "Route for IP %s already exists on device " % ip
                                            self.categorized_error = (
                                                self.ERROR_CATEGORY["NETWORK"].format(msg)
                                                if self.ERROR_CATEGORY.get("NETWORK")
                                                else ""
                                            )
                                            self.exit_error(msg)
                            #
                            # Applying required apply-group if not present already on the PE
                            pe_port = device_info["Client Interface"]
                            pe_port_role = self.get_port_role(self.circuit_details, device + "-" + pe_port)
                            pe_port_res_id = self.get_port_id_from_port_name_and_device_id_retry(pe_port, nf["id"])
                            pe_port_res = self.bpo.resources.get(pe_port_res_id)
                            admin_state = pe_port_res["properties"]["state"].upper()

                            # CONFIRM THAT SUBINTERFACE IS NOT ALREADY PROVISIONED WITH EXISTING SERVICE
                            endpoints = self.circuit_details["properties"]["service"][0]["data"]["evc"][0]["endPoints"]
                            for endpoint in endpoints:
                                is_type_2 = (
                                    True
                                    if endpoint.get("type2") and endpoint["uniId"].split("-")[0] in nf["label"]
                                    else False
                                )
                                if is_type_2:
                                    break
                            if is_type_2:
                                unit = endpoint["unit"]
                                subinterface = pe_port.lower() + "." + unit
                            else:
                                subinterface = pe_port.lower() + "." + svlan
                            is_rphy = True if self.circuit_details["properties"]["serviceType"] == "VIDEO" else False
                            if not is_rphy and self.is_already_provisioned(device_prid, subinterface):
                                msg = """Error! %s is already provisioned with an existing service.""" % subinterface
                                self.categorized_error = (
                                    self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                                )
                                self.exit_error(msg)

                            if admin_state == "IS" or pe_port_role.upper() == "ENNI":
                                continue
                            pe_port_description = device_info["Client Interface Description"]
                            self.logger.debug(pe_port_description)

                            # Check if MX has been converted to EDNA to determine appropriate
                            # names to use for apply-groups, filters, and policers.
                            is_edna = self.check_is_edna(device_prid)

                            self.logger.info("IS_EDNA: %s" % is_edna)

                            # BEGIN Apply-Group determination
                            apply_group_roles = ["CPE", "MTU", "EP-UNI", "EVP-UNI"]
                            pe_port_roles = [pe_port_description.split(":")[0], pe_port_description.split(":")[1]]
                            required_apply_group = ""

                            for pe_port_field in pe_port_roles:
                                if pe_port_field in apply_group_roles:
                                    required_apply_group = pe_port_field

                            if is_edna:
                                required_apply_group = (
                                    "TP_SERVICEPORT"
                                    if required_apply_group in ["CPE", "MTU"]
                                    else "TP_" + required_apply_group
                                )
                            else:
                                required_apply_group = (
                                    "SERVICEPORT" if required_apply_group in ["CPE", "MTU"] else required_apply_group
                                )

                            if pe_port is None:
                                msg = self.error_formatter(
                                    self.INCORRECT_DATA_ERROR_TYPE,
                                    "Client Interface Role",
                                    f"device: {device_info['Host Name']} client interface role: None"
                                )
                                self.categorized_error = msg
                                self.exit_error(msg)

                            try:
                                if "UNI" not in pe_port_role.upper():
                                    current_task = "getting Bridge Domains"
                                    is_cpe_mgmt_present = self.execute_ra_command_file(
                                        device_prid,
                                        "get-bridge-domains.json",
                                        parameters={
                                            "interface": pe_port.lower(),
                                            "unit": "99",
                                            "bridge_domain": "CPEMGMT",
                                        },
                                        headers=None,
                                    )
                                    if is_cpe_mgmt_present.json()["result"].lower() == "not present":
                                        current_task = "setting Bridge Domain for CPEMGMT to 99"
                                        self.execute_ra_command_file(
                                            device_prid,
                                            "set-bridge-domain-inner.json",
                                            parameters={
                                                "interface": pe_port.lower(),
                                                "unit": "99",
                                                "bridge_domain": "CPEMGMT",
                                            },
                                            headers=None,
                                        )
                                current_task = "getting Apply Groups"
                                is_nni_present = self.execute_ra_command_file(
                                    device_prid,
                                    "get-apply-groups.json",
                                    parameters={"interface": pe_port.lower(), "group": "TP_NNI" if is_edna else "NNI"},
                                    headers=None,
                                )
                                is_nni_present = is_nni_present.json()
                                if is_nni_present.get("result") is False:
                                    is_serviceport_present = self.execute_ra_command_file(
                                        device_prid,
                                        "get-apply-groups.json",
                                        parameters={
                                            "interface": pe_port.lower(),
                                            "group": "TP_SERVICEPORT" if is_edna else "SERVICEPORT",
                                        },
                                        headers=None,
                                    )
                                    required_apply_group_present = None
                                    if not required_apply_group == "SERVICEPORT":
                                        is_required_apply_group_present = self.execute_ra_command_file(
                                            device_prid,
                                            "get-apply-groups.json",
                                            parameters={"interface": pe_port.lower(), "group": required_apply_group},
                                            headers=None,
                                        )
                                        required_apply_group_present = is_required_apply_group_present.json()["result"]

                                    if not is_serviceport_present.json()["result"] and (
                                        required_apply_group_present is None or not required_apply_group_present
                                    ):
                                        current_task = "setting Apply Groups for SERVICEPORT"
                                        self.execute_ra_command_file(
                                            device_prid,
                                            "set-apply-groups-inner.json",
                                            parameters={"interface": pe_port.lower(), "group": required_apply_group},
                                            headers=None,
                                        )

                            except Exception as e:
                                msg = "Error '%s' communicating with RA/Device occurred while %s, on device %s" % (
                                    str(e),
                                    current_task,
                                    device_info["Host Name"],
                                )
                                self.categorized_error = (
                                    self.ERROR_CATEGORY["MDSO"].format(msg) if self.ERROR_CATEGORY.get("MDSO") else ""
                                )
                                self.exit_error(msg)
        return

    def ip_already_exist(self, dest_ip, fre_res):
        """
        Finds if the Route is already present
        in the FRE Resource
        """

        route_type = "ipv6" if fre_res["label"].endswith("inet6.0") else "ipv4"
        route_list = fre_res["properties"]["data"]["attributes"]["routingInstance"]["ribList"][0]["routeList"]

        self.logger.debug("Checking for ip %s in route list %s" % (dest_ip, route_list))
        for route in route_list:
            existing_dest_ip = (
                route["match"]["routeType"]["ipv4"]["destIpv4Address"]
                if route_type == "ipv4"
                else route["match"]["routeType"]["ipv6"]["destIpv6Address"]
            )
            if dest_ip.lower() == existing_dest_ip:
                return True

        return False

    def pe_applygroup_serviceport(self, tpe_res):
        """
        Add SERVICEPORT apply-group to PE physical interface
        in the TPE Resource
        """
        self.logger.debug("Applying SERVICEPORT apply-group to %s " % (tpe_res))

        apply_groups = tpe_res["properties"]["data"]["attributes"]["additionalAttributes"].get("apply-groups", [])

        if "SERVICEPORT" not in apply_groups:
            apply_groups.append("SERVICEPORT")

        tpe_res["properties"]["data"]["attributes"]["additionalAttributes"]["apply-groups"] = apply_groups

        # patch = {"properties": tpe_res["properties"]}

        self.execute_ra_command_file(
            tpe_res["providerResourceId"].split("::")[0], "create-tpe-config-command.json", tpe_res, headers=None
        )

        # self.bpo.resources.patch(tpe_res['id'], patch)
        # self.await_differences_cleared_collect_timing("Applying Apply-group SERVICEPORT to PE port", tpe_res['id'])

    def is_already_provisioned(self, device_prid, subinterface):
        subinterface_data = {"interface": subinterface.split(".")[0], "unit": subinterface.split(".")[1]}
        subinterface_config = self.execute_ra_command_file(
            device_prid, "check-subinterface.json", subinterface_data, headers=None
        )
        subinterface_config_result = subinterface_config.json()["result"]
        return True if subinterface_config_result else False

    def get_opposite_side_core_mgmt_ip(self, device_info):
        """Retreives Core Router IP of PE on Other Side of Circuit"""
        a_side_pe = self.circuit_details["properties"]["topology"][0]["data"]["node"][-1]
        z_side_pe = self.circuit_details["properties"]["topology"][-1]["data"]["node"][0]
        if device_info['Role'] == "PE":
            # Nokia is PE and is l2circuit neighbor of core router on the other side
            core_router = a_side_pe if device_info['location'] == "Z_SIDE" else z_side_pe
        else:
            # Nokia is CPE and core router is on the same side upstream from the device
            core_router = a_side_pe if device_info['location'] == "A_SIDE" else z_side_pe
        core_mgmt_ip = [pair["value"] for pair in core_router["name"] if pair["name"] == "Management IP"][0]
        return core_mgmt_ip
