import logging
from arda_app.bll.net_new.ip_reservation.utils.granite_utils import granite_assignment
from arda_app.common.cd_utils import granite_shelves_post_url

from common_sense.common.errors import abort
from arda_app.bll.net_new.ip_reservation.assign_ip import assign_static_ip_main, get_network_and_gateway_ip
from arda_app.bll.models.payloads.ip_reservation import IPReservationPayloadModel, SideInfo
from arda_app.bll.net_new.ip_reservation.utils.mdso_utils import confirm_router_supports_rphy
from arda_app.dll.granite import get_granite, get_shelf_udas, get_vgw_id, put_granite
from arda_app.dll.ipc import get_subnet_block_by_ip, modify_block

from thefuzz import fuzz


logger = logging.getLogger(__name__)


def ip_delegation(payload: IPReservationPayloadModel) -> dict:
    """
    Reserve an IP address from IP Control.
    """
    resp = {}

    # FIA, SIP, PRI, and Hosted Voice logic
    if payload.z_side_info.product_name in {
        "Carrier Fiber Internet Access",
        "Fiber Internet Access",
        "Hosted Voice - (Fiber)",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
    }:
        # Check if IPs exist
        _check_ip_subnets(payload.z_side_info)
        ip_static_resp = assign_static_ip_main(payload)

        return {**ip_static_resp, **resp}

    # FC + Remote PHY logic
    if payload.z_side_info.product_name in {"FC + Remote PHY"}:
        ip_static_resp = confirm_router_supports_rphy(payload.z_side_info.cid)
        return {**ip_static_resp, **resp}

    return resp if resp else {"message": "IP Reservation isn't needed for this EPR."}


def _check_ip_subnets(zside_info: SideInfo) -> None:
    """
    Checks if a circuit's IPv4 & IPv6 subnets exists in Granite
    Writes an attempt to granite none found.
    """
    resp = get_granite(f"/pathElements?CIRC_PATH_HUM_ID={zside_info.cid}")
    data = resp[0] if isinstance(resp, list) else {}

    if zside_info.product_name in {
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
    }:
        vgw_id = get_vgw_id(zside_info.cid)
        gne_ip_address = [
            attr.get("ATTR_VALUE") for attr in get_shelf_udas(vgw_id) if attr.get("ATTR_NAME", "") == "GNE IP ADDRESS"
        ]
        if gne_ip_address and gne_ip_address[0] == "AUTOMATION ATTEMPTING":
            abort(500, "VGW has GNE IP ADDRESS set to AUTOMATION ATTEMPTING")

        put_granite(
            granite_shelves_post_url(),
            {"SHELF_INST_ID": vgw_id, "UDA": {"Device Info": {"GNE IP ADDRESS": "AUTOMATION ATTEMPTING"}}},
        )
    else:
        # Get IP Subnets
        ip_subnets = {
            "IPv4 assigned subnets": data.get("IPV4_ASSIGNED_SUBNETS"),
            "IPv6 assigned subnets": data.get("IPV6_ASSIGNED_SUBNETS"),
            "IPv4 glue subnet": data.get("IPV4_GLUE_SUBNET"),
            "IPv6 glue subnet": data.get("IPV6_GLUE_SUBNET"),
        }

        # Abort if IP Subnets exist
        if any(ip_subnets.values()):
            for ip_type, value in ip_subnets.items():
                if value:
                    abort(500, f"Customer already has {ip_type} as {value}")

        # Before writing to Granite for automation, check if retain ip address is set to "yes"
        if zside_info.retain_ip_addresses == "Yes":
            check_for_retaining_address(zside_info, data)

        # Write the UDA payload values into Granite for automation attempt
        path_inst_id = data.get("CIRC_PATH_INST_ID")
        if not path_inst_id:
            abort(500, f"Unable to find PATH_INST_ID for CID: {zside_info.cid}")

        params = {
            "PATH_INST_ID": path_inst_id,
            "UDA": {"INTERNET SERVICE ATTRIBUTES": {"IPv4 ASSIGNED SUBNET(s)": "AUTOMATION ATTEMPTING"}},
        }
        granite_assignment(params)


def check_for_retaining_address(zside_info, data) -> None:
    customer_address = data.get("PATH_Z_SITE")
    if not customer_address:
        msg = f"Unable to retrive Customer address from pathelements {data}"
        logger.error(msg)
        abort(500, msg)
    ip = zside_info.ip_address
    if not ip or "/" not in ip:
        msg = f"Unable to retrive IP address form zside info {zside_info} or cidr is missing in ip {ip}"
        logger.error(msg)
        abort(500, msg)

    # Check if ip is of type Network
    network_ip, gateway_ip = get_network_and_gateway_ip(ip)
    logger.debug(f"Network IP is {network_ip} and Gateway IP is {gateway_ip}")

    # Look for customer name in IPC
    ipc_resp = get_subnet_block_by_ip(network_ip)
    logger.debug(ipc_resp)
    # Clean up customer address
    start_index = customer_address.find("-") + 1  # Start after '-'
    end_index = customer_address.find("/")
    customer_address = customer_address[start_index:end_index]

    ipc_post_response = ipc_post(ipc_resp, customer_address, network_ip, zside_info, data)
    return ipc_post_response


def ipc_post(ipc_data, customer_address, ip, zside_info, data) -> None:
    """
    create payload to call modifyBlock
    """
    try:
        user_defined_fields = ipc_data["userDefinedFields"]
    except (KeyError, TypeError, IndexError):
        msg = f"Unable to get userDefinedFields from IPC {ipc_data}"
        abort(500, msg)

    company_name = None
    for field in user_defined_fields:
        if field.startswith("Company_Name="):
            company_name = field.split("=")[1]
            break

    match = fuzz.ratio(customer_address, company_name)
    if match < 80:
        msg = f"customer name mismatch. Granite: {customer_address} IPC: {company_name}"
        abort(500, msg)

    # Post call to IPC to modify subnet block
    block = get_subnet_block_by_ip(ip)
    user_defined_fields = (
        zside_info.engineering_id + ",\n" + zside_info.cid + ",\n" + data.get("PATH_Z_SITE").split("//")[1]
    )
    block["userDefinedFields"] = user_defined_fields
    resp = modify_block(block, retain_ip_logic=True)
    logger.debug(resp)
