import logging

from beorn_app.dll.granite import _update_path_status, granite_get, call_granite_for_uda
from common_sense.common.errors import abort
from beorn_app.common.granite_operations import call_denodo_for_circuit_devices
from beorn_app.common.endpoints import GRANITE_EQUIPMENTS, GRANITE_SHELF_UDA, ELAN_SLM


logger = logging.getLogger(__name__)


def set_circuit_auto_provisioned(cid):
    """
    Update Granite circuit status to Auto-Provisioned
    upon successful provisioning
    """
    return _update_path_status(cid, "Auto-Provisioned")


def is_full_disconnect_present(impact_analysis):
    return True if "FULL" in impact_analysis.values() else False


def get_granite_impact_analysis(topology):
    try:
        try:
            evc = topology["service"][0]["data"]["evc"]
            evc_endpoint_num = evc[0]["maxNumOfEvcEndPoint"]
        except Exception as excp:
            abort(502, f"Granite Impact Analysis Error Deriving Service Type : {excp}")

        # 1 EVC endpoint signifies FIA, only Z side present
        if evc_endpoint_num == 1:
            response = get_impact_by_side(topology=topology, side="z_side", topology_index_type="FIA")
        # multiple EVC endpoints signifies ELINE, A + Z sides present
        else:
            # a side
            response = get_impact_by_side(topology=topology, side="a_side", topology_index_type="ELINE")
            # z side
            response = get_impact_by_side(
                topology=topology, side="z_side", topology_index_type="ELINE", response=response
            )
    except Exception as excp:
        abort(502, f"Granite Impact Analysis Error: {excp}")

    return response


FIA_TOPOLOGY_INDEXES = {"z_side": {"topology_index": 0, "endpoint_index": -1, "address_index": 0}}


ELINE_TOPOLOGY_INDEXES = {
    "a_side": {"topology_index": 0, "endpoint_index": 0, "address_index": 0},
    "z_side": {"topology_index": 1, "endpoint_index": -1, "address_index": 1},
}


def get_impact_by_side(topology, side, topology_index_type, response=None):
    indexes = FIA_TOPOLOGY_INDEXES if topology_index_type == "FIA" else ELINE_TOPOLOGY_INDEXES
    topology_index = indexes[side]["topology_index"]
    endpoint_index = indexes[side]["endpoint_index"]
    address_index = indexes[side]["address_index"]

    if not response:
        response = {}

    topology_side = topology["topology"][topology_index]["data"]["node"]

    tid = topology_side[endpoint_index]["uuid"]
    response[f"{side}_endpoint"] = tid

    address = topology["service"][0]["data"]["evc"][0]["endPoints"][address_index]["address"]
    response[f"{side}_address"] = address

    equipment_count = get_granite_equipment_count(tid)
    if equipment_count > 2:
        response[f"{side}_disconnect"] = "PARTIAL"
    else:
        response[f"{side}_disconnect"] = "FULL"

    return response


def get_granite_equipment_count(tid):
    try:
        clli = tid[:-3]
        params = {"CLLI": clli, "EQUIP_NAME": tid, "OBJECT_TYPE": "PORT", "USED": "IN_USE", "WILD_CARD_FLAG": "1"}
        equipments_granite_response = granite_get(GRANITE_EQUIPMENTS, params)
        if not equipments_granite_response:
            return 0
        else:
            unique_curr_path_name = {
                equipment["CURRENT_PATH_NAME"]
                for equipment in equipments_granite_response
                if "CURRENT_PATH_NAME" in equipment
            }
            unique_next_path_name = {
                equipment["NEXT_PATH_NAME"] for equipment in equipments_granite_response if "NEXT_PATH_NAME" in equipment
            }
            return len(unique_curr_path_name) + len(unique_next_path_name)
    except Exception as excp:
        abort(502, f"Granite Equipment Get API Error: {excp}")


def get_equipments(object_type, clli=None, equip_name=None):
    """(CLLI or EQUIP_NAME) and OBJECT_TYPE is required"""
    try:
        params = {"CLLI": clli}
        if not clli:
            params = {"EQUIP_NAME": equip_name}
        params.update({"OBJECT_TYPE": object_type})
        logger.info(params)
        shelf_udas_granite_response = granite_get(GRANITE_EQUIPMENTS, params)
        if not shelf_udas_granite_response:
            return False
        return shelf_udas_granite_response
    except Exception as excp:
        abort(502, f"Granite Equipment Get API Error: {excp}")


def get_attribute_value(elements: list, attribute_name):
    for e in elements:
        if e.get("ATTR_NAME") == attribute_name:
            return e.get("ATTR_VALUE")


def get_shelf_udas(equip_inst_id=None, site_name=None, equip_name=None):
    """equip_inst_id or (site_name and equip_name) are required"""
    try:
        params = {"EQUIP_INST_ID": equip_inst_id}
        if not equip_inst_id:
            params = {"SITE_NAME": site_name, "EQUIP_NAME": equip_name}
        shelf_udas_granite_response = granite_get(GRANITE_SHELF_UDA, params)
        if not shelf_udas_granite_response:
            return False
        return shelf_udas_granite_response
    except Exception as excp:
        abort(502, f"Granite Shelf Uda Get API Error: {excp}")


def get_vpls_vlan_id(network_object):
    vpls_vlan_id_attribute_name = "NETWORK VLAN-ID"
    granite_uda = get_uda_value(network_object["path_inst_id"], vpls_vlan_id_attribute_name)
    return granite_uda


def get_uda_value(circ_path_inst_id, attribute_name):
    uda_elements = call_granite_for_uda(circ_path_inst_id)
    for uda in uda_elements:
        if uda.get("ATTR_NAME") == attribute_name:
            return uda.get("ATTR_VALUE")


def is_uda_value_matching(circ_path_inst_id, attribute_name, attribute_value):
    uda_elements = call_granite_for_uda(circ_path_inst_id)
    for uda in uda_elements:
        if uda.get("ATTR_NAME") == attribute_name and uda.get("ATTR_VALUE") == attribute_value:
            return True
    return False


def is_elan_slm_eligible(cid):
    denodo_data = call_denodo_for_circuit_devices(cid)
    path_id = get_vpls_path_id(denodo_data)
    if path_id:
        attribute_name = "SERVICE LEVEL MONITORING"
        attribute_value = "CONFIGURED"
        return is_uda_value_matching(path_id, attribute_name, attribute_value)
    return False


def get_vpls_path_id(denodo_data):
    for segment in denodo_data[0]["data"]:
        if segment["topology"] == "Cloud" and "EPLAN" in segment["path_type"] and "MPLS" not in segment["path_name"]:
            return segment["path_inst_id"]


def get_source_mep(path_id):
    attribute_name = "SOURCE MEP ID"
    return get_uda_value(path_id, attribute_name)


def get_elan_slm_data(cid, circ_path_inst_id):
    params = {"CIRC_PATH_HUM_ID": cid}
    elan_slm_data = granite_get(ELAN_SLM, params, best_effort=True)
    if not elan_slm_data:
        return generate_slm_data(circ_path_inst_id, cid)
    camel_keys = {
        "SOURCE_CID": "sourceCid",
        "SOURCE_MEP_ID": "sourceMepId",
        "DESTINATION_MEP_ID": "destinationMepId",
        "DESTINATION_CID": "destinationCid",
        "SOURCE_ID": "sourceId",
    }
    elan_slm_data = [{camel_keys[k]: v for k, v in elan_slm_data[0].items()}]
    return elan_slm_data


def get_vc_class_type(circ_path_inst_id):
    endpoint = call_granite_for_uda(circ_path_inst_id)
    for points in endpoint:
        if points["ATTR_NAME"] == "VC CLASS":
            return points["ATTR_VALUE"]


def generate_slm_data(circ_path_inst_id, cid):
    source_mep_id = get_source_mep(circ_path_inst_id)
    if source_mep_id and source_mep_id.split("::")[1] == "10":
        elan_slm_data = [
            {
                "sourceCid": cid,
                "sourceMepId": source_mep_id,
                "destinationMepId": source_mep_id,
                "destinationCid": cid,
                "sourceId": cid,
            }
        ]
        return elan_slm_data
