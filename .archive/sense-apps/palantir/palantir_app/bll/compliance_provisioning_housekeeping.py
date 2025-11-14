import logging

from palantir_app.bll.ddos_compliance import ddos_validation_process
from common_sense.common.errors import abort, error_formatter, get_standard_error_summary, GRANITE, INCORRECT_DATA
from palantir_app.common.compliance_utils import ComplianceStages, get_pri_trunks, is_live
from palantir_app.common.constants import (
    ASSOCIATION_STATUS_CHG_PRODUCTS,
    ASST_PUT_NUMBER_TYPE,
    ASSTN_USED_STATUS,
    CHANGE_ORDER_TYPE,
    DDOS_PRODUCTS,
    GRANITE_STATUS_LIVE,
    PATH_STATUS_STAGE,
    READY_TO_SET_LIVE_STATUSES,
    SET_CONFIRMED_TRUE,
    STL_PARENT_SVC_TYPES,
    STL_SVC_ELEMENT_TYPES,
    SURPRISE_STATUSES,
)
from palantir_app.dll import granite
from palantir_app.common.endpoints import (
    GRANITE_ELEMENTS,
    GRANITE_NETWORKS,
    GRANITE_ASSOCIATIONS_NUMBER_PUT,
    SHELF_UDAS,
    SHELF_UPDATE,
    GRANITE_SITES,
    GRANITE_EQUIPMENTS,
)

logger = logging.getLogger(__name__)


def set_to_live(cid, order_type, compliance_status, product_name=None, path_data=None, additional_attributes=None):
    """Set CID path status to Live"""
    if not path_data:
        path_data = granite.get_path_details_by_cid(cid)
    logger.debug(f"{path_data = }")
    # get latest revision to evaluate status
    all_revisions, revision_count = granite.get_all_revisions(path_data)
    latest_revision = granite.get_latest_revision(all_revisions)
    path_data_latest_revision = [path for path in path_data if path["pathRev"] == latest_revision]

    if product_name in DDOS_PRODUCTS:
        # ddos products require granite UDA validation prior to setting circuit path live
        ddos_validation_process(cid, product_name, path_data_latest_revision[0]["pathInstanceId"])

    path_status = _get_status(path_data_latest_revision)
    # pre-check for any surprise statuses that shouldn't be here at compliance
    if _is_invalid_status(path_status):
        detail = f"Unexpected path status: {path_status}"
        compliance_status.update({PATH_STATUS_STAGE: detail})
        msg = error_formatter(GRANITE, INCORRECT_DATA, "Path Status", detail)
        abort(502, compliance_status, summary=get_standard_error_summary(msg))
    # we don't need to do anything for orders that are already live/no designed path
    if not _change_required(path_status, compliance_status):
        compliance_status.update({PATH_STATUS_STAGE: "Successful - No path status changes required"})
        return
    if not path_data:
        compliance_status.update({PATH_STATUS_STAGE: "Mandatory Circuit Information Missing"})
        abort(502, compliance_status)

    if CHANGE_ORDER_TYPE in order_type:
        _remove_existing_live_path(revision_count, path_data, cid, compliance_status)

    if product_name:
        set_associated_path_to_live(product_name, path_data_latest_revision, cid, compliance_status)

    if additional_attributes and isinstance(additional_attributes, dict):
        shelf_serial_number = additional_attributes.get("serial_number")
        tid = additional_attributes.get("tid")
    else:
        shelf_serial_number = None
        tid = None

    _update_shelf_info(cid, tid, shelf_serial_number)

    for revision in path_data_latest_revision:
        set_elements_to_live(cid, revision, compliance_status)

    set_latest_revision_to_live(cid, latest_revision, compliance_status)

    if "PRI" in path_data[0]["category"]:
        _pri_stl_process(cid, compliance_status)

    compliance_status.update({PATH_STATUS_STAGE: ComplianceStages.SUCCESS_STATUS})


def _get_status(path_data):
    status = path_data[0]["status"]
    logger.debug(f"{ status = }")
    return status


def _is_invalid_status(path_status):
    if path_status in SURPRISE_STATUSES:
        return True
    return False


def _change_required(path_status, compliance_status):
    if is_live(path_status):
        return False  # already live, no change required
    if path_status in READY_TO_SET_LIVE_STATUSES:
        return True  # change is required, we're ready to set to live
    # if we get this far, something weird is going on. abandon ship.
    detail = f"Unexpected path status while evaluating required changes: {path_status}"
    compliance_status.update({PATH_STATUS_STAGE: detail})
    msg = error_formatter(GRANITE, INCORRECT_DATA, "Path Status", detail)
    abort(502, compliance_status, summary=get_standard_error_summary(msg))


def _remove_existing_live_path(count: int, path_data: list, cid: str, compliance_status: dict):
    if count > 2:
        compliance_status.update({PATH_STATUS_STAGE: "More than two revisions found in Granite"})
        abort(502, compliance_status)

    live_revisions = [x for x in path_data if x["status"] == "Live"]
    if not live_revisions:
        if count > 1:
            compliance_status.update({PATH_STATUS_STAGE: "Missing Live revision in Granite"})
            abort(502, compliance_status)
    else:
        delete_path_error = granite.delete_path(live_revisions, cid, "Canceled")
        if delete_path_error:
            compliance_status.update({PATH_STATUS_STAGE: delete_path_error})
            abort(501, compliance_status)


def set_associated_path_to_live(product_name, path_data_latest_revision, cid, compliance_status):
    for assct_status_prdt in ASSOCIATION_STATUS_CHG_PRODUCTS:
        if assct_status_prdt.upper() in product_name.upper():
            _update_path_associations_status(path_data_latest_revision, cid, compliance_status)
            break


def _update_path_associations_status(path_data: list, cid: str, compliance_status):
    for path in path_data:
        path_instance_id = path.get("pathInstanceId")
        path_associations = granite.get_path_associations(cid, path_instance_id)
        if isinstance(path_associations, str):
            compliance_status.update({PATH_STATUS_STAGE: path_associations})
            abort(502, compliance_status)
        else:
            _update_association_number_status(path_associations, cid, compliance_status)


def _update_association_number_status(path_associations: list, cid: str, compliance_status):
    for association in path_associations:
        association_value = association.get("associationValue")
        if ASST_PUT_NUMBER_TYPE in association.get("associationType") and association_value:
            update_parameters = {
                "RANGE_NAME": association.get("numberRangeName"),
                "NUMBER_TYPE": ASST_PUT_NUMBER_TYPE,
                "NUMBER": association_value,
                "STATUS": ASSTN_USED_STATUS,
            }

            association_put_resp = granite.granite_put(
                endpoint=GRANITE_ASSOCIATIONS_NUMBER_PUT, payload=update_parameters, best_effort=True
            )
            if "errorStatusCode" in association_put_resp:
                granite_err_resp = association_put_resp["errorStatusMessage"]
                error_msg = f"Path Association Status Update Failed for CID : {cid}\
                      and Association : {association_value}.Error {granite_err_resp}"
                compliance_status.update({PATH_STATUS_STAGE: error_msg})
                abort(502, compliance_status)

            if "retString" not in association_put_resp or (
                "retString" in association_put_resp and "Number Updated" not in association_put_resp["retString"]
            ):
                error_msg = f"Path Association Status Update Failed for CID : {cid} and Association :\
                        {association_value} -  {str(association_put_resp)}"
                compliance_status.update({PATH_STATUS_STAGE: error_msg})
                abort(502, compliance_status)


def _update_shelf_info(cid, tid, shelf_serial_number):
    update_equipments = _get_shelves_no_media_type(cid)
    for update_equipment in update_equipments:
        shelf_inst_id = update_equipment["SHELF_INST_ID"]
        element_category = update_equipment.get("SHELF_INST_ID", "")

        update_parameters = {
            "SHELF_INST_ID": shelf_inst_id,
            "SHELF_NAME": update_equipment["SHELF_NAME"],
            "SITE_NAME": update_equipment["SITE_NAME"],
            "UDA": {
                "Purchase Info": {"TRANSPORT MEDIA TYPE": "FIBER"},
                "RESPONSIBLE ORGANIZATION": {"RESPONSIBLE TEAM": "ENT-SVC-IP"},
            },
        }

        if element_category != "FDP":
            update_parameters["UDA"]["Device Config-Equipment"] = {"IP MGMT TYPE": "DHCP"}

        shelf_uda_upd_response = granite.granite_put(SHELF_UPDATE, payload=update_parameters)
        logger.info(f"{shelf_inst_id} shelf update response: {shelf_uda_upd_response}")

    if shelf_serial_number and tid:
        _update_shelf_serial_num(tid, shelf_serial_number)


def _update_shelf_serial_num(tid, shelf_serial_number):
    shelf_equipments = _get_shelves(tid)
    for shelf_inst_id in shelf_equipments:
        update_parameters = {"SHELF_INST_ID": shelf_inst_id, "SHELF_SERIALNUMBER": shelf_serial_number}
        shelf_uda_upd_response = granite.granite_put(SHELF_UPDATE, payload=update_parameters)
        logger.info(f"{shelf_inst_id} shelf_inst_id shelf_uda_upd_response : {shelf_uda_upd_response}")


def _get_shelves(tid):
    shelf_equipments = []
    url = f"{GRANITE_EQUIPMENTS}?CLLI={tid[:8]}&EQUIP_NAME={tid}&OBJECT_TYPE=SHELF&WILD_CARD_FLAG=1"
    shelf_status_data = granite.granite_get(url)
    for shelf in shelf_status_data:
        equip_inst_id = shelf["EQUIP_INST_ID"]
        shelf_equipments.append(equip_inst_id)
    return shelf_equipments


def _get_shelves_no_media_type(cid):
    path_elements_response = _get_granite_elements(cid)
    update_equipments = []
    for granite_element in path_elements_response:
        equipment_id = granite_element.get("ELEMENT_REFERENCE")
        if granite_element.get("ELEMENT_TYPE") == "PORT" and equipment_id:
            params = {"EQUIP_INST_ID": equipment_id}
            shelf_uda_response = granite.granite_get(SHELF_UDAS, params=params)
            update_equipment = _get_invalid_shelf(shelf_uda_response)
            if update_equipment and "SHELF_INST_ID" in update_equipment:
                update_equipments.append(update_equipment)
    return update_equipments


def _get_granite_elements(cid):
    params = {"CIRC_PATH_HUM_ID": cid, "LVL": 1}
    path_elements_response = granite.granite_get(GRANITE_ELEMENTS, params=params)
    return path_elements_response


def _get_invalid_shelf(shelf_udas):
    found_invalid = {"TRANSPORT": False, "MGMT": False}
    update_equipment = {}
    if isinstance(shelf_udas, list):
        for shelf_uda in shelf_udas:
            equip_inst_id = str(shelf_uda.get("EQUIP_INST_ID"))
            equip_name = str(shelf_uda.get("EQUIP_NAME"))
            site_name = str(shelf_uda.get("SITE_NAME"))
            if (
                shelf_uda.get("GROUP_NAME") == "Purchase Info"
                and shelf_uda.get("ATTR_NAME") == "TRANSPORT MEDIA TYPE"
                and shelf_uda.get("ATTR_VALUE")
            ):
                found_invalid["TRANSPORT"] = True
            elif (
                shelf_uda.get("GROUP_NAME") == "Device Config-Equipment"
                and shelf_uda.get("ATTR_NAME") == "IP MGMT TYPE"
                and shelf_uda.get("ATTR_VALUE")
            ):
                found_invalid["MGMT"] = True
        if (not found_invalid["TRANSPORT"] or not found_invalid["MGMT"]) and equip_inst_id:
            update_equipment["SHELF_INST_ID"] = equip_inst_id
            update_equipment["SHELF_NAME"] = equip_name
            update_equipment["SITE_NAME"] = site_name
    return update_equipment


def set_elements_to_live(cid, revision, compliance_status):
    if not _is_valid_current_path_status(revision["status"]):
        compliance_status.update(
            {PATH_STATUS_STAGE: "Circuit is not in Designed, Auto-Designed, or Auto-Provisioned state"}
        )
        abort(502, compliance_status)
    set_elements_live_error = update_path_elements_to_live(revision.get("product_Service_UDA"), cid)
    if not set_elements_live_error:
        set_elements_live_error = update_parent_path_to_live(revision)

    if set_elements_live_error:
        compliance_status.update({"Path Status Update": set_elements_live_error})
        abort(502, compliance_status)


def _is_valid_current_path_status(revision_status):
    if revision_status not in READY_TO_SET_LIVE_STATUSES:
        return False
    return True


def set_latest_revision_to_live(cid, latest_revision, compliance_status):
    update_parameters = {
        "PATH_NAME": cid,
        "PATH_REVISION": latest_revision,
        "PATH_STATUS": GRANITE_STATUS_LIVE,
        "SET_CONFIRMED": SET_CONFIRMED_TRUE,
    }

    path_update_msg = granite.update_path_by_parameters(update_parameters)
    if path_update_msg != ComplianceStages.SUCCESS_STATUS:
        compliance_status.update({PATH_STATUS_STAGE: path_update_msg})
        abort(502, compliance_status)


def update_parent_path_to_live(path_data):
    cilli_list = []
    cilli_list.append(path_data.get("zSideSiteName").split("-")[0].replace(" ", ""))

    if path_data["product_Service_UDA"] in STL_PARENT_SVC_TYPES:
        cilli_list.append(path_data.get("aSideSiteName").split("-")[0].replace(" ", ""))

    for cilli in cilli_list:
        payload = {"SITE_NAME": cilli, "SITE_TYPE": "BUILDING", "SITE_STATUS": "Live"}
        granite_response = granite.granite_put(GRANITE_SITES, payload, calling_function="update_parent_path_to_live")
        if not granite_response:
            return f"Failure updating Parent Path {cilli} status to Live"


def update_path_elements_to_live(service_type, cid):
    if service_type and service_type in STL_SVC_ELEMENT_TYPES:
        element_types = STL_SVC_ELEMENT_TYPES[service_type]
        stl_elements_full = _get_elements_references(cid, element_types)
        elements_stl_error = _update_elements_to_live_by_reference(stl_elements_full)
        if elements_stl_error:
            return elements_stl_error


def _get_elements_references(cid, element_types):
    stl_elements_full = []
    for element_type in element_types:
        params = {"CIRC_PATH_HUM_ID": cid, "ELEMENT_TYPE": element_type}
        logger.info(f"_get_elements_references params : {params}")
        granite_response = granite.granite_get(GRANITE_ELEMENTS, params=params)
        logger.info(f"_get_elements_references granite_response : {granite_response}")
        stl_elements_full += _get_elements_from_granite_resp(granite_response)
    return stl_elements_full


def _get_elements_from_granite_resp(granite_response):
    stl_elements = []
    if granite_response and isinstance(granite_response, list):
        for response_elements in granite_response:
            if (
                response_elements.get("ELEMENT_REFERENCE")
                and response_elements.get("ELEMENT_STATUS")
                and response_elements.get("ELEMENT_STATUS") != GRANITE_STATUS_LIVE
            ):
                stl_elements.append(response_elements["ELEMENT_REFERENCE"])
    if granite_response and isinstance(granite_response, dict) and _not_live(granite_response, response_elements):
        stl_elements.append(response_elements["ELEMENT_REFERENCE"])
    return stl_elements


def _not_live(granite_response, response_elements):
    return (
        granite_response.get("ELEMENT_REFERENCE")
        and response_elements.get("ELEMENT_STATUS")
        and granite_response.get("ELEMENT_STATUS") != GRANITE_STATUS_LIVE
    )


def _update_elements_to_live_by_reference(stl_elements):
    for stl_element in stl_elements:
        payload = {"NETWORK_INST_ID": stl_element, "NETWORK_STATUS": GRANITE_STATUS_LIVE}
        logger.info(f"_update_elements_by_reference payload : {payload}")
        stl_element_update_resp = granite.granite_put(GRANITE_NETWORKS, payload, best_effort=True)
        logger.info(f"_update_elements_by_reference stl_element_update_resp : {stl_element_update_resp}")
        if not (
            stl_element_update_resp
            and isinstance(stl_element_update_resp, dict)
            and stl_element_update_resp.get("status") == GRANITE_STATUS_LIVE
        ):
            return f"Failure updating Path Element {stl_element} status to {GRANITE_STATUS_LIVE}"


def _pri_stl_process(cid: str, compliance_status: dict):
    pri_trunks = get_pri_trunks(cid, live_only=True)
    if pri_trunks:
        for trunk in pri_trunks:
            update_parameters = {
                "PATH_NAME": trunk[0],
                "PATH_REVISION": trunk[1],
                "PATH_STATUS": GRANITE_STATUS_LIVE,
                "SET_CONFIRMED": SET_CONFIRMED_TRUE,
            }
            path_update_msg = granite.update_path_by_parameters(update_parameters)
            if path_update_msg != ComplianceStages.SUCCESS_STATUS:
                compliance_status.update({PATH_STATUS_STAGE: path_update_msg})
                abort(502, compliance_status)
