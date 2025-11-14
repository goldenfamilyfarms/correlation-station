import logging

from palantir_app.dll.denodo import denodo_get
from palantir_app.dll.ndos import ndos_post
from palantir_app.common.endpoints import DENODO_CEDR_DV

logger = logging.getLogger(__name__)


def query_by_tid_or_ip(tid=None, ip=None):
    """Returns info for a device based on ip or tid"""

    if not tid and not ip:
        return None
    alias = "hostname" if tid else "ipaddr"
    endpoint = f"{DENODO_CEDR_DV}{alias}/views/bv_cedr_device_by_{alias}?{alias}={tid if tid else ip}"
    return denodo_get(endpoint)["elements"]


def isin_update(ip):
    """POST to NDOS isin service with the IP"""

    endpoint = "/ndos-isin-service/api/isin"
    ndos_payload = {"ipaddr": ip}
    return ndos_post(endpoint, ndos_payload, timeout=90)


def is_tid_in_isin(ip: str, tid: str) -> bool:
    """
    Checks if a tid is in the ISIN service

    :param ip: IP address of the device
    :type ip: str
    :param tid: TID of the device
    :type tid: str
    :return: True if the tid is in the ISIN service, False otherwise
    :rtype: bool
    """
    logger.debug(f"Checking ISIN for {ip} with tid {tid}")
    endpoint = "/ndos-isin-service/api/v1.1/isin"
    ndos_payload = {"ipaddr": ip, "hostname": tid}
    r = ndos_post(endpoint, ndos_payload, timeout=90)
    logger.debug(f"ISIN response: {r}")
    # Parsing the response for v2/Device purposes
    if r:
        try:
            return True if r["appMediation"]["ise"] else False
        except KeyError:
            return False
    return False
