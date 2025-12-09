import logging
from common_sense.common.errors import abort
from arda_app.dll.granite import get_granite, update_port_paid
from arda_app.dll.sense import get_sense, _handle_sense_resp


logger = logging.getLogger(__name__)


def get_path_elements_data(circuit_id: str) -> dict:
    """Get path element of hub to CPE device"""
    endpoint = f"/pathElements?CIRC_PATH_HUM_ID={circuit_id}&LVL=2"
    granite_resp = get_granite(endpoint)

    if isinstance(granite_resp, dict) and granite_resp.get("retString"):
        abort(500, f"No records found in Granite for cid: {circuit_id}")
    logger.debug(f"PATH ELEMENTS RESPONSE: {granite_resp}")

    # Filter for non-Live transports
    granite_resp = [
        elem
        for elem in granite_resp
        if elem["PATH_STATUS"] in ["Designed", "Auto-Designed", "Planned", "Auto-Planned"]
        and elem["SERVICE_TYPE"] in ["INT-ACCESS TO PREM TRANSPORT", "INT-EDGE TRANSPORT"]
    ]

    hub_tid = ""
    if len(granite_resp) == 0:
        abort(500, "No non-Live hub to prem transport found")
    elif len(granite_resp) > 2:
        # first search for MTU
        for path in granite_resp:
            device_type = path.get("TID")[-2:]
            if (
                path["PATH_Z_SITE_TYPE"] == "ACTIVE MTU"
                and path["SERVICE_TYPE"] == "INT-EDGE TRANSPORT"
                and device_type in ["CW", "QW"]
            ):
                hub_tid = path["PATH_NAME"].split(".")[-2]
                break
        # if no MTU, search for CW or QW
        if not hub_tid:
            for path in granite_resp:
                device_type = path.get("TID")[-2:]
                if device_type in ["CW", "QW"] and path["SERVICE_TYPE"] == "INT-ACCESS TO PREM TRANSPORT":
                    return path
    else:
        hub_tid = granite_resp[0]["PATH_NAME"].split(".")[-2]

    for elem in granite_resp:
        if elem["TID"] == hub_tid:
            return elem

    abort(500, f"Hub port to prem not found for hub device: {hub_tid}")


def check_port(tid, port_id):
    endpoint = f"/palantir/v2/port?tid={tid}&port_id={port_id}&production=true&timer=1"

    for x in range(3):
        resp = get_sense(endpoint, return_resp=True)

        if resp.status_code in (200, 201):
            return _handle_sense_resp(endpoint, "GET", resp=resp)
        elif resp.status_code == 404 and x == 2:
            logger.debug(
                "The design of the circuit was completed successfully but Optic is not reachable. "
                f"Manual check required for URL: {endpoint} developer error: {resp.text}"
            )
            return


def qfx_paid_check(hub_inst_id, hub_model, hub_paid):
    if hub_model == "ACX5448":
        if "GE" in hub_paid:
            fix_paid = hub_paid.replace("GE", "XE")

            resp = update_port_paid(hub_inst_id, fix_paid)

            if resp["retString"] != "Port Updated":
                logger.error("Unable to update port access id")
                abort(500, f"Unable to update port access id: {hub_paid}")
