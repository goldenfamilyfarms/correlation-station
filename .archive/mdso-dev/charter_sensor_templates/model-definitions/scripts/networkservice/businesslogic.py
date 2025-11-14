"""-*- coding: utf-8 -*-

ServiceDeviceOnboarder Plans

Versions:
   0.1 Jun 27, 2018
       Initial check in of Business Logic plans

"""

import ipaddress
import json
import re
import sys
from collections import OrderedDict, defaultdict
from copy import deepcopy

from ra_plugins.ra_cutthrough import RaCutThrough

sys.path.append("model-definitions")
from scripts.common_plan import CommonPlan


class BusinessLogic(CommonPlan):
    """
    The functions in this class embody Charter's business logic to convert
    the Beorn response to be usable with the RTs and STs in
    charter_sensor_templates. The Beorn response will
    include the data from Granite.

    The functions in this BusinessLogic class are intended to be understood
    and maintained by Charter developers who might not have full knowledge of
    the code in charter_sensor_templates and bp-so-mef-templates.
    """

    node_variables_lookup = {
        "hostName": "Host Name",
        "deviceRole": "Role",
        "vendor": "Vendor",
        "model": "Model",
        "managementIP": "Management IP",
        "location": "location",
        "address": "Address",
        "fqdn": "FQDN",
        "equipmentStatus": "Equipment Status",
    }
    ownednodeedgepoint_variable_lookup = {
        "name": "Name",
        "portRole": "Role",
        "lagMember": "LAG Member",
        "transportId": "Transport ID",
        "channelName": "Channel Name",
    }
    device_roles_lookup = {
        "PE": [
            "JUNIPER MX240",
            "JUNIPER MX480",
            "JUNIPER MX960",
            "JUNIPER MX240 ETHERNET ROUTER",
            "JUNIPER MX480 ETHERNET ROUTER",
            "JUNIPER MX960 ETHERNET ROUTER",
            "JUNIPER MX80 MODULAR",
            "CISCO ASR 9001",
            "CISCO ASR 9006",
            "CISCO ASR 9010",
            "NOKIA 7750 SR-7",
            "NOKIA 7750 SR-2S",
            "NOKIA 7750 SR-12",
            "NOKIA 7750 SR-1",
        ],
        "CPE": [
            "JUNIPER MX240",
            "JUNIPER MX480",
            "JUNIPER MX80 MODULAR",
            "RAD 2I",
            "RAD 220A",
            "RAD ETX203AX",
            "ADVA GE114",
            "ADVA GE114PRO",
            "ADVA XG116PRO",
            "ADVA XG116PROH",
            "ADVA XG118PRO (SH)",
            "ADVA XG108",
            "ADVA 825",
            "CIENA 3931",
            "CISCO ASR-920-12CZ",
            "CISCO ASR-920-24SZ",
            "CISCO ASR-920-4SZ-A",
            "CISCO ME-3400E-24TS-M",
            "CISCO ME-3400-EG-12CS-M",
            "CISCO ME-3400EG-2CS-A",
            "CISCO ME-3400-2CS",
        ],
        "MTU": [
            "JUNIPER EX4200",
            "RAD 2I",
            "RAD 220A",
            "ADVA XG116PRO",
            "ADVA XG116PROH",
            "ADVA XG118PRO (SH)",
            "ADVA XG120PRO",
        ],
        "AGG": ["JUNIPER QFX", "JUNIPER ACX5448"],
    }

    def __init__(self, common_plan):
        self.plan = common_plan

    def convert_variable_names(self, beorn_response):
        """
        convert camelCase in name/value pairs to
        match ONF TAPI model.
        e.g. camelCase changes to Camel Case
        """
        topology = beorn_response["topology"]

        for topo in topology:
            for node in topo["data"]["node"]:
                for name in node["name"]:
                    if name["name"] not in self.node_variables_lookup:
                        msg = self.error_formatter(
                            self.MISSING_DATA_ERROR_TYPE,
                            self.TOPOLOGIES_DATA_SUBCATEGORY,
                            f"Node {node} in Beorn response contains undefined parameter {name['name']}",
                            system=self.CIRCUIT_DETAILS_DATABASE,
                        )
                        self.categorized_error = msg
                        self.plan.exit_error(msg)

                    # conversatively right strip white spaces
                    if name["value"] != name["value"].rstrip():
                        self.plan.logger.warning(f"value {name['value']} has trailing white spaces.")
                        name["value"] = name["value"].rstrip()

                    if name["name"] == "hostName":
                        name["value"] = name["value"].upper()

                    if name["name"] == "fqdn":
                        name["value"] = name["value"].upper()

                        # FQDN check, rejects any FQDN without . notation
                        if name["value"].find(".") == -1:
                            msg = self.plan.error_formatter(
                                self.plan.INCORRECT_DATA_ERROR_TYPE,
                                "FQDN",
                                f"invalid format {name['value']}",
                                system=self.plan.CIRCUIT_DETAILS_DATABASE,
                            )
                            self.categorized_error = msg
                            self.plan.exit_error(msg)

                    name["name"] = self.node_variables_lookup[name["name"]]

                for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                    if {"name": "leg"} in ownedNodeEdgePoint["name"]:
                        ownedNodeEdgePoint["name"].remove({"name": "leg"})

                    for name in ownedNodeEdgePoint["name"]:
                        if name["name"] not in self.ownednodeedgepoint_variable_lookup:
                            msg = self.plan.error_formatter(
                                self.MISSING_DATA_ERROR_TYPE,
                                self.TOPOLOGIES_DATA_SUBCATEGORY,
                                (
                                    f"ownedNodeEdgePoint {ownedNodeEdgePoint} in Beorn Response"
                                    f"contains undefined parameter {name['name']}"
                                ),
                                system=self.plan.CIRCUIT_DETAILS_DATABASE,
                            )
                            self.categorized_error = msg
                            self.plan.exit_error(msg)

                        name["name"] = self.ownednodeedgepoint_variable_lookup[name["name"]]

        self.plan.logger.info(
            f"Beorn Response after converting from camelCase is {json.dumps(beorn_response, indent=4)}"
        )

        return beorn_response

    def handle_fia_section(self, beorn_response):
        """
        applies business logic to
        FIA section of Beorn response
        """
        response_with_firewall = self.add_firewall_object(beorn_response)
        response_with_ips = self.translate_ips(response_with_firewall)

        self.plan.logger.info(f"Beorn Response after handling FIA section is {json.dumps(response_with_ips, indent=4)}")

        return response_with_ips

    def translate_ips(self, beorn_response):
        """
        Translates Network IP addresses provided by
        mule soft to required IPs
        """
        fia = beorn_response["service"][0]["data"]["fia"][0]
        fia_endpoint = fia["endPoints"][0]
        service_type = beorn_response["serviceType"]

        if "VOICE" in service_type:
            if "lanIpv4Addresses" not in fia_endpoint:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"Key lanIpv4Addresses missing in fia_endpoint {fia_endpoint}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.plan.exit_error(msg)

            ip_lists = fia_endpoint["lanIpv4Addresses"]
        else:
            if "lanIpv6Addresses" not in fia_endpoint or "lanIpv4Addresses" not in fia_endpoint:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"Key lanIpv6Addresses or lanIpv4Addresses missing in fia_endpoint {fia_endpoint}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.plan.exit_error(msg)

            for ip_lists in [fia_endpoint["lanIpv6Addresses"], fia_endpoint["lanIpv4Addresses"]]:
                for ip in ip_lists:
                    self.verify_network_address(ip)

        if fia["type"] == "DIRECT":
            # Calculate Lan Ipv4 Addresses from the network address provided by MULE SOFT
            new_lanIpv4Addresses = []

            for ip in fia_endpoint["lanIpv4Addresses"]:
                new_lanIpv4Addresses.append(self.increment_ip_address(ip))

            fia_endpoint["lanIpv4Addresses"] = new_lanIpv4Addresses

            # Calculate NextHop Ipv6 Address
            if "wanIpv6Address" in fia_endpoint:
                if fia_endpoint["wanIpv6Address"].split("/")[-1] == "127":
                    fia_endpoint["nextIpv6Hop"] = self.increment_ip_address(fia_endpoint["wanIpv6Address"]).split("/")[
                        0
                    ]
                else:
                    fia_endpoint["wanIpv6Address"] = self.increment_ip_address(fia_endpoint["wanIpv6Address"])
                    fia_endpoint["nextIpv6Hop"] = self.increment_ip_address(fia_endpoint["wanIpv6Address"]).split("/")[
                        0
                    ]

        if fia["type"] == "VOICE":
            # Calculate Lan Ipv4 Addresses from the Voice Gateway device address provided by BEORN
            fia_endpoint["lanIpv4Addresses"] = self.decrement_ip_address(fia_endpoint["lanIpv4Addresses"])
            fia["type"] = "DIRECT"

        if fia["type"] == "STATIC":
            if "wanIpv6Address" in fia_endpoint:
                if fia_endpoint["wanIpv6Address"].split("/")[-1] == "127":
                    fia_endpoint["nextIpv6Hop"] = self.increment_ip_address(fia_endpoint["wanIpv6Address"]).split("/")[
                        0
                    ]
                else:
                    fia_endpoint["wanIpv6Address"] = self.increment_ip_address(fia_endpoint["wanIpv6Address"])
                    fia_endpoint["nextIpv6Hop"] = self.increment_ip_address(fia_endpoint["wanIpv6Address"]).split("/")[
                        0
                    ]

            if "wanIpv4Address" in fia_endpoint:
                fia_endpoint["wanIpv4Address"] = self.increment_ip_address(fia_endpoint["wanIpv4Address"])
                fia_endpoint["nextIpv4Hop"] = self.increment_ip_address(fia_endpoint["wanIpv4Address"]).split("/")[0]

        return beorn_response

    def verify_network_address(self, ip):
        """
        verifies if the provided Ip address
        is a network address or not
        """
        try:
            ipaddress.ip_network(ip)
        except ValueError:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                self.TOPOLOGIES_DATA_SUBCATEGORY,
                f"IP {ip} is not a network address",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.plan.exit_error(msg)

    def increment_ip_address(self, cidr):
        """
        increments an Ip address by 1
        """
        ip, mask = cidr.split("/")

        incremented_ip = ipaddress.ip_address(ip) + 1
        incremented_cidr = f"{incremented_ip}/{mask}"

        return incremented_cidr

    def decrement_ip_address(self, ip_lists):
        """
        decrements an Ip address by 1 for VOICE service types
        """
        cidr = ip_lists
        ip, mask = cidr.split("/")

        decremented_ip = ipaddress.ip_address(ip) - 1
        decremented_cidr = [f"{decremented_ip}/{mask}"]

        return decremented_cidr

    def add_firewall_object(self, beorn_response):
        """
        adds Firewall object to fia part
        of beorn response if not already there
        """
        firewall_object = [
            {"name": "FIA-Filter", "direction": "ingress", "type": "inet"},
            {"name": "FIA-Filter-v6", "direction": "ingress", "type": "inet6"},
        ]

        if "fia" in beorn_response["service"][0]["data"] and "VOICE" not in beorn_response["serviceType"]:
            fia = beorn_response["service"][0]["data"]["fia"]

            if "firewallFilters" not in fia[0]["endPoints"][0]:
                fia[0]["endPoints"][0]["firewallFilters"] = firewall_object

        return beorn_response

    def apply_uni_port_roles(self, beorn_response):
        """
        assuming that port role for UNI isnt specified
        and supplying it through the function
        may have to remove the function later
        """
        for topo in beorn_response["topology"]:
            for node in topo["data"]["node"]:
                for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                    for name in ownedNodeEdgePoint["name"]:
                        if name["name"] == "Role" and "value" not in name:
                            name["value"] = "UNI"

        self.plan.logger.info(
            f"Update Beorn Response after addming UNI port role is: {json.dumps(beorn_response, indent=4)}"
        )
        return beorn_response

    def remove_empty_lag_members(self, beorn_response):
        """
        removing key lag member from
        ownedNodeEdgePoints which are not part
        of LAG
        """
        for topo in beorn_response["topology"]:
            for node in topo["data"]["node"]:
                for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                    for name in ownedNodeEdgePoint["name"]:
                        if name["name"] == "LAG Member" and "value" not in name:
                            ownedNodeEdgePoint["name"].remove(name)

        self.plan.logger.info(
            f"Update Beorn Response after removing empty lag members is: {json.dumps(beorn_response, indent=4)}"
        )
        return beorn_response

    def validate_endpoints_data(self, beorn_response):
        """Checking to see if the list is valid"""
        for service in beorn_response["service"]:
            for evc in service["data"]["evc"]:
                for endpoint in evc["endPoints"]:
                    if not endpoint:
                        self.plan.logger.info(
                            f"Following EndPoints data contains invalid entry {json.dumps(evc['endPoints'], indent=4)}"
                        )
                        msg = self.plan.error_formatter(
                            self.plan.MISSING_DATA_ERROR_TYPE,
                            "Endpoints Data",
                            f"{evc['endPoints']}",
                            system=self.plan.CIRCUIT_DETAILS_DATABASE,
                        )
                        self.categorized_error = msg
                        self.plan.exit_error(msg)

    def apply_descriptions_to_interfaces(self, circuit_details):
        """
        applies description to all the
        interfaces present in beorn
        response
        """
        updated_circuit_details = deepcopy(circuit_details)
        index = 0

        for topo in updated_circuit_details["topology"]:
            for node in topo["data"]["node"]:
                node_role = self.plan.get_node_role(circuit_details, node["uuid"], which_index=index)
                network_interface = self.plan.get_node_network_interface(
                    circuit_details, node["uuid"], which_index=index
                )
                client_interface = self.plan.get_node_client_interface(circuit_details, node["uuid"], which_index=index)

                if network_interface is not None and not network_interface == "None":
                    nw_int_description = self.get_port_description(
                        circuit_details, node_role, f"{node['uuid']}-{network_interface}", "upstream", index
                    )
                    node["name"].append({"name": "Network Interface Description", "value": nw_int_description})

                if client_interface is not None and not client_interface == "None":
                    cli_int_description = self.get_port_description(
                        circuit_details, node_role, f"{node['uuid']}-{client_interface}", "downstream", index
                    )
                    node["name"].append({"name": "Client Interface Description", "value": cli_int_description})

            index += 1

        self.plan.logger.info(f"Updated Circuit Details are: {updated_circuit_details}")
        return updated_circuit_details

    def apply_elan_service(self, circuit_details):
        """updates the circuit details with the ELAN service info"""
        if "ELAN" not in circuit_details["serviceType"].upper():
            return circuit_details

        elan_service = {}

        if (
            "elan" in circuit_details["service"][0]["data"].keys()
            and len(circuit_details["service"][0]["data"]["elan"]) > 0
        ):
            elan_service = circuit_details["service"][0]["data"]["elan"][0]

        if not elan_service.get("asNumber"):
            # Per the CVI / Service Solution Guild for ELAN
            #
            # vrf-target format: target:<National_Backbone_ASN>:<vcid>
            # where National_Backbone_ASN = 7843 and VCID=101000-199999
            elan_service["asNumber"] = 7843

        if not elan_service.get("vrfId"):
            elan_service["vrfId"] = circuit_details["service"][0]["data"]["evc"][0]["evcId"]

        circuit_details["service"][0]["data"]["elan"] = []
        circuit_details["service"][0]["data"]["elan"].append(elan_service)

        return circuit_details

    def get_port_description(self, circuit_details, node_role, port, direction, index):
        """Fetches port description for all types of ports
        Updated
        """
        # adding racutthrough option
        self.cutthrough = RaCutThrough()

        port_role = self.plan.get_port_role(circuit_details, port)
        node, port = self.plan.get_node_port_name_from_uuid(port)
        node_vendor = self.plan.get_node_property(circuit_details, node, "Vendor")
        self.plan.logger.info(f"The device node vendor is: {node_vendor}")

        # To determine if slax verification is required.....has to be JUNIPER all others shall pass
        if node_role in ["PE", "AGG"] and node_vendor == "JUNIPER":
            # This method takes the circuit_details and node attributes and checks the PE(MX) or AGG(QFX)
            # slax scripts and return a boolean, True would mean apply new IDS
            new_description_standard_apply = self.description_standard_decision(circuit_details, node)
        else:
            new_description_standard_apply = True

        port_transportId = self.plan.get_port_transportId(circuit_details, f"{node}-{port}")
        customer_address = self.plan.get_customer_addresses(circuit_details)
        customer_zipcode = customer_address[index].split()[-1]

        self.plan.logger.debug(f"index is {index}")
        self.plan.logger.debug(f"zipcode: {customer_zipcode}")
        self.plan.logger.debug(f"customer addresses {customer_address}")
        self.plan.logger.debug("params are")
        self.plan.logger.debug(f"node role: {node_role}")
        self.plan.logger.debug(f"port: {port}")
        self.plan.logger.debug(f"direction: {direction}")

        if port_role == "UNI":
            cvlan = self.plan.get_cvlans_for_uni_ep(circuit_details, f"{node}-{port}")
            service_type = "EVP-UNI" if cvlan else "EP-UNI"

            if service_type == "EP-UNI":
                if node_role == "PE":
                    if new_description_standard_apply:
                        port_description = f":EP-UNI:{customer_zipcode}:{circuit_details['customerName']}:"
                    else:
                        port_description = (
                            f"EP-UNI:{circuit_details['serviceType']}:{circuit_details['customerName']}@"
                            f"{customer_address[index]}:{circuit_details['serviceName']}:"
                        )
                else:
                    # This is default for CPE devices to use the new standard going forward
                    port_description = f":EP-UNI:{customer_zipcode}:{circuit_details['customerName']}:"
            else:
                port_description = f":EVP-UNI:{customer_zipcode}:{circuit_details['customerName']}:"

        if port_role == "ENNI":
            if new_description_standard_apply:
                port_description = f"{port_transportId}:NNI1:{customer_zipcode}:{circuit_details['customerName']}:"
            else:
                # Previous standard
                port_description = f"NNI:::{circuit_details['serviceName']}:"

        if direction == "downstream" and node_role in ["PE", "MTU", "AGG"] and port_role not in ["UNI", "ENNI"]:
            neighbor = self.plan.get_node_client_neighbor(circuit_details, node, index)

            if neighbor is not None and not neighbor == "None":
                neighbor_role = self.plan.get_node_role(circuit_details, neighbor)
                neighbor_ip = self.plan.get_node_management_ip(circuit_details, neighbor)

            client_neighbor_interface = self.plan.get_node_client_neighbor_interface(circuit_details, node, index)
            self.plan.logger.info(
                f"The device neighbor is: {neighbor} "
                f"the neighbor interface is: {client_neighbor_interface} "
                f"the neighbor ip is: {neighbor_ip}"
            )

            if node_role == "PE" and neighbor_role == "AGG":
                if new_description_standard_apply:
                    if port_transportId is None:
                        # New standard description for PE physical port connected to AGG
                        port_description = (
                            f"{client_neighbor_interface}:AGG:{neighbor}:{client_neighbor_interface}:{neighbor_ip}"
                        )
                else:
                    # Old standard PE physical port connected to AGG
                    port_description = f"AGG:{neighbor}:{client_neighbor_interface}:{neighbor_ip}:{node}:{neighbor}"
            else:
                if new_description_standard_apply:
                    # New standard description for PE physical port to all devices that are not AGG
                    port_description = (
                        f"{port_transportId}:{neighbor_role}:{neighbor}:{client_neighbor_interface}:{neighbor_ip}"
                    )
                else:
                    # Old description standard for PE physical port to all devices that are not AGG
                    port_description = (
                        f"{neighbor_role}:{circuit_details['customerName']}:{customer_address[index]}:{neighbor}:"
                    )

        if direction == "upstream" and node_role in ["CPE", "MTU", "AGG"]:
            neighbor = self.plan.get_node_network_neighbor(circuit_details, node)

            if neighbor is not None and not neighbor == "None":
                neighbor_role = self.plan.get_node_role(circuit_details, neighbor)

            neighbor_interface = self.plan.get_node_network_neighbor_interface(circuit_details, node)
            neighbor_ip = self.plan.get_node_management_ip(circuit_details, neighbor)
            neighbor_role = self.plan.get_node_role(circuit_details, neighbor)

            if node_role == "AGG" or "MTU":
                if new_description_standard_apply:
                    if port_transportId is None:
                        port_description = f"{neighbor_interface}:UPLINK:{neighbor}:{neighbor_interface}:{neighbor_ip}"
                    else:
                        port_description = f"{port_transportId}:UPLINK:{neighbor}:{neighbor_interface}:{neighbor_ip}"
                else:
                    # Previous standard
                    port_description = f"UPLINK:{neighbor}:{neighbor_interface}:{neighbor_ip}:"

            if node_role == "CPE":
                # We decided that by default we are changing all the CPE's to new IDS going forward
                port_description = f"{port_transportId}:UPLINK:{neighbor}:{neighbor_interface}:{neighbor_ip}"

        if (
            node_role == "CPE"
            and "ge114" in self.plan.get_node_model(circuit_details, node).lower()
            and "pro" not in self.plan.get_node_model(circuit_details, node).lower()
        ):
            port_description = self.truncate_port_description(port_description)

        self.plan.logger.info(f"port description for port {port} is {port_description}")

        return port_description.replace("\n", "")

    def check_device_slax_version(self, slax_script_data, evi_slax_version):
        """This is to parse the netconf gathered data for the version of the slax script
        and compares it to the evi_slax_version and determines which description standard
        to apply for specific device and returns True or False

        where called:
            description_standard_decision()

        returns:
            True or False
        """
        pattern = re.compile(r'\$sanity = "(.*?)";')
        matches = pattern.findall(slax_script_data)
        version = float(matches[0].replace("v", ""))
        self.plan.logger.info(f"The current device slax script version on device: {version}")

        if version >= evi_slax_version:
            return True

        return False

    def description_standard_decision(self, circuit_details, node):
        """Makes a decision as to what description standard to apply to PE and AGG juniper devices.
         MTU is not added at this time.

        additional details: parses the slax script and searches for specific version to determine which description
            standard to apply.  If slax name not found or devices PE or AGG not onboarded it assumes old version

        arguments:
            circuit_details, node = 'uuid' or tid
        returns:
            boolean
        """
        # gets the fqdn value
        fqdn = self.plan.get_node_fqdn(circuit_details, node)

        # method from common_plan.py to gather the device resource id by fqdn
        device_resource_id = self.plan.get_network_function_by_host(fqdn)
        agg_slax_scripts = ["Sanity-QFX.slax", "Sanity-ACX.slax"]
        pe_slax_scripts = ["Sanity-L3-EDR.slax", "Sanity-L3.slax"]
        python_scripts = [
            "Sanity-ACX.py",
            "Sanity-QFX.py",
            "Sanity-L3-EDR.py",
            "Sanity-L3.py",
            "Sanity-L3-EDR-v1.9.py",
            "Sanity-L3-v1.9.py",
        ]
        valid_scripts = agg_slax_scripts + pe_slax_scripts + python_scripts

        try:
            show_device_scripts = self.cutthrough.execute_ra_command_file(
                device_resource_id["providerResourceId"], "get_device_scripts.json", headers=None
            ).json()["result"]
        except Exception:
            self.logger.info("No response recieved when checking for sanity scripts on device. Defaulting to New IDS")
            # Default to TRUE (new standard) if PE/AGG is not yet onboard
            return True

        scripts_on_device = None

        if show_device_scripts.get("data"):
            if show_device_scripts["data"].get("configuration", {}):
                scripts_on_device = (
                    show_device_scripts["data"]
                    .get("configuration", {})
                    .get("system", {})
                    .get("scripts", {})
                    .get("commit", {})
                    .get("file")
                )

        if not scripts_on_device:
            self.logger.info("No sanity scripts found on device. Defaulting to New IDS")
            # Default to TRUE (new standard) if PE/AGG is not yet onboard
            return True

        if isinstance(scripts_on_device, list):
            for script in scripts_on_device:
                if "@inactive" not in script and script["name"] in valid_scripts:
                    device_script = script["name"]
                    break
        else:
            if "@inactive" not in scripts_on_device:
                device_script = scripts_on_device["name"]

        if device_script in agg_slax_scripts:
            self.logger.info(
                f"$$$$$ I&O NEEDS TO UPDATE THE SANITY SCRIPT ON THIS DEVICE. CURRENTLY USING: {device_script} $$$$$"
            )
            # AGG slax scripts version 1.4 or higher will recieve new IDS
            return self.sanity_exec(device_resource_id, device_script, 1.4, version_check=True)

        if device_script in pe_slax_scripts:
            self.logger.info(
                f"$$$$$ I&O NEEDS TO UPDATE THE SANITY SCRIPT ON THIS DEVICE. CURRENTLY USING: {device_script} $$$$$"
            )
            # PE slax scripts version 2.44 or higher will recieve new IDS
            return self.sanity_exec(device_resource_id, device_script, 2.44, version_check=True)

        if device_script in python_scripts:
            # All python sanity scripts will recieve new IDS
            self.logger.info(f"Applying new IDS for sanity script: {device_script}")
            return True

    def device_type(self, circuit_details):
        device_details = circuit_details["topology"][0]["data"]["node"][0]["name"]

        for device in device_details:
            if device["name"] == "Model":
                return device["value"]

    def sanity_exec(self, device_resource_id, sanity_script, evi_slax_version, version_check=False):
        # Default to TRUE (new standard) if PE/AGG is not yet onboard
        self.logger.info(f"THIS IS THE SANITY SCRIPT WE ARE TRYING TO RUN: {sanity_script}")
        new_description_standard_apply = True
        sanity_data = {"version": sanity_script}

        try:
            # racutthrough to gather slax data to parse for version
            slax_script_data = self.cutthrough.execute_ra_command_file(
                device_resource_id["providerResourceId"], "show_sanity_script.json", sanity_data, headers=None
            ).json()["result"]

            self.plan.logger.info(f"The is the slax script data: {slax_script_data}")
            self.plan.logger.info(f"The device device_resource_id: {device_resource_id['providerResourceId']}")

            # returns True or False to determine new or old description standard
            if version_check:
                new_description_standard_apply = self.check_device_slax_version(str(slax_script_data), evi_slax_version)
                self.plan.logger.info(f"new_description_standard_apply: {new_description_standard_apply} ")

            return new_description_standard_apply
        except Exception as e:
            self.plan.logger.info(f"this is the exception raised while trying to find the slax script: {e}")
            return False

    def truncate_port_description(self, description):
        """
        truncates port description to 64 characters
        if length is more than 64
        """
        return_value = description.replace("\n", "")

        if len(description) > 64:
            cutme = len(description) - 64
            list_description = description.split(":")
            cut_addr = list_description[2]
            reqd_addr = cut_addr[:-(cutme)]
            list_description[2] = reqd_addr
            return_value = ":".join(c for c in list_description)

        return return_value

    def apply_descriptions_to_service_endpoints(self, circuit_details):
        """
        applies description to service endpoints

        Juniper PE's only get slax verified. All others will be new IDS(Interface Description Standard)
        by default
        """
        updated_circuit_details = deepcopy(circuit_details)
        endpoints = updated_circuit_details["service"][0]["data"]["evc"][0]["endPoints"]
        is_type_2 = False

        # add a method to get all PE's for a list should be a maximum of 2
        pe_node_fqdn_list = self.plan.get_pe_nodes_from_circuit_details(circuit_details)
        self.plan.logger.info(f"pe_node_list: {pe_node_fqdn_list}")
        index = 0

        # remove type 2 endpoint prior to looping through endpoints to determine ids
        for endpoint in endpoints:
            if endpoint.get("type2"):
                is_type_2 = True
                type_2_endpoint_index = endpoints.index(endpoint)
                type_2_endpoint = endpoint
                del endpoints[type_2_endpoint_index]

        for service in updated_circuit_details["service"]:
            for evc in service["data"]["evc"]:
                index = 0

                for endpoint, pe_fqdn in zip(evc["endPoints"], pe_node_fqdn_list):
                    node = pe_fqdn.split(".")[0]
                    node_vendor = self.plan.get_node_property(circuit_details, node, "Vendor")

                    if node_vendor == "JUNIPER":
                        new_description_standard_apply = self.description_standard_decision(circuit_details, node)
                    else:
                        new_description_standard_apply = True

                    self.plan.logger.info(
                        f"pe_node: {node} new_description_standard_apply: {new_description_standard_apply}"
                    )
                    endpoint["userLabel"] = self.get_service_endpoint_description(
                        circuit_details, endpoint["uniId"], index, new_description_standard_apply
                    )
                    index += 1

        self.plan.logger.info(f"Update circuit details after endpoints description is: {updated_circuit_details}")

        # insert type 2 endpoint back into circuit details and apply same IDS logic that other endpoints recieved
        if is_type_2:
            index = self.determine_index_for_type_2_address(circuit_details, type_2_endpoint)
            endpoints.insert(type_2_endpoint_index, type_2_endpoint)
            node = type_2_endpoint["uniId"].split("-")[0]
            node_vendor = self.plan.get_node_property(circuit_details, node, "Vendor")

            if node_vendor == "JUNIPER":
                new_description_standard_apply = self.description_standard_decision(circuit_details, node)
            else:
                new_description_standard_apply = True

            self.plan.logger.info(
                f"TYPE 2 pe_node: {node} new_description_standard_apply: {new_description_standard_apply}"
            )
            endpoints[type_2_endpoint_index]["userLabel"] = self.get_service_endpoint_description(
                circuit_details, type_2_endpoint["uniId"], index, new_description_standard_apply
            )

        return updated_circuit_details

    def determine_index_for_type_2_address(self, circuit_details, type_2_endpoint):
        customer_address = self.plan.get_customer_addresses(circuit_details)
        type_2_address = type_2_endpoint.get("address")
        index = 0 if type_2_address == customer_address[0] else 1

        if len(customer_address) > 1 and type_2_address != customer_address[1]:
            self.logger.info("Unable to determine which side of circuit is Type 2, defaulting to Z-side")

        return index

    def convert_cevlans_to_integer(self, circuit_details):
        """converts ceVlans to integer type"""
        updated_circuit_details = deepcopy(circuit_details)

        for service in updated_circuit_details["service"]:
            for evc in service["data"]["evc"]:
                for endpoint in evc["endPoints"]:
                    if "ceVlans" in endpoint:
                        for vlan in endpoint["ceVlans"]:
                            endpoint["ceVlans"][endpoint["ceVlans"].index(vlan)] = int(vlan)

        self.logger.info(
            f"Update circuit details after converting ceVlans to integer type is: {updated_circuit_details}"
        )

        return updated_circuit_details

    def ctbh_check_and_update(self, circuit_details):
        # Check and update serviceType and customerType if CTBH circuit
        if "CTBH" in circuit_details["serviceType"]:
            circuit_details["customerType"] = "CTBH"
            circuit_details["serviceType"] = "ELINE"

        return circuit_details

    def get_service_endpoint_description(self, circuit_details, endpoint, index, new_description_standard_apply=False):
        """
        fetches description for service endpoints
        """
        # node = self.get_node_port_name_from_uuid(endpoint)[0]
        customer_address = self.plan.get_customer_addresses(circuit_details)
        customer_zipcode = customer_address[index].split()[-1]
        self.plan.logger.debug(f"customer addresses {customer_address}")

        # Call check to update serviceType and customerType if CTBH circuit
        circuit_details = self.ctbh_check_and_update(circuit_details)

        if new_description_standard_apply:
            endpoint_description = (
                f"{circuit_details['serviceName']}:{circuit_details['customerType']}:"
                f"{circuit_details['serviceType']}:{customer_zipcode}:"
            )
        else:
            endpoint_description = (
                f"{circuit_details['customerType']}:{circuit_details['serviceType']}:"
                f"{circuit_details['customerName']}@{customer_address[index]}:{circuit_details['serviceName']}:"
            )

        self.plan.logger.info(f"Service end-point description for {endpoint} is {endpoint_description}")
        return endpoint_description.replace("\n", "")

    def apply_svlans_to_service_endpoints(self, circuit_details):
        """
        applies temporary patch svlans to all service endpints
        """
        updated_circuit_details = deepcopy(circuit_details)

        for service in updated_circuit_details["service"]:
            for evc in service["data"]["evc"]:
                svlan = evc["sVlan"]

                for endpoint in evc["endPoints"]:
                    if "sVlan" not in endpoint.keys():
                        endpoint["sVlan"] = svlan

        self.plan.logger.info(f"Update circuit details after endpoints svlan addition is: {updated_circuit_details}")

        return updated_circuit_details

    def replace_ports_with_lags_service_endpoints(self, circuit_details):
        """
        replace individual ports with LAG ports in
        Service End Points
        """
        new_dict = {}
        new_list = []
        node_port_dict = {}
        spoke_list = self.plan.create_device_dict_from_circuit_details(circuit_details)

        for spoke in spoke_list:
            for k, v in spoke.items():
                if not len(v["Lags"]) == 0:
                    for lag in v["Lags"]:
                        key = k + "-" + list(lag.keys())[0]
                        new_dict[key] = lag[list(lag.keys())[0]]

        for key, value in new_dict.items():
            node_name = key.split("-")[0]

            for member in value:
                new_list.append(f"{node_name}-{member}")

            node_port_dict[key] = new_list
            new_list = []

        for service in circuit_details["service"]:
            for evc in service["data"]["evc"]:
                endpoints_list = evc["endPoints"]

                for lag, members in node_port_dict.items():
                    for member in members:
                        for ep in endpoints_list:
                            if ep["uniId"] == member:
                                ep["uniId"] = lag

                unique_endpoints_list = list(OrderedDict((item["uniId"], item) for item in endpoints_list).values())
                evc["endPoints"] = unique_endpoints_list

            if "fia" in service["data"].keys():
                for fia in service["data"]["fia"]:
                    endpoint = fia["endPoints"][0]

                    for lag, members in node_port_dict.items():
                        for member in members:
                            if endpoint["uniId"] == member:
                                endpoint["uniId"] = lag

        self.plan.logger.debug(f"Update circuit details after endpoints port to lag is: {circuit_details}")

        return circuit_details

    def convert_mx_lag_ports(self, circuit_details):
        """
        Converts the client interface of MX LAG endpoints to the corresponding LAG member interface
        :param circuit_details: circuit details data
        :return: circuit details data
        """
        for topo in circuit_details["topology"]:
            for node in topo["data"]["node"]:
                vendor = [name["value"] for name in node["name"] if name["name"] == "Vendor"][0]
                model = [name["value"] for name in node["name"] if name["name"] == "Model"][0]

                if vendor == "JUNIPER" and "MX" in model:
                    for edge in node["ownedNodeEdgePoint"]:
                        lag_members = [name["value"] for name in edge["name"] if name["name"] == "LAG Member"]

                        if len(lag_members) > 0:
                            port_name = [name["value"] for name in edge["name"] if name["name"] == "Name"][0]

                            for name in node["name"]:
                                if name["name"] == "Client Interface" and name["value"] == port_name:
                                    name["value"] = lag_members[0]

        return circuit_details

    def convert_rad_port_name(self, circuit_details):
        """
        convert RAD port names from format
        ETH PORT 1
        to format
        ETHERNET-1
        """
        self.plan.logger.debug(f"cd before is: {json.dumps(circuit_details, indent=4)}")
        rad_220s = []

        for topo in circuit_details["topology"]:
            for node in topo["data"]["node"]:
                vendor = [name["value"] for name in node["name"] if name["name"] == "Vendor"][0]

                if vendor == "RAD":
                    for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                        if "ETH PORT" in ownedNodeEdgePoint["uuid"]:
                            ownedNodeEdgePoint["uuid"] = ownedNodeEdgePoint["uuid"].replace("ETH PORT ", "ETHERNET-")
                        else:
                            ownedNodeEdgePoint["uuid"] = ownedNodeEdgePoint["uuid"].replace(
                                node["uuid"], f"{node['uuid']}-ETHERNET"
                            )

                        for name in ownedNodeEdgePoint["name"]:
                            if name["name"] == "Name":
                                if "ETH PORT" in name["value"].upper():
                                    name["value"] = name["value"].replace("ETH PORT ", "ETHERNET-")
                                else:
                                    name["value"] = f"ETHERNET-{name['value']}"
                                    rad_220s.append(node["uuid"])

            rad_220s = list(set(rad_220s))

            for link in topo["data"]["link"]:
                link["uuid"] = link["uuid"].replace("ETH PORT ", "ETHERNET-")
                new_nodeEdgePoint = []

                for nodeEdgePoint in link["nodeEdgePoint"]:
                    new_nodeEdgePoint.append(nodeEdgePoint.replace("ETH PORT ", "ETHERNET-"))

                link["nodeEdgePoint"] = new_nodeEdgePoint

                for rad_220 in rad_220s:
                    if rad_220 in link["uuid"] and not rad_220 + "-ETHERNET" in link["uuid"]:
                        link["uuid"] = link["uuid"].replace(rad_220, rad_220 + "-ETHERNET")

        for service in circuit_details["service"]:
            for evc in service["data"]["evc"]:
                for ep in evc["endPoints"]:
                    ep["uniId"] = ep["uniId"].replace("ETH PORT ", "ETHERNET-")

                    for rad_220 in rad_220s:
                        if rad_220 in ep["uniId"]:
                            ep["uniId"] = ep["uniId"].replace(rad_220, rad_220 + "-ETHERNET")

        self.plan.logger.debug(f"cd after is: {json.dumps(circuit_details, indent=4)}")

        return circuit_details

    def convert_cisco_and_adva116pro_port_name(self, circuit_details):
        """
        convert CISCO port names to format

        TenGigE0/0/1/3,  GigabitEthernet0/1/0/0, MgmtEth0-RSP0-CPU0-0-10.92.19.71/24, BVI1116,
        HundredGigE0/0/1/3,  Bundle-Ether7-7.7.7.7/24

        "BDI1000-97.105.228.179/28" need to check with Sahil
        Port-channel

        {
            "source": "Te([0-9\/]+)",
            "destination": "TenGigE\\1"
        },
        {
            "source": "Hu([0-9\/]+)",
            "destination": "HundredGigE\\1"
        },
        {
            "source": "Gi([0-9\/]+)",
            "destination": "GigabitEthernet\\1"
        },
        {
            "source": "BV([0-9]+)",
            "destination": "BVI\\1"
        },
        {
            "source": "BE([0-9]+)",
            "destination": "Bundle-Ether\\1"
        }
        """
        pattern_dict = {
            "TE": "TenGigabitEthernet",  # Need to check with Sahil for devices giving TenGigabitEthernet0-0-3
            "GI": "GigabitEthernet",
            "HU": "HundredGigE",
            "BV": "BVI",
            "BE": "Bundle-Ether",
            "FA": "FastEthernet",
        }
        uuid_dict = {}

        for topo in circuit_details["topology"]:
            for node in topo["data"]["node"]:
                vendor = [name["value"] for name in node["name"] if name["name"] == "Vendor"][0]
                model = [name["value"] for name in node["name"] if name["name"] == "Model"][0]

                if vendor == "CISCO":
                    for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                        if (ownedNodeEdgePoint["uuid"][3]) == "-":
                            _, __, port = ownedNodeEdgePoint["uuid"].split("-", 2)
                        else:
                            device, port = ownedNodeEdgePoint["uuid"].split("-", 1)

                        port = port.replace("/", "-")
                        changed_port_name = port.replace(port[:2], pattern_dict[port[:2]])
                        changed_owned_node_edge_point = f"{device}-{changed_port_name}"
                        uuid_dict[ownedNodeEdgePoint["uuid"]] = changed_owned_node_edge_point
                        ownedNodeEdgePoint["uuid"] = changed_owned_node_edge_point

                        for name in ownedNodeEdgePoint["name"]:
                            if name["name"] == "Name":
                                name["value"] = changed_port_name

                            if name["name"] == "LAG Member":
                                lag_mem = name["value"]
                                changed_lag_mem = lag_mem.replace(lag_mem[:2], pattern_dict[lag_mem[:2]])
                                name["value"] = changed_lag_mem

                elif self.is_tengig_adva(vendor, model):
                    for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                        if (ownedNodeEdgePoint["uuid"][3]) == "-":
                            _, __, port = ownedNodeEdgePoint["uuid"].split("-", 2)
                        else:
                            device, port = ownedNodeEdgePoint["uuid"].split("-", 1)

                        changed_port_name = port.replace("ETH_PORT", "ETH-PORT")
                        changed_uuid = f"{device}-{changed_port_name}"
                        ownedNodeEdgePoint["uuid"] = changed_uuid

                        for name in ownedNodeEdgePoint["name"]:
                            if name["name"] == "Name":
                                name["value"] = changed_port_name

            for link in topo["data"]["link"]:
                uuid = link["uuid"].replace("ETH_PORT", "ETH-PORT")
                link_devices = uuid.split("_")

                if uuid_dict.get(link_devices[0]):
                    link_devices[0] = uuid_dict[link_devices[0]]

                if uuid_dict.get(link_devices[1]):
                    link_devices[1] = uuid_dict[link_devices[1]]

                link["uuid"] = f"{link_devices[0]}_{link_devices[1]}"
                new_nodeEdgePoint = []

                for nodeEdgePoint in link["nodeEdgePoint"]:
                    if uuid_dict.get(nodeEdgePoint):
                        new_nodeEdgePoint.append(uuid_dict[nodeEdgePoint])
                    else:
                        new_nodeEdgePoint.append(nodeEdgePoint.replace("ETH_PORT", "ETH-PORT"))

                link["nodeEdgePoint"] = new_nodeEdgePoint

        for service in circuit_details["service"]:
            for evc in service["data"]["evc"]:
                for ep in evc["endPoints"]:
                    if uuid_dict.get(ep["uniId"]):
                        ep["uniId"] = uuid_dict[ep["uniId"]]
                    else:
                        ep["uniId"] = ep["uniId"].replace("ETH_PORT", "ETH-PORT")

            if "fia" in service["data"]:
                for ep in service["data"]["fia"][0]["endPoints"]:
                    if uuid_dict.get(ep["uniId"]):
                        ep["uniId"] = uuid_dict[ep["uniId"]]
                    else:
                        ep["uniId"] = ep["uniId"].replace("ETH_PORT", "ETH-PORT")

        return circuit_details

    def is_tengig_adva(self, vendor, model):
        if vendor != "ADVA":
            return False
        tengig_advas = ["XG116PRO", "XG118", "XG120"]
        for adva in tengig_advas:
            if adva in model:
                return True
        return False

    def convert_adva_vendor_name(self, circuit_details):
        """
        check if adva node is 825 and convert vendor if necessary
        """
        for topo in circuit_details["topology"]:
            for node in topo["data"]["node"]:
                model = [name["value"] for name in node["name"] if name["name"] == "Model"][0]

                for data in node["name"]:
                    if data["name"] == "Vendor" and data["value"] == "ADVA" and model == "FSP 150CCF-825":
                        data["value"] = "ADVA0825"

        return circuit_details

    def add_connection_type_to_name(self, circuit_details):
        """
        check if connection type key is present in EVC endpoints
        and add "point-2-point as default if not present
        """
        for service in circuit_details["service"]:
            for evc in service["data"]["evc"]:
                if "connectionType" not in evc:
                    evc["connectionType"] = "Point to Point"

        return circuit_details

    def delete_perftier(self, circuit_details):
        """
        Deletes the key perfTier from service section
        of beorn response
        """
        circuit_details["service"][0]["data"]["evc"][0].pop("perfTier", None)
        return circuit_details

    def convert_customer_name(self, circuit_details):
        """
        converts Customer name with special characters
        """
        circuit_details["customerName"] = circuit_details["customerName"].encode("ascii", "ignore").decode()
        return circuit_details

    def convert_mx_cpe(self, circuit_details):
        """
        converts all mx CPE roles to PE roles
        """
        for topo in circuit_details["topology"]:
            for node in topo["data"]["node"]:
                vendor = [name["value"] for name in node["name"] if name["name"] == "Vendor"][0]
                model = [name["value"] for name in node["name"] if name["name"] == "Model"][0]

                if vendor.upper() == "JUNIPER" and "MX" in model.upper():
                    for name in node["name"]:
                        if name["name"].upper() == "ROLE":
                            name["value"] = "PE"

        return circuit_details

    def planned_link_sanity_check(self, circuit_details):
        """
        This is a function to weed out topologies with -planned- legs in the design, which were causing outages.
        Mechanically it looks for TIDs connected to multiple other TIDs by looping throught the UUID TIDs for multiples.
        For example, if the UUIDs show a Juniper TID connected to both a QFX TID and a CPE TID,
        it will throw an exception.

        example for a GOOD link_list = ['KYLETX051CW-KYLETX050QW',
                                        'KYLETX051CW-KYLETX050QW',
                                        'KYLETX050QW-SMRCTXAO1ZW']

        example for a BAD link_list = ['KYLETX051CW-KYLETX050QW',
                                       'KYLETX051CW-KYLETX050QW',
                                       'KYLETX051CW-SMRCTXAO1ZW',
                                       'KYLETX050QW-SMRCTXAO1ZW']

        5/24/22-David Edelson: Additional functionality added to ensure any one port is only linked once within the
        topology.
        """
        self.plan.logger.info("Starting planned link sanity check")

        for topo in circuit_details["topology"]:
            link_list = []
            port_list = []
            dupe_ports = []
            port_set = set()

            for link in topo["data"]["link"]:
                for nep in link["nodeEdgePoint"]:
                    port_list.append(nep)

                if "ETH_PORT" in link["uuid"]:
                    link_list.append(link["uuid"].replace("ETH_PORT", "ETHPORT"))
                else:
                    link_list.append(link["uuid"])

            self.plan.logger.info(f"========= PORT_LIST: {port_list}")

            # Iterate through ports, ensure no ports duplicated within links.
            for port in port_list:
                port_set.add(port) if port not in port_set else dupe_ports.append(port)

            if len(dupe_ports) > 0:
                msg = self.plan.error_formatter(
                    self.plan.INCORRECT_DATA_ERROR_TYPE,
                    "Port(s) Linked More Than Once",
                    f"{dupe_ports}",
                    system=self.plan.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                raise Exception(msg)

            for link in link_list:
                for link2 in link_list:
                    if (
                        self.plan.get_node_port_name_from_uuid(link.split("_", 1)[0])[0]
                        == self.plan.get_node_port_name_from_uuid(link2.split("_", 1)[0])[0]
                    ):
                        if (
                            self.plan.get_node_port_name_from_uuid(link.split("_", 1)[1])[0]
                            != self.plan.get_node_port_name_from_uuid(link2.split("_", 1)[1])[0]
                        ):
                            msg = self.plan.error_formatter(
                                self.plan.INCORRECT_DATA_ERROR_TYPE,
                                "Multiple Device Pairings",
                                system=self.plan.CIRCUIT_DETAILS_DATABASE,
                            )
                            self.categorized_error = msg
                            raise Exception(msg)

                    if (
                        self.plan.get_node_port_name_from_uuid(link.split("_", 1)[1])[0]
                        == self.plan.get_node_port_name_from_uuid(link2.split("_", 1)[1])[0]
                    ):
                        if (
                            self.plan.get_node_port_name_from_uuid(link.split("_", 1)[0])[0]
                            != self.plan.get_node_port_name_from_uuid(link2.split("_", 1)[0])[0]
                        ):
                            msg = self.plan.error_formatter(
                                self.plan.INCORRECT_DATA_ERROR_TYPE,
                                "Multiple Device Pairings",
                                f"{link.split('_', 1)[0]} {link2.split('_', 1)[0]}",
                                system=self.plan.CIRCUIT_DETAILS_DATABASE,
                            )
                            self.categorized_error = msg
                            raise Exception(msg)

    def Lag_Sanity_check(self, circuit_details):
        """check if circuit details is missing lag details,
           to be used to avoid infinite loop in Circuit details collector

        example for link_list = ['KYLETX051CW-ET-0/3/0_KYLETX050QW-ET-0/0/96',
                                 'KYLETX051CW-ET-2/3/0_KYLETX050QW-ET-1/0/96',
                                 'KYLETX050QW-GE-0/0/47_SMRCTXAO1ZW-ETHERNET-1']
        example for linked_nodes_list = ['KYLETX051CW-KYLETX050QW',
                                         'KYLETX051CW-KYLETX050QW',
                                         'KYLETX050QW-SMRCTXAO1ZW']
        example for duplicates_linked_nodes_list = ['KYLETX051CW-KYLETX050QW']
        example for indoubt_nodes = ['KYLETX051CW', 'KYLETX050QW']

        """
        link_list = []
        linked_nodes_list = []
        duplicates_linked_nodes_list = []
        indoubt_nodes = []

        for topo in circuit_details["topology"]:
            for link in topo["data"]["link"]:
                link_list.append(link["uuid"])

        for link in link_list:
            linked_nodes = self.get_nodes_from_link(link)
            linked_nodes_list.append(linked_nodes)

        for linked_nodes in linked_nodes_list:
            if linked_nodes_list.count(linked_nodes) > 1:
                duplicates_linked_nodes_list.append(linked_nodes)

        duplicates_linked_nodes_list = list(set(duplicates_linked_nodes_list))

        for linked_nodes in duplicates_linked_nodes_list:
            node1, node2 = linked_nodes.split("-", 1)
            indoubt_nodes.extend((node1, node2))

        if indoubt_nodes != []:
            self.is_lag_present(indoubt_nodes, circuit_details)

    def get_nodes_from_link(self, link):
        node = link.split("_")
        return f"{node[0].split('-')[0]}-{node[1].split('-')[0]}"

    def is_lag_present(self, indoubt_nodes, circuit_details):
        # name_value_pair = {}
        # port_list = []
        lag_members = []

        for topo in circuit_details["topology"]:
            for node in topo["data"]["node"]:
                for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                    node_name = self.plan.get_node_port_name_from_uuid(ownedNodeEdgePoint["uuid"])[0]
                    port_name = self.plan.get_node_port_name_from_uuid(ownedNodeEdgePoint["uuid"])[1]

                    if node_name in indoubt_nodes:
                        for name in ownedNodeEdgePoint["name"]:
                            if name["name"] == "LAG Member":
                                # lag_name = name["value"]
                                lag_members.append(port_name)

        if lag_members == []:
            msg = self.plan.error_formatter(
                self.plan.MISSING_DATA_ERROR_TYPE,
                "Lag Details",
                f"{port_name}",
                system=self.plan.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            raise Exception(msg)

    def get_node_name(self, node_port):
        node_name = None

        # existing logic. node name can have a - at that position
        if node_port[3] == "-":
            node_name_1, node_name_2, _ = node_port.split("-", 2)
            node_name = f"{node_name_1}-{node_name_2}"
        else:
            node_name = node_port.split("-")[0]

        return node_name

    def validate_circuit_details(self, cd):
        self.validate_structure(cd)
        self.validate_endpoints_data(cd)
        self.validate_links(cd)

    def validate_structure(self, cd):
        """
        Verify that the json response from Beorn has expected elements.
        Here we verify the top level elements.
        Each individual element properties will be verified at the specific validation functions.
        """
        service = cd.get("service")

        if not service:
            msg = self.plan.error_formatter(
                self.plan.MISSING_DATA_ERROR_TYPE,
                self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                "service not found in top level circuit details response",
                system=self.plan.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.plan.exit_error(msg)

        for s in service:
            data = s.get("data")

            if not data:
                msg = self.plan.error_formatter(
                    self.plan.MISSING_DATA_ERROR_TYPE,
                    self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                    "data not found in service of circuit details response",
                    system=self.plan.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.plan.exit_error(msg)

            evcs = data.get("evc")

            if not evcs:
                msg = self.plan.error_formatter(
                    self.plan.MISSING_DATA_ERROR_TYPE,
                    self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                    "evc not found in service->data of circuit details response",
                    system=self.plan.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.plan.exit_error(msg)

            for evc in evcs:
                endpoints = evc.get("endPoints")

                if not endpoints:
                    msg = self.plan.error_formatter(
                        self.plan.MISSING_DATA_ERROR_TYPE,
                        self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                        "endPoints not found in service->data->evc of circuit details response",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

        topology = cd.get("topology")

        if not topology:
            msg = self.plan.error_formatter(
                self.plan.MISSING_DATA_ERROR_TYPE,
                self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                "topology not found in top level circuit details response",
                system=self.plan.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.plan.exit_error(msg)

        for t in topology:
            data = t.get("data")

            if not data:
                msg = self.plan.error_formatter(
                    self.plan.MISSING_DATA_ERROR_TYPE,
                    self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                    "data not found in topology of circuit details response",
                    system=self.plan.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.plan.exit_error(msg)

            # We have valid case of having only PE and link being empty array []
            # We will only fail if link is not in the Beorn response
            links = data.get("link", None)

            if links is None:
                msg = self.plan.error_formatter(
                    self.plan.MISSING_DATA_ERROR_TYPE,
                    self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                    "link not found in topology->data of circuit details response",
                    system=self.plan.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.plan.exit_error(msg)

            for link in links:
                # {
                #   "nodeEdgePoint": [
                #     "AUSDTXIR2QW-XE-1/0/35",
                #     "AUSLTXAB6AW-ETH PORT 0/1"
                #   ],
                #   "uuid": "AUSDTXIR2QW-XE-1/0/35_AUSLTXAB6AW-ETH PORT 0/1"
                # }
                if not link.get("uuid"):
                    msg = self.plan.error_formatter(
                        self.plan.MISSING_DATA_ERROR_TYPE,
                        self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"topology->data->link {link} does not contain uuid",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                if not link.get("nodeEdgePoint"):
                    msg = self.plan.error_formatter(
                        self.plan.MISSING_DATA_ERROR_TYPE,
                        self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"topology->data->link {link} does not contain nodeEdgePoint",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                if len(link["nodeEdgePoint"]) != 2:
                    msg = self.plan.error_formatter(
                        self.plan.INCORRECT_DATA_ERROR_TYPE,
                        self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"topology->data->link {link} does not contain 2 elements in the nodeEdgePoint",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

            nodes = data.get("node")

            if not nodes:
                msg = self.plan.error_formatter(
                    self.plan.MISSING_DATA_ERROR_TYPE,
                    self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                    "node not found in topology->data of circuit details response",
                    system=self.plan.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.plan.exit_error(msg)

            for n in nodes:
                names = n.get("name")

                if not names:
                    msg = self.plan.error_formatter(
                        self.plan.MISSING_DATA_ERROR_TYPE,
                        self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                        "name not found in topology->data->node of circuit details response",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                for name in names:
                    # "name": [
                    # {"name": "hostName", "value": "AUSLTXAB6AW"},
                    # {"name": "deviceRole", "value": "MTU"},
                    # {"name": "vendor", "value": "RAD"},
                    # {"name": "model", "value": "ETX-2I-10G/4SFPP/24SFP"},
                    # {"name": "managementIP", "value": "97.77.67.20"},
                    # {"name": "address", "value": "11921 N MOPAC EXPY"},
                    # {"name": "fqdn", "value": "AUSLTXAB6AW.DEV.CHTRSE.COM"}]
                    if not name.get("name"):
                        msg = self.plan.error_formatter(
                            self.plan.MISSING_DATA_ERROR_TYPE,
                            self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                            f"name not found in topology->data->node->name of circuit details response: {name}",
                            system=self.plan.CIRCUIT_DETAILS_DATABASE,
                        )
                        self.categorized_error = msg
                        self.plan.exit_error(msg)

                    if not name.get("value"):
                        device_missing_value = self.get_device_name(names)
                        msg = self.plan.error_formatter(
                            self.plan.MISSING_DATA_ERROR_TYPE,
                            self.plan.TOPOLOGIES_DATA_SUBCATEGORY,
                            (
                                "value not found in topology->data->node->name of circuit details response "
                                f"for device {device_missing_value}: {name}"
                            ),
                            system=self.plan.CIRCUIT_DETAILS_DATABASE,
                        )
                        self.categorized_error = msg
                        self.plan.exit_error(msg)

    def get_device_name(self, names):
        for name in names:
            if name.get("name") == "hostName":
                return name.get("value")

    def validate_links(self, cd):
        """
        We have seen response from Beorn with links PE->AGG, AGG->MTU and then PE->MTU
        We cannot handle that because at the MTU handling, the neighbor is PE, so it goes back to PE
        and goes into a tight loop
        Note: call validate_structure() before calling this
        """
        topology = cd.get("topology")

        for t in topology:
            data = t.get("data")
            links = data.get("link")
            nodes = data.get("node")

            hostNameToDeviceRole = {}

            for n in nodes:
                # Turn the following into a dict
                # "name": [
                # {"name": "hostName", "value": "AUSLTXAB6AW"},
                # {"name": "deviceRole", "value": "MTU"},
                # {"name": "vendor", "value": "RAD"},
                # {"name": "model", "value": "ETX-2I-10G/4SFPP/24SFP"},
                # {"name": "managementIP", "value": "97.77.67.20"},
                # {"name": "address", "value": "11921 N MOPAC EXPY"},
                # {"name": "fqdn", "value": "AUSLTXAB6AW.DEV.CHTRSE.COM"}]
                #
                # {"hostName": "AUSLTXAB6AW",
                #  "deviceRole": "MTU",
                #  "vendor": "RAD",
                #  "model": "ETX-2I-10G/4SFPP/24SFP",
                #  "managementIP": "97.77.67.20",
                #  "address": "11921 N MOPAC EXPY",
                #  "fqdn": "AUSLTXAB6AW.DEV.CHTRSE.COM"}
                name_lookup = {}
                names = n.get("name")

                for name in names:
                    name_lookup[name["name"]] = name["value"]

                deviceRole = name_lookup.get("deviceRole")

                if not deviceRole:
                    msg = self.plan.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"topology->data->node->name {n['name']} does not contain deviceRole",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                hostName = name_lookup.get("hostName")

                if not hostName:
                    msg = self.plan.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"topology->data->node->name {n['name']} does not contain hostName",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                hostNameToDeviceRole[hostName] = deviceRole

            l_lookup = defaultdict(list)

            for link in links:
                src = self.get_node_name(link["nodeEdgePoint"][0])

                if not src:
                    msg = self.plan.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"invalid node name in nodeEdgePoint {link['nodeEdgePoint'][0]}",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                dst = self.get_node_name(link["nodeEdgePoint"][1])

                if not dst:
                    msg = self.plan.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"invalid node name in nodeEdgePoint {link['nodeEdgePoint'][1]}",
                        system=self.plan.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                l_lookup[src].append(dst)

            # find the host name associated with CPE. no CPE is OK
            cpe_host = None

            for h_n, r in hostNameToDeviceRole.items():
                if r == "CPE":
                    cpe_host = h_n
                    break

            # Check that we don't have a loop for the PE
            for k, v in l_lookup.items():
                deviceRole = hostNameToDeviceRole.get(k)

                if deviceRole == "PE":
                    # existing logic, remove the CPE entry before counting number of links
                    if cpe_host and cpe_host in v:
                        v.remove(cpe_host)

                    # remove duplicate entries (i.e. LAG related)
                    v_set = set(v)

                    if len(v_set) > 1:
                        msg = self.plan.error_formatter(
                            self.plan.INCORRECT_DATA_ERROR_TYPE,
                            "PE Multiple Links",
                            f"{k} {v_set}",
                            system=self.plan.CIRCUIT_DETAILS_DATABASE,
                        )
                        self.categorized_error = msg
                        self.plan.exit_error(msg)

            # reset for the next leg of the topology
            l_lookup = defaultdict(list)

    def validate_device_roles(self, cd):
        """
        Validating the device roles in the Beorn response
        """
        topology = cd.get("topology")

        for t in topology:
            data_value = t.get("data")
            nodes = data_value.get("node")

            for n in nodes:
                uuid = n.get("uuid")
                node_vendor = self.plan.get_node_vendor(cd, uuid)
                node_model = self.plan.get_node_model(cd, uuid)
                node_role = self.plan.get_node_role(cd, uuid)

                if "RAD" in node_vendor:
                    model = f"RAD {node_model}"

                    if "220A" in node_model:
                        model = "RAD 220A"
                    elif "2I" in node_model:
                        model = "RAD 2I"
                    elif "203" in node_model:
                        model = "RAD ETX203AX"
                elif "JUNIPER" in node_vendor:
                    model = f"JUNIPER {node_model}"

                    if "EX" in node_model:
                        model = "JUNIPER EX4200"
                    elif "QFX" in node_model:
                        model = "JUNIPER QFX"
                    elif "ACX" in node_model:
                        model = "JUNIPER ACX5448"
                elif "ADVA" in node_vendor:
                    model = f"ADVA {re.split('-|/', node_model)[1]}"
                elif "CISCO" in node_vendor:
                    model = f"CISCO {node_model}"
                # At this time only the CIENA 3931 IS SUPPORTED AS A PRE-INSTALL CTBH CPE
                # THE MODEL NAME FOR THIS DEVICE INCLUDES THE VENDOR NAME: "CIENA 3931"
                elif "CIENA" in node_vendor:
                    model = node_model
                elif "NOKIA" in node_vendor:
                    model = f"NOKIA {node_model}"
                elif node_vendor not in ["RAD", "JUNIPER", "ADVA", "CISCO", "CIENA", "NOKIA"]:
                    msg = self.plan.error_formatter(
                        self.UNSUPPORTED_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"DEVICE VENDOR {node_vendor} is NOT SUPPORTED",
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)

                if model not in (self.device_roles_lookup[node_role]):
                    msg = self.plan.error_formatter(
                        self.UNSUPPORTED_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"DEVICE ROLE {node_role} is INVALID for {node_vendor} {node_model}",
                    )
                    self.categorized_error = msg
                    self.plan.exit_error(msg)
