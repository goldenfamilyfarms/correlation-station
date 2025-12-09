from common_sense.common.errors import abort
from arda_app.common.cd_utils import granite_paths_get_url
from arda_app.dll.granite import get_granite, get_path_elements


def get_circuit_tid_ports(cid: str, path_instid: str) -> dict:
    """Get the circuit tid ports."""

    if path_instid:
        circ_path_inst_id = path_instid
    else:
        url = granite_paths_get_url(cid)
        resp = get_granite(url)
        circ_path_inst_id = [path.get("pathInstanceId") for path in resp][0]

    path_elements = get_path_elements(cid, f"&INITIAL_CIRCUIT_ID={circ_path_inst_id}")

    devices = {}
    eligible_status = ["LIVE", "DO-NOT-USE", "PENDING DECOMMISSION"]

    for elem in path_elements:
        if (elem.get("PATH_STATUS").upper() == "LIVE") and (elem.get("ELEMENT_STATUS").upper() in eligible_status):
            tid = elem.get("TID")
            if tid:
                if elem["LVL"] == "1":
                    if "ZW" in tid[-2:] or "01W" in tid[-3:] or "AW" in tid[-2:]:
                        if elem["PORT_ROLE"] == "UNI-EVP":
                            abort(500, "Trunked handoff circuits are unsupported at this time")
                        devices[tid] = elem["PORT_ACCESS_ID"]
                elif elem["LVL"] == "2":
                    if "CW" in tid[-2:]:
                        if (elem["LEG_NAME"] != "1") and ("/" in elem["LEG_NAME"]):
                            devices[tid] = elem["LEG_NAME"].split("/")[0]
                        else:
                            devices[tid] = elem["PORT_ACCESS_ID"]
                    elif "AW" in tid[-2:] or "QW" in tid[-2:]:
                        devices[tid] = elem["PORT_ACCESS_ID"]
                    elif "ZW" in tid[-2:]:
                        if not devices.get(tid):
                            devices[tid] = elem["PORT_ACCESS_ID"]
    return devices


def get_nni_tid_port(nni: str) -> dict:
    """Get the router tid port for the NNI"""
    path_elements = get_path_elements(nni)

    device = {}
    eligible_status = ["LIVE", "DO-NOT-USE", "PENDING DECOMMISSION"]
    for elem in path_elements:
        if (elem.get("PATH_STATUS").upper() == "LIVE") and (elem.get("ELEMENT_STATUS").upper() in eligible_status):
            tid = elem.get("TID")
            if tid:
                if elem["LVL"] == "1":
                    if elem["ELEMENT_CATEGORY"].upper() == "ROUTER":
                        device[tid] = elem["PORT_ACCESS_ID"]
    return device


def get_device_vlans(hostname, port) -> list:
    """Loop through MDSO"""
    return []
