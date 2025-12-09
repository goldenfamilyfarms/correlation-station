import logging

from common_sense.common.errors import abort
from palantir_app.dll import granite
from palantir_app.dll.granite import granite_get
from palantir_app.common.endpoints import (
    GRANITE_CARDS,
    GRANITE_ELEMENTS,
    GRANITE_EQUIPMENTS,
    GRANITE_PORTS,
    GRANITE_SHELVES,
)
from palantir_app.common import compliance_utils
from palantir_app.bll.compliance_provisioning_housekeeping import set_to_live


logger = logging.getLogger(__name__)


def run_rphy_compliance(cid, order_type):
    """
    Main Rphy compliance Logic
    """
    # Get device information
    params = {"CIRC_PATH_HUM_ID": cid, "LEG_NAME": "RPHY"}
    path_elements = granite_get(GRANITE_ELEMENTS, params=params, return_response_obj=True, operation="mne").json()
    if "retString" in path_elements and "No records" in path_elements["retString"]:
        abort(500, "RPHY leg does not exist in granite")
    logger.info(f"RPHY LEG returned: {path_elements}")
    set_shelf_live(path_elements)
    set_ports_live(path_elements)
    set_card_live(path_elements)
    order_type = compliance_utils.translate_sf_order_type(order_type, "RPHY")
    compliance_status = compliance_utils.ComplianceStages(order_type, housekeeping_only=False).status
    set_to_live(cid, order_type, compliance_status)
    return {"message": "RPHY Compliance Success"}


def set_shelf_live(path_elems):
    for record in path_elems:
        if record["ELEMENT_STATUS"] != "Live" and "TRANSPORT" not in record["ELEMENT_CATEGORY"]:
            params = {
                "SHELF_INST_ID": record["ELEMENT_REFERENCE"],
                "SITE_NAME": record["A_SITE_NAME"],
                "SHELF_STATUS": "Live",
                "SET_CONFIRMED": "TRUE",
            }
            if record["ELEMENT_CATEGORY"] != "RF_TAP":
                params.update({"UDA": {"Purchase Info": {"TRANSPORT MEDIA TYPE": "FIBER"}}})
            response = granite.granite_put(GRANITE_SHELVES, params, True, "RPHY Compliance")
            logger.info(f"Shelf STL Payload: {params}, response: {response}")
            if "errorStatusMessage" in response:
                abort(500, f"Error during shelf STL: name: {record['ELEMENT_NAME']}, {response['errorStatusMessage']}")


def set_ports_live(path_elems):
    """
    This function will update Granite Ports live for Meraki devices
    Following 2 methods, including this one, will set their namesakes live
    ONLY for Meraki MX devices at this time.
    Ports are set to skip any template warnings from granite.
    """
    failed = False
    for record in path_elems:
        if record["ELEMENT_STATUS"] != "Live" and record["MODEL"]:
            params = {
                "PORT_INST_ID": record["PORT_INST_ID"],
                "PORT_STATUS": "Assigned",
                "PORT_NAME": record["PORT_NAME"],
                "SET_CONFIRMED": "TRUE",
            }
            logger.info(f"port  STL payload {params}")
            response = granite.granite_put(GRANITE_PORTS, params)
            if response:
                continue
            else:
                failed = True
                reason = response.content
    if failed:
        abort(500, f"Ports STL failed due. response: {reason}")
    else:
        return 200, "Ports set to live successfully"


def set_card_live(path_elems):
    for record in path_elems:
        if record["MODEL"] and record["ELEMENT_STATUS"] != "Live":
            tid = record["ELEMENT_NAME"].split("/")[0]
            port_id = record["PORT_INST_ID"]
            params_str = f"?CLLI={tid[0:8]}&EQUIP_NAME={tid}&OBJECT_TYPE=PORT&WILD_CARD_FLAG=1&PORT_INST_ID={port_id}"
            response = granite.granite_get(f"{GRANITE_EQUIPMENTS}{params_str}", operation="mne")
            if response:
                if response[0]["CARD_STATUS"] != "Live":
                    params = {"CARD_INST_ID": response[0]["CARD_INST_ID"], "CARD_STATUS": "Live"}
                    response = granite.granite_put(GRANITE_CARDS, params)
                    if response:
                        continue
                    else:
                        abort(500, f"Error setting card to live: {response}")
                else:
                    logger.info("Card already live")
                    continue
            else:
                abort(500, f"Error getting card from granite: {response}")
    return "Cards set live successfully"
