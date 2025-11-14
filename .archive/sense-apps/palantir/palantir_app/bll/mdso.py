import logging
import warnings
import time

from palantir_app.common.constants import FIA
from palantir_app.dll.mdso import mdso_get, mdso_delete, mdso_patch
from palantir_app.dll.sense import beorn_get

warnings.simplefilter("ignore", UserWarning)

logger = logging.getLogger(__name__)
delete_error_message = ""


def get_active_resource(resource_id):
    endpoint = f"/bpocore/market/api/v1/resources/{resource_id}?validate=false"
    resource = mdso_get(endpoint)
    if resource.get("orchState") != "active":
        return None
    return resource


def get_activating_resource_id_by_type_and_filters(resource_type, filters):
    endpoint = f"/bpocore/market/api/v1/resources/?resourceTypeId={resource_type}&q={filters}&offset=0&limit=1000"
    activating_statuses = ("requested", "activating")
    activating_resources = mdso_get(endpoint, return_response=True)
    logger.debug(f"activating resources: {activating_resources}")
    if not activating_resources:
        return
    activating_resources = activating_resources.json()
    for item in activating_resources["items"]:
        if "orchState" in item and item["orchState"] in activating_statuses:
            # already in process, mdso resource instantiated
            # good! just return the resource
            if len(item["id"]) > 0:
                # there is a resource that can already be queried
                return item["id"]


def get_resource_by_type_and_label(resource_type, label):
    """
    Get resource(s) using label and resourceType paramaters
    Return value: list of resource id(s)
    """
    endpoint = f"bpocore/market/api/v1/resources?resourceTypeId={resource_type}&q=label%3A{label}&offset=0&limit=1000"

    resource = mdso_get(endpoint)

    if resource and resource.get("items"):
        return resource["items"][0]["id"]


def get_resource_ids(endpoint):
    resources = mdso_get(endpoint)
    resource_ids = []
    if resources and resources.get("items"):
        for resource in resources["items"]:
            resource_ids.append(resource["id"])
    return resource_ids


def get_bpo_provider_resource_ids(endpoint):
    resource_ids = []
    response = mdso_get(endpoint)
    resources = response["items"]
    for resource in resources:
        try:
            if resource["providerResourceId"] not in resource_ids:
                resource_ids.append(resource["providerResourceId"])
        except KeyError:
            pass

    return resource_ids


def get_resource_ids_by_network_function(endpoint, network_function_bpo_provider_resource_ids):
    resource_ids = []
    response = mdso_get(endpoint)
    resources = response["items"]
    for resource in resources:
        try:
            # To make sure the properties-device field of resource matches with the BPO or Provider resource id
            if resource["properties"]["device"] in network_function_bpo_provider_resource_ids:
                if resource["id"] not in resource_ids:  # To avoid collecting duplicate values in the list
                    resource_ids.append(resource["id"])
        except KeyError:
            pass

    return resource_ids


def delete_network_service_resources(resource_id):
    """
    delete network service resource
    delete dependant resources before deleting the Network Service Resource
    """
    global delete_error_message
    endpoint = f"/bpocore/market/api/v1/resources/{resource_id}/dependencies"
    dependant_resource_ids = get_resource_ids(endpoint)
    if dependant_resource_ids:
        for dep_rsrc_id in dependant_resource_ids:
            logger.info(f"Deleting Network Service Dependant Resource {dep_rsrc_id}")
            mdso_delete(dep_rsrc_id)  # delete the individual dependant resource id
        time.sleep(2)  # wait time for 2 seconds after dependencies deletion

    logger.info(f"Deleting Network Service Resource {resource_id}")
    mdso_delete(resource_id)  # delete the Network service resource by id
    retry = 1
    while retry <= 20:
        time.sleep(3)  # wait time for 3 seconds before validating the delete below
        endpoint = f"/bpocore/market/api/v1/resources/{resource_id}"
        result = mdso_get(endpoint)
        if "id" in result:
            if retry >= 20:  # if resource id is returned that means delete is not successful, after complete retrials
                if "reason" in result:
                    delete_error_message += "Failure Deleting Network Resource - reason: {}".format(result.get("reason"))
                else:
                    delete_error_message += "\nFailure Deleting Network Resource , Reason Unknown"
            retry = retry + 1  # to retry checking the deletion again in a loop
        else:
            retry = 99  # to break the loop if resource has been already deleted


def delete_tpe_resources(circuit_data):
    """Intake circuit and topology information, iterate through topology and delete any dependent resources"""
    # check for existing stranded TPE resources and delete any if found
    tpe_resource_id_dict = {}  # Dictionary to store unique TPE resource IDs for deletion
    global delete_error_message
    for devices in circuit_data["topology"]:
        if not devices.get("data"):
            continue
        else:
            if not devices["data"].get("node"):
                continue
        for device in devices["data"]["node"]:
            tid = device.get("uuid")
            # Below to find BPO resource id for a given TID
            resource_type = "tosca.resourceTypes.NetworkFunction"
            endpoint = (
                f"/bpocore/market/api/v1/resources?resourceTypeId={resource_type}&q=label%3A{tid}&offset=0&limit=1000"
            )
            network_function_bpo_provider_resource_ids = get_bpo_provider_resource_ids(endpoint)
            # Below to find port and vlan , TPE resource label is in the format of port.vlan
            if not network_function_bpo_provider_resource_ids:
                continue
            try:
                service_type = circuit_data.get("serviceType")
                pe_port = get_phys_ds_interface(device, service_type)
                vlan = 0
                if not circuit_data["service"][0]["data"]["evc"][0]["sVlan"] == "Untagged":
                    circuit_data["service"][0]["data"]["evc"][0]["sVlan"]
                cid_tpe_label = f"{pe_port}.{vlan}"
            except Exception as excp:
                cid_tpe_label = None
                delete_error_message += f"\nTPE - Error while determining TPE Label for TID : {tid} - Exception : {excp}"
                continue
            # Below is to fetch the TPE resource IDs
            by_resource_type_base = "/bpocore/market/api/v1/resources?resourceTypeId="
            resource_type = "tosca.resourceTypes.TPE"
            endpoint = f"{by_resource_type_base}{resource_type}&q=label%3A{cid_tpe_label}&offset=0&limit=1000"
            cid_tpe_resource_ids = get_resource_ids_by_network_function(
                endpoint, network_function_bpo_provider_resource_ids
            )

            if not cid_tpe_resource_ids:
                continue
            else:
                for tpe_resource in cid_tpe_resource_ids:  # This is to loop on TPE Resources to delete
                    if (
                        tpe_resource not in tpe_resource_id_dict
                    ):  # This check is to not try to delete a TPE resource if already deleted
                        logger.info("Deleting TPE Resource ", tpe_resource)
                        mdso_delete(resource_id=tpe_resource)
                        time.sleep(10)
                        tpe_resource_id_dict[tpe_resource] = tpe_resource


def delete_fre_resources(cid, circuit_data):
    """Intake circuit and topology information, iterate through topology and delete any dependent resources"""
    # check for existing stranded FRE resources and delete any if found
    global delete_error_message
    resource_type = "tosca.resourceTypes.FRE"
    service_type = circuit_data.get("serviceType")
    vlan = 0
    try:
        if not circuit_data["service"][0]["data"]["evc"][0]["sVlan"] == "Untagged":
            vlan = circuit_data["service"][0]["data"]["evc"][0]["sVlan"]
    except Exception as excp:
        delete_error_message += f"\nFRE - Exception while deriving vlan : {excp}"
    for devices in circuit_data["topology"]:
        if not devices.get("data"):
            continue
        else:
            if not devices["data"].get("node"):
                continue
        by_resource_type_base = "bpocore/market/api/v1/resources?resourceTypeId="
        for device in devices["data"]["node"]:
            tid = device.get("uuid")
            try:
                device_model = get_device_model(device)
                # if eline: gather neighbor ip, local port, circuit vlan for fre label
                if service_type == "ELINE" and "MX" in device_model:
                    neighbor_ip = get_neighbors(device, circuit_data)
                    pe_port = get_phys_ds_interface(device, service_type)
                    if neighbor_ip == "local":
                        l2circuit_fre_label = f"{pe_port}.{vlan}"
                    else:
                        l2circuit_fre_label = f"{neighbor_ip}:{pe_port}.{vlan}"
                    endpoint = (
                        f"{by_resource_type_base}{resource_type}&q=label%3A{l2circuit_fre_label}&offset=0&limit=1000"
                    )
                    l2circuit_fre_resource_ids = get_resource_ids(endpoint)
                    if l2circuit_fre_resource_ids:
                        for fre in l2circuit_fre_resource_ids:
                            logger.info("Deleting L2 FRE Resource ", fre)
                            mdso_delete(resource_id=fre)
                            time.sleep(10)
                cid_fre_label = f"{tid}::FRE_{cid}"
                endpoint = f"{by_resource_type_base}{resource_type}&q=label%3A{cid_fre_label}&offset=0&limit=1000"
                cid_fre_resource_ids = get_resource_ids(endpoint)
                if cid_fre_resource_ids:
                    for fre_resource in cid_fre_resource_ids:
                        logger.info("Deleting CID FRE Resource ", fre_resource)
                        mdso_delete(resource_id=fre_resource)
                        time.sleep(10)
            except Exception as excp:
                delete_error_message += f"\nFRE - Error while deleting resources for TID : {tid} - Exception : {excp}"
                continue


def delete_legato_resources(cid):
    global delete_error_message
    legato_resources = []
    try:
        payload = {"desiredOrchState": "terminated", "orchState": "terminated"}
        by_resource_type = "bpocore/market/api/v1/resources?resourceTypeId="
        legato_service_type = "mef.resourceTypes.LegatoService"
        legato_pc_type = "mef.resourceTypes.LegatoPC"
        mef_service_type = "bpoextensions.resourceTypes.MarketRequest"
        legato_bld_type = "mef.resourceTypes.LegatoBuilder"

        # get legato resource ids to terminate
        legato_service = f"{by_resource_type}{legato_service_type}&q=label%3A{cid}.mef_service&offset=0&limit=1000"
        legato_pc = f"{by_resource_type}{legato_pc_type}&q=label%3A{cid}.mef_service&offset=0&limit=1000"
        mef = f"{by_resource_type}{mef_service_type}&q=label%3A{cid}.mef_service.ProductLookup&offset=0&limit=1000"
        legato_builder = f"{by_resource_type}{legato_bld_type}&q=label%3A{cid}.mef_service.Builder&offset=0&limit=1000"
        get_legato_resources = [
            get_resource_ids(legato_service),
            get_resource_ids(legato_pc),
            get_resource_ids(mef),
            get_resource_ids(legato_builder),
        ]
        # flatten list of lists
        legato_resources = [resource for resource_list in get_legato_resources for resource in resource_list]
    except Exception as excp:
        delete_error_message += f"\nLEGATO - Error while Finding resources for CID : {cid} - Exception : {excp}"
        return
    for resource_id in legato_resources:
        logger.info("Terminating Legato Resource ", resource_id)
        mdso_patch(resource_id, payload)


def get_device_model(device):
    """Get device model"""

    ven_models = {
        "JUNIPER": ["MX", "QFX", "EX"],
        "ADVA": ["114/", "114PRO", "116PRO", "825", "120PRO"],
        "RAD": ["203", "220", "2I"],
        "CISCO": ["9001", "9006", "9010", "920"],
    }
    vendor = get_device_vendor(device)
    model = get_node_value(device, "model")
    for mod in ven_models[vendor]:
        if mod in model:
            dev_model = mod.replace("/", "")
            if dev_model in ["9001", "9006", "9010"]:
                dev_model = "9K"

    return dev_model


def get_device_vendor(device):
    """Get device vendor"""

    return get_node_value(device, "vendor")


def get_node_value(device, device_pair_name):
    for uuid_pair in device["name"]:
        if uuid_pair["name"].casefold() == device_pair_name.casefold():
            return uuid_pair["value"]


def get_device_mgmt_ip(device):
    """Get device role"""

    return get_node_value(device, "managementIP")


def get_phys_ds_interface(device, service_type, lag_member=True):
    """Determine which port is the downstream interface on a device"""
    port_pos = 0
    if service_type == FIA or device["topo_id"] == 1:
        port_pos = -1
    physical_interface = str(device["ownedNodeEdgePoint"][port_pos]["name"][0]["value"]).lower()
    if lag_member and device["ownedNodeEdgePoint"][port_pos]["name"][-1]["name"] == "lagMember":
        lag_name = device["ownedNodeEdgePoint"][port_pos]["name"][-1]["value"]
        physical_interface = str(lag_name).lower()
    # TODO - ELSE Logic for non-FIA/ELINE circuits will go here someday in the ethernet future
    return physical_interface


def get_neighbors(device, circuit_data):
    """Retreives neighbors IP"""

    if get_device_mgmt_ip(circuit_data["topology"][0]["data"]["node"][-1]) != get_device_mgmt_ip(device):
        neighbor = get_device_mgmt_ip(circuit_data["topology"][0]["data"]["node"][-1])
    elif get_device_mgmt_ip(circuit_data["topology"][-1]["data"]["node"][0]) != get_device_mgmt_ip(device):
        neighbor = get_device_mgmt_ip(circuit_data["topology"][-1]["data"]["node"][0])
    else:
        neighbor = "local"
    return neighbor


def delete_mdso_resources(cid, resource_id):
    # best effort
    global delete_error_message
    try:
        logger.info(f"Executing delete_mdso_resources for CID : {cid} and MDSO Resource ID : {resource_id}")

        logger.info(f"Calling Delete Network Resource Function for MDSO Resource ID : {resource_id}")
        delete_network_service_resources(resource_id)

        logger.info(f"Calling Delete LEGATO Function for cid : {cid}")
        delete_legato_resources(cid)

        topology_endpoint = f"/v3/topologies?cid={cid}"
        logger.info(f"Executing Beorn Endpoint for Topology : {cid} and MDSO Resource ID : {resource_id}")
        circuit_data = beorn_get(topology_endpoint)

        if circuit_data and circuit_data.get("topology"):
            logger.info(f"Calling Delete TPE Function for cid : {cid} and MDSO Resource ID : {resource_id}")
            delete_tpe_resources(circuit_data)

            logger.info(f"Calling Delete FRE Function for cid : {cid} and MDSO Resource ID : {resource_id}")
            delete_fre_resources(cid, circuit_data)
        else:
            delete_error_message += f"Error Fetching Topology for CID : {cid}"

        if delete_error_message:
            logger.warning(delete_error_message)
    except Exception as excp:
        delete_error_message += (
            f"\nError Deleting MDSO Resources for CID : {cid} and Resource ID : {resource_id} - Exception : {excp}"
        )
        logger.warning(delete_error_message)
