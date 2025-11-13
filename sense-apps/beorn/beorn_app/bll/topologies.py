import logging
import re

from common_sense.common.errors import (
    abort,
    granite_msg,
    topologies_msg,
    INCORRECT_DATA,
    MISSING_DATA,
    get_standard_error_summary,
)
from beorn_app.bll.eligibility.mdso_eligible import (
    EQUIPMENT_TYPES,
    JUNIPER_ACX_MODELS,
    NOKIA_7750_MODELS,
    NOKIA_7705_MODELS,
    NOKIA_7210_MODELS,
)
from beorn_app.common.granite_operations import call_denodo_for_circuit_devices
from beorn_app.common.utils import clean_data
from beorn_app.bll.granite import get_vpls_vlan_id, get_elan_slm_data, get_vc_class_type
from common_sense.common.network_devices import VOICE_GATEWAY_MODELS

logger = logging.getLogger(__name__)


FIA_SERVICE_TYPES = (
    "FIA",
    "DIA",
    "SECURE INT",
    "VOICE-PRI",
    "VOICE-SIP",
    "VOICE-HOST",
    "VOICE",
    "MSS DIA",
    "MRS_MSS DI",
    "MRS INTERN",
)

MULTI_LEG_SERVICE_TYPES = ("CAR-CTBH 4G", "CTBH 4G")

ELINE_SERVICE_TYPES = ("EPL", "EVPL", "E-ACCESS F", "MRS EPL", "MRS EVPL")

NNI_SERVICE_TYPES = ("NNI",)

ELAN_SERVICE_TYPES = ("EPLAN", "EVPLAN", "VIDEO-FC P", "MRS EPLAN")

PORT_ROLES = {
    (
        "INT-ACCESS TO PREM TRANSPORT",
        "COM-CUST TO EDGE TRANSPORT",
        "CAR-CUST TO EDGE TRANSPORT",
        "COM-HUB TO HUB TRANSPORT",
        "CAR-HUB TO HUB TRANSPORT",
        "INT-EDGE TRANSPORT",
        "INT-NNI-FIBER",
    ): "INNI",
    ("CAR-CTBH NNI", "CAR-NNI", "COM-NNI", "TWC-BUY NNI", "CUS-ENNI-BUY", "CUS-ENNI-SELL"): "ENNI",
    ("CAR-CUSTOMER TRANSPORT", "COM-CUSTOMER TRANSPORT", "INT-CUSTOMER HANDOFF"): "UNI",
}

SUPPORTED_MEDIA_TYPES = ["FIBER", "FIBER/COAX HYBRID"]

NNI_PATHS = ["CUS-ENNI-BUY", "CAR-NNI", "INT-NNI-FIBER", "COM-NNI"]

SUBNET = "IPv4 Subnet"

TRUNK_ELIGIBLE = ["VOICE-HOST", "MSS DIA", "MRS INTERN"]


class Topologies:
    def __init__(self, cid):
        self.cid = cid
        self.circuit_elements = call_denodo_for_circuit_devices(cid)
        self.utils = TopologyUtils()
        self._set_is_type_2()
        self.trunked = False

    def _set_is_type_2(self):
        vc_class = get_vc_class_type(self.circuit_elements[0]["circ_path_inst_id"])
        self.is_type_2 = True if vc_class == "TYPE 2" else False

    def create_topology(self):
        if self._is_multi_leg():
            topology = self._create_multi_leg_topology()
        else:
            topology = self._create_topology()
        self.topology = topology
        return topology

    def _is_multi_leg(self):
        if self.circuit_elements[0]["service_type"] not in MULTI_LEG_SERVICE_TYPES:
            # hosted voice circuits technically have multiple legs but are not modeled as such (mgmt, service legs)
            return False
        legs = []
        for circ_element in self.circuit_elements:
            leg = []
            for element in circ_element["data"]:
                leg.append(element["leg_name"])
            legs.append(tuple(leg))

        return len(set(legs)) > 1

    def _create_multi_leg_topology(self):
        # set legs as attributes to allow eligibility checks access
        # they need to be passed to create topology despite this to allow override of default arg
        self._set_legs()
        topology = {
            "PRIMARY": self._create_topology(self.primary_leg_elements),
            "SECONDARY": self._create_topology(self.secondary_leg_elements),
        }

        if not topology["PRIMARY"]["service"][0]["data"]["evc"][0].get("evcId"):
            msg = granite_msg(MISSING_DATA, "EVCID", f"{self.service_type} {self.cid}")
            abort(400, msg, summary=get_standard_error_summary(msg))

        if "," in topology["PRIMARY"]["service"][0]["data"]["evc"][0]["evcId"]:
            topology = self._remediate_evc_ids(topology)

        return topology

    def _set_legs(self):
        self.primary_leg_elements = []
        self.secondary_leg_elements = []
        element_index = 0
        for element in self.circuit_elements:
            (
                self.primary_leg_elements.append(element)
                if element_index % 2 == 0
                else self.secondary_leg_elements.append(element)
            )
            element_index += 1

    def _create_topology(self, elements_by_leg=None):
        denodo_elements = elements_by_leg if elements_by_leg else self.circuit_elements
        if denodo_elements[0]["service_type"] in TRUNK_ELIGIBLE:
            self._remove_mgmt88_elements()
        if "VOICE-HOST" in denodo_elements[0]["service_type"]:
            self.trunked = True

        self.circuit_data = self.utils.get_circuit_data(denodo_elements)
        if not self.circuit_data["service_type"]:
            msg = granite_msg(MISSING_DATA, "Service Type", self.cid)
            abort(400, msg, summary=get_standard_error_summary(msg))
        self._voice_ip_modification(self.circuit_data)
        self._set_service_type()
        if not self.service_type:
            msg = topologies_msg(f"Service Type {self.circuit_data['service_type']}")
            abort(400, msg, summary=get_standard_error_summary(msg))
        base_topology = self._create_base_topology()

        # filter out unneeded elements
        self.circuit_data["data"] = self._get_required_circuit_data()

        # validate required elements
        self._validate_required_circuit_data()

        topology_creators = {
            "FIA": self._create_single_topology,
            "CTBH 4G": self._create_double_topology,
            "ELINE": self._create_double_topology,
            "NNI": self._create_single_topology,
            "ELAN": self._create_single_topology,
            "VIDEO": self._create_single_topology,
            "VOICE": self._create_single_topology,
        }

        topology = topology_creators[self.service_type](base_topology)
        return topology

    def _voice_ip_modification(self, data):
        if data["service_type"] in ["VOICE-SIP", "VOICE-PRI"]:
            for element in data["data"]:
                if element["model"] in VOICE_GATEWAY_MODELS:
                    ip4address = element["management_ip"]
                    self.circuit_data["ip4_address"] = str(ip4address)
                    self.circuit_data["ipv4_assigned_gateway"] = str(ip4address)
        return data

    def _remove_mgmt88_elements(self):
        """Removing the MGMT 88 leg from a CIRCUIT"""
        for i in range(len(self.circuit_elements)):
            if re.search("VLAN88", str(self.circuit_elements[i])):
                del self.circuit_elements[i]
                break

    def _set_service_type(self):
        self.service_type = self._get_service_type()
        if "VOICE" in self.circuit_data["service_type"]:
            self.service_type = "VOICE"
        if "VIDEO-FC P" in self.circuit_data["service_type"]:
            self.service_type = "VIDEO"

    def _get_service_type(self):
        translated_service_types = {
            "FIA": FIA_SERVICE_TYPES,
            "CTBH 4G": MULTI_LEG_SERVICE_TYPES,
            "ELINE": ELINE_SERVICE_TYPES,
            "NNI": NNI_SERVICE_TYPES,
            "ELAN": ELAN_SERVICE_TYPES,
        }
        for service in translated_service_types:
            if self.circuit_data["service_type"] in translated_service_types[service]:
                return service

    def _create_base_topology(self):
        return {
            "customerName": self.circuit_data["customer_name"],
            "serviceName": self.circuit_data["cid"],
            "customerType": self._get_customer_type(),
            "modelVersion": "2.0",
            "serviceType": self.service_type,
            "serviceMedia": self.circuit_data["service_media"],
            "topology": [],
            "service": [],
        }

    def _get_customer_type(self):
        denodo_customer_type = self.circuit_data["customer_type"]
        translated_customer_types = {"COM": "CUST", "CUS": "CUST", "CAR": "CARR"}
        if translated_customer_types.get(denodo_customer_type):
            return translated_customer_types[denodo_customer_type]
        if denodo_customer_type:
            return denodo_customer_type
        msg = granite_msg(MISSING_DATA, "Customer Type", self.cid)
        abort(501, msg, summary=get_standard_error_summary(msg))

    def _get_required_circuit_data(self):
        required_data = [
            x
            for x in self.circuit_data["data"]
            if x["eq_type"] in EQUIPMENT_TYPES and x["model"] not in VOICE_GATEWAY_MODELS or x["split_id"]
        ]
        if not required_data:
            msg = granite_msg(MISSING_DATA, "Network Equipment", self.cid)
            abort(400, msg, summary=get_standard_error_summary(msg))
        return required_data

    def _validate_required_circuit_data(self):
        # ensure data present at circuit data level is supported for modeling topology
        if self.circuit_data["service_media"] not in SUPPORTED_MEDIA_TYPES:
            msg = topologies_msg(f"Service Media {self.circuit_data['service_media']}")
            abort(502, msg, summary=get_standard_error_summary(msg))
        cross_footprint, msg = self._is_cross_footprint()
        if cross_footprint:
            msg = topologies_msg(msg)
            abort(502, msg, summary=get_standard_error_summary(msg))

    def _is_cross_footprint(self):
        if "INT-NNI-FIBER" in str(self.circuit_data):
            logger.info(f"{self.cid} Cross Footprint Circuit - Internal NNI in path")
            return True, "Cross Footprint Circuit"
        clouds = []
        cloud_last = False
        for element in self.circuit_data["data"]:
            if element.get("topology") == "Cloud" and cloud_last is False:
                clouds.append(element)
                cloud_last = True
            else:
                cloud_last = False
        if len(clouds) > 1:
            logger.info(f"{self.cid} Cross Footprint Circuit - Multiple Non-Sequential Clouds")
            return True, "Cross Footprint Circuit"
        return False, ""

    def _create_single_topology(self, topology):
        network_elements = self._get_validated_network_elements()
        topology_data = self._build_topology_model(network_elements)
        topology["topology"].append(topology_data)
        service_data = self._build_service_model(network_elements)
        topology["service"].append(service_data)
        return topology

    def _create_double_topology(self, topology):
        # Pull out a and z side lists
        a_side_network_elements = []
        z_side_network_elements = []

        self.circuit_data["data"] = self.utils.consolidate_clouds(self.circuit_data["data"])
        is_mpls_cloud_detected = (
            True if [device for device in self.circuit_data["data"] if device.get("topology", "") == "Cloud"] else False
        )

        if is_mpls_cloud_detected:
            self.determine_a_and_z_loc_for_eline_with_cloud()
            if [x for x in self.circuit_data["data"] if x["split_id"]]:
                # will only have split id if it is a cloud element
                for i, data in enumerate(self.circuit_data["data"]):
                    if data["split_id"]:
                        a_side_network_elements = self.circuit_data["data"][0:i]
                        z_side_network_elements = self.circuit_data["data"][i + 1 :]  # noqa: E203
                        break
        else:
            self.add_locally_switched_to_evc_id()
            a_side_network_elements, z_side_network_elements = self.determine_a_and_z_loc_for_eline()

        if not a_side_network_elements:
            a_side_network_elements = self.circuit_data["data"]

        # validate elements
        for element in a_side_network_elements + z_side_network_elements:
            self._check_required_data_exists(element)

        # Build a side
        topology_data = self._build_topology_model(a_side_network_elements)
        topology["topology"].append(topology_data)
        # Build z side
        topology_data = self._build_topology_model(z_side_network_elements)
        topology["topology"].append(topology_data)
        # build a side service data
        service_data = self._build_service_model(a_side_network_elements)
        # add z side service data
        self._add_evc_endpoints(service_data["data"]["evc"][0], z_side_network_elements)
        topology["service"].append(service_data)
        return topology

    def is_enni(self):
        return (
            True
            if any(device for device in self.circuit_data["data"] if self._get_port_role(device) == "ENNI")
            else False
        )

    def determine_a_and_z_loc_for_eline_with_cloud(self):
        pe_sequences = []
        for node in self.circuit_data["data"]:
            if "Cloud" in node.get("topology", ""):
                pe_sequences.append(node["sequence"][:4])
        for device in self.circuit_data["data"]:
            if device["sequence"][:4] < pe_sequences[0][:4]:
                device["location"] = "A_SIDE"
            elif device["sequence"][:4] >= pe_sequences[0][:4]:
                device["location"] = "Z_SIDE"

    def determine_a_and_z_loc_for_eline(self):
        a_side_network_elements = []
        z_side_network_elements = []
        pe_sequences = self.get_all_pe_router_sequence_ids()
        for device in self.circuit_data["data"]:
            if device["sequence"][:4] <= pe_sequences[0] and "Cloud" not in device["topology"]:
                device["location"] = "A_SIDE"
                a_side_network_elements.append(device)
            elif device["sequence"][:4] >= pe_sequences[-1] and "Cloud" not in device["topology"]:
                device["location"] = "Z_SIDE"
                z_side_network_elements.append(device)
            elif "Cloud" in device["topology"]:
                device["location"] = "cloud"
        return a_side_network_elements, z_side_network_elements

    def get_all_pe_router_sequence_ids(self):
        pe_sequences = []
        for device in self.circuit_data["data"]:
            if self.is_enni():
                if device["eq_type"] == "ROUTER" and device["chan_name"]:
                    pe_sequences.append(device["sequence"][:4])
            else:
                if device["eq_type"] == "ROUTER" and device["tid"].endswith("ZW"):
                    pe_sequences.append(device["sequence"][:4])
                if device["device_role"] == "C":
                    pe_sequences.append(device["sequence"][:4])
        pe_sequences = sorted(set(pe_sequences))
        return pe_sequences

    def add_locally_switched_to_evc_id(self):
        if not self.circuit_data["evc_id"]:
            self.circuit_data["evc_id"] = "LOCALLY SWITCHED"

    def _get_validated_network_elements(self):
        # ensure required data at element level of circuit data exists
        network_elements = []
        for data in self.circuit_data["data"]:
            data["location"] = "Z_SIDE"
            if not data["split_id"]:
                self._check_required_data_exists(data)
                network_elements.append(data)
        return network_elements

    def _check_required_data_exists(self, data):
        tid = data.get("tid")
        if not data["port_access_id"]:
            logger.debug(f"{data} missing port_access_id")
            msg = granite_msg(MISSING_DATA, "Port Access ID", tid)
            abort(501, msg, summary=get_standard_error_summary(msg))
        if not data["path_name"]:
            logger.debug(f"{data} missing path_name")
            msg = granite_msg(MISSING_DATA, "Path Name", tid)
            abort(501, msg, summary=get_standard_error_summary(msg))
        if not data["leg_name"]:
            logger.debug(f"{data} missing leg_name")
            msg = granite_msg(MISSING_DATA, "Leg Name", tid)
            abort(501, msg, summary=get_standard_error_summary(msg))
        if not data["path_type"]:
            logger.debug(f"{data} missing path_type")
            msg = granite_msg(MISSING_DATA, "Path Type", f"{tid} {data['path_name']}")
            abort(501, msg, summary=get_standard_error_summary(msg))
        if not data["management_ip"]:
            logger.debug(f"{data} missing management IP")
            msg = granite_msg(MISSING_DATA, "Management IP", tid)
            abort(501, msg, summary=get_standard_error_summary(msg))
        if "|" in data["leg_name"]:
            logger.debug(f"{data} incorrect leg name")
            msg = granite_msg(INCORRECT_DATA, "Leg Name", f"{tid} {data['leg_name']}")
            abort(501, msg, summary=get_standard_error_summary(msg))
        invalid_acx_port = self.validate_acx_port_format(data)
        if invalid_acx_port:
            logger.debug(f"{invalid_acx_port} ACX port is incorrectly named")
            msg = granite_msg(INCORRECT_DATA, "Port Name", f"{tid} ACX Port {invalid_acx_port}")
            abort(502, msg, summary=get_standard_error_summary(msg))

    def validate_acx_port_format(self, data):
        """returns a port value if acx port not correct"""
        if data["model"] in JUNIPER_ACX_MODELS and "GE" in data["port_access_id"]:
            return data["port_access_id"]

    def _build_topology_model(self, network_elements):
        topology_data = {"model": "ONF_TAPI", "version": "2.0.0", "data": {"node": [], "link": []}}
        curr = {}
        for network_device in network_elements:
            if not network_device["tid"]:
                msg = granite_msg(MISSING_DATA, "Device TID", f"sequence {network_device['sequence']}")
                abort(400, msg, summary=get_standard_error_summary(msg))
            #  Check if we are adding an ownedNodeEdgePoint to an existing node
            for node in topology_data["data"]["node"]:
                if network_device["tid"][0:11] == node["uuid"]:
                    for owned_edge_point in node["ownedNodeEdgePoint"]:
                        network_device_uuid = self._get_device_uuid(
                            network_device["tid"], network_device["port_access_id"]
                        )
                        if owned_edge_point["uuid"] == network_device_uuid:
                            port_role = self._get_port_role(network_device)
                            for nv in owned_edge_point["name"]:
                                # update the port role if ENNI
                                if port_role == "ENNI" and nv["name"] == "portRole":
                                    nv["value"] = "ENNI"
                            break
                    else:  # Add new owned edge point
                        owned_node_data = self._build_owned_node_edge_point(network_device, network_elements)
                        if owned_node_data:
                            node["ownedNodeEdgePoint"].append(owned_node_data)
                        break
                    break
            else:  # New node
                node_data = self._build_node_data(network_device, network_elements)
                topology_data["data"]["node"].append(node_data)

            link_data = {"nodeEdgePoint": [], "uuid": ""}
            if self.is_type_2 and network_device["path_type"] in NNI_PATHS:
                if "//" in str(network_device["chan_name"]):
                    link_data = self._build_type_2_link_data(network_elements, link_data)
                    topology_data["data"]["link"].append(link_data)
            if not curr:
                curr = network_device
            elif curr["path_inst_id"] == network_device["path_inst_id"]:
                # Correcting legacy charter invalid CER TIDs for links
                link_data = self._build_link_data(curr, link_data, network_device)
                topology_data["data"]["link"].append(link_data)
                curr = {}
            else:
                curr = network_device

        self._check_topology_links(topology_data)
        return topology_data

    def _get_device_uuid(self, tid, port):
        return f"{tid[0:11]}-{port.split('.')[0]}"

    def _build_type_2_link_data(self, network_elements, link_data):
        self._check_network_elements(network_elements)
        downstream_uplink = network_elements[1]["owned_edge_point"]
        upstream_handoff = network_elements[2]["owned_edge_point"]
        link_data["nodeEdgePoint"] = [downstream_uplink, upstream_handoff]
        link_data["uuid"] = f"{downstream_uplink}_{upstream_handoff}"
        return link_data

    def _check_network_elements(self, network_elements):
        if len(network_elements) < 3:
            msg = granite_msg(MISSING_DATA, "Type II Link Data", network_elements)
            abort(502, msg, summary=get_standard_error_summary(msg))

    def _build_link_data(self, curr, link_data, network_device):
        oep_parts = [curr["tid"][0:11], curr["port_access_id"]]
        curr["owned_edge_point"] = "-".join(oep_parts)
        link_data["nodeEdgePoint"] = [curr["owned_edge_point"], network_device["owned_edge_point"]]
        link_data["uuid"] = f"{curr['owned_edge_point']}_{network_device['owned_edge_point']}"
        return link_data

    def _get_port_role(self, network_device):
        port_role = "UNI"  # Default
        for description, role in PORT_ROLES.items():
            if network_device["path_type"] in description:
                port_role = role
                break
        return port_role

    def _build_owned_node_edge_point(self, network_device, network_elements):
        port_role = self._get_port_role(network_device)
        port_name = network_device["port_access_id"].split(".")[0]
        # don't add the wonky bonus port that comes with hosted voice CPEs
        if self.is_bonus_hosted_voice_port(port_name, network_device["device_role"]):
            return
        owned_node_data = {
            "uuid": self._get_device_uuid(network_device["tid"], network_device["port_access_id"]),
            "name": [
                {"name": "name", "value": port_name},
                {"name": "portRole", "value": port_role},
                {"name": "transportId", "value": network_device["path_name"]},
            ],
        }

        for device in network_elements:
            if device["owned_edge_point"] == network_device["owned_edge_point"] and device["path_name"] != self.cid:
                owned_node_data["name"][-1]["value"] = device["path_name"]

        lag_member = ""
        if "/" in network_device["leg_name"]:
            # split bandwidth off of lag value on the last space character, split lags
            lag_member_values = network_device["leg_name"].rsplit(" ", 1)[0].split("/")
            if len(lag_member_values) == 1:
                lag_member = {"name": "lagMember", "value": lag_member_values[0]}
            elif len(lag_member_values) == 2:
                # use the TIDs in the "path_name" with the "sequence" to determine lag sort
                path_val = network_device["path_name"].split(".")
                if network_device["sequence"].split(".")[3] == "0001" and network_device["tid"][0:11] in path_val[2]:
                    # path_val[2] = first TID (A-facing)
                    lags_to_join = [lag_member_values[0]]
                else:
                    lags_to_join = [lag_member_values[1]]
                lag_member = {"name": "lagMember", "value": " ".join(lags_to_join)}

            elif len(lag_member_values) > 2:
                msg = granite_msg(INCORRECT_DATA, "Leg Name", network_device["leg_name"])
                abort(502, msg, summary=get_standard_error_summary(msg))

            # Check that we're actually working with a lag
            multi_leg_names = ["PRIMARY", "SECONDARY"]
            add_lag = False if lag_member_values[-1] in multi_leg_names else True
            if add_lag is True and isinstance(lag_member, dict):
                owned_node_data["name"].append(lag_member)

        return owned_node_data

    def is_bonus_hosted_voice_port(self, port_name, device_role):
        # bonus port only found on hosted voice service type Z (CPE) device role, no need to search if not those
        if self.circuit_data["service_type"] != "VOICE-HOST":
            return False
        if device_role != "Z":
            return False
        # bonus port naming schema are "<number>-<number>" or "USER <number>-<number>"
        bonus_port_found = False
        bonus_port_simple_pattern = re.fullmatch(r"\d-\d", port_name)
        bonus_port_user_pattern = re.fullmatch(r"USER \d-\d", port_name)
        if bonus_port_simple_pattern or bonus_port_user_pattern:
            bonus_port_found = True
        return bonus_port_found

    def _build_node_data(self, network_device, network_elements):
        node_data = {
            "uuid": network_device["tid"][0:11],
            "name": [
                {"name": "hostName", "value": network_device["tid"][0:11]},
                {"name": "deviceRole", "value": self._get_device_role(network_device)},
                {"name": "vendor", "value": self._get_vendor(network_device)},
                {"name": "model", "value": network_device["model"]},
                {"name": "managementIP", "value": self._get_management_ip(network_device)},
                {"name": "location", "value": network_device["location"]},
                {"name": "address", "value": network_device["full_address"] + " " + network_device["zip_code"]},
                {"name": "fqdn", "value": network_device["device_id"]},
                {"name": "equipmentStatus", "value": network_device["device_status"].upper()},
            ],
            "ownedNodeEdgePoint": [],
        }
        owned_node_data = self._build_owned_node_edge_point(network_device, network_elements)
        if owned_node_data:
            node_data["ownedNodeEdgePoint"].append(owned_node_data)
        return node_data

    def _get_device_role(self, network_device):
        device_roles = {"C": "PE", "A": "MTU", "Q": "AGG", "Z": "CPE"}
        if network_device["vendor"] == "ALCATEL" or network_device["vendor"] == "NOKIA":
            return self._get_alcatel_device_role(network_device)
        # check for agg customer handoff
        if network_device["device_role"] == "A" and network_device["site_type"] in ("LOCAL", "CUST_PREM"):
            return "CPE"
        # check for CTBH CPE
        if network_device["site_type"] == "CELL":
            return "CPE"
        return device_roles.get(network_device["device_role"], "")

    def _get_vendor(self, network_device):
        if network_device["vendor"] == "ALCATEL":
            return "NOKIA"
        return network_device["vendor"]

    def _get_alcatel_device_role(self, network_device):
        if network_device["model"] in NOKIA_7750_MODELS:
            return "PE"
        elif network_device["model"] in NOKIA_7210_MODELS or network_device["model"] in NOKIA_7705_MODELS:
            return "CPE"

    def _get_management_ip(self, network_device):
        management_ip = None
        if network_device["management_ip"]:
            management_ip = network_device["management_ip"].split("/")[0]
        return management_ip

    def _build_service_model(self, network_elements, connection_type=None):
        #  init the service data model
        service_data = {"model": "MEF-LEGATO-EVC", "version": "2017-07-27", "data": {"evc": []}}
        if self.service_type in FIA_SERVICE_TYPES:
            service_data["data"]["fia"] = self._build_fia_service_data(network_elements[0]["owned_edge_point"])

        cos = self.circuit_data["cos"]
        bandwidth = self._get_bandwidth()
        if not connection_type:
            connection_type = "Point to Point"

        evc_data = {
            "cosNames": self._get_cos_names(cos),
            "evc-ingress-bwp": bandwidth,
            "evc-egress-bwp": bandwidth,
            "adminState": True,
            "userLabel": self.circuit_data["cid"],
            "maxNumOfEvcEndPoint": self._get_max_evc_endpoints(),
            "serviceType": self._get_evc_service_type(),
            "connectionType": connection_type,
            "sVlan": "Untagged",  # Default
        }
        if self.trunked:
            evc_data["msVlan"] = "88"
        evc_data["endPoints"] = []
        if cos:
            evc_data["perfTier"] = self._get_cos_perf_tier(cos)
        if self.circuit_data["evc_id"]:
            evc_data["evcId"] = self.circuit_data["evc_id"]
        if self.service_type == "ELAN":
            evc_data = self._add_elan_evc_data(evc_data)

        # default if none populated based on service type
        if not evc_data["maxNumOfEvcEndPoint"]:
            evc_data["maxNumOfEvcEndPoint"] = 2
        if not evc_data["serviceType"]:
            evc_data["serviceType"] = self.service_type

        if self.service_type == "NNI":
            evc_data = self._add_carrier_nni_evc_endpoints(evc_data, network_elements)
        evc_data = self._add_evc_endpoints(evc_data, network_elements)
        service_data["data"]["evc"].append(evc_data)

        return service_data

    def _build_fia_service_data(self, owned_node_edgepoint_uni_id):
        bgp = self._is_bgp()
        fia_service_data = []

        data = {"type": self._get_fia_type(bgp), "endPoints": []}

        fia_endpoints = {
            "uniId": owned_node_edgepoint_uni_id,
            "lanIpv4Addresses": self._get_lan_ipv4_addresses(),
            "lanIpv6Addresses": self._get_lan_ipv6_addresses(),
        }
        ipv4_glue_subnet = self.circuit_data["ipv4_glue_subnet"]
        if ipv4_glue_subnet:
            fia_endpoints["wanIpv4Address"] = ipv4_glue_subnet.replace(" ", "")
        ipv6_glue_subnet = self.circuit_data["ipv6_glue_subnet"]
        if ipv6_glue_subnet:
            fia_endpoints["wanIpv6Address"] = ipv6_glue_subnet.replace(" ", "")
        if bgp:
            fia_endpoints["bgp"] = {
                "asn": self.circuit_data["cust_bgp_asn"],
                "BGPIpv4Prefixes": self.circuit_data["ipv4_bgp_cust_blocks"],
                "exportpolicy": self.circuit_data["ipv4_bgp_requested_routes"],
            }
        data["endPoints"].append(fia_endpoints)
        fia_service_data.append(data)
        return fia_service_data

    def _is_bgp(self):
        bgp = True if self.circuit_data["cust_bgp_asn"] else False
        return bgp

    def _get_fia_type(self, bgp):
        if self.service_type == "VOICE" and "HOST" not in self.circuit_data["service_type"]:
            return "VOICE"
        if not self.circuit_data["ipv4_glue_subnet"] and not bgp:
            return "DIRECT"
        elif bgp:
            return "BGP"
        else:
            return "STATIC"

    def _get_lan_ipv4_addresses(self):
        lan_ipv4_addresses = []
        if self.circuit_data["ip4_address"]:
            ip4_addresses = self.circuit_data["ip4_address"].split(",")
            subnets = None
            if self.circuit_data.get("ipv4_assigned_subnet"):
                subnets = self.circuit_data["ipv4_assigned_subnet"].split(",")
            elif self.circuit_data.get("ipv4_assigned_gateway"):
                gateways = self.circuit_data.get("ipv4_assigned_gateway").split(",")
                subnets = [subnet_cidr.split("/")[-1] for subnet_cidr in gateways if len(subnet_cidr.split("/")) > 1]
            if not subnets:
                ip_cidr = self.circuit_data["ip4_address"].split("/")
                if len(ip_cidr) > 1:
                    subnets = [ip_cidr[-1]]
            if self.service_type == "VOICE" and "HOST" not in self.circuit_data["service_type"]:
                return self.circuit_data["ip4_address"]
            if subnets is None:
                msg = granite_msg(MISSING_DATA, SUBNET)
                abort(502, msg, summary=get_standard_error_summary(msg))
            if len(ip4_addresses) != len(subnets):
                msg = granite_msg(INCORRECT_DATA, SUBNET, f"{ip4_addresses} {subnets}")
                abort(502, msg, summary=get_standard_error_summary(msg))
            for count, ip in enumerate(ip4_addresses):
                clean_ipv4 = clean_data(ipv4=ip.strip() + subnets[count].strip())
                try:
                    lan_ipv4_addresses.append(clean_ipv4["ipv4"]["ipv4_subnet_list"][0])
                except IndexError:
                    msg = granite_msg(MISSING_DATA, SUBNET, ip4_addresses)
                    abort(502, msg, summary=get_standard_error_summary(msg))
        else:
            if "ipv4_assigned_subnet" in self.circuit_data and self.circuit_data["ipv4_assigned_subnet"]:
                clean_ipv4 = clean_data(ipv4=self.circuit_data["ipv4_assigned_subnet"])
                lan_ipv4_addresses = clean_ipv4["ipv4"]["ipv4_subnet_list"]
        return lan_ipv4_addresses

    def _get_lan_ipv6_addresses(self):
        lan_ipv6_addresses = []
        if self.circuit_data["ipv6_assigned_subnet"]:
            lan_ipv6_addresses = self.circuit_data["ipv6_assigned_subnet"].split(",")
            for i, ip in enumerate(lan_ipv6_addresses):
                lan_ipv6_addresses[i] = ip.replace(" ", "")
        return lan_ipv6_addresses

    def _get_cos_names(self, cos):
        # use designed value
        if cos:
            cos_level = cos.split(" ")[0]
            return [{"name": cos_level}]
        # use default value
        else:
            if self.service_type in FIA_SERVICE_TYPES:
                return [{"name": "BRONZE"}]
            else:
                cos_names = [{"name": "SILVER"}]
                customer_type = self.circuit_data["customer_type"]
                if customer_type and customer_type == "CAR":
                    cos_names = [{"name": "GOLD"}]
                return cos_names

    def _add_elan_evc_data(self, evc_data):
        circ_path_inst_id = self.circuit_elements[0]["circ_path_inst_id"]
        vpls_network_object = self.circuit_elements[0]["data"][0]
        vpls_network_id = vpls_network_object.get("path_name")
        evc_data["vplsNetworkId"] = vpls_network_id.replace(" ", "_")
        vpls = get_vpls_vlan_id(vpls_network_object)
        evc_data["vplsVlanId"] = vpls
        elan_slm_data = get_elan_slm_data(self.cid, circ_path_inst_id)
        if elan_slm_data:
            evc_data["elanSlm"] = elan_slm_data
        return evc_data

    def _get_cos_perf_tier(self, cos):
        cos_perf_tier = cos.split(" ")[1]
        return [{"name": cos_perf_tier}]

    def _get_bandwidth(self):
        bw_value = self.circuit_data["bandwidth"].split(" ")[0]
        try:
            bw_unit = self.circuit_data["bandwidth"].split(" ")[1].lower()
        except IndexError:
            msg = granite_msg(INCORRECT_DATA, "Bandwidth", self.circuit_data["bandwidth"])
            abort(502, msg, summary=get_standard_error_summary(msg))
        if "m" in bw_unit:
            bw_unit = "m"
        else:
            bw_unit = "g"
        return f"{bw_value}{bw_unit}"

    def _get_max_evc_endpoints(self):
        max_evc_endpoints = {"FIA": 1, "VOICE": 1, "ELINE": 2, "ELAN": 1, "NNI": 1, "VIDEO": 1}
        return max_evc_endpoints.get(self.service_type)

    def _get_evc_service_type(self):
        for element in self.circuit_data["data"]:
            cevlan = False
            if element["cevlan"]:
                # if cevlan exists, evc_data['serviceType'] will be EVPL* instead of EPL*
                cevlan = True
                break

        evc_service_types = {
            "FIA": "IP",
            "VOICE": "IP",
            "ELINE": "EVPL" if cevlan else "EPL",
            "CTBH 4G": "EVPL" if cevlan else "EPL",
            "ELAN": "EVP-LAN" if cevlan else "EP-LAN",
            "NNI": "NNI",
            "VIDEO": "RPHY",
        }
        return evc_service_types.get(self.service_type)

    def _add_evc_endpoints(self, evc_data, network_elements):
        found_svlan = False
        last_evc_endpoint = {}  # Use this if no vlan is found
        for network_device in network_elements:
            # add endPoints that don't have TRANSPORT or NNI at the end of the path_type
            if network_device["path_type"].split(" ")[-1] not in ("TRANSPORT", "NNI"):
                if network_device["svlan"]:
                    found_svlan = True
                    evc_endpoint = self._build_base_evc_endpoint(network_device)
                    evc_endpoint["sVlan"] = network_device["svlan"]
                    if network_device["vlan_operation"]:
                        evc_endpoint["sVlanOperation"] = network_device["vlan_operation"]
                    if network_device["cevlan"]:
                        evc_endpoint["ceVlans"] = network_device["cevlan"].split(",")
                    evc_data["sVlan"] = network_device["svlan"]
                    evc_data["endPoints"].append(evc_endpoint)
                elif not found_svlan and network_device["chan_name"]:
                    evc_data["sVlan"] = network_device["chan_name"][4:]
                else:
                    last_evc_endpoint = self._build_base_evc_endpoint(network_device)
        if not found_svlan:
            if "VOICE-HOST" in self.circuit_data["service_type"]:
                last_evc_endpoint = self._build_base_evc_endpoint(network_elements[-1])
                evc_data["sVlan"] = network_elements[-1]["svlan"]
            evc_data["endPoints"].append(last_evc_endpoint)
        if self.is_type_2:
            evc_data["endPoints"] = self._type_2_endpoint_fields(evc_data["endPoints"], network_elements)
        if self.trunked:
            evc_data["endPoints"][0]["msVlan"] = "88"
            if evc_data["endPoints"][0].get("ceVlan"):
                evc_data["endPoints"][0]["ceVlans"].append("88")
            else:
                evc_data["endPoints"][0]["ceVlans"] = [evc_data["sVlan"], "88"]
        return evc_data

    def _build_base_evc_endpoint(self, network_device):
        return {
            "uniId": f"{network_device['tid'][0:11]}-{network_device['port_access_id'].split('.')[0]}",
            "adminState": True,
            "address": network_device["full_address"].strip() + " " + network_device["zip_code"],
        }

    def _type_2_endpoint_fields(self, evc_data, network_elements):
        for network_device in network_elements:
            for index, evc in enumerate(evc_data):
                if evc.get("uniId") == f"{network_device['tid'][0:11]}-{network_device['port_access_id'].split('.')[0]}":
                    evc_endpoint = evc_data[index]
                    if network_device["chan_name"]:
                        if "//" in network_device["chan_name"]:
                            evc_endpoint["unit"] = network_device["chan_name"].split(":")[0]
                            evc_endpoint["outerVlan"] = (
                                network_device["chan_name"].split(":")[1].split("//")[0].split("-")[1].lstrip("0")
                            )
                            evc_endpoint["innerVlan"] = (
                                network_device["chan_name"].split(":")[1].split("//")[1].split("-")[1].lstrip("0")
                            )
                            evc_endpoint["type2"] = True
        return evc_data

    def _add_carrier_nni_evc_endpoints(self, evc_data, network_elements):
        for network_device in network_elements:
            # add endPoints for NNI paths
            if network_device["path_type"].split(" ")[-1] in ("CAR-NNI", "CUS-ENNI-BUY"):
                evc_endpoint = self._build_base_evc_endpoint(network_device)
                evc_data["endPoints"].append(evc_endpoint)
        return evc_data

    def _remediate_evc_ids(self, ml_topology):
        ml_evc_ids = ml_topology["PRIMARY"]["service"][0]["data"]["evc"][0]["evcId"].split(",")

        if len(ml_evc_ids) != len(ml_topology):
            msg = granite_msg(INCORRECT_DATA, "EVCID", "number of evcids does not align with number of legs in circuit")
            abort(501, msg, summary=get_standard_error_summary(msg))

        ml_topology["PRIMARY"]["service"][0]["data"]["evc"][0]["evcId"] = ml_evc_ids[0]
        ml_topology["SECONDARY"]["service"][0]["data"]["evc"][0]["evcId"] = ml_evc_ids[-1]

        return ml_topology

    def _check_topology_links(self, topology_data):
        links = []
        ports = []

        for link in topology_data["data"]["link"]:
            for port in link["nodeEdgePoint"]:
                ports.append(port)
                links.append(self._normalize_link(link["uuid"]))

        duplicate_ports = {port for port in ports if ports.count(port) > 1}
        if duplicate_ports:
            logger.debug("Granite Issue - Multiple linked ports")
            msg = granite_msg(INCORRECT_DATA, "Linked Ports", duplicate_ports)
            abort(501, msg, summary=get_standard_error_summary(msg))

        upstream_tids = [self._get_tid_from_edgepoint(link.split("_", 1)[0]) for link in links]
        downstream_tids = [self._get_tid_from_edgepoint(link.split("_", 1)[1]) for link in links]
        linked_tids = zip(upstream_tids, downstream_tids)
        for first_upstream_tid, first_downstream_tid in linked_tids:
            for second_upstream_tid, second_downstream_tid in linked_tids:
                upstream_pair = f"{first_upstream_tid}<>{second_upstream_tid}"
                downstream_pair = f"{first_downstream_tid}<>{second_downstream_tid}"
                pairs = f"Upstream: {upstream_pair} Downstream: {downstream_pair}"
                if first_upstream_tid == second_upstream_tid and first_downstream_tid != second_downstream_tid:
                    logger.debug(f"Granite Issue - Multiple device pairings: {pairs}")
                    msg = granite_msg(INCORRECT_DATA, "Paired Devices", pairs)
                    abort(501, msg, summary=get_standard_error_summary(msg))
                if first_downstream_tid == second_downstream_tid and first_upstream_tid != second_upstream_tid:
                    logger.debug(f"Granite Issue - Multiple device pairings: {pairs}")
                    msg = granite_msg(INCORRECT_DATA, "Paired Devices", pairs)
                    abort(501, msg, summary=get_standard_error_summary(msg))

    def _normalize_link(self, link):
        return link.replace("ETH_PORT", "ETHPORT")

    def _get_tid_from_edgepoint(self, port_uuid):
        if (port_uuid[3]) == "-":
            tid_1, tid_2, _ = port_uuid.split("-", 2)
            tid = tid_1 + "-" + tid_2
            if re.match(r"^[-a-zA-Z0-9]*$", tid) and len(tid) == 11:
                return tid
            else:
                logger.debug("Invalid TID")
                msg = granite_msg(INCORRECT_DATA, "Device TID", tid)
                abort(501, msg, summary=get_standard_error_summary(msg))
        else:
            tid = port_uuid.split("-", 1)[0]
            if re.match(r"^[-a-zA-Z0-9]*$", tid) and len(tid) == 11:
                return tid
            else:
                logger.debug("Invalid TID")
                msg = granite_msg(INCORRECT_DATA, "Device TID", tid)
                abort(501, msg, summary=get_standard_error_summary(msg))


class TopologyUtils:
    def get_circuit_data(self, denodo_elements):
        denodo_element = None
        for element in denodo_elements:
            if element["status"] == "Designed":
                denodo_element = element
                break
            elif element["status"] == "Live":
                denodo_element = element
            else:
                denodo_element = element
        return denodo_element

    def consolidate_clouds(self, data):
        """Turn multiple clouds that are all back to back into a single cloud element for splitting purposes"""
        cloud_consolidation = []
        preceeding_cloud = False

        for device in data:
            if not device["split_id"]:
                preceeding_cloud = False
                cloud_consolidation.append(device)
            elif device["split_id"] and len(cloud_consolidation) > 0 and not preceeding_cloud:
                preceeding_cloud = True
                cloud_consolidation.append(device)

        return cloud_consolidation

    def get_linked_interfaces(self, topology):
        links = []
        for topo in topology["topology"]:
            for link in topo["data"]["link"]:
                if link.get("uuid"):
                    links.append(link["uuid"])
        return links

    def get_topology_devices(self, topology, links):
        required_name_data = ["hostName", "vendor", "model", "deviceRole", "equipmentStatus", "fqdn"]
        required_owned_node_edge_point_data = ["name", "portRole"]
        device_data = []

        for topo in topology["topology"]:
            for device in topo["data"]["node"]:
                data = {item["name"]: item["value"] for item in device["name"] if item["name"] in required_name_data}
                for node in device["ownedNodeEdgePoint"]:
                    data["node_uuid"] = node["uuid"]
                    for item in node["name"]:
                        if item["name"] in required_owned_node_edge_point_data:
                            data[item["name"]] = item["value"]

                    if len([i for i in links if data["node_uuid"] in i]) == 0:
                        data["link"] = False
                    else:
                        data["link"] = True

                    device_data.append(data.copy())
        return device_data
