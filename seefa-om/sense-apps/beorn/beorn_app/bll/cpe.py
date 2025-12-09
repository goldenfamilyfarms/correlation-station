import copy
import logging
import re
from time import sleep

from beorn_app.bll.eligibility import mdso_eligible
from common_sense.common.errors import abort
from beorn_app.common.mdso_auth import create_token, delete_token
from beorn_app.common.mdso_operations import post_to_service, product_query
from beorn_app.common.utils import set_headers
from beorn_app.dll.mdso import (
    get_ip,
    get_mac,
    get_port_status,
    mdso_get,
    mdso_post,
    resync_resource,
    service_details,
    service_id_lookup,
)

logger = logging.getLogger(__name__)

ELIGIBLES = {
    "FIA": {
        "JUNIPER": {
            mdso_eligible.JUNIPER_MX_MODELS: {
                "NEW": ["INNI", "UNI", "ENNI"],
                "DISCONNECT": ["INNI", "UNI", "ENNI"],
                "CHANGE": ["INNI", "UNI", "ENNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.JUNIPER_QFX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.JUNIPER_ACX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": [],
            },
            mdso_eligible.JUNIPER_EX_MODELS: {
                "NEW": ["INNI", "UNI"],
                "DISCONNECT": ["INNI", "UNI"],
                "CHANGE": ["INNI", "UNI"],
                "INSTALL": ["INNI"],
            },
        },
        "RAD": {
            mdso_eligible.RAD_220_MODELS: {
                "NEW": ["UNI", "ENNI", "INNI"],
                "DISCONNECT": ["UNI", "ENNI", "INNI"],
                "CHANGE": ["UNI", "ENNI", "INNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.RAD_203_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": ["UNI", "INNI"],
            },
            mdso_eligible.RAD_2I_MODELS: {
                "NEW": ["ENNI", "INNI", "UNI"],
                "DISCONNECT": ["ENNI", "INNI", "UNI"],
                "CHANGE": ["ENNI", "INNI", "UNI"],
                "INSTALL": ["UNI", "INNI"],
            },
        },
        "ADVA": {
            mdso_eligible.ADVA_114_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": ["UNI"],
            },
            mdso_eligible.ADVA_116_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": ["UNI"],
            },
            mdso_eligible.ADVA_120_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": [],
            },
            mdso_eligible.ADVA_108_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": ["UNI"],
            },
        },
        "CISCO": {
            mdso_eligible.CISCO_9K_MODELS: {
                "NEW": ["INNI", "UNI", "ENNI"],
                "DISCONNECT": [],
                "CHANGE": [],
                "INSTALL": [],
            },
            mdso_eligible.CISCO_920_MODELS: {
                "NEW": ["INNI", "UNI", "ENNI"],
                "DISCONNECT": [],
                "CHANGE": [],
                "INSTALL": [],
            },
        },
    },
    "ELINE": {
        "JUNIPER": {
            mdso_eligible.JUNIPER_MX_MODELS: {
                "NEW": ["INNI", "ENNI"],
                "DISCONNECT": ["INNI", "ENNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": [],
            },
            mdso_eligible.JUNIPER_QFX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": [],
            },
            mdso_eligible.JUNIPER_ACX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": [],
            },
            mdso_eligible.JUNIPER_EX_MODELS: {
                "NEW": ["INNI", "UNI"],
                "DISCONNECT": ["INNI", "UNI"],
                "CHANGE": ["INNI", "UNI"],
                "INSTALL": [],
            },
        },
        "RAD": {
            mdso_eligible.RAD_220_MODELS: {
                "NEW": ["UNI", "ENNI", "INNI"],
                "DISCONNECT": ["UNI", "ENNI", "INNI"],
                "CHANGE": ["UNI", "ENNI", "INNI"],
                "INSTALL": [],
            },
            mdso_eligible.RAD_203_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": [],
            },
            mdso_eligible.RAD_2I_MODELS: {
                "NEW": ["ENNI", "INNI", "UNI"],
                "DISCONNECT": ["ENNI", "INNI", "UNI"],
                "CHANGE": ["ENNI", "INNI", "UNI"],
                "INSTALL": [],
            },
        },
        "ADVA": {
            mdso_eligible.ADVA_114_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": [],
            },
            mdso_eligible.ADVA_116_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": [],
            },
            mdso_eligible.ADVA_120_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": [],
            },
            mdso_eligible.ADVA_108_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": [],
            },
        },
    },
    "VOICE": {
        "JUNIPER": {
            mdso_eligible.JUNIPER_MX_MODELS: {
                "NEW": ["INNI", "UNI", "ENNI"],
                "DISCONNECT": ["INNI", "UNI", "ENNI"],
                "CHANGE": ["INNI", "UNI", "ENNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.JUNIPER_QFX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.JUNIPER_ACX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": [],
            },
            mdso_eligible.JUNIPER_EX_MODELS: {
                "NEW": ["INNI", "UNI"],
                "DISCONNECT": ["INNI", "UNI"],
                "CHANGE": ["INNI", "UNI"],
                "INSTALL": ["INNI"],
            },
        },
        "RAD": {
            mdso_eligible.RAD_220_MODELS: {
                "NEW": ["UNI", "ENNI", "INNI"],
                "DISCONNECT": ["UNI", "ENNI", "INNI"],
                "CHANGE": ["UNI", "ENNI", "INNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.RAD_203_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": ["UNI", "INNI"],
            },
            mdso_eligible.RAD_2I_MODELS: {
                "NEW": ["ENNI", "INNI", "UNI"],
                "DISCONNECT": ["ENNI", "INNI", "UNI"],
                "CHANGE": ["ENNI", "INNI", "UNI"],
                "INSTALL": ["UNI", "INNI"],
            },
        },
        "ADVA": {
            mdso_eligible.ADVA_114_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": ["UNI"],
            },
            mdso_eligible.ADVA_116_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": [],
                "INSTALL": ["UNI"],
            },
            mdso_eligible.ADVA_120_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": [],
                "INSTALL": [],
            },
            mdso_eligible.ADVA_108_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": [],
            },
        },
        "CISCO": {
            mdso_eligible.CISCO_9K_MODELS: {"NEW": ["INNI", "UNI", "ENNI"], "CHANGE": [], "INSTALL": []},
            mdso_eligible.CISCO_920_MODELS: {"NEW": ["INNI", "UNI", "ENNI"], "CHANGE": [], "INSTALL": []},
        },
    },
    "VIDEO": {
        "JUNIPER": {
            mdso_eligible.JUNIPER_MX_MODELS: {
                "NEW": ["INNI", "UNI", "ENNI"],
                "DISCONNECT": ["INNI", "UNI", "ENNI"],
                "CHANGE": ["INNI", "UNI", "ENNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.JUNIPER_QFX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.JUNIPER_ACX_MODELS: {
                "NEW": ["INNI"],
                "DISCONNECT": ["INNI"],
                "CHANGE": ["INNI"],
                "INSTALL": [],
            },
            mdso_eligible.JUNIPER_EX_MODELS: {
                "NEW": ["INNI", "UNI"],
                "DISCONNECT": ["INNI", "UNI"],
                "CHANGE": ["INNI", "UNI"],
                "INSTALL": ["INNI"],
            },
        },
        "RAD": {
            mdso_eligible.RAD_220_MODELS: {
                "NEW": ["UNI", "ENNI", "INNI"],
                "DISCONNECT": ["UNI", "ENNI", "INNI"],
                "CHANGE": ["UNI", "ENNI", "INNI"],
                "INSTALL": ["INNI"],
            },
            mdso_eligible.RAD_203_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": ["UNI", "INNI"],
            },
            mdso_eligible.RAD_2I_MODELS: {
                "NEW": ["ENNI", "INNI", "UNI"],
                "DISCONNECT": ["ENNI", "INNI", "UNI"],
                "CHANGE": ["ENNI", "INNI", "UNI"],
                "INSTALL": ["UNI", "INNI"],
            },
        },
        "ADVA": {
            mdso_eligible.ADVA_114_MODELS: {
                "NEW": ["UNI", "INNI"],
                "DISCONNECT": ["UNI", "INNI"],
                "CHANGE": ["UNI", "INNI"],
                "INSTALL": ["UNI"],
            },
            mdso_eligible.ADVA_116_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": [],
                "INSTALL": ["UNI"],
            },
            mdso_eligible.ADVA_120_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "DISCONNECT": ["INNI", "ENNI", "UNI"],
                "CHANGE": [],
                "INSTALL": [],
            },
            mdso_eligible.ADVA_108_MODELS: {
                "NEW": ["INNI", "ENNI", "UNI"],
                "CHANGE": ["INNI", "ENNI", "UNI"],
                "INSTALL": [],
            },
        },
        "CISCO": {
            mdso_eligible.CISCO_9K_MODELS: {
                "NEW": ["INNI", "UNI", "ENNI"],
                "DISCONNECT": [],
                "CHANGE": [],
                "INSTALL": [],
            },
            mdso_eligible.CISCO_920_MODELS: {"NEW": ["INNI", "UNI", "ENNI"], "CHANGE": [], "INSTALL": []},
        },
    },
    "CTBH 4G": {
        "JUNIPER": {
            mdso_eligible.JUNIPER_MX_MODELS: {"NEW": ["INNI", "ENNI"], "CHANGE": [], "INSTALL": []},
            mdso_eligible.JUNIPER_QFX_MODELS: {"NEW": ["INNI"], "CHANGE": [], "INSTALL": []},
            mdso_eligible.JUNIPER_ACX_MODELS: {"NEW": ["INNI"], "CHANGE": [], "INSTALL": []},
            mdso_eligible.JUNIPER_EX_MODELS: {"NEW": ["INNI"], "CHANGE": [], "INSTALL": []},
        },
        "RAD": {
            mdso_eligible.RAD_220_MODELS: {"NEW": ["INNI"], "CHANGE": [], "INSTALL": []},
            mdso_eligible.RAD_203_MODELS: {"NEW": [], "CHANGE": [], "INSTALL": []},
            mdso_eligible.RAD_2I_MODELS: {"NEW": ["INNI"], "CHANGE": [], "INSTALL": []},
        },
        "ADVA": {
            mdso_eligible.ADVA_114_MODELS: {"NEW": [], "CHANGE": [], "INSTALL": []},
            mdso_eligible.ADVA_116_MODELS: {"NEW": ["INNI", "ENNI", "UNI"], "CHANGE": [], "INSTALL": []},
            mdso_eligible.ADVA_120_MODELS: {"NEW": ["INNI"], "CHANGE": [], "INSTALL": []},
        },
        "CIENA": {mdso_eligible.CIENA_MODELS: {"NEW": ["UNI", "INNI", "ENNI"], "CHANGE": [], "INSTALL": []}},
    },
    "NNI": {
        "JUNIPER": {
            mdso_eligible.JUNIPER_MX_MODELS: {
                "NEW": ["INNI", "UNI", "ENNI"],
                "DISCONNECT": [],
                "CHANGE": [],
                "INSTALL": ["INNI", "ENNI"],
            }
        }
    },
    "NO_SERVICE": {
        "JUNIPER": {
            mdso_eligible.JUNIPER_MX_MODELS: {
                "SCOD": ["INNI"],
                "TULIP": ["INNI"],
                "FIRMUP": [],
                "PORT_PATTERNS": [r"^(G|X)E-([0-9]|10)\/\d\/\d{1,2}$"],
            },
            mdso_eligible.JUNIPER_QFX_MODELS: {
                "TULIP": ["INNI"],
                "SCOD": ["INNI"],
                "FIRMUP": [],
                "PORT_PATTERNS": [r"^(G|X)E-[01]\/0\/(\d|([0-8][0-9])|(9[0-5]))$"],
            },
            mdso_eligible.JUNIPER_ACX_MODELS: {
                "SCOD": ["INNI"],
                "TULIP": ["INNI"],
                "FIRMUP": [],
                "PORT_PATTERNS": [r"^XE-0\/0\/(\d|([0-3][0-9])|(4[0-7]))$"],
            },
            mdso_eligible.JUNIPER_EX_MODELS: {
                "SCOD": ["INNI"],
                "TULIP": ["INNI"],
                "FIRMUP": [],
                "PORT_PATTERNS": [r"^(G|X)E-\d\/[01]\/([0-9]|([1-3][0-9])|4[0-8])$"],
            },
        },
        "RAD": {
            mdso_eligible.RAD_220_MODELS: {
                "SCOD": ["INNI", "UNI"],
                "TULIP": ["INNI"],
                "FIRMUP": [],
                "PORT_PATTERNS": [r"^[3-4]\/[1-2]$|^1\/([1-9]|10)$"],
            },
            mdso_eligible.RAD_203_MODELS: {
                "SCOD": ["UNI"],
                "TULIP": [],
                "FIRMUP": ["UNI"],
                "PORT_PATTERNS": [r"^ETH PORT [1-6]$"],
            },
            mdso_eligible.RAD_2I_MODELS: {
                "SCOD": ["INNI", "UNI"],
                "TULIP": ["INNI"],
                "FIRMUP": ["UNI"],
                # Rad 2i and 2i-B are in same mdso_eligible.RAD_2I_MODELS list,
                # 1st pattern is for 2i (non Rev-B) models, 2nd pattern is for 2i Rev B models
                "PORT_PATTERNS": [r"(^ETH PORT 0\/[1-9]$)|(^ETH PORT 0\/((1[0-9])|(2[0-8]))$)", r"^0\/[1-8]$"],
            },
        },
        "ADVA": {
            mdso_eligible.ADVA_114_MODELS: {
                "SCOD": ["UNI"],
                "TULIP": [],
                "FIRMUP": ["UNI"],
                "PORT_PATTERNS": [r"^ACCESS-1-1-1-[3-6]$|^NETWORK-1-1-1-[1,2]$"],
            },
            mdso_eligible.ADVA_116_MODELS: {
                "SCOD": ["UNI"],
                "TULIP": [],
                "FIRMUP": ["UNI"],
                "PORT_PATTERNS": [r"ETH_PORT-1-1-1-[1-8]$"],
            },
            mdso_eligible.ADVA_120_MODELS: {
                "SCOD": [],
                "TULIP": [],
                "FIRMUP": [],
                "PORT_PATTERNS": [r"ETH_PORT-1-1-1-([1-9]|1[0-9]|2[0-6])$"],
            },
            mdso_eligible.ADVA_108_MODELS: {
                "SCOD": ["UNI"],
                "TULIP": [],
                "FIRMUP": ["UNI"],
                "PORT_PATTERNS": [r"^ACCESS-1-1-1-[3-6]$|^NETWORK-1-1-1-[1,2]$"],
            },
        },
    },
    "Unsupported": {},  # dictionary to use for unsupported services
}


def create_activate_site_op_id(mdso_network_service_id, ip, tid, port_id):
    if ip:
        payload = {"interface": "activateSite", "inputs": {"ip": ip, "site": tid, "port": port_id}}
    else:
        payload = {"interface": "activateSite", "inputs": {"site": tid, "port": port_id}}
    endpoint = f"/bpocore/market/api/v1/resources/{mdso_network_service_id}/operations"
    mdso_operation = mdso_post(endpoint, payload)
    if mdso_operation["items"]:
        return mdso_operation["items"][0]["id"]
    else:
        abort(404, "Operation ID not returned from MDSO")


def get_uni_port_from_circuit_details(mdso_network_service_id):
    query = f"/bpocore/market/api/v1/resources/{mdso_network_service_id}/dependencies?recursive=true&offset=0&limit=1000"
    response_json = mdso_get(query)
    for i in response_json["items"]:
        if i["resourceTypeId"] == "charter.resourceTypes.CircuitDetails":
            try:
                for top in i["properties"]["topology"]:
                    for node in top["data"]["node"]:
                        device = {x["name"]: x["value"] for x in node["name"]}
                        if device["Role"] == "CPE":
                            for d in node["ownedNodeEdgePoint"]:
                                edge = {}
                                for z in d["name"]:
                                    edge[z["name"]] = z["value"]
                                if edge["Role"] == "UNI":
                                    return edge["Name"]
            except KeyError:
                continue
    return "No UNI Port found"


def lookup_existing_cpe_activator_resource(mdso_network_service_id):
    query = (
        f"/bpocore/market/api/v1/resources/{mdso_network_service_id}/dependencies?recursive=false&"
        f"resourceTypeId=charter.resourceTypes.cpeActivator&obfuscate=true&offset=0&limit=1000"
    )
    response_json = mdso_get(query)
    cpe_activator_resources = []
    for i in response_json["items"]:
        cpe_activator_resource = {"cpea_resource_id": i["id"], "cpea_orchState": i["orchState"]}
        cpe_activator_resources.append(cpe_activator_resource)

    return cpe_activator_resources


def dependencies_by_resource(resource_id, cid):
    endpoint = (
        "/bpocore/market/api/v1/resources/{}/dependencies?recursive=true&q=label:{}.cd&offset=0&limit=1000".format(
            resource_id, cid
        )
    )
    return mdso_get(endpoint)


def is_network_service_orchState_active(network_service_resources):
    for resource in network_service_resources["items"]:
        if resource["orchState"] == "active":
            return resource

    return None


def activate_cpe(body):
    # Body Data #
    cid = body.get("cid")
    tid = body.get("tid")
    port_id = body.get("port_id")
    ip = body.get("ip")

    # Get Network Service ID #
    mdso_network_service_id = service_id_lookup(cid)

    # Create Activate Site Op ID #
    mdso_operation_id = create_activate_site_op_id(mdso_network_service_id, ip, tid, port_id)
    response = {"operationId": mdso_operation_id["id"], "resourceId": mdso_operation_id["resourceId"]}
    # Lookup Dependencies #
    response["uni_port"] = get_uni_port_from_circuit_details(mdso_network_service_id)
    # Return Response #
    return response


def cpe_activation_state(cid):
    network_service = service_details(cid, "charter.resourceTypes.NetworkService")
    network_service_items = network_service.get("items")
    if not network_service_items:
        abort(404, "Network Service Not Found")
    resource_id = network_service_items[0]["id"]

    dependencies = dependencies_by_resource(resource_id, cid)
    dependencies_items = dependencies.get("items")
    if not dependencies_items:
        abort(404, "No Dependency Items Found")

    response = {
        "resourceId": resource_id,
        "serviceType": dependencies_items[0]["properties"]["serviceType"],
        "networkServiceState": dependencies_items[0]["properties"]["state"],
        "cpeState": network_service_items[0]["properties"]["site_status"][0]["state"],
        "cid": cid,
        "customer": dependencies_items[0]["properties"]["customerName"],
    }

    for link in dependencies_items[0]["properties"]["topology"][0]["data"]["link"]:
        uuid = link["uuid"].split("_")
        uuid_a = uuid[0].split("-")
        uuid_b = uuid[1].split("-")
        cpe = uuid_b[0]
        if cpe.lower()[-2:] in ["zw", "ww", "xw", "yw"]:
            response["tid"] = uuid_a[0]
            response["portid"] = "-".join(uuid_a[1:])
            break
    for node in dependencies[0]["properties"]["topology"][0]["data"]["node"]:
        name = {}
        for pair in node["name"]:
            name[pair["name"]] = pair["value"]
        if name["Role"] == "CPE":
            response["physicalAddress"] = name["Address"]
            break
    if "cpe_activation" in network_service_items[0]["properties"]:
        response["cpeActivationStatus"] = network_service_items[0]["properties"]["cpe_activation"]
    if "cpe_activation_error" in network_service_items[0]["properties"]:
        response["cpeActivationError"] = network_service_items[0]["properties"]["cpe_activation_error"]
    return response


def get_service_type_eligibility(cid_topology):
    """
    Intake obj:cid_topology
    If not FIA; set ineligible to serviceType
    Return ineligible
    """
    ineligible = None
    if cid_topology["serviceType"] != "FIA":
        ineligible = cid_topology["serviceType"]
    return ineligible


# cleaning JSON response for feasible parsing later
def unpack_topology_json(cid_topology):
    topologies = []

    for topology in cid_topology["topology"]:
        new_topology = []
        for node in topology["data"]["node"]:
            curr_node = {"uuid": node["uuid"]}
            for old_value in node["name"]:
                curr_node[old_value["name"]] = old_value["value"]
            curr_node["ownedNodeEdgePoint"] = []

            for old_edge_point in node["ownedNodeEdgePoint"]:
                curr_edge_point = {"uuid": old_edge_point["uuid"]}
                for old_value in old_edge_point["name"]:
                    curr_edge_point[old_value["name"]] = old_value["value"]
                curr_node["ownedNodeEdgePoint"].append(curr_edge_point)

            new_topology.append(curr_node)

        topologies.append(new_topology)

    return topologies


def get_data(topology, cid):
    """
    Flatten topology for easier parsing
    Find UNI port role, add portRole under uni key to data, set upstream device tid
    Add UNI key:values to data
    Find upstream info to add to data
    Returns dict:data
    """
    flattened_topology = unpack_topology_json(topology)
    data = {}

    # Find UNI node and upstream tid
    for node in flattened_topology[0]:
        if node["deviceRole"] == "CPE":
            for edge_point in node["ownedNodeEdgePoint"]:
                if edge_point["portRole"] == "UNI":
                    uni_edge_node = node
                    data["uni"] = {"device_portRole": edge_point["portRole"], "port_name": edge_point["name"]}

    # Assign UNI values
    data["uni"]["device_model"] = uni_edge_node["model"]
    data["uni"]["device_role"] = uni_edge_node["deviceRole"]
    data["uni"]["device_vendor"] = uni_edge_node["vendor"]
    data["uni"]["uuid"] = uni_edge_node["uuid"]
    data["uni"]["equipmentStatus"] = uni_edge_node["equipmentStatus"]
    data["upstream"] = {}

    # Get upstream device model, vendor, and port role
    for node in flattened_topology[0]:
        equip_stat_live = node["equipmentStatus"] == "LIVE"
        pending_decommision = node["equipmentStatus"] == "PENDING DECOMMISSION"
        if (equip_stat_live or pending_decommision) and (node["deviceRole"] != "CPE"):
            for edge_point in node["ownedNodeEdgePoint"]:
                if edge_point["transportId"].split(".")[-1] == data["uni"]["uuid"]:
                    data["upstream"]["device_vendor"] = node["vendor"]
                    data["upstream"]["device_model"] = node["model"]
                    data["upstream"]["portRole"] = edge_point["portRole"]
                    data["upstream"]["portName"] = edge_point["name"]
                    data["upstream"]["hostname"] = node["uuid"]

    data_issue = None
    if (data.get("uni") == {}) or (data.get("upstream") == {}):
        data_issue = "Unable to determine CPE or upstream device"

    return data, data_issue


def cpe_device_eligibility(cpe_data, service_type="FIA", legacy_CPEA=True, task="INSTALL"):
    """
    Determine CPE Activation Device eligibility for CPE device.
    Default service type to FIA until stand alone config is fully live
    in MDSO/Beorn/Palantir/DICE
    """
    cpe_vendor = cpe_data["device_vendor"].upper()
    cpe_model = cpe_data["device_model"].upper()
    cpe_port_role = cpe_data["device_portRole"]
    ineligible = None
    eligible = False

    # Find vendor device models
    if cpe_vendor in ELIGIBLES[service_type].keys():
        for device_models in ELIGIBLES[service_type][cpe_vendor].keys():
            # Find cpe model in device_models
            if cpe_model in device_models:
                if cpe_port_role in ELIGIBLES[service_type][cpe_vendor][device_models][task]:
                    if not legacy_CPEA and cpe_model == "FSP 150CC-GE114/114S":
                        break
                    eligible = True
                    break
    if not eligible:
        if legacy_CPEA:
            ineligible = {"cpe_model": cpe_model, "cpe_port_role": cpe_port_role}
            return ineligible
        else:
            ineligible = {"cpe_vendor": cpe_vendor, "cpe_model": cpe_model}
            return ineligible
    if legacy_CPEA:
        if cpe_data["equipmentStatus"] == "LIVE":
            ineligible = {"cpe_equipment_status": cpe_data["equipmentStatus"]}
        return ineligible


def get_pe_router_eligibility(pe_router_data):
    """
    Determine CPE Activation Device eligibility for pe router device.
    Default service type to FIA until stand alone config is fully live
    in MDSO/Beorn/Palantir/DICE
    """
    el_pe_vendors = ["JUNIPER"]

    pe_router_model = pe_router_data["device_model"].upper()
    pe_router_vendor = pe_router_data["device_vendor"].upper()
    ineligible = None
    eligible = False

    if pe_router_model in mdso_eligible.JUNIPER_MX_MODELS and pe_router_vendor in el_pe_vendors:
        eligible = True

    if not eligible:
        ineligible = {"pe_router_vendor": pe_router_vendor, "pe_router_model": pe_router_model}
    return ineligible


def get_upstream_device_eligibility(upstream_data, service_type="FIA", task="INSTALL"):
    """
    Determine CPE Activation Device eligibility for upstream device.
    Default service type to FIA until stand alone config is fully live
    in MDSO/Beorn/Palantir/DICE
    """
    upstream_vendor = upstream_data["device_vendor"].upper()
    upstream_model = upstream_data["device_model"].upper()
    upstream_port_role = upstream_data["portRole"]
    ineligible = None
    eligible = False

    # Check vendor eligibility
    if upstream_vendor in ELIGIBLES[service_type].keys():
        for device_models in ELIGIBLES[service_type][upstream_vendor].keys():
            if upstream_model in device_models:
                if upstream_port_role in ELIGIBLES[service_type][upstream_vendor][device_models][task]:
                    eligible = True
                    break

    if not eligible:
        ineligible = {"upstream_device_model": upstream_model, "upstream_device_port_role": upstream_port_role}
    return ineligible


def mdso_resource_eligibility(topology, cid, cpea_data):
    upstream_hostname = cpea_data["upstream"]["hostname"]
    cpe_hostname = cpea_data["uni"]["uuid"]

    mdso_resource_eligibility = {}

    logger.info("Checking MDSO Network Service Resource")
    network_service_resource = service_details(cid, "charter.resourceTypes.NetworkService")
    active_network_service = is_network_service_orchState_active(network_service_resource)

    if not active_network_service:
        mdso_resource_eligibility["network_service_active"] = False
        return mdso_resource_eligibility, None, None

    network_service_resource_id = active_network_service["id"]

    logger.info("Checking For Existing CPE Activation Resources")
    existing_active_cpe_activator, failed_activator = get_existing_active_cpe_activator(network_service_resource_id)
    if existing_active_cpe_activator:
        mdso_resource_eligibility["existing_cpea_resource"] = existing_active_cpe_activator
        return mdso_resource_eligibility, None, None

        # PLACEHOLDER FOR reattempt eligibility
    logger.info("Checking all Network Function Resources")
    bad_network_functions, network_functions = get_nf_resource(
        topology, upstream_hostname, cpe_hostname, failed_activator
    )
    if bad_network_functions:
        mdso_resource_eligibility["network_function_status"] = bad_network_functions
        return mdso_resource_eligibility, None, None

    return None, network_functions, network_service_resource_id


def get_nf_resource(topology, upstream_hostname, cpe_hostname, failed_activator):
    flattened_topology = unpack_topology_json(topology)
    network_functions = {}
    network_functions["pe_nf"] = None
    for node in flattened_topology[0]:
        hostname = node["uuid"]
        if node["equipmentStatus"] == "LIVE" or node["equipmentStatus"] == "PENDING DECOMMISSION":
            path = "/bpocore/market/api/v1/resources?resourceTypeId=tosca.resourceTypes.NetworkFunction"
            mdso_url = f"{path}&q=label%3A{hostname}&obfuscate=true&offset=0&limit=1000"
            network_function_data = mdso_get(mdso_url)

            if len(network_function_data["items"]) == 0:
                # Instead of checking against FQDN in granite, check against partial match for full TID
                # Including domain trailing TID, to allow for legacy domain names

                mdso_url = f"{path}&p=label%3A{hostname}*&obfuscate=true&offset=0&limit=1000"
                network_function_data = mdso_get(mdso_url)
                logger.info("NETWORK FUNCTION DATA :")
                logger.info(network_function_data)

                if len(network_function_data["items"]) > 0:
                    wanted_list = [node["fqdn"], node["managementIP"]]
                    new_network_function_data = copy.deepcopy(network_function_data)
                    new_network_function_data["items"] = []
                    for item in network_function_data["items"]:
                        if item["properties"]["connection"]["hostname"] in wanted_list:
                            new_network_function_data["items"].append(item)
                            logger.info(new_network_function_data)
                    if len(new_network_function_data["items"]) > 0:
                        network_function_data = copy.deepcopy(new_network_function_data)
                    else:
                        network_function_data["items"] = []

            network_function = None
            for item in network_function_data["items"]:
                if item["orchState"] == "active":
                    network_function = item
                elif network_function is None:
                    network_function = item

            if node["deviceRole"] == "PE":
                network_functions["pe_nf"] = network_function
            if hostname == upstream_hostname:
                network_functions["upstream_nf"] = network_function

            if not network_function and hostname != cpe_hostname:
                return {"hostname": node["uuid"], "network_function_status": "Network Function does not exist"}, None

            if network_function and network_function["orchState"] != "active":
                if not (hostname == cpe_hostname and failed_activator):
                    return {"hostname": node["uuid"], "network_function_status": "Network Function is not active"}, None

    return None, network_functions


def find_mac_on_agg(nf_resource, upstream_port, model):
    mac_response = get_mac(nf_resource["providerResourceId"], upstream_port, model)
    mac_address = False
    logger.info("=================== mac_response ========================")
    logger.info(mac_response)
    if "QFX" in model:
        logger.info("Attempting to find MAC on QFX")
        if not mac_response["l2ng-l2ald-interface-macdb-vlan"].get("l2ng-l2ald-mac-entry-vlan"):
            return None
        mac_resp = mac_response["l2ng-l2ald-interface-macdb-vlan"]
        mac_respo = mac_resp.get("l2ng-l2ald-mac-entry-vlan")

        if isinstance(mac_respo, list):
            maclist = []
            for entry_vlan in mac_respo:
                if isinstance(entry_vlan["l2ng-mac-entry"], list):
                    for entry in entry_vlan["l2ng-mac-entry"]:
                        maclist.append(entry["l2ng-l2-mac-address"])
                else:
                    maclist.append(entry_vlan["l2ng-mac-entry"]["l2ng-l2-mac-address"])

            logger.info("&&&&&&&&&& That isn't right, there are too many macs for a new install &&&&&&&&&&&&&&")
            logger.info(maclist)
            maclist_str = ", ".join(maclist)
            mac_msg = "More than one mac address found: {}.".format(maclist_str)
            return mac_msg

        else:
            mac_address = mac_respo.get("l2ng-mac-entry").get("l2ng-l2-mac-address")

    if "EX" in model:
        logger.info("Attempting to find MAC on EX")
        mac_resp = mac_response["ethernet-switching-table-information"]["ethernet-switching-table"]
        if not mac_resp.get("mac-table-entry"):
            return None

        eth_switching = mac_response["ethernet-switching-table-information"]["ethernet-switching-table"]
        for mac_info in eth_switching["mac-table-entry"]:
            if len(mac_info["mac-address"]) > 1:
                mac_address = mac_info["mac-address"]

    return mac_address


def find_ip(nf_resource, data_identifer):
    logger.info("Retrieving ARP table")
    ip_response = get_ip(nf_resource["providerResourceId"], "|irb.99")

    # Determine if data_identifier is mac-address or interface-name
    if data_identifer[2] == ":":
        arp_match = "mac-address"
    else:
        arp_match = "interface-name"

    logger.info("Checking for IP address")
    ip_exist = False
    for arp_entry in ip_response:
        if data_identifer in arp_entry[arp_match]:
            return True
    if not ip_exist:
        return False


def network_upstream_port_status(network_functions, cpea_data):
    upstream_port = cpea_data["upstream"]["portName"]
    upstream_model = cpea_data["upstream"]["device_model"]
    upstream_hostname = cpea_data["upstream"]["hostname"]
    pe_nf_resource = network_functions["pe_nf"]
    upstream_nf = network_functions["upstream_nf"]

    logger.info("Getting Admin and Op state of upstream port")
    logger.info("First, we must resync the upstream device, %s - %s" % (upstream_hostname, upstream_nf))
    resync_response = resync_resource(upstream_nf["id"])
    logger.info("resync_response:")
    logger.info(resync_response)
    sleep(5)

    port_status = get_port_status(upstream_nf["providerResourceId"], upstream_port)["result"]
    admin_state = port_status["interface-information"]["physical-interface"]["admin-status"]["#text"]
    link_state = port_status["interface-information"]["physical-interface"]["oper-status"]
    juniper_aggs = ["QFX", "EX"]
    if admin_state != link_state:
        return "Invalid Port State"

    if link_state.lower() == "up":
        for agg in juniper_aggs:
            if agg in upstream_model:
                mgmt_mac = find_mac_on_agg(upstream_nf, upstream_port, agg)
                if not mgmt_mac:
                    return f"Mac Address Not Found on {upstream_hostname} - {upstream_port}"
                if len(mgmt_mac) > 17:
                    return mgmt_mac

                mgmt_ip = find_ip(pe_nf_resource, mgmt_mac)
                if not mgmt_ip:
                    return f"IP Address Not Found for mac {mgmt_mac} on {pe_nf_resource['label']}"

        if "MX" in upstream_model:
            mgmt_ip = find_ip(upstream_nf, f"{upstream_port.lower()}.99")
            if not mgmt_ip:
                return f"IP Address Not Found on {upstream_hostname} - {upstream_port}"
    return None


def inflight_design_change_check(cpea_specific_data, ns_id):
    # Specific items to catch; upstream device change, upstream port change, cpe device change
    logger.info("Getting MDSO Circuit Details Resource for CID Network Service")
    url = (
        f"/bpocore/market/api/v1/resources/{ns_id}/dependencies?recursive=false&resourceTypeId=charter"
        f".resourceTypes.CircuitDetails&obfuscate=true&offset=0&limit=1000 "
    )

    circuit_details = mdso_get(url)
    nodes = circuit_details["items"][0]["properties"]["topology"][0]["data"]["node"]
    link_data = circuit_details["items"][0]["properties"]["topology"][0]["data"]["link"]
    flat_nodes = flatten_nodes(nodes)

    upstream_device_exists = False
    cpe_exists = False
    for node in flat_nodes:
        logger.info("Checking for Upstream Host Change")
        if node["Host Name"] == cpea_specific_data["upstream"]["hostname"]:
            upstream_device_exists = True
            logger.info("Checking for Upstream Port Change")
            for edgepoint in node["ownedNodeEdgePoint"]:
                cpe_host = cpea_specific_data["uni"]["uuid"]

                if "Transport ID" in edgepoint and edgepoint["Transport ID"].split(".")[-1] == cpe_host:
                    if cpea_specific_data["upstream"]["portName"] != edgepoint["Name"]:
                        return "Upstream port"
                else:
                    upstream_port = get_upstream_port_from_link_data(cpea_specific_data, link_data)
                    if upstream_port is None or upstream_port != cpea_specific_data["upstream"]["portName"]:
                        return "Upstream port"

        logger.info("Checking for CPE Change")
        if node["Host Name"] == cpea_specific_data["uni"]["uuid"]:
            cpe_exists = True
            logger.info("Checking for CPE UNI Port Change")
            for edgepoint in node["ownedNodeEdgePoint"]:
                if edgepoint["Role"] == "UNI":
                    # cleanse port naming for Advas
                    if "ETH-PORT" in edgepoint["Name"]:
                        edgepoint["Name"] = edgepoint["Name"].replace("ETH-PORT", "ETH_PORT")
                    # cleanse port naming for Rads
                    if "ETHERNET" in edgepoint["Name"]:
                        edgepoint["Name"] = edgepoint["Name"].replace("ETHERNET-", "ETH PORT ")
                    if cpea_specific_data["uni"]["port_name"] != edgepoint["Name"]:
                        return "CPE port"
            logger.info("Checking for CPE Model Change")
            if node["Model"] != cpea_specific_data["uni"]["device_model"]:
                return "CPE model"

    if not cpe_exists:
        return "CPE design change"

    if not upstream_device_exists:
        return "Upstream Device design change"

    return None


def get_upstream_port_from_link_data(cpea_specific_data, link_data):
    for link in link_data:
        edgepoints = []
        for edgepoint in link["nodeEdgePoint"]:
            tid, port = edgepoint.split("-", 1)
            edgepoints.append({"tid": tid, "port": port})

        upstream_host, cpe_host = (cpea_specific_data["upstream"]["hostname"], cpea_specific_data["uni"]["uuid"])

        if edgepoints[0]["tid"] == upstream_host and edgepoints[1]["tid"] == cpe_host:
            return edgepoints[0]["port"]
        if edgepoints[1]["tid"] == upstream_host and edgepoints[0]["tid"] == cpe_host:
            return edgepoints[1]["port"]

    return None


def flatten_nodes(nodes):
    flat_nodes = []
    for node in nodes:
        curr_node = {"uuid": node["uuid"]}
        for item in node["name"]:
            curr_node[item["name"]] = item["value"]

        curr_node["ownedNodeEdgePoint"] = []
        for edgepoint in node["ownedNodeEdgePoint"]:
            curr_edgepoint = {}
            for item in edgepoint["name"]:
                curr_edgepoint[item["name"]] = item["value"]
            curr_node["ownedNodeEdgePoint"].append(curr_edgepoint)

        flat_nodes.append(curr_node)

    return flat_nodes


def get_existing_active_cpe_activator(ns_id):
    existing_activator_resources = lookup_existing_cpe_activator_resource(ns_id)
    if len(existing_activator_resources) == 0:
        return None, None

    active_activator = None
    failed_activator = None
    for activator in existing_activator_resources:
        if activator["cpea_orchState"] == "active":
            active_activator = activator
        if activator["cpea_orchState"] == "activating" and active_activator is None:
            active_activator = activator
        if activator["cpea_orchState"] == "failed":
            failed_activator = activator

    return active_activator, failed_activator


def cpe_activation_eligibility(topology, cid):
    logger.info("Checking CPE Activation Eligibility")
    eligibility = {}

    logger.info("Checking Service Type Eligibility")
    ineligible_service_type = get_service_type_eligibility(topology)
    if ineligible_service_type is not None:
        eligibility["eligible"] = False
        eligibility["ineligible_service_type"] = ineligible_service_type
        return eligibility

    logger.info("Flattening topology")
    cpea_specific_data, data_issue = get_data(topology, cid)

    if data_issue is not None:
        eligibility["eligible"] = False
        eligibility["data_issue"] = data_issue
        return eligibility

    logger.info("Checking Upstream Device Eligibility")
    upstream_ineligibility = get_upstream_device_eligibility(
        cpea_specific_data["upstream"], topology["serviceType"], "INSTALL"
    )
    if upstream_ineligibility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = {}
        eligibility["device_eligibility"]["upstream_model"] = upstream_ineligibility["upstream_device_model"]
        eligibility["device_eligibility"]["upstream_port_role"] = upstream_ineligibility["upstream_device_port_role"]
        return eligibility

    logger.info("Checking CPE Device Eligibility")
    cpe_ineligiility = cpe_device_eligibility(cpea_specific_data["uni"], topology["serviceType"], True)
    if cpe_ineligiility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = cpe_ineligiility
        return eligibility

    logger.info("Checking MDSO Eligibility")
    mdso_resource_ineligibility, network_functions, ns_id = mdso_resource_eligibility(topology, cid, cpea_specific_data)
    if mdso_resource_ineligibility:
        eligibility["eligible"] = False
        eligibility["mdso_resource_eligibility"] = mdso_resource_ineligibility
        return eligibility

    logger.info("Checking Inflight Design Changes")
    inflight_change = inflight_design_change_check(cpea_specific_data, ns_id)
    if inflight_change:
        eligibility["eligible"] = False
        eligibility["inflight_design_change"] = inflight_change
        return eligibility

    logger.info("Checking Network Status")
    network_invalid_reason = network_upstream_port_status(network_functions, cpea_specific_data)
    if network_invalid_reason:
        eligibility["eligible"] = False
        eligibility["network_ready_port_status"] = network_invalid_reason
        return eligibility

    # check cpe for special requirements
    eligibility["eligible"] = True
    cpe_model = cpea_specific_data["uni"]["device_model"]
    if (cpe_model in mdso_eligible.RAD_2I_MODELS) or (cpe_model in mdso_eligible.ADVA_116_MODELS):
        eligibility["pre-reqs"] = f"management configuration required for {cpe_model}"

    return eligibility


def standalone_config(validated_params):
    # Get product ID for standalone config delivery from MDSO
    token = create_token()
    headers = set_headers(token=token)
    mdso_response, prod_id = product_query(headers, "standaloneConfigDelivery")
    delete_token(token)
    logger.info("mdso_response: %s" % mdso_response)
    logger.info("product: %s" % prod_id)
    error_message = "Unable to obtain product ID for Stand Alone Config from MDSO"
    if mdso_response:
        abort(500, error_message)

    # Generate payload for MDSO post
    data = payload_generator(prod_id, validated_params)
    logger.info("==================data=======================")
    logger.info(data)

    # Initiate standalone config delivery in MDSO
    token = create_token()
    headers = set_headers(token=token)
    logger.debug("Attempting CPEA standalone activation {}".format(data["label"]))
    err_msg, resource_id = post_to_service(headers, data, cid=None, ok_200=True)
    delete_token(token)
    if err_msg:
        abort(500, err_msg)

    return resource_id


def sanitize_models(params):
    """
    This will attempt to compare known models with input models that may have unexpected dashes or whitespace
    Input:
        params - dictionary
    Output:
        ret_params - dictionary
    """
    models = {}
    ret_params = {}
    dvc_models = []

    for vendor in mdso_eligible.DEVICES.keys():
        for model_type in mdso_eligible.DEVICES[vendor]:
            for model in mdso_eligible.DEVICES[vendor][model_type]:
                dvc_models.append(model)

    for param_key in params.keys():
        ret_params[param_key] = params[param_key]
        if "model" in param_key:
            for model in dvc_models:
                if model.replace("-", "").replace(" ", "") == params[param_key].replace("-", "").replace(" ", ""):
                    models[param_key] = model

    for modl in models:
        ret_params[modl] = models[modl]

    return ret_params


def input_parameter_validation(input_parms, required_parms, nonSCoD=False):
    """
    Input parameter validation to ensure all necessary data was provided
    Simple FQDN validation
    Input:
        input_parms - dictionary
        required_parms - list
    Output:
        validated dictionary
    """
    validated_parm = {}
    error_message = {}
    ip_parms = sanitize_models(input_parms)

    if not nonSCoD:
        error_message = {"eligible": False}
        # Ensure if CPE requires changing in granite, CID is provided
        if ip_parms["update_cpe"].lower() == "true":
            if "circuit_id" not in input_parms.keys():
                error_message["Error"] = "CPE update requires circuit ID not provided"
                error_message["Error Code"] = 1001
                return error_message, None
            else:
                validated_parm["update_cpe"] = True
                validated_parm["circuit_id"] = ip_parms["circuit_id"]

    missing_parms = []

    # Step through required parameters to ensure all were provided
    for parm in required_parms:
        if parm not in ip_parms.keys():
            missing_parms.append(parm)
        else:
            validated_parm[parm] = ip_parms[parm]

    if len(missing_parms) != 0:
        error_message["Error"] = "Missing Parameters: " + ", ".join(missing_parms)
        error_message["Error Code"] = 1000
        return error_message, None

    fqdns = []
    for param in validated_parm:
        if param[-4:] == "fqdn":
            fqdns.append(validated_parm[param])

    if input_fqdn_validator(fqdns):
        error_message["Error"] = "Invalid FQDNs: " + ", ".join(input_fqdn_validator(fqdns))
        error_message["Error Code"] = 1100
        return error_message, None

    if "upstream_device_port" in input_parms.keys():
        ups_vendor = input_parms["upstream_device_vendor"]
        ups_model = input_parms["upstream_device_model"]
        ups_port = input_parms["upstream_device_port"]
        if not validate_port(ups_vendor, ups_model, ups_port):
            error_message["Error"] = f"Invalid Upstream Device Port {ups_port} for {ups_vendor} {ups_model}"
            error_message["Error Code"] = 1200
            return error_message, None

    if "target_device_uplink" in input_parms.keys():
        td_vendor = input_parms["target_device_vendor"]
        td_model = input_parms["target_device_model"]
        td_uplink = input_parms["target_device_uplink"]

        if not validate_port(td_vendor, td_model, td_uplink):
            error_message["Error"] = f"Invalid Target Device Uplink {td_uplink} for {td_vendor} {td_model}"
            error_message["Error Code"] = 1201
            return error_message, None

        validated_parm["target_uplink"] = td_uplink

    return None, validated_parm


def validate_port(vendor, model, port):
    for device_models in ELIGIBLES["NO_SERVICE"][vendor].keys():
        if model in device_models:
            p_pat = 1 if "10G-B" in model else 0
            port_pattern = ELIGIBLES["NO_SERVICE"][vendor][device_models]["PORT_PATTERNS"][p_pat]
            if re.search(port_pattern, port):
                logger.info(f"Port name: {port} is a VALID name for a: {vendor} {model}")
                return True
            else:
                logger.info(f"Port name: {port} is an INVALID name for a: {vendor} {model}")


def input_fqdn_validator(fqdns):
    """
    Function for simple validation of FQDNs conforming to Charter standards
    Input:
        List of FQDNs
    Output:
        List of noncoforming FQDNs or none
    """
    bad_fqdns = []
    for fq in fqdns:
        if len(fq.split(".")) < 3:
            bad_fqdns.append(fq)

    return bad_fqdns if len(bad_fqdns) > 0 else None


def payload_generator(prod_id, params, nonSCoD=False):
    """
    Function to format provided data for MDSO consumption
    Input:
        Product ID (for standalone config delivery)
        Provided parameters
    Output:
        Formatted payload
    """
    payload = {}
    payload["productId"] = prod_id
    props = {
        "pe_router_vendor": params["pe_router_vendor"],
        "upstream_port": params["upstream_device_port"],
        "pe_router_FQDN": params["pe_router_fqdn"],
        "upstream_device_FQDN": params["upstream_device_fqdn"],
        "upstream_device_vendor": params["upstream_device_vendor"],
    }
    if nonSCoD:
        payload["label"] = params["upstream_device_fqdn"].split(".")[0] + "_" + params["upstream_device_port"]

    else:
        payload["label"] = (
            params["upstream_device_fqdn"].split(".")[0] + "_" + params["target_device_fqdn"].split(".")[0]
        )
        props["target_vendor"] = params["target_device_vendor"]
        props["target_model"] = params["target_device_model"]
        props["target_device"] = params["target_device_fqdn"]
        if "target_uplink" in params:
            props["target_uplink"] = params["target_uplink"]
        props["cpe_config"] = params["configuration"].split("||")  # split parameter=double pipe ||
        stripped_config = []
        for line in props["cpe_config"]:
            stripped_config.append(line.strip())

        props["cpe_config"] = stripped_config

    payload["properties"] = props
    return payload


def firm_up_payload_generator(prod_id, params):
    """
    Function to format provided data for MDSO consumption
    Input:
        Product ID (for firmware updater)
        Provided parameters
    Output:
        Formatted payload
    """
    payload = {}
    payload["productId"] = prod_id
    props = {
        "target_vendor": params["device_vendor"],
        "target_model": params["device_model"],
        "target_FQDN": params["device_fqdn"],
        "target_ip": params["device_ip"],
        "firmware": params["firmware_file"],
    }

    payload["label"] = params["device_fqdn"].split(".")[0] + "_" + params["firmware_file"]

    payload["properties"] = props

    return payload


def stand_alone_eligibility(devices):
    logger.info("Checking Standalone CPE Activation Eligibility")
    eligibility = {}

    pe_router = {
        "device_vendor": devices["pe_router_vendor"],
        "device_model": devices["pe_router_model"],
        "portRole": "INNI",
    }
    upstream_device = {
        "device_vendor": devices["upstream_device_vendor"],
        "device_model": devices["upstream_device_model"],
        "portRole": "INNI",
    }
    cpe_device = {
        "device_vendor": devices["target_device_vendor"],
        "device_model": devices["target_device_model"],
        "device_portRole": "UNI",
    }

    logger.info("Checking PE Router Eligibility")
    pe_ineligibility = get_pe_router_eligibility(pe_router)
    if pe_ineligibility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = {}
        eligibility["device_eligibility"]["pe_router_vendor"] = pe_ineligibility["pe_router_vendor"]
        eligibility["device_eligibility"]["pe_router_model"] = pe_ineligibility["pe_router_model"]
        eligibility["Error Code"] = 1200
        return eligibility

    logger.info("Checking Upstream Device Eligibility")
    upstream_ineligibility = get_upstream_device_eligibility(upstream_device, "NO_SERVICE", "SCOD")
    if upstream_ineligibility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = {}
        eligibility["device_eligibility"]["upstream_vendor"] = upstream_device["device_vendor"]
        eligibility["device_eligibility"]["upstream_model"] = upstream_ineligibility["upstream_device_model"]
        eligibility["Error Code"] = 1201
        return eligibility

    logger.info("Checking CPE Device Eligibility")
    cpe_ineligibility = cpe_device_eligibility(cpe_device, "NO_SERVICE", False, "SCOD")
    if cpe_ineligibility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = {}
        eligibility["device_eligibility"]["cpe_vendor"] = cpe_ineligibility["cpe_vendor"]
        eligibility["device_eligibility"]["cpe_model"] = cpe_ineligibility["cpe_model"]
        eligibility["Error Code"] = 1202
        return eligibility

    # check cpe for special requirements
    eligibility["eligible"] = True
    cpe_model = cpe_device["device_model"]
    if (cpe_model in mdso_eligible.RAD_2I_MODELS) or (cpe_model in mdso_eligible.ADVA_116_MODELS):
        eligibility["pre-reqs"] = f"management configuration required for {cpe_model}"

    return eligibility


def build_arda_swap_data(arda_response):
    logger.info("[[[[[[[[[[[arda_response in build_arda_swap_data]]]]]]]]]]")
    logger.info(arda_response)
    if isinstance(arda_response, str):
        return {"unfortunate_unicorn": arda_response}
    arda_updata = {"status_code": arda_response.status_code}
    arda_json = arda_response.json()
    for key, value in arda_json.items():
        arda_updata[key] = value

    return arda_updata


def build_tulip(validated_parm):
    # Get product ID for turnup_locate_ip tool from MDSO
    token = create_token()
    headers = set_headers(token=token)
    # once we change MDSO we need to change the resource type
    mdso_response, prod_id = product_query(headers, "turnupLocateIP")
    delete_token(token)
    logger.info("mdso_response: %s" % mdso_response)
    logger.info("product: %s" % prod_id)
    if mdso_response:
        return {"error": "Unable to obtain product ID for cpe Firmware Detection from MDSO", "error_code": "TULIP1300"}

    # Generate payload for MDSO post
    data = payload_generator(prod_id, validated_parm, True)
    logger.info("==================data========================")
    logger.info(data)

    # Create TULIP resource in MDSO
    token = create_token()
    headers = set_headers(token=token)
    logger.debug("Attempting Tulip {}".format(data["label"]))
    err_msg, resource_id = post_to_service(headers, data, cid=None, ok_200=True)
    delete_token(token)

    if err_msg:
        logger.info(f"Error Message from MDSO: {err_msg}")
        return {"error": "Failed to create new TULIP resource in MDSO", "error_code": "TULIP1301"}

    return {"rid": resource_id}


def turnup_locate_ip_eligibility(devices):
    logger.info("Checking Turnup Locate IP Eligibility")
    eligibility = {"eligible": True}
    pe_router = {
        "device_vendor": devices["pe_router_vendor"],
        "device_model": devices["pe_router_model"],
        "portRole": "INNI",
    }
    upstream_device = {
        "device_vendor": devices["upstream_device_vendor"],
        "device_model": devices["upstream_device_model"],
        "portRole": "INNI",
    }

    logger.info("Checking PE Router Eligibility")
    pe_ineligibility = get_pe_router_eligibility(pe_router)
    if pe_ineligibility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = {}
        eligibility["device_eligibility"]["pe_router_vendor"] = pe_ineligibility["pe_router_vendor"]
        eligibility["device_eligibility"]["pe_router_model"] = pe_ineligibility["pe_router_model"]
        eligibility["Error Code"] = 1200
        return eligibility

    logger.info("Checking Upstream Device Eligibility")
    upstream_ineligibility = get_upstream_device_eligibility(upstream_device, "NO_SERVICE", "TULIP")
    if upstream_ineligibility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = {}
        eligibility["device_eligibility"]["upstream_vendor"] = upstream_device["device_vendor"]
        eligibility["device_eligibility"]["upstream_model"] = upstream_ineligibility["upstream_device_model"]
        eligibility["Error Code"] = 1201
        return eligibility

    return eligibility


def build_firmware_updater(validated_parm):
    # Get product ID for Firmware Upgrade tool from MDSO
    token = create_token()
    headers = set_headers(token=token)
    # once we change MDSO we need to change the resource type
    mdso_response, prod_id = product_query(headers, "firmwareUpdater")
    delete_token(token)
    logger.info("mdso_response: %s" % mdso_response)
    logger.info("product: %s" % prod_id)
    error_message = "Unable to obtain product ID for cpe Firmware Updater from MDSO"
    if mdso_response:
        abort(500, error_message)

    # Generate payload for MDSO post
    data = firm_up_payload_generator(prod_id, validated_parm)
    logger.info("==================data========================")
    logger.info(data)

    # Initiate firmware updater in MDSO
    token = create_token()
    headers = set_headers(token=token)
    logger.debug("Attempting to update firmware {}".format(data["label"]))
    err_msg, resource_id = post_to_service(headers, data, cid=None, ok_200=True)
    logger.info(err_msg)
    delete_token(token)
    if err_msg:
        abort(500, err_msg)

    return resource_id


def firm_up_eligibility(devices):
    logger.info("Checking Firmware Update Eligibility")
    eligibility = {"eligible": True}

    cpe_device = {
        "device_vendor": devices["device_vendor"],
        "device_model": devices["device_model"],
        "device_portRole": "UNI",
    }

    logger.info("Checking CPE Device Eligibility")
    cpe_ineligibility = cpe_device_eligibility(cpe_device, "NO_SERVICE", False, "FIRMUP")
    if cpe_ineligibility is not None:
        eligibility["eligible"] = False
        eligibility["device_eligibility"] = {}
        eligibility["device_eligibility"]["cpe_vendor"] = cpe_ineligibility["cpe_vendor"]
        eligibility["device_eligibility"]["cpe_model"] = cpe_ineligibility["cpe_model"]
        eligibility["Error Code"] = 1202
        return eligibility
    return eligibility


def build_post_install_light_level(input_params, device_tid):
    # Get product ID for Post Install Light Level Tool from MDSO
    token = create_token()
    headers = {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"token {token}"}
    # once we change MDSO we need to change the resource type
    mdso_response, prod_id = product_query(headers, "postInstallLightLevels")
    error_message = "Unable to obtain product ID for post install light levels from MDSO"
    if mdso_response:
        abort(500, error_message)

    # Generate payload for MDSO post
    data = pill_payload_generator(prod_id, input_params)
    logger.info("==================data========================")
    logger.info(f"====== pill_payload_generator data: {data}")
    # call to MDSO
    pill_resource_id = create_pill(data, device_tid)
    return pill_resource_id


def pill_payload_generator(prod_id, input_params):
    """
    Function to format provided data for MDSO consumption
    Input:
        Product ID (for post install light level)
        Provided parameters
    Output:
        Formatted payload
    """
    payload = {"productId": prod_id}
    device_tid = input_params["device_tid"]
    device_port = input_params["device_port"]
    props = {"device_tid": input_params["device_tid"], "port": input_params["device_port"]}

    if input_params.get("network_function_id"):
        props["device_id"] = input_params["network_function_id"]
    payload["label"] = f"{device_tid}_{device_port}"
    payload["properties"] = props

    return payload


def create_pill(data, device_tid):
    no_light_level = "no light level found"
    token = create_token()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "token {}".format(token),
    }
    try:
        err_msg, pill_rid = post_to_service(headers, data, device_tid)
    except Exception:
        if err_msg:
            return {"device_tid": no_light_level, "FAIL_REASON": err_msg}, 502
        else:
            return {
                "device_tid": no_light_level,
                "FAIL_REASON": "Unable to create Post Install Light Level resource in MDSO",
            }, 502
    return pill_rid
