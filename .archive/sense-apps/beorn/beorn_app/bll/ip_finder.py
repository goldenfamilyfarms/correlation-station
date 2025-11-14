import logging

from beorn_app.common.mdso_auth import create_token

from beorn_app.common.mdso_operations import post_to_service, product_query
from beorn_app.dll.mdso import poll_resource_status

logger = logging.getLogger(__name__)


def ip_finder(cid: str, tid: str) -> tuple:
    cpe_ip = ""
    err_msg = ""
    try:
        token = create_token()

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "token {}".format(token),
        }

        err_msg, product_id = product_query(headers, "cpeIpProvider")
    except Exception:
        if err_msg:
            return {"CPE_IP": cpe_ip, "FAIL_REASON": err_msg}, 502
        else:
            return {"CPE_IP": cpe_ip, "FAIL_REASON": "Unable to obtain necessary resources from MDSO"}, 502

    data = {
        "label": cid + "_" + tid,
        "description": "IP Finder Info",
        "productId": product_id,
        "properties": {"cid": cid, "target_device": tid},
        "autoclean": True,
    }

    # Call MDSO to find IP Address
    logger.debug("Finding IP for {} - {}".format(cid, tid))
    try:
        err_msg, resource_id = post_to_service(headers, data, cid)
    except Exception:
        if err_msg:
            return {"CPE_IP": cpe_ip, "FAIL_REASON": err_msg}, 502
        else:
            return {"CPE_IP": cpe_ip, "FAIL_REASON": "Unable to create IP Provider resource in MDSO"}, 502

    logger.debug("THE CPE PROVIDER IP RESOURCE ID IS {}".format(resource_id))

    resource_data, response_code = poll_resource_status(resource_id)

    if resource_data["CPE_IP"] == "no ip found":
        return {"CPE_IP": resource_data["CPE_IP"], "FAIL_REASON": resource_data["FAIL_REASON"]}, response_code
    else:
        return {"CPE_IP": resource_data["CPE_IP"]}, response_code
