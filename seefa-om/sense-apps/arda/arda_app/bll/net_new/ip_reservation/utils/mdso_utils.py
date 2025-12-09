import ipaddress
import logging
import re
import subprocess

from common_sense.common.errors import abort
from arda_app.dll.mdso import onboard_and_exe_cmd
from arda_app.dll.granite import get_path_elements
from arda_app.dll.ipc import get_block_by_blockname


logger = logging.getLogger(__name__)


# TODO: Button this up once MDSO API released!
def obtain_pe_isis_area(cid, pe, attempt_onboarding=False):
    """Obtain the IS-IS Area from the PE router via MDSO in order to determine proper IPC Container.
    This method must be used for LCHTR circuits.

     :param cid: The main service circuit ID
     :param pe: The hub router for the circuit
    """
    logger.info(f"Obtaining IS-IS Area information via MDSO for {cid} from {pe}")

    mdso_response = onboard_and_exe_cmd(command="show_isis", hostname=pe, attempt_onboarding=attempt_onboarding)

    mdso_isis_area = None

    try:
        mdso_isis_area = mdso_response["result"]["isis-overview-information"]["isis-overview"]["isis-router-areaid"]
        logger.info(f"IS-IS area extracted as {mdso_isis_area}")
    except Exception:
        logger.exception("Exception while attempting to obtain IS-IS area from MDSO")
        abort(500, f"Unable to locate IS-IS Area information from {pe} via MDSO")

    # IS-IS Area is formatted as xx.yyyy (i.e. 49.2225), we need only the second part
    mdso_isis_area = mdso_isis_area.split(".")[1]

    return mdso_isis_area


def obtain_pe_bgp_asn(cid, pe, attempt_onboarding=False):
    """Obtain the BGP AS Number from the PE router via MDSO in order to determine proper IPC Container.
    This method must be used for LTWC and Legacy Bresnan LCHTR circuits.

     :param cid: The main service circuit ID
     :param pe: The hub router for the circuit
    """
    logger.info(f"Obtaining BGP AS Number via MDSO for {cid} from {pe}")

    mdso_response = onboard_and_exe_cmd(
        command="show_routing_options", hostname=pe, attempt_onboarding=attempt_onboarding
    )

    mdso_bgp_as = None

    try:
        mdso_bgp_as = mdso_response["result"]["routing-options"]["autonomous-system"]["as-number"]
        logger.info(f"BGP AS extracted as {mdso_bgp_as}")
    except Exception:
        logger.exception("Exception while attempting to obtain BGP AS from MDSO")
        abort(500, f"Unable to locate BGP AS information from {pe} via MDSO")

    return mdso_bgp_as


def mdso_static_validation(ip, ip_block, hostname, attempt_onboarding):
    logger.info(f"Validating route table in MDSO for {ip} in {hostname}")
    # Validate Static IP records against network route advertisements to determine potential IP conflicts
    check_error = ""

    if hostname:
        mdso_result = onboard_and_exe_cmd(
            command="show_route", parameter=ip, hostname=hostname, timeout=120, attempt_onboarding=attempt_onboarding
        )

        # get route table object and check route table for assigned IPv4s
        mdso_route_table = None

        try:
            mdso_route_table = mdso_result["result"]["route-information"]["route-table"]
        except (AttributeError, KeyError, TypeError):
            logger.exception(f"Could not read MDSO route table result: {mdso_result}")
            abort(500, f"Could not read MDSO route table result: {mdso_result}")

        if mdso_route_table:
            check_error = _check_route_table(mdso_route_table, ip)

    # If IPv4, run fping for further validation
    if ipaddress.ip_address(ip).version == 4 and not check_error:
        check_error = _fping_ip(ip_block)
        # for local testing you can comment out the fping check
        # pass

    if check_error:
        return check_error


def get_connection_info(cid) -> tuple:
    """Get port connection info needed for MDSO call"""
    circuit_data = get_path_elements(cid, "&LVL=1")
    transport_name = None
    hostname: str = ""
    leg_name: str = ""
    for circuit in circuit_data:
        try:
            element_name = circuit["ELEMENT_NAME"]
            split_name = element_name.split(".")
            if re.search(r"CW$", split_name[2]):
                logger.debug(f"TRANSPORT PATH: {element_name}")
                transport_name = element_name
                hostname = split_name[2]
                break
        except (KeyError, IndexError):
            abort(500, f"No element found in Granite for {cid}")

    if transport_name is None:
        abort(500, f"No transport element found in Granite for {cid}")
    transport_data = get_path_elements(transport_name, "&LVL=1")

    try:
        leg_name = transport_data[0].get("LEG_NAME").split("/")[0].lower()
    except (KeyError, IndexError):
        abort(500, f"No leg name found in Granite for {transport_name}")

    return hostname, leg_name


def network_address_from_gateway(gateway: str) -> str:
    address = ipaddress.ip_interface(gateway)
    return address.network


def check_router_ip_block(hostname, leg_name, isp=False) -> str:
    """Get IP address from MDSO"""

    # attempt to get ip address using customer port else call mdso again with static port routing
    port = f"{leg_name}.4063"
    block = _validate_mdso_ip_response(hostname, port, leg_name)
    if not block:
        block = _validate_mdso_ip_response(hostname, "irb.4063")

    # verify ip address is a /28 block
    valid_blocks = []
    if isinstance(block, list):
        for address in block:
            if re.search(r"/28$", address["name"]):
                valid_blocks.append(address["name"])
    elif isinstance(block, dict) and re.search(r"/28$", block["name"]):
        valid_blocks.append(block["name"])

    if not valid_blocks and not isp:
        abort(500, f"No IP found in MDSO for hostname {hostname} and port {port}")
    return valid_blocks


def confirm_router_supports_rphy(cid, hostname="", leg_name="", isp=False) -> dict:
    # grabbing hostname and legname if not provided to function(ISP transport path will provide)
    if not isp:
        hostname, leg_name = get_connection_info(cid)

    blocks = check_router_ip_block(hostname, leg_name, isp)

    for block in blocks:
        block = network_address_from_gateway(block)
        ipc_resp = get_block_by_blockname(block)

        try:
            if ipc_resp and int(ipc_resp["numassignedhosts"]) < int(ipc_resp["numaddressablehosts"]):
                return {"message": "Found available IP to support FC + Remote PHY"}
        except KeyError:
            continue

    # only abort when this function is used in IP reservation not ISP transport path creation
    if not isp:
        abort(500, f"No available RPHY IP address space on {hostname} - {leg_name}")


def _validate_mdso_ip_response(hostname: str, port: str, leg_name: str = "irb") -> str:
    try:
        mdso_response = onboard_and_exe_cmd(hostname, "get_interfaces", port, attempt_onboarding=True)
        mdso_response = (
            mdso_response["result"]["configuration"]["interfaces"][leg_name]["unit"]
            if isinstance(mdso_response, dict) and mdso_response.get("result")
            else {}
        )
        return mdso_response[0]["family"]["inet"]["address"]
    except Exception:
        return ""


def _check_route_table(route_table, ip):
    """Here we are taking the route table section from the MDSO IP lookup response object and checking for IPs in
    the rt-destination fields to make sure we don't override a live IP as a safety check"""
    logger.info(f"Validating route table response from MDSO for {ip}")
    logger.info(f"Network route table {route_table}")
    blocks = []

    if isinstance(route_table, dict):
        block = route_table.get("rt", {}).get("rt-destination")
        if isinstance(block, str) and block not in "0.0.0.0/0":
            blocks.append(block)
        else:
            abort(500, f"Route table block in unexpected format: {block}")
    else:
        for route in route_table:  # these objects are highly nested
            if isinstance(route, dict):
                block = route.get("rt", {}).get("rt-destination", "")
                if block not in "0.0.0.0/0":
                    blocks.append(block)

    if blocks:
        for block in blocks:
            # Split out CIDR notation from IP Block
            cidr = None
            try:
                cidr = int(block.split("/")[1])
            except (AttributeError, IndexError):
                logger.exception(f"Error while parsing MDSO route table response: {block} Route Table: {route_table}")
                return (
                    502,
                    f"Invalid IP block returned in MDSO route table lookup: {block}. Route table: {route_table}",
                )
            logger.info(f"version number: {ipaddress.ip_address(ip).version}")
            # Apply separate logic based on IPv4/IPv6
            # if ipv4
            if ipaddress.ip_address(ip).version == 4:
                # check to see if the ip is in use
                if cidr > 23:
                    ip_in_use = True
                else:
                    ip_in_use = False

            # if ipv6
            elif ipaddress.ip_address(ip).version == 6:
                # check to see if the ip is in use
                ipv6_in_use_cidr_blocks = [48, 64, 127]
                if cidr in ipv6_in_use_cidr_blocks:
                    ip_in_use = True
                else:
                    ip_in_use = False
            else:
                logger.exception(f"IP is neither ipv4 or ipv6 version number is: {ipaddress.ip_address(ip).version}")
                return (502, f"IP is neither ipv4 or ipv6 version number is: {ipaddress.ip_address(ip).version}")

            # error out if the ip is in use
            if ip_in_use:
                logger.error(
                    f"Potential IP conflict found between newly-assigned IP {ip} "
                    f"and route table entry {block} Route table response: {route_table}"
                )
                return (
                    502,
                    f"Potential IP conflict found between newly-assigned customer block {ip} "
                    f"and route table entry {block} Route table response: {route_table}",
                )
    else:
        logger.info(f"Blocks did not exist for ip: {ip} and route table: {route_table}")

    logger.info(f"MDSO route table validated successfully for {ip}")


def _fping_ip(block_name):
    """uses fping to check the status of IPs within the designated block and returns the number of
    IPs marked as alive; if any, fall out."""
    logger.info(f"Beginning fping verification for {block_name}")
    cmd = [_fping_os_cmd(), "-ags", f"{block_name}"]
    gateway, output = None, None

    try:
        res = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
        gateway, output = res.communicate()
    except Exception as e:  # Need blanket exception to catch all cases of failure
        logger.exception("Error running fping to check for alive IPs")
        abort(500, f"Error running fping to check for alive IPs: {e}")

    str_output = str(output)
    logger.info(f"Fping executed successfully: \n{str_output}")
    spl_output = str_output.split()
    alive_index = spl_output.index(r"alive\n")
    logger.info(f"Validating alive IPs from result of {alive_index}")
    num_alive = int(spl_output[(alive_index - 1)])

    if num_alive > 0:
        logger.error(f"fping found at least 1 IP in {block_name} marked alive")
        return (502, f"fping found at least 1 IP in {block_name} marked alive")

    logger.info(f"Fping completed successfully for {block_name}")


def _fping_os_cmd():
    with open("/etc/os-release") as f:
        os_output = f.read().lower()
    return "/usr/sbin/fping" if re.search("centos", os_output) else "/usr/bin/fping"
