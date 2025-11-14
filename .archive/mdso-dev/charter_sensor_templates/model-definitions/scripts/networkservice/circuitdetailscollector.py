"""-*- coding: utf-8 -*-

CircuitDataCollection Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of CircuitDataCollection plans

"""

import json
import re
import sys
from copy import deepcopy
from typing import Any

from scripts.common_plan import CommonPlan
from scripts.networkservice.businesslogic import BusinessLogic

sys.path.append("model-definitions")


class Activate(CommonPlan):
    """this is the class that is called for the initial activation of the
    CircuitDataCollection.  The only input it requires is the circuit_id
    associated with the service.
    """

    MANDATORY_RESPONSE_STRUCTURE_ITEMS = [
        "customerName",
        "serviceName",
        "serviceType",
        "modelVersion",
        "topology",
        "service",
    ]

    MANDATORY_TOPOLOGY_ITEMS = ["model", "version", "data"]
    MANDATORY_TOPOLOGY_DATA_ITEMS = ["node"]
    MANDATORY_TOPOLOGY_DATA_NODE_ITEMS = ["ownedNodeEdgePoint", "uuid", "name"]
    MANDATORY_TOPOLOGY_DATA_NODE_NAME_ITEMS = ["Host Name", "Role", "Vendor", "Model"]
    MANDATORY_TOPOLOGY_DATA_NODE_OWNEDNODEEDGEPOINT_ITEMS = ["uuid", "name"]
    MANDATORY_TOPOLOGY_DATA_LINK_ITEMS = ["nodeEdgePoint", "uuid"]
    MANDATORY_SERVICE_ITEMS = ["model", "version", "data"]
    MANDATORY_SERVICE_DATA_ITEMS = ["evc"]

    MANDATORY_SERVICE_DATA_EVC_ITEMS = [
        "endPoints",
        "connectionType",
        "adminState",
        "userLabel",
        "maxNumOfEvcEndPoint",
        "serviceType",
    ]
    MANDATORY_SERVICE_DATA_EVC_ENDPOINTS_ITEMS = ["uniId", "adminState", "userLabel", "sVlan"]
    MANDATORY_SERVICE_DATA_FIA_ITEMS = ["type", "endPoints"]
    MANDATORY_SERVICE_DATA_FIA_ENDPOINTS_ITEMS = ["uniId"]
    MANDATORY_SERVICE_DATA_ELAN_ITEMS = []

    CD_RESOURCE_POST_ERROR_TYPE_REGEX = 'keyword: "([^"]+)"'
    CD_RESOURCE_POST_ERROR_FAILURE_REGEX = "error: ([^\n\r]+)"

    def process(self):
        self.use_alternate_url = bool(self.properties.get("use_alternate_circuit_details_server", False))
        self.stage = self.properties["stage"]
        self.network_service_resource_id = self.properties.get("network_service_resource_id", "")
        self.operation = self.properties["operation"]
        self.business_logic = BusinessLogic(self)
        self.circuit_id = self.properties["circuit_id"]

        # Set return Object
        output = {"circuit_details_id": "", "leg_details_ids": []}
        created_leg_details_ids = []

        # Instantiate Status Update Product
        # ! This is best effort
        try:
            status_updater_product = self.get_built_in_product(self.BUILT_IN_STATUS_UPDATER_TYPE)
            status_updater_details = {
                "label": "{}.status_updater".format(self.circuit_id),
                "productId": status_updater_product["id"],
                "properties": {
                    "network_service_resource_id": self.network_service_resource_id,
                    "circuit_id": self.circuit_id,
                    "operation": self.operation,
                },
            }
            self.bpo.resources.create(
                parent_resource_id=self.network_service_resource_id, data=status_updater_details, wait_active=False
            )
        except Exception:
            # ! No Exit, Best Effort
            self.logger.exception("failed to create status_updater resource")

        # Get Circuit information(Topology) from Circuit details server(SENSE -> BEORN)
        topology = self.get_topology_from_sense()

        # Check for CID in top level, if exists single leg process begins
        if topology.get("serviceName"):
            output["circuit_details_id"] = self.circuit_details_process(topology)
            created_leg_details_ids.append(output["circuit_details_id"])
            output["leg_details_ids"] = created_leg_details_ids
        else:
            for leg in topology:
                created_leg_details_ids.append(self.circuit_details_process(topology[leg], leg))

            output["circuit_details_id"] = created_leg_details_ids[0]
            output["leg_details_ids"] = created_leg_details_ids

        return output

    def run_business_logic(self, circuit_details: dict, leg_identifier: str = ""):  # -> dict[str, Any]:
        """Run business Logic on Topology from BEORN

        :param circuit_details: This is the topology of a single leg provided by BEORN
        :type circuit_details: dict
        :param leg_identifier: Name of the leg usually how BEORN Identifies it ex. PRIMARY/SECONDARY for CTBH,
        :type leg_identifier: str, optional
        :return: Returns the business logic corrected topology aka Circuit Details
        :rtype: dict
        """

        if leg_identifier:
            circuit_id = self.circuit_id + "-" + leg_identifier
        else:
            circuit_id = self.circuit_id
        # Do upfront validation of the response and only continue if it is valid
        self.business_logic.validate_circuit_details(circuit_details)

        # convert variable names from camel case to as expected by code
        cd_corrected = self.business_logic.convert_variable_names(circuit_details)

        # convert all MX CPEs to PEs
        cd_corrected = self.business_logic.convert_mx_cpe(cd_corrected)

        # Do validation of the device roles in response and only continue if all are valid
        self.business_logic.validate_device_roles(cd_corrected)

        # Check if BEORN payload has the correct lag info
        self.business_logic.Lag_Sanity_check(cd_corrected)

        # Check if BEORN payload has conflicting Planned Path
        self.business_logic.planned_link_sanity_check(cd_corrected)

        # Correct the FIA section if present
        if cd_corrected["serviceType"] == "FIA" or cd_corrected["serviceType"] == "VOICE":
            cd_corrected = self.business_logic.handle_fia_section(cd_corrected)

        # Temporary patch for UNI ports
        cd_corrected = self.business_logic.apply_uni_port_roles(cd_corrected)

        # Temporary patch to remove lag members key without values
        cd_corrected = self.business_logic.remove_empty_lag_members(cd_corrected)

        # Convert names of RAD ports
        cd_corrected = self.business_logic.convert_rad_port_name(cd_corrected)

        # Convert names of CISCO ports
        cd_corrected = self.business_logic.convert_cisco_and_adva116pro_port_name(cd_corrected)

        # Convert vendor of ADVA 825 device
        cd_corrected = self.business_logic.convert_adva_vendor_name(cd_corrected)

        # Convert Customer name with special characters
        cd_corrected = self.business_logic.convert_customer_name(cd_corrected)

        # update the topology with neighbor information
        updated_topology = self.update_circuit_details_with_neighbor_info(cd_corrected)
        cd_data_compliant = deepcopy(cd_corrected)
        cd_data_compliant["topology"] = updated_topology
        cd_svlan_added = self.business_logic.apply_svlans_to_service_endpoints(cd_data_compliant)
        # Converting cevlan to integer to match type of circuit details tosca
        cd_cevlan_conversion = self.business_logic.convert_cevlans_to_integer(cd_svlan_added)
        cd_connection_type_added = self.business_logic.add_connection_type_to_name(cd_cevlan_conversion)
        cd_lag_instead_of_ports = self.business_logic.replace_ports_with_lags_service_endpoints(
            cd_connection_type_added
        )
        cd_mx_lag = self.business_logic.convert_mx_lag_ports(cd_lag_instead_of_ports)
        cd_interface_description = self.business_logic.apply_descriptions_to_interfaces(cd_mx_lag)
        cd_service_description = self.business_logic.apply_descriptions_to_service_endpoints(cd_interface_description)
        cd_service_description = self.business_logic.apply_elan_service(cd_service_description)

        # Compliancy check on the data
        self.data_compliancy_check(cd_service_description)

        # Get the CircuitDetails product
        product = self.get_built_in_product(self.BUILT_IN_CIRCUIT_DETAILS_TYPE)

        # Build Circuit Details
        label = circuit_id + ".cd"
        circuit_details = {
            "label": label,
            "productId": product["id"],
            "properties": {
                "circuit_id": cd_service_description["serviceName"],
                "stage": self.stage,
                "network_service_resource_id": self.network_service_resource_id,
                "modelVersion": float(cd_service_description["modelVersion"]),
                "serviceName": cd_service_description["serviceName"],
                "serviceType": cd_service_description["serviceType"],
                "customerType": cd_service_description["customerType"],
                "customerName": cd_service_description["customerName"],
                "topology": cd_service_description["topology"],
                "service": cd_service_description["service"],
            },
        }

        self.logger.info("CircuitDetails:\n" + str(circuit_details))

        return circuit_details

    def circuit_details_process(self, topology: dict, leg_identifier: str = "") -> str:
        # business LOGIC
        corrected_circuit_details = self.run_business_logic(topology, leg_identifier)
        # BUILD ASSOCIATIONS
        parent_resource = self.get_associated_parent_resource()
        # CREATE CD RESOURCE
        circuit_details_resource = self.create_and_associate_circuit_details_resource(
            corrected_circuit_details, parent_resource
        )
        # PATCH CD RESOURCE WITH CPE STUFF
        self.patch_cpe_with_initial_state(circuit_details_resource, parent_resource)

        return circuit_details_resource["id"]

    def create_and_associate_circuit_details_resource(
        self, circuit_details: dict, parent_resource: Any | Any | None = None
    ):
        parent_resource_id: str = self.resource["id"]
        if parent_resource:
            parent_resource_id: str = parent_resource["id"]

        return self.create_circuit_details(parent_resource_id, circuit_details)

    def patch_cpe_with_initial_state(self, circuit_details: dict, parent_resource: Any | Any | None) -> None:
        """Patches the CPE Initial State to the Parent Resource for Select Workstreams

        :param circuit_details: _description_
        :type circuit_details: dict
        :param parent_resource: _description_
        :type parent_resource: Any | Any | None
        """
        # NOW UPDATE THE CIRCUIT DETAILS WITH THE CPE AND INITIAL STATE OF THE CPE
        site_status = []
        cpe_node_list = []
        for topology in circuit_details["properties"]["topology"]:
            for node in topology["data"]["node"]:
                for name in node["name"]:
                    if name["name"] == "Role" and name["value"] == "CPE":
                        cpe_node_list.append(node)

        cpe_updated_dict = {}
        for cpe_node in cpe_node_list:
            cpe_updated_dict[cpe_node["uuid"]] = {}
            for name in cpe_node["name"]:
                if name["name"] == "Customer Address":
                    cust_addr = name["value"]
                    cpe_updated_dict[cpe_node["uuid"]]["customeraddr"] = cust_addr
                if name["name"] == "Host Name":
                    host_name = name["value"]
                    cpe_updated_dict[cpe_node["uuid"]]["hostname"] = host_name

        for cpe in cpe_updated_dict:
            site_status.append(
                {
                    "site": cpe_updated_dict[cpe].get(
                        "customeraddr", str(self.get_customer_addresses(circuit_details)[0])
                    ),
                    "host": cpe_updated_dict[cpe]["hostname"],
                    "state": "NOT_STARTED",
                }
            )

        patch = {"properties": {"site_status": site_status}}

        is_update_or_delete: bool = True
        if self.operation == "NETWORK_SERVICE_ACTIVATION":
            is_update_or_delete = False

        if parent_resource is not None and not is_update_or_delete:
            self.patch_observed(parent_resource["id"], patch)
        else:
            self.logger.warning("No parent resource associated with Circuit Details Collector, unable to patch parent.")

    def get_associated_parent_resource(self):  # -> Any | Any | None:
        """Return the Parent Resource that called CDC from a pre defined list
        :return: Parent resource that called CDC
        :rtype: dict | None
        """
        parent_resource = None
        if self.operation in ["NETWORK_SERVICE_DELETION", "NETWORK_SERVICE_UPDATE"]:
            parent_resource = self.get_associated_network_service_update_or_delete_for_resource(self.resource["id"])
        elif self.operation in ["NETWORK_SERVICE", "NETWORK_SERVICE_ACTIVATION"]:
            parent_resource = self.get_associated_network_service_for_resource(self.resource["id"])
        elif self.operation == "CPE_ACTIVATION":
            parent_resource = self.get_associated_resource(self.resource["id"], self.BUILT_IN_CPE_ACTIVATOR_TYPE)
        elif self.operation == "SERVICE_MAPPER":
            parent_resource = self.get_associated_resource(self.resource["id"], self.BUILT_IN_SERVICE_MAPPER_TYPE)
        elif self.operation == "TRANSPORT":
            parent_resource = self.get_associated_resource(
                self.resource["id"], self.BUILT_IN_TRANSPORT_NNI_PROVISIONER_TYPE
            )
        elif self.operation == "SMOKE_TEST":
            parent_resource = self.get_associated_resource(self.resource["id"], self.BUILT_IN_SMOKE_TEST_TYPE)
        return parent_resource

    def get_topology_from_sense(self):
        """Get the Topology from SENSE or S.M.A.R.T for alternate CD use cases

        :return: Topolgy from SENSE
        :rtype: dict
        """
        # Get BPO Constants
        self.bpo_constants = self.get_bpo_contants_resource()
        if self.bpo_constants is None:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, "Application Configuration", "No active BPO Constants available"
            )
            self.logger.info(msg)
            self.categorized_error = msg
            self.exit_error(msg)

        server_details = self.bpo_constants["properties"]["circuit_details_server_info"]

        def get_circuit_details_url(property="server") -> dict:
            try:
                url = server_details["%s_url" % property]
                url += server_details["%s_get_url" % property]

                ckt_id = self.circuit_id

                return url.replace("${circuit_id}", ckt_id)

            except KeyError:
                msg = self.error_formatter(
                    self.SYSTEM_ERROR_TYPE,
                    "Application Configuration",
                    f"{property} is not a valid URL property in BPO Constants",
                )
                self.categorized_error = msg
                self.exit_error(msg)

        headers = server_details.get("server_headers", {"Accept": "application/json"})
        url = get_circuit_details_url("alternate_server" if self.use_alternate_url else "server")
        self.logger.info(f"Requesting circuit details call via URL: {url}")

        res = self.get_circuit_details_with_retry(url, headers)

        # Check for JSON if not it was a text return from ALT CD Server than can be converted to JSON
        topology = res.json
        if not isinstance(topology, dict):
            topology = json.loads(res.text)

        self.logger.info("SENSE Topology: " + json.dumps(topology, indent=4))
        return topology

    def data_compliancy_check(self, data):
        """
        checks to ensure that mandatory fields are provided
        and response from server is compliant.

        No Return value

        If the response from server is not exactly what it is
        required to be, exception is raised and resource moves to failed state

        :param data: Response received from server
        :type data: dict

        """
        self.logger.debug("Starting compliancy check.")

        self.logger.debug("Verifying response outer structure")
        self.check_keys_in_dict(self.MANDATORY_RESPONSE_STRUCTURE_ITEMS, data)

        self.logger.debug("Verifying topology structure")

        # code below verifies that the topology section of data received from server
        # has all the mandatory parameters

        present_name_keys = []
        owned_name_keys = []
        pe_count = 0
        for topology in data["topology"]:
            self.check_keys_in_dict(self.MANDATORY_TOPOLOGY_ITEMS, topology)
            self.check_keys_in_dict(self.MANDATORY_TOPOLOGY_DATA_ITEMS, topology["data"])
            for node in topology["data"]["node"]:
                self.check_keys_in_dict(self.MANDATORY_TOPOLOGY_DATA_NODE_ITEMS, node)
                for nodename in node["name"]:
                    self.check_keys_in_dict(["name", "value"], nodename)
                    present_name_keys.append(nodename["name"])
                    if nodename["name"] == "Role" and nodename["value"] == "PE":
                        pe_count += 1
                present_name_keys_set = set(present_name_keys)
                missing_keys = [
                    x for x in self.MANDATORY_TOPOLOGY_DATA_NODE_NAME_ITEMS if x not in present_name_keys_set
                ]
                if len(missing_keys) != 0:
                    msg = self.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"device: {node['uuid']} missing keys: {missing_keys}",
                        system=self.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.exit_error(msg)
                present_name_keys = []
                for ownededgepoint in node["ownedNodeEdgePoint"]:
                    self.check_keys_in_dict(self.MANDATORY_TOPOLOGY_DATA_NODE_OWNEDNODEEDGEPOINT_ITEMS, ownededgepoint)
                    for ownedname in ownededgepoint["name"]:
                        self.check_keys_in_dict(["name", "value"], ownedname)
                        owned_name_keys.append(ownedname["name"])
                    if "Name" not in owned_name_keys or "Role" not in owned_name_keys:
                        missing = self.get_missing_owned_name_key(owned_name_keys)
                        self.logger.debug(
                            f"CIRCUIT DETAILS SERVER RESPONSE ERROR: port name/Role not provided for \
                            ownedNodeEgePoint {ownededgepoint} node {node} topology {topology}"
                        )
                        msg = self.error_formatter(
                            self.MISSING_DATA_ERROR_TYPE,
                            self.TOPOLOGIES_DATA_SUBCATEGORY,
                            f"device: {ownededgepoint['uuid']} missing port data: {missing}",
                            system=self.CIRCUIT_DETAILS_DATABASE,
                        )
                        self.categorized_error = msg
                        self.exit_error(msg)

                    owned_name_keys = []

            if "link" in topology["data"].keys():
                for link in topology["data"]["link"]:
                    self.check_keys_in_dict(self.MANDATORY_TOPOLOGY_DATA_LINK_ITEMS, link)

            if pe_count == 0:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"no PEs found for topology spoke {topology}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)
            if pe_count > 1:
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"multiple PEs found for topology spoke {topology}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

            pe_count = 0

        if data["serviceType"] == "FIA" or data["serviceType"] == "VOICE":
            self.MANDATORY_SERVICE_DATA_ITEMS = ["fia"]

        if data["serviceType"] == "ELAN":
            self.MANDATORY_SERVICE_DATA_EVC_ITEMS.append("vplsVlanId")
            self.MANDATORY_SERVICE_DATA_EVC_ITEMS.append("vplsNetworkId")

        self.logger.debug("verifying mandatory service keys and structure")

        # code below verifies that the topology section of data received from server
        # has all the mandatory parameters

        for service in data["service"]:
            self.check_keys_in_dict(self.MANDATORY_SERVICE_ITEMS, service)
            self.check_keys_in_dict(self.MANDATORY_SERVICE_DATA_ITEMS, service["data"])
            if "evc" in service["data"].keys():
                for evc in service["data"]["evc"]:
                    self.check_keys_in_dict(self.MANDATORY_SERVICE_DATA_EVC_ITEMS, evc)
                    for endpoint in evc["endPoints"]:
                        self.check_keys_in_dict(self.MANDATORY_SERVICE_DATA_EVC_ENDPOINTS_ITEMS, endpoint, length=False)
            if "fia" in service["data"].keys():
                for fia in service["data"]["fia"]:
                    self.check_keys_in_dict(self.MANDATORY_SERVICE_DATA_FIA_ITEMS, fia)
                    for endpoint in fia["endPoints"]:
                        if self.is_missing_required_lan_ips(fia["type"], endpoint):
                            msg = self.error_formatter(
                                self.MISSING_DATA_ERROR_TYPE,
                                "LAN IP Addresses",
                                f"fia type: {fia['type']} missing: LAN IPv4 and IPv6",
                                system=self.CIRCUIT_DETAILS_DATABASE,
                            )
                            self.categorized_error = msg
                            self.exit_error(msg)
                        if self.is_missing_required_wan_ips(fia["type"], endpoint):
                            msg = self.error_formatter(
                                self.MISSING_DATA_ERROR_TYPE,
                                "WAN IP Addresses",
                                f"fia type: {fia['type']} missing: WAN IPv4 and IPv6",
                                system=self.CIRCUIT_DETAILS_DATABASE,
                            )
                            self.categorized_error = msg
                            self.exit_error(msg)
                        self.check_keys_in_dict(self.MANDATORY_SERVICE_DATA_FIA_ENDPOINTS_ITEMS, endpoint)
            if "elan" in service["data"].keys():
                for elan in service["data"]["elan"]:
                    self.check_keys_in_dict(self.MANDATORY_SERVICE_DATA_ELAN_ITEMS, elan)
        self.logger.debug("Completed compliancy check.")

    def get_missing_owned_name_key(self, owned_name_keys):
        if "Name" not in owned_name_keys and "Role" not in owned_name_keys:
            return "port name and port role"
        elif "Name" not in owned_name_keys:
            return "port name"
        elif "Role" not in owned_name_keys:
            return "port role"
        return ""

    def check_keys_in_dict(self, keys, dictionary, length=True):
        """verify if provided keys are present in provided dictionary"""
        for key in keys:
            if key not in dictionary.keys() or dictionary[key] is None or len(str(dictionary[key])) == 0:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    self.TOPOLOGIES_DATA_SUBCATEGORY,
                    f"data: {dictionary} missing: {key}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)
            if length:
                if isinstance(dictionary[key], list) and len(dictionary[key]) == 0:
                    msg = self.error_formatter(
                        self.MISSING_DATA_ERROR_TYPE,
                        self.TOPOLOGIES_DATA_SUBCATEGORY,
                        f"data: {dictionary} empty list: {key}",
                        system=self.CIRCUIT_DETAILS_DATABASE,
                    )
                    self.categorized_error = msg
                    self.exit_error(msg)

    def is_missing_required_lan_ips(self, fia_type, endpoint):
        return (
            fia_type == "DIRECT"
            and "lanIpv4Addresses" not in endpoint.keys()
            and "lanIpv6Addresses" not in endpoint.keys()
        )

    def is_missing_required_wan_ips(self, fia_type, endpoint):
        return (
            fia_type == "STATIC" and "wanIpv4Address" not in endpoint.keys() and "wanIpv6Address" not in endpoint.keys()
        )

    def create_circuit_details(self, parent_id, circuit_details):
        """create the circuit details resource

        special code here to catch the exception on the POST and provide a better exception message

        :param circuit_details: Topology from circuit details resource or the complete circuit details resource
        :param parent_id: Parent resource ID
        :type circuit_details: dict
        :type parent_id: string

        :return: Circuit Details resource
        :rtype: dict
        """
        # Create the CircuitDetails and build associations
        try:
            circuit_details_resource = self.bpo.market.post("/resources", circuit_details)
        except Exception as ex:
            self.logger.exception(ex)
            self.process_cd_post_failure(ex)

        self.bpo.relationships.add_relationship(parent_id, circuit_details_resource["id"])
        return self.await_active_collect_timing([circuit_details_resource["id"]])[0]

    def process_cd_post_failure(self, exception):
        """process the Circuit Details POST failure

        :param exception: exception
        :type exception: Exception
        """
        error_response = "Check Mulesoft response"
        error_message = str(exception).replace("\\n", "\n")

        type_match = re.search(self.CD_RESOURCE_POST_ERROR_TYPE_REGEX, error_message)
        type_message = re.search(self.CD_RESOURCE_POST_ERROR_FAILURE_REGEX, error_message)
        if not type_match:
            msg = self.error_formatter(
                self.SYSTEM_ERROR_TYPE, "Market Post", error_response + ", unknown model error: " + error_message
            )
            self.categorized_error = msg
            self.exit_error(msg)

        msg = self.error_formatter(
            self.SYSTEM_ERROR_TYPE,
            "Market Post",
            error_response + f", {type_match.group(1).upper()} model error: {type_message.group(1)}",
        )
        self.categorized_error = msg
        self.exit_error(msg)

    def update_circuit_details_with_neighbor_info(self, circuit_details):
        """
        Takes Topology from Circuit Details response
        and updates it with Neighbor and Interface Information

        :param circuit_details : Topology from circuit details resource or the complete circuit details resource
        :circuit_details type: dict

        :return_value topology: Updated Topology
        :return_value type: list of dicts
        """

        spoke_list = self.create_device_dict_with_neighbor_info(circuit_details)

        topology = circuit_details
        if "topology" in circuit_details.keys():
            topology = circuit_details["topology"]

        # updating original topology on the basis of topology processing done by function
        # create_device_dict_with_neighbor_info"
        for spoke in spoke_list:
            topo = topology[spoke_list.index(spoke)]
            for node in topo["data"]["node"]:
                node_in_spoke = spoke[node["uuid"]]
                network_neighbor = node_in_spoke["Network Neighbor"]
                client_neighbor = node_in_spoke["Client Neighbor"]
                network_neighbor_interface = node_in_spoke["Network Neighbor Interface"]
                client_neighbor_interface = node_in_spoke["Client Neighbor Interface"]
                network_interface = node_in_spoke["Network Interface"]
                client_interface = node_in_spoke["Client Interface"]

                network_neighbor_dict = {"name": "Network Neighbor", "value": network_neighbor}
                client_neighbor_dict = {"name": "Client Neighbor", "value": client_neighbor}
                network_interface_dict = {"name": "Network Interface", "value": network_interface}
                client_interface_dict = {"name": "Client Interface", "value": client_interface}
                network_neighbor_interface_dict = {
                    "name": "Network Neighbor Interface",
                    "value": network_neighbor_interface,
                }
                client_neighbor_interface_dict = {
                    "name": "Client Neighbor Interface",
                    "value": client_neighbor_interface,
                }

                node["name"].extend(
                    [
                        network_neighbor_dict,
                        client_neighbor_dict,
                        network_interface_dict,
                        network_neighbor_interface_dict,
                        client_interface_dict,
                        client_neighbor_interface_dict,
                    ]
                )

        self.logger.debug("Updated Topology is" + json.dumps(topology, indent=4))

        return topology

    def create_device_dict_with_neighbor_info(self, circuit_details):
        """returns a dictionary of devices from CircuitDetails indexed by hostname
        containing neighbor information

        :param circuit_details: CircuitDetails resource or Topology section of circuit details response
        :type circuit_details: obj

        :return: dict keyed by hostname with the properties
        :rtype: dict
        """

        spoke_list = self.create_device_dict_from_circuit_details(circuit_details)

        # traversing from PE to client for every spoke and updating neighbor information
        for device_dict in spoke_list:
            ordered_topology = self.get_ordered_topology(device_dict)
            ordered_list = [list(d.keys())[0] for d in ordered_topology]
            self.logger.info("ordered list for topology spoke %s is %s" % (str(device_dict), str(ordered_list)))
            for node in ordered_list:
                neighbors = self.get_neighbors(node, ordered_list)
                device_dict[node]["Network Neighbor"] = neighbors[0]
                device_dict[node]["Client Neighbor"] = neighbors[1]
                interfaces = self.get_interfaces_from_neighbors(node, neighbors, device_dict, circuit_details)
                device_dict[node]["Network Neighbor Interface"] = interfaces["Network Neighbor Interface"]
                device_dict[node]["Client Neighbor Interface"] = interfaces["Client Neighbor Interface"]
                device_dict[node]["Network Interface"] = interfaces["Network Interface"]
                device_dict[node]["Client Interface"] = interfaces["Client Interface"]

        self.logger.debug("Returning list of spoke dict: " + json.dumps(spoke_list, indent=4))
        return spoke_list

    def get_neighbors(self, hostname, side_devices):
        """returns the hostnames of the network and the client side (NNI and UNI).

        returns [ <network_host>, <client_host> ]

        :param hostname: Device host name
        :param side_devices: Ordered list of spoks:
        :type hostname: str
        :type side_devices: list

        :return: List of adjacent devices
        :rtype: List of strings
        """
        network_host = "None"
        client_host = "None"
        last_host = "None"

        hosts = side_devices
        for i in range(0, len(hosts)):
            if hosts[i] == hostname:
                network_host = last_host
                if i < (len(hosts) - 1):
                    client_host = hosts[i + 1]
                break
            last_host = hosts[i]

        self.logger.debug("Returning client host %s for host %s" % (str(client_host), hostname))
        self.logger.debug("Returning network host %s for host %s" % (str(network_host), hostname))
        return [network_host, client_host]

    def get_interfaces_from_neighbors(self, uuid, neighbors, device_dict, circuit_details):
        """
        returns self and neighbor interface information for a device

        returns {} with keys Network Interface,Network Neighbor Interface,Client Neighbor Interface,Client Interface
        :param uuid : node uuid
        :uuid type : str

        :param neighbors: neighbors returned by function get_neighbors
        :neighbors type: list

        :param device_dict: device dictionary indexed by hostname
        :device_dict type: dict

        """

        client_neighbor = neighbors[1]
        network_neighbor = neighbors[0]
        client_links = []
        network_links = []
        return_value = {}

        if device_dict[uuid]["Role"] != "PE":
            if len(device_dict[uuid].get("links", [])) == 0:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    "Linked Device Data",
                    f"device: {uuid} role: {device_dict[uuid]['Role']}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

        if device_dict[uuid].get("links") is None:
            return_value["Network Neighbor Interface"] = "None"
            return_value["Client Neighbor Interface"] = "None"
            return_value["Network Interface"] = "None"
            return_value["Client Interface"] = "None"
            return return_value

        for link in device_dict[uuid]["links"]:
            if client_neighbor is not None and client_neighbor in str(link):
                client_links.append(str(link))
            if network_neighbor is not None and network_neighbor in str(link):
                network_links.append(str(link))

        if len(client_links) > 1:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Multiple Client Links",
                f"device: {device_dict[uuid]} client links: {client_links}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)
        if len(client_links) == 1:
            client_link = client_links[0]
        else:
            client_link = None
            return_value["Client Neighbor Interface"] = "None"

        if len(network_links) > 1:
            msg = self.error_formatter(
                self.INCORRECT_DATA_ERROR_TYPE,
                "Multiple Network Links",
                f"device: {device_dict[uuid]} network links: {network_links}",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)
        if len(network_links) == 1:
            network_link = network_links[0]
        else:
            network_link = None
            return_value["Network Neighbor Interface"] = "None"

        if network_link is not None:
            node_ports = network_link.split("_")
            for np in node_ports:
                if uuid in np:
                    self_node_port = np
                else:
                    peer_node_port = np

            return_value["Network Interface"] = self.get_node_port_name_from_uuid(self_node_port)[1]
            return_value["Network Neighbor Interface"] = self.get_node_port_name_from_uuid(peer_node_port)[1]

        else:
            return_value["Network Interface"] = self.fetch_port(uuid, circuit_details, "NNI")
            return_value["Network Neighbor Interface"] = "None"

        if client_link is not None:
            node_ports = client_link.split("_")
            for np in node_ports:
                if uuid in np:
                    self_node_port = np
                else:
                    peer_node_port = np

            return_value["Client Interface"] = self.get_node_port_name_from_uuid(self_node_port)[1]
            return_value["Client Neighbor Interface"] = self.get_node_port_name_from_uuid(peer_node_port)[1]
        else:
            return_value["Client Interface"] = self.fetch_port(uuid, circuit_details, "UNI")
            if return_value["Client Interface"] == "None":
                return_value["Client Interface"] = self.fetch_port(uuid, circuit_details, "ENNI")

            # Exit if device handoff port is not UNI/ENNI
            if return_value["Client Interface"] == "None":
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    "Client Interface Role",
                    f"device: {uuid} client interface role: {device_dict[uuid]['Role']}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)
            return_value["Client Neighbor Interface"] = "None"

        self.logger.info("Returning Neighbor info for node %s" % uuid)
        self.logger.info(return_value)
        return return_value

    def get_ordered_topology(self, device_dict):
        """This will return the array of devices associated with a specific hostname that
        are in the same spoke chain.

        Chain defined as PE --> AGG --> MTU --> CPE (and combinations).

        :param device_dict: device dictionary indexed by hostname
        :device_dict type: obj

        :return: list of dicts keyed by hostname with the properties
        :rtype: list
        """
        pe_list = []
        section = []
        section_list = []
        node_dict = {}

        for uuid, device in device_dict.items():
            if device["Role"] == "PE":
                pe_list.append(uuid)
            if len(pe_list) > 1:
                msg = self.error_formatter(
                    self.INCORRECT_DATA_ERROR_TYPE,
                    "More Than One PE Found In Spoke",
                    f"devices: {pe_list}",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)
            elif device["Role"] == "CPE" and device["links"] == []:
                msg = self.error_formatter(
                    self.MISSING_DATA_ERROR_TYPE,
                    "CPE Uplink Device",
                    f"device: {device['Host Name']} missing: uplink device",
                    system=self.CIRCUIT_DETAILS_DATABASE,
                )
                self.categorized_error = msg
                self.exit_error(msg)

        pe = pe_list[0]

        section.append(pe)
        last_node = pe
        next_link = None
        last_link = None
        link_list = None
        neighbor = None
        while True:
            link_list = device_dict[last_node].get("links")
            if link_list is None:
                break
            if len(link_list) == 0:
                break
            elif len(link_list) == 1:
                if link_list[0] == last_link:
                    break
                next_link = link_list[0]
            else:
                next_link = [li for li in link_list if not li == last_link][0]
            neighbor = self.get_neighbor_from_link(last_node, next_link)
            section.append(neighbor)
            if device_dict[neighbor]["Role"] == "CPE":
                break
            last_node = neighbor
            last_link = next_link

        for node in section:
            node_dict[node] = device_dict[node]
            section_list.append(node_dict)
            node_dict = {}

        self.logger.debug("Returning topology chain %s" % json.dumps(section_list, indent=4))
        return section_list

    def get_pe_network_interface(self, node):
        """
        returns Network interface for a PE node

        :param node: node_uuid
        :node type : str

        :rtype string
        """

        network_interface = "None"
        for ownededgepoint in node["ownedNodeEdgePoint"]:
            for name in ownededgepoint["name"]:
                if name["name"] == "Role" and "NNI" in name["value"].upper():
                    network_interface = self.get_node_port_name_from_uuid(ownededgepoint["uuid"])[1]

        if network_interface == "None":
            self.logger.warn("Unable to fetch Network Interface for PE node %s" % node)

        return network_interface

    def get_cpe_client_interface(self, node):
        """
        returns Client interface for a CPE node

        :param node: node_uuid
        :node type : str

        :rtype string
        """

        client_interface = "None"
        for ownededgepoint in node["ownedNodeEdgePoint"]:
            for name in ownededgepoint["name"]:
                if name["name"] == "Role" and (name["value"].upper() in ["UNI", "ENNI"]):
                    client_interface = self.get_node_port_name_from_uuid(ownededgepoint["uuid"])[1]

        if client_interface == "None":
            msg = self.error_formatter(
                self.MISSING_DATA_ERROR_TYPE,
                "CPE Client Interface",
                f"device: {node} missing: client interface",
                system=self.CIRCUIT_DETAILS_DATABASE,
            )
            self.categorized_error = msg
            self.exit_error(msg)

        return client_interface

    def fetch_port(self, uuid, circuit_details, port_type):
        """
        fetches the Client port when node is the last node in spoke
        """

        required_interface = "None"
        for topology in circuit_details["topology"]:
            for node in topology["data"]["node"]:
                if node["uuid"] == uuid:
                    for ownedNodeEdgePoint in node["ownedNodeEdgePoint"]:
                        for name in ownedNodeEdgePoint["name"]:
                            if name["name"] == "Role" and port_type == name["value"]:
                                required_interface = self.get_node_port_name_from_uuid(ownedNodeEdgePoint["uuid"])[1]

        return required_interface
