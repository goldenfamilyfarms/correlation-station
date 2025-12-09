import logging
import requests

import beorn_app

from common_sense.common.errors import abort
from common_sense.dll.hydra import HydraConnector
from beorn_app.dll.denodo import denodo_get
from beorn_app.common.endpoints import DENODO_SPIRENT_VTA

logger = logging.getLogger(__name__)

"""This file is not deprecated. It is still used for v3 circuit test if the service type isn't CTBH."""

CIRCUIT_ID_REGEX = r"^([A-Z0-9]){2}\.([A-Z0-9]){4}\.([A-Z0-9]){6}\..*?\..{4}$"

SRVC_TYPE = ["EPL", "EVPL", "ETHERNET", "E-ACCESS F", "EPLAN", "NNI", "UNI", "DIA", "MSS DIA", "SECURE INT"]
FIA_TYPE_SERVICE = ["DIA", "MSS DIA", "SECURE INT", "FIA", "E-ACCESS F"]
ELINE_TYPE_SERVICE = ["EPL", "EVPL", "ELINE"]


def _tid_data_search(tid):
    """get tid information"""
    endpoint = f"{DENODO_SPIRENT_VTA}?pe_tid={tid}"
    return denodo_get(endpoint, operation="spirent")["elements"]


def get_pe_details(pe: dict, is_ctbh=False):
    """get target details on a valid PE"""
    hostname = pe.get("tid")
    if not hostname and not isinstance(hostname, str):
        return None, None
    else:
        hostname = hostname.split("-")[0]  # Strip out suffix e.x. PEWTWICI2TW-ESR02
    tid_data = _tid_data_search(hostname)

    """Add Circuit OAM TESTING for Y.1564 on eligible circuits. This is required for E ACCESS Fiber circuit testing
    (DICE ELINE Service Activation Test in Visionworks)."""
    circ_path_inst_id_list = [k.get("test_circ_inst") for k in tid_data]
    env = beorn_app.app_config.USAGE_DESIGNATION
    hc = HydraConnector(
        beorn_app.url_config.HYDRA_BASE_URL,
        beorn_app.auth_config.BEORN_HYDRA_KEY,
        environment="prd" if env == "PRODUCTION" else "dev",
    )
    logger.debug(f"list - {circ_path_inst_id_list}")
    if circ_path_inst_id_list:
        circ_path_inst_id_list_str = ", ".join([str(k) for k in circ_path_inst_id_list])
        dv_circ_path_attr_settings = hc.dv_circ_path_attr_settings(
            filter=f"(circ_path_inst_id in ({circ_path_inst_id_list_str})and val_attr_inst_id=3821)"
        )
        logger.debug(f"return - {dv_circ_path_attr_settings}")
        for k in dv_circ_path_attr_settings.get("elements", {}):
            if k.get("attr_value") in ["Y.1564"]:
                for i, data in enumerate(tid_data):
                    if k.get("circ_path_inst_id") == data.get("test_circ_inst"):
                        tid_data[i].update({"Circuit_OAM_TESTING": k.get("attr_value")})
                        break

    logger.debug(f"tid_data - {tid_data}")
    keys = [
        "test_circ_inst",
        "test_tid",
        "test_fqdn",
        "test_circ_status",
        "test_equip_status",
        "test_equip_vendor",
        "test_equip_model",
        "Circuit_OAM_TESTING",
    ]
    data = []
    if not tid_data:
        return []

    # Search each PE record with a Live status and fqdn is not NULL
    # and equipment model includes "NFX" per Spirent requirements
    # then adds each id to the tid_nfx_list
    tid_nfx_list = []
    for id, device in enumerate(tid_data):
        # conditions for a valid test circuit
        if device.get("test_circ_status", "").upper() != "LIVE":
            continue
        logger.debug(f"Test Circuit Status for PE {hostname}-{device['test_circ_inst']} is inactive")
        if device.get("test_equip_status", "").upper() != "LIVE":
            continue
        logger.debug(f"Test Equipment Status for PE {hostname}-{device['test_circ_inst']} is inactive")
        if device.get("test_fqdn", "") is None:
            continue
        logger.debug(f"Test fqdn for PE {hostname} is not found.")
        if not is_ctbh:
            if device.get("test_equip_model", "").upper().find("NFX") == -1:
                continue
            logger.debug(f"Test Equipment Model for PE {hostname} is invalid.")
        tid_nfx_list.append(id)
    logger.debug(f"FOUND! {len(tid_nfx_list)} device(s)")
    if not tid_nfx_list:
        return [dict.fromkeys(keys)]
    # Mine data from each PE record
    for entry in tid_nfx_list:
        nfx = {}
        for key in keys:
            if key not in tid_data[entry].keys():
                nfx[key] = None
            elif key not in ("test_fqdn", "test_circ_inst", "test_equip_model", "test_equip_status"):
                nfx[key] = tid_data[entry].get(key, None)
            elif tid_data[entry][key]:
                nfx[key] = tid_data[entry].get(key, None)
            else:
                return abort(502, "Unable to determine {} for PE {}".format(key, hostname))
        data.append(nfx)
    return data


class PalantirConnector:
    def __init__(self, url):
        self.url = url
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"Log_Message=Palantir connector created for url '{self.url}'")

    def ip_update(self, ip_address: str, tid: str) -> bool:
        circuit_test_endpoint = f"{self.url}/v2/device/ip_update?ip={ip_address}&tid={tid}"
        try:
            response = requests.get(circuit_test_endpoint, timeout=150, verify=False)
            if response.status_code != 200:
                error_msg = (
                    f"IP_Address={ip_address} | Hostname={tid} | Url={circuit_test_endpoint} | "
                    f"Status_Code={response.status_code} | "
                    f"Log_Message=Unable to retrieve the circuit details for spirent test circuit."
                )
                self.logger.warning(error_msg, exc_info=True)
                return False
            json_response = response.json()
            return json_response

        except Exception as ex:
            error_msg = (
                f"IP_Address={ip_address} | Hostname={tid} | Url={circuit_test_endpoint} | "
                f"Log_Message=Exception when Retrieving the circuit details for spirent test circuit, {ex}"
            )
            self.logger.warning(error_msg, exc_info=True)
            return False
