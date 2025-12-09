import datetime
import logging
import re
import time

from palantir_app.bll.resource_status import get_resource_status
from common_sense.common.errors import abort
from palantir_app.dll.denodo import get_target_and_vendor, denodo_get
from palantir_app.dll.mdso import mdso_get, mdso_post, product_query, mdso_patch
from palantir_app.dll.sense import beorn_get
from palantir_app.common.endpoints import DENODO_CIRCUIT_DEVICES

logger = logging.getLogger(__name__)


def _get_port_resource(target, port_id, production):
    """Call to MDSO to check if there's an existing resource ID based on port id"""
    endpoint = "/bpocore/market/api/v1/resources?resourceTypeId=charter.resourceTypes.PortActivation"
    params = {"q": f"properties.deviceName:{target},properties.portname:{port_id}", "offset": 0, "limit": 1000}
    data = mdso_get(endpoint, params, calling_function="_get_port_resource", production=production)
    logger.debug(f"Checking for an existing port resource for {target}")
    if data.get("items") and data["items"]:
        for record in data["items"]:
            if record["properties"]["deviceName"] == target and record["properties"]["portname"] == port_id:
                if record["properties"].get("status") and record["properties"]["status"] == "Ready to configure":
                    logger.debug(f"Resource found!  Returned ID: {record['id']}")
                    return record["id"]
    return None


def _create_port_resource(tid, target, vendor, timer, port_id, port_act_product_id, production=False):
    endpoint = "/bpocore/market/api/v1/resources?validate=false"
    data = {
        "desiredOrchState": "active",
        "label": "{}_{}".format(tid, port_id),
        "autoClean": False,
        "reason": "string",
        "discovered": False,
        "properties": {"portname": port_id, "deviceName": target, "vendor": vendor, "terminationTime": timer},
        "productId": port_act_product_id,
    }
    data = mdso_post(endpoint, data, calling_function="_create_port_resource", production=production)
    if data:
        logger.info(f"Created port resource: {data}\n")
        if isinstance(data, list):
            for record in data:
                if record["properties"]["deviceName"] == target and record["properties"]["portname"] == port_id:
                    return record["id"]
            else:
                abort(502, "Device not found when activating the port")
        else:
            return data["id"]
    else:
        abort(502, "MDSO failed to activating the port")


def _get_port_status(resource_id, port_status_op_id, production=False):
    """Call to MDSO to get status on port."""
    endpoint = f"/bpocore/market/api/v1/resources/{resource_id}/operations/{port_status_op_id}"
    return mdso_get(endpoint, calling_function="_get_port_status", production=production)


def _get_port_status_oper(resource_id, production=False, return_all_ops=False):
    """Call to MDSO to generate operations id for checking status"""
    endpoint = f"/bpocore/market/api/v1/resources/{resource_id}/operations?offset=0&limit=1000"
    data = mdso_get(endpoint, calling_function="_get_port_status_oper", production=production)
    if data.get("items") and data["items"]:
        if return_all_ops:
            return data.get("items")

        # List of all ids, timestamp, and what the operation was for (i.e. "getPortStatus")
        op_ids = [
            (x["id"], datetime.datetime.strptime(x["createdAt"], "%Y-%m-%dT%H:%M:%S.%fZ"), x["interface"])
            for x in data["items"]
        ]
        # Sort by timestamp
        op_ids.sort(key=lambda x: x[1])
        if op_ids[-1][2] != "getPortStatus":
            # if last operation was some other action, we'll need to create a new op id
            return None
        else:
            # otherwise, we need to reuse the latest op id
            return op_ids[-1][0]
    else:
        return None


def _get_operation_status_for_set_port_status(resource_id):
    """Checks the port's Port Activation resource in MDSO for any setPortStatus operations

    :param resource_id: resource_id for Port Activation resource whose operations you want to view
    :type resource_id: str
    :return: returns the status message from the first instance of setPortStatus
    :rtype: str
    """
    operations = _get_port_status_oper(resource_id=resource_id, return_all_ops=True)
    set_port_status_ops = []
    error_messages_to_match = ["Port already in", "port was not activated", "not in Ready to configure state"]

    if operations:
        for operation in operations:
            if operation.get("interface") == "setPortStatus":
                set_port_status_ops.append(operation)

    if set_port_status_ops:
        # Retrieves the status of the first instance of setPortStatus (if multiple exist)
        first_set_port_status_msg = set_port_status_ops[-1].get("outputs").get("status")
        if first_set_port_status_msg and any(text in first_set_port_status_msg for text in error_messages_to_match):
            return first_set_port_status_msg

    return None


def _create_port_status_oper(resource_id, production=False):
    """
    Returns operation id of creating the port status
    """
    endpoint = f"/bpocore/market/api/v1/resources/{resource_id}/operations"
    payload = {"description": "string", "interface": "getPortStatus", "title": "string"}
    logger.debug("Creating getPortStatus operation via mdso_post")
    return mdso_post(endpoint, payload, calling_function="_create_port_status_oper", production=production)["id"]


def _set_port_status(resource_id, activate=True):
    """Call to activate the port, returns operation_id"""
    endpoint = f"/bpocore/market/api/v1/resources/{resource_id}/operations"
    # payload = {"activate": true}  # true for up, false for down
    if activate:
        status = "up"
    else:
        status = "down"
    payload = {"interface": "setPortStatus", "inputs": {"reqdstate": status}}
    data = mdso_post(endpoint, payload, calling_function="_set_port_status")
    logger.debug(f"Setting port status via mdso_post  | response: {data}")
    return {"resourceId": data["resourceId"], "operationId": data["id"], "data": data}


def _get_port_activation_resource(tid, port_id, timer, production=False):
    target, vendor = get_target_and_vendor(tid)

    logger.debug(f"Checking for any existing Port Activation resources for {tid}_{port_id}")
    if vendor.upper() != "JUNIPER":
        abort(501, "Non Juniper devices not supported")

    port_act_product_id = product_query("PortActivation", production)
    # Onboard resource to MDSO #
    resource_id = _get_port_resource(target, port_id, production)
    if not resource_id:
        logger.info(f"No resource_id found.  Creating resource for {tid}_{port_id}")
        resource_id = _create_port_resource(tid, target, vendor, timer, port_id, port_act_product_id, production)

    port_res_resp = get_resource_status(
        resource_id, map_responses=False, poll=True, poll_counter=10, poll_sleep=30, production=production
    )

    if port_res_resp["status"] != "Completed":
        logger.error(
            f"Unable to successfully create Port Activation resource for {tid}_{port_id}  | "
            f"Data: {port_res_resp['data']}"
        )
        abort(
            502,
            f"Unable to successfully create Port Activation resource for {tid}_{port_id}  | "
            f"Data: {port_res_resp['data']}",
        )
    return resource_id


def update_port(tid, port_id, timer, activate=True):
    """
    Retrieves or creates a Port Activation resource for the TID/Port.
    """
    resource_id = _get_port_activation_resource(tid, port_id, timer)
    action = "activate" if activate else "deactivate"
    report_word = "Activated" if activate else "Deactivated"

    # Getting previous port status to determine if it is in a hardloop
    status = check_port_status(tid, port_id)
    try:
        prev_admin_state = status["adminstate"]
    except Exception as ex:
        prev_admin_state = "N/A"
        logger.error(
            f"An error has occurred while attempting to retrieve previous admin/oper states.  "
            f"Attempting to continue.  | Details: {ex}  | Port Status: {status}"
        )

    # Activate or Deactivate port #
    port_act_resp = _set_port_status(resource_id, activate=activate)

    port_act_res_status = get_resource_status(
        port_act_resp["resourceId"], map_responses=False, poll=True, poll_counter=10, poll_sleep=30
    )

    if port_act_res_status["status"] != "Completed":
        abort(502, f"Failed to {action} port  | Details: {port_act_res_status}")

    status = check_port_status(tid, port_id)

    try:
        admin_state = status["adminstate"]
        oper_state = status["operstate"]
    except Exception as ex:
        admin_state = "N/A"
        oper_state = "N/A"
        logger.error(
            f"An error has occurred while attempting to retrieve current admin/oper states.  "
            f"Attempting to continue.  | Details: {ex}  | Port Status: {status['outputs']['status']}"
        )

    if prev_admin_state == "down" and admin_state == "down":
        # i.e. setPortStatus failed despite the resource status being Active/Completed

        # Checks the setPortStatus operation(s) to see if an error message was included
        potential_failure_reason = _get_operation_status_for_set_port_status(resource_id)
        abort_msg = (
            f"Port failed to {action} via SetPortStatus operation.  |  "
            f"admin/operstate: {status.get('adminstate')}/{status.get('operstate')} |  "
        )

        if potential_failure_reason:
            abort_msg += f"SetPortStatus details: {potential_failure_reason}"
        else:
            abort_msg += f"Data: {port_act_resp.get('data')}"
        abort(404, abort_msg)

    if timer == 0:
        if prev_admin_state == "down" and admin_state == "up" and oper_state == "up":
            # Hard loop was found
            port_act_resp = _set_port_status(resource_id, activate=False)

            port_act_res_status = get_resource_status(
                port_act_resp["resourceId"], map_responses=False, poll=True, poll_counter=10, poll_sleep=30
            )

            if port_act_res_status["status"] != "Completed":
                abort(
                    502,
                    f"Port was found in hard loop and was attempted to be turned down but failed  |"
                    f"Resource Status: {port_act_res_status}",
                )

            status = check_port_status(tid, port_id)
            admin_state = status["adminstate"]

            if admin_state == "down":
                return {
                    "TID": tid,
                    "Port": port_id,
                    f"{report_word}": False,
                    "message": "Port was found in hard loop and was successfully turned back down",
                    "data": status,
                }

    if activate:
        if admin_state == "up":
            success = True
        else:
            success = False
    else:
        if admin_state == "down":
            success = True
        else:
            success = False

    return {"TID": tid, "Port": port_id, f"{report_word}": success, "data": status}


def check_port_status(tid, port_id, production=False, timer=60):
    """
    Retrieves/creates a Port Activation resource and executes a GetPortStatus operation
    """
    num_attempts = 18
    wait_time_between_attempts = 10

    resource_id = _get_port_activation_resource(tid, port_id, timer, production)
    logger.debug(f"Resource_id for {tid}_{port_id} returned from _get_port_activation_resource()")

    # Retrieves or creates the GetPortStatus operation ID
    port_status_op_id = _get_port_status_oper(resource_id, production)
    if port_status_op_id:
        logger.debug(f"GetPortStatus operation ID for {resource_id}: {port_status_op_id}")
    else:
        port_status_op_id = _create_port_status_oper(resource_id, production)
        logger.debug(f"Newly created GetPortStatus operation ID for {resource_id}: {port_status_op_id}")

    # Checks resource's properties to ensure that it's in a Ready to Configure state being running GetPortStatus
    url = f"/bpocore/market/api/v1/resources/{resource_id}"
    resource_data = mdso_get(url, calling_function="get_resource_status", production=production)

    # If the resource isn't ready to configure to begin with, _get_port_status() will not work
    if resource_data["properties"]["status"] == "Ready to configure":
        for _i in range(num_attempts):
            port_data = _get_port_status(resource_id, port_status_op_id, production)
            state = port_data.get("state")
            if not state:
                logger.error(f"No port status found for resource_id: {resource_id}  | GetPortStatus Data: {port_data}")
                abort(404, f"No port status found for resource_id: {resource_id}  | GetPortStatus Data: {port_data}")
            elif state == "failed":
                logger.error(f"Failed port status operation for resource_id: {resource_id} ")
                abort(502, f"Failed port status operation for resource_id: {resource_id} ")
            elif state == "successful":
                try:
                    logger.debug(
                        f"GetPortStatus for {tid}_{port_id} returned successful.  | GetPortStatus Data: {port_data}"
                    )
                    return {
                        "adminstate": port_data["outputs"]["adminstate"],
                        "operstate": port_data["outputs"]["operstate"],
                        "transmitting_optical_power": port_data["outputs"]["portTxAvgOpticalPower"],
                        "receiving_optical_power": port_data["outputs"]["portRxAvgOpticalPower"],
                        "portSFPvendorPartNumber": port_data["outputs"]["portSFPvendorPartNumber"],
                        "portSFPwavelength": port_data["outputs"]["portSFPwavelength"],
                        "portSFPvendorName": port_data["outputs"]["portSFPvendorName"],
                        "status_info": port_data["outputs"]["status"],
                    }

                except KeyError as ke:
                    logger.error(
                        f"A KeyError occurred while trying to return the port status information.  "
                        f"KeyError: {ke}  | GetPortStatus Data: {port_data}"
                    )
                    abort(
                        404,
                        f"A KeyError occurred while trying to return the port status information.  "
                        f"KeyError: {ke}  | GetPortStatus Data: {port_data}",
                    )

                except Exception as exc:
                    logger.error(
                        f"Optic is not reachable.  Manual check required.  Error: {exc}  | "
                        f"GetPortStatus Data: {port_data}"
                    )
                    abort(
                        404,
                        f"Optic is not reachable.  Manual check required.  Error: {exc}  | "
                        f"GetPortStatus Data: {port_data}",
                    )
            time.sleep(wait_time_between_attempts)

        # If the for loop ends and the operation still hasn't turned successful, it errors out.
        logger.error(
            f"Waited and never got status for port.  | Resource Data: {resource_data}  | GetPortStatus Data: {port_data}"
        )
        abort(
            404,
            f"Waited and never got status for port.  | Resource Data: {resource_data}  | "
            f"GetPortStatus Data: {port_data}",
        )

    else:
        logger.error("Resource is not in a ready to configure state and cannot have its port status retrieved.")
        abort(404, "Resource is not in a ready to configure state and cannot have its port status retrieved.")


def get_ports(cid):
    # Determine if it is a path cid or standard cid
    if re.match(r"[0-9]{5}\.GE10?\..*", cid):
        # Path Cid
        path_topology = denodo_get(DENODO_CIRCUIT_DEVICES, params={"cid": cid})
        ports = _get_path_ports_to_activate(path_topology, cid)
    else:
        endpoint = "/v3/topologies"
        params = {"cid": cid}
        topologies = beorn_get(endpoint, params=params)
        if "error" in topologies.keys():
            return topologies
        unpacked_topology = unpack_topology_json(topologies)
        ports = _get_ports_to_activate(unpacked_topology)
    return {"ports": ports}


def _get_ports_to_activate(topologies):
    ports = []
    cpes = []
    upstream_device = ""

    for topology in topologies:
        for node in topology:
            if node["deviceRole"] == "CPE" and (
                node["equipmentStatus"] == "PLANNED" or node["equipmentStatus"] == "DESIGNED"
            ):
                cpes.append(node)
        for cpe in cpes:
            for edgePoint in cpe["ownedNodeEdgePoint"]:
                if edgePoint["portRole"] == "INNI":
                    upstream_device = edgePoint["transportId"].split(".")[-2]
            for node in topology:
                try:
                    if node["uuid"] == upstream_device and node["equipmentStatus"] == "LIVE":
                        for edgePoint in node["ownedNodeEdgePoint"]:
                            if edgePoint["transportId"].split(".")[-1] == cpe["uuid"]:
                                curr_port = {"tid": node["uuid"], "port_name": edgePoint["name"]}
                                ports.append(curr_port)
                except KeyError as ke:
                    logger.debug(f"KeyError for {node}  |  Key info: {ke}")
                    continue

    return ports


def unpack_topology_json(cid_topology):
    topologies = []

    # Cell Tower Back Hauls have two legs/topologies nested under "PRIMARY" and "SECONDARY"
    if cid_topology.get("PRIMARY"):
        cid_topology = cid_topology.get("PRIMARY")

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


def _get_path_ports_to_activate(path_topology, cid):
    ports = []
    upstream_tid, cpe_tid = cid.split(".")[2:4]

    for topology in path_topology["elements"]:
        for element in topology["data"]:
            if element["device_id"].split(".")[0] == upstream_tid:
                ports.append({"tid": upstream_tid, "port_name": element["port_access_id"]})

    return ports


def _get_all_port_activation_resources():
    logger.info("Retrieving Port Activation resources from MDSO")
    endpoint = (
        "/bpocore/market/api/v1/resources?resourceTypeId=charter.resourceTypes.PortActivation&obfuscate=true&offset=0"
    )
    all_port_activation_mdso_resources = mdso_get(endpoint, None, calling_function="_get_port_activation_resources")
    resources_count = len(all_port_activation_mdso_resources["items"])
    logger.info(f"Available Port Activation resources in MDSO : {resources_count}")
    return all_port_activation_mdso_resources


def _delete_port_activation_resource(resource_id):
    payload = {"desiredOrchState": "terminated", "orchState": "terminated"}
    response = mdso_patch(resource_id, payload, "_delete_port_activation_resources")
    logger.info(
        f"Port Activation Resource ID: {resource_id}  |  Termination Response: {response.status_code} - {response.text}"
    )
    return response


def _clear_all_port_activation_mdso_resources():
    logger.info("Deleting Port Activation resources")
    all_port_activation_mdso_resources = _get_all_port_activation_resources()
    counter = 0
    return_msg = None
    for item in all_port_activation_mdso_resources["items"]:
        resource_id = item.get("id")
        desired_orch_state = item.get("desiredOrchState")
        orch_state = item.get("orchState")
        if resource_id and (desired_orch_state != "terminated" or orch_state != "terminated"):
            response = _delete_port_activation_resource(resource_id)
            if response.status_code == 200:
                counter += 1
        return_msg = f"Active Port Activation resources deleted in MDSO: {counter}"
    logger.info(f"Response Summary : {return_msg}")
    return {"msg": return_msg}
