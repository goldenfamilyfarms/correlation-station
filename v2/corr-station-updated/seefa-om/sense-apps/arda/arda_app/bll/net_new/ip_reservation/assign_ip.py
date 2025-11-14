import logging
from typing import Any, Dict
from arda_app.bll.models.payloads.ip_reservation import IPReservationPayloadModel
from arda_app.bll.net_new.ip_reservation.utils.granite_utils import (
    circuit_site_info_path,
    get_circuit_info_and_map_legacy,
    granite_assignment,
)

from common_sense.common.errors import abort
from arda_app.bll.net_new.ip_reservation.utils.static_ip_utils import get_customer_ips
from arda_app.dll.granite import get_path_elements, get_vgw_id, put_granite
from arda_app.common.cd_utils import granite_shelves_post_url
from arda_app.bll.utils import get_ips_from_subnet
import ipaddress


logger = logging.getLogger(__name__)


def assign_static_ip_main(payload: IPReservationPayloadModel, attempt_onboarding: bool = False) -> Dict[str, Any]:
    """Assign static IP address(es) to a circuit."""
    cid = payload.z_side_info.cid
    logger.debug(f"Starting static IP assignment process for {cid}")

    product_name = payload.z_side_info.product_name
    ipv4_type = payload.z_side_info.ipv4_type.upper() if isinstance(payload.z_side_info.ipv4_type, str) else ""
    # Default to 30 if product is a Voice, SIP, or PRI
    block_size = _validate_block_size(payload.z_side_info.block_size) if payload.z_side_info.block_size else "30"

    # values extracted from here are used in in both static assignment logic and payload response
    customer_circuit_info = get_circuit_info_and_map_legacy(cid, attempt_onboarding)

    # get service location information
    service_location_info = circuit_site_info_path(cid)

    # compose full IPC container path and UDF values
    assignment_setup_params = {
        "container": customer_circuit_info["ipc_path"],
        "Account_Number": customer_circuit_info["customer_id"],
        "companyName": customer_circuit_info["customer_name"],
        "Zip_Code": service_location_info["z_zip"],
        "Notes": rf"{payload.z_side_info.engineering_id}\r\n"
        rf"{cid}\r\n"
        rf"{service_location_info['z_address']}\r\n"
        rf"{service_location_info['z_city']}\r\n"
        rf"{service_location_info['z_state']}\r\n"
        rf"{service_location_info['z_zip']}",
        "epr": payload.z_side_info.engineering_id,
    }

    retain_ip = False
    try:
        if payload.z_side_info.retain_ip_addresses == "Yes":
            retain_ip = True
    except (AttributeError, TypeError):
        logger.exception(f"missing retain_ip field in the payload {payload.z_side_info}")

    customer_ips = get_customer_ips(
        assignment_setup_params,
        customer_circuit_info["mx"],
        ipv4_type,
        block_size,
        attempt_onboarding,
        retain_ip,
        product_name,
    )

    if retain_ip:
        network_ip, gateway_ip = get_network_and_gateway_ip(payload.z_side_info.ip_address)
        block = "/" + payload.z_side_info.ip_address.split("/")[1]
        customer_ips["v4_glue_block"] = network_ip + block
        customer_ips["v4_glue_gateway"] = gateway_ip + block

    _write_ips_to_granite(cid, customer_circuit_info, customer_ips, product_name, ipv4_type)

    return _format_resp_payload(product_name, customer_ips, ipv4_type)


def _write_ips_to_granite(
    cid: str, customer_circuit_info: dict, customer_ips: dict, product_name: str, ipv4_type: str
) -> None:
    """Build out granite payload used to update the Granite UDAs with Static IP info."""
    granite_payload = {
        "PATH_NAME": customer_circuit_info["path_name"],
        "PATH_REVISION": customer_circuit_info["path_rev"],
        "PATH_CUSTOMER_NAME": customer_circuit_info["customer_name"],
        "PATH_CUSTOMER_ID": customer_circuit_info["customer_id"],
        "LEG_NAME": customer_circuit_info["leg_name"],
    }

    if product_name in {"Hosted Voice - (Fiber)"}:
        granite_payload["UDA"] = {
            "INTERNET SERVICE ATTRIBUTES": {
                "IPv4 ASSIGNED SUBNET(s)": customer_ips["v4_route_block"],
                "IPv4 ASSIGNED GATEWAY": customer_ips["v4_route_gateway"],
                "IPv4 SERVICE TYPE": "LAN",
                "IPv6 SERVICE TYPE": "NONE",
            }
        }
    elif product_name in {
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
    }:
        tid = get_tid(cid)
        last_octet_static_ip = str(int(customer_ips["v4_route_gateway"].split("/")[0].split(".")[-1]) + 1)
        octets = customer_ips["v4_route_gateway"].split("/")[0].split(".")
        static_ip = f"{'.'.join(octets[0:-1])}.{last_octet_static_ip}/30"
        granite_payload = {
            "SHELF_INST_ID": get_vgw_id(cid),
            "UDA": {
                "Device Info": {"GNE IP ADDRESS": customer_ips["v4_route_gateway"], "GNE TARGET ID (GNE-TID)": tid},
                "Device Config-Equipment": {"IPv4 ADDRESS": static_ip},
            },
        }
    elif ipv4_type == "ROUTED":
        granite_payload["UDA"] = {
            "INTERNET SERVICE ATTRIBUTES": {
                "IPv4 GLUE SUBNET": customer_ips["v4_glue_block"],
                # ex. "75.114.42.192/27"
                "IPv4 ASSIGNED SUBNET(s)": customer_ips["v4_route_block"],
                # ex. "75.114.42.193"
                "IPv4 ASSIGNED GATEWAY": customer_ips["v4_route_gateway"],
                "IPv4 SERVICE TYPE": "ROUTED",
                "IPv6 GLUE SUBNET": customer_ips["v6_glue_block"],
                # ex. "2605:A40A:20B::/48"
                "IPv6 ASSIGNED SUBNET(s)": customer_ips["v6_route_block"],
                "IPv6 SERVICE TYPE": "ROUTED",
            }
        }
    else:
        granite_payload["UDA"] = {
            "INTERNET SERVICE ATTRIBUTES": {
                # ex. "75.114.42.192/27"
                "IPv4 ASSIGNED SUBNET(s)": customer_ips["v4_glue_block"],
                # ex. "75.114.42.193"
                "IPv4 ASSIGNED GATEWAY": customer_ips["v4_glue_gateway"],
                "IPv4 SERVICE TYPE": "LAN",
                "IPv6 GLUE SUBNET": customer_ips["v6_glue_block"],
                # ex. "2605:A40A:20B::/48"
                "IPv6 ASSIGNED SUBNET(s)": customer_ips["v6_route_block"],
                "IPv6 SERVICE TYPE": "ROUTED",
            }
        }

    # Write the UDA payload values into Granite else update granite shelves for SIP products
    (
        granite_assignment(granite_payload)
        if product_name
        not in {"SIP - Trunk (Fiber)", "SIP Trunk(Fiber) Analog", "PRI Trunk (Fiber)", "PRI Trunk(Fiber) Analog"}
        else put_granite(granite_shelves_post_url(), granite_payload)
    )


def _format_resp_payload(product_name: str, customer_ips: dict, ipv4_type: str) -> dict:
    """Format api endpoint response payload."""
    if product_name == "Hosted Voice - (Fiber)":
        resp = {"ipv4_assigned_subnets": "/30 has been successfully assigned."}
    elif product_name in {
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
    }:
        resp = {
            "ipv4_assigned_subnets": "/30 has been successfully assigned.",
            "v4_block": customer_ips["v4_route_block"],
            "v4_net": customer_ips["v4_route_net"],
            "v4_gateway": customer_ips["v4_route_gateway"],
        }
    elif ipv4_type == "ROUTED":
        resp = {
            "ipv4_service_type": "ROUTED",
            "ipv4_glue_subnet": customer_ips["v4_glue_block"],
            "ipv4_assigned_subnets": customer_ips["v4_route_block"],
            "ipv4_assigned_gateway": customer_ips["v4_route_gateway"],
            "ipv6_service_type": "ROUTED",
            "ipv6_glue_subnet": customer_ips["v6_glue_block"],  # /127
            "ipv6_assigned_subnet": customer_ips["v6_route_block"],  # /48
        }
    else:
        resp = {
            "ipv4_service_type": "LAN",
            "ipv4_glue_subnet": "",
            "ipv4_assigned_subnets": customer_ips["v4_glue_block"],
            "ipv4_assigned_gateway": customer_ips["v4_glue_gateway"],
            "ipv6_service_type": "ROUTED",
            "ipv6_glue_subnet": customer_ips["v6_glue_block"],  # /127
            "ipv6_assigned_subnet": customer_ips["v6_route_block"],  # /48
        }
    logger.info(f"Static IP assignment and update of Granite UDAs completed. Response payload: {resp}")
    return resp


def _validate_block_size(block_size):
    """Format and validate block_size for use within sense logic."""

    # Usable range passed from SF can be formatted to either include either CIDR
    # and number of IPs ('/29=5'), or just CIDR ('/29')
    if "=" in block_size:
        block_size, _ = block_size.split("=")

    # blocks larger than /28 require special approval forms, and therefore must be handled manually
    if block_size not in ["/27", "/28", "/29", "/30"]:
        logger.error(f"Unsupported block_size: {block_size}, only CIDR ranges from /30 - /27 are supported")
        abort(500, f"Unsupported block_size: {block_size}, only CIDR ranges from /30 - /27 are supported")

    block_size = block_size.strip("/")
    logger.info(f"block_size formatted to {block_size}")

    return block_size


def get_tid(cid: str):
    """Grabbing existing shelf"""
    circuit_data = get_path_elements(cid, "&LVL=2")

    return "".join([element["TID"] for element in circuit_data if "CW" in element["TID"]][0])


def get_network_and_gateway_ip(ip: str) -> tuple[str, str]:
    network_ip = ""
    gateway_ip = ""
    ips_to_check = get_ips_from_subnet(ip)
    ip = ip.split("/")[0]
    try:
        if ip == ips_to_check[0]:
            network_ip = ip
            ip_int = int(ipaddress.IPv4Address(ip)) + 1
            next_ip = str(ipaddress.IPv4Address(ip_int))
            gateway_ip = next_ip
        elif ip != ips_to_check[0]:
            gateway_ip = ip
            ip_int = int(ipaddress.IPv4Address(ip)) - 1
            ip = str(ipaddress.IPv4Address(ip_int))
            network_ip = ip
            if ip != ips_to_check[0]:
                msg = f"IP provided is not a network IP {ip}"
                abort(500, msg)
    except IndexError:
        msg = "Did not receive ips from get_ips_from_subnet call"
        abort(500, msg)

    return network_ip, gateway_ip
