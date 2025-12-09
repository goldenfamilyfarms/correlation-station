import logging
import ipaddress
from arda_app.bll.net_new.ip_reservation.utils.mdso_utils import mdso_static_validation

from common_sense.common.errors import abort
from arda_app.dll.ipc import get_subnet_block_by_ip, modify_block, create_static_iprecord

logger = logging.getLogger(__name__)


def get_customer_ips(params, hub_pe, ipv4_type, block_size, attempt_onboarding, retain_ip, product=None):
    """Build and execute assignment of customer Static IPs"""
    static_blocks = _get_static_blocks(ipv4_type, product, retain_ip)
    logger.debug(f"static blocks to be pulled:\n{static_blocks}")

    # Set block type if product is SIP
    block_type = ""
    if product in {"SIP - Trunk (Fiber)", "SIP Trunk(Fiber) Analog", "PRI Trunk (Fiber)", "PRI Trunk(Fiber) Analog"}:
        block_type = "VoIP"

    return _get_ip_blocks(static_blocks, params, hub_pe, block_size, attempt_onboarding, block_type)


def _get_static_blocks(ipv4_type, product, retain_ip):
    static_blocks = {"v4_route": False, "v4_glue": True, "v6_route": True, "v6_glue": True}

    if product == "Hosted Voice - (Fiber)":
        static_blocks = {"v4_route": True, "v4_glue": False, "v6_route": False, "v6_glue": False}

    if product in {"SIP - Trunk (Fiber)", "SIP Trunk(Fiber) Analog", "PRI Trunk (Fiber)", "PRI Trunk(Fiber) Analog"}:
        static_blocks = {"v4_route": True, "v4_glue": False, "v6_route": False, "v6_glue": False}

    if ipv4_type == "ROUTED":
        static_blocks["v4_route"] = True

    if retain_ip:
        static_blocks = {"v4_route": False, "v4_glue": False, "v6_route": True, "v6_glue": True}

    return static_blocks


def _get_ip_blocks(static_blocks, params, hub_pe, block_size, attempt_onboarding, block_type=None, tries=5):
    ip_blocks = {}

    for k, v in static_blocks.items():
        block_tries = tries
        if v:
            if k == "v4_glue" and static_blocks["v4_route"]:
                block_size = "30"
            elif k == "v6_route":
                block_size = "48"
            elif k == "v6_glue":
                block_size = "64"

            while block_tries:
                block_tries -= 1
                check_error, ip_blocks, net_addr = _check_ip_blocks(
                    ip_blocks, params, k, hub_pe, block_size, block_type, attempt_onboarding
                )

                if check_error:
                    block = get_subnet_block_by_ip(net_addr)
                    modify_block(block)
                else:
                    logger.info(f"Successfully pulled statics: {ip_blocks}")
                    break
            if not block_tries:
                abort(*check_error)

    logger.info(f"Successfully pulled statics: {ip_blocks}")
    return ip_blocks


def _check_ip_blocks(ip_blocks, params, k, hub_pe, block_size, block_type, attempt_onboarding):
    static_res, net_addr, ipc_result = _pull_static_ip(
        params, k, host=hub_pe, block_size=block_size, block_type=block_type, attempt_onboarding=attempt_onboarding
    )

    ip_blocks.update(static_res)
    check_error = mdso_static_validation(net_addr, ipc_result, hub_pe, attempt_onboarding)

    return check_error, ip_blocks, net_addr


def _pull_static_ip(params, class_type, host, block_size=None, block_type=None, attempt_onboarding=False):
    """Assign a static IP block for the customer in IP Control"""
    logger.debug(f"Pulling static record class {class_type}, host {host}, block size {block_size}")

    res = create_static_iprecord(class_type, params, block_type, block_size)

    content = None

    try:
        content = res
        logger.info(f"IPC Response converted to , assigned to content var: \n{content}")
    except (AttributeError, TypeError):
        logger.exception(f"Error while attempting to parse IP Control response \nResponse: \n{res}")
        abort(502, "Invalid response from IPControl", response=res)

    # default assignments to be written in try/except
    ipc_result = ""
    net_addr = ""
    gateway_ip = ""

    if content:
        try:
            # Pull out specific k/v pair for 'result'
            ipc_result = content.get("result", "")
            # convert into IP Address object
            ipc_result = ipaddress.ip_network(ipc_result)
            # Extract network address (first IP in block)
            net_addr = ipc_result[0]
            # Calculate v4 gateway_ip from network address
            if ipaddress.ip_address(net_addr).version == 4:
                gateway_ip = ipaddress.IPv4Address(net_addr) + 1
            else:
                gateway_ip = ""
            logger.info(f"Network Address extracted from Result: {str(net_addr)}")
        except (AttributeError, IndexError, ValueError):
            logger.exception(
                f"Error while parsing IP values from IP Control response JSON: {content}\nResponse: \n{res}"
            )
            abort(
                502,
                message=f"Issue encountered while parsing block address and size from IP Control payload {content}",
                response=res,
            )

    logger.info(f"Static {class_type} block {ipc_result} pulled successfully")

    # No longer need them as IP objects, return as strings
    static_res = {
        f"{class_type}_block": str(ipc_result),
        f"{class_type}_net": str(net_addr),
        f"{class_type}_cidr": f"/{block_size}",
        f"{class_type}_gateway": str(gateway_ip) + f"/{block_size}",
    }

    logger.debug(f"Returning static_res: \n{static_res}")
    return static_res, str(net_addr), str(ipc_result)
