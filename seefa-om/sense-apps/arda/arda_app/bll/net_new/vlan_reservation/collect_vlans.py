import logging

from common_sense.common.errors import abort

from arda_app.bll.net_new.vlan_reservation.vlan_utils import get_circuit_tid_ports, get_nni_tid_port
from arda_app.bll.utils import get_4_digits, get_special_char
from arda_app.dll.granite import get_granite, get_device_vendor, get_device_model
from arda_app.dll.mdso import onboard_and_exe_cmd

logger = logging.getLogger(__name__)


def check_primary_vlan(network_vlans, granite_vlans, primary_vlan):
    error_message = f"VLAN {primary_vlan} is already in use"
    if str(primary_vlan) in network_vlans:
        error_message += " in network vlans"
    elif str(primary_vlan) in granite_vlans:
        error_message += " in granite vlans"
    else:
        return primary_vlan

    abort(500, message=error_message)


def get_next_available_vlan_or_subinterface(
    network_vlans: set, granite_vlans: set, product_name, primary_vlan="", type2=False, outer_vlan=False
):
    vlans = set()
    vlans.update(network_vlans, granite_vlans)

    if primary_vlan and primary_vlan.isdigit() and product_name != "FC + Remote PHY":
        check_reserved_vlans(primary_vlan)
        return check_primary_vlan(network_vlans, granite_vlans, int(primary_vlan))

    vlan_range = []
    if outer_vlan:
        vlan_range = list(range(5, 4000))
    elif product_name in ("Fiber Internet Access", "Carrier Fiber Internet Access"):
        if type2:
            vlan_range = list(range(11000, 12000))
        else:
            vlan_range = list(range(1100, 1200)) + list(range(1500, 3000))
    elif product_name in ("Hosted Voice - (Fiber)"):
        vlan_range = list(range(1300, 1400)) + list(range(1500, 3000))
    elif product_name in {
        "SIP - Trunk (Fiber)",
        "SIP Trunk(Fiber) Analog",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
    }:
        vlan_range = list(range(1300, 1400))
    elif product_name == "Carrier E-Access (Fiber)":
        if primary_vlan and primary_vlan.isdigit():
            return check_primary_vlan(network_vlans, granite_vlans, int(primary_vlan))
        else:
            vlan_range = list(range(1200, 1300)) + list(range(1400, 1500))
    elif product_name == "FC + Remote PHY":
        vlan_range = [primary_vlan] + [f"{primary_vlan}-{i}" for i in range(1, 101)]
    elif product_name in ("EP-LAN (Fiber)", "EPL (Fiber)"):
        vlan_range = list(range(1200, 1300))
    else:
        abort(500, message=f"Product name error: {product_name}.")

    for vlan in vlan_range:
        if str(vlan) not in vlans:
            return vlan

    abort(500, message=f"No available VLAN found in range: {vlan_range[1]}-{vlan_range[-1]}.")


def get_granite_vlans(transport_paths, primary_vlan="", type2=False, outer_vlan=False) -> set:
    """Pull available VLANs from Granite transport paths"""
    granite_vlan_list = []
    min_vlan = primary_vlan if primary_vlan and primary_vlan.isdigit() else "1100"
    max_vlan = primary_vlan if primary_vlan and primary_vlan.isdigit() else "4063"

    for path in transport_paths:
        logger.info(f"Pulling VLAN data from Granite for {path}")

        if outer_vlan:
            element = path["PATH_NAME"]  # get NNI id
        else:
            element = path["ELEMENT_NAME"]  # get transport path

        if type2:
            granite_get_url = f"/pathChanAvailability?PATH_NAME={element}"
        else:
            granite_get_url = (
                f"/pathChanAvailability?PATH_NAME={element}&MIN_VLAN={min_vlan}&MAX_VLAN={max_vlan}&MAX_FETCH=3000"
            )
        granite_response = get_granite(granite_get_url)
        logger.info(f"Granite pathChanAvailaility response for {element} VLAN lookup: \n{granite_response}")
        granite_vlans = granite_response

        # TODO: check list functionality for duplicates (handled by python?)
        if "retString" in granite_response:
            continue
        else:
            for v in granite_vlans:
                channel_name = v["CHAN_NAME"]
                # for an outer vlan request, make sure to skip vlans prefixed with "VLAN"
                if channel_name[0:4].upper() == "VLAN" and (not outer_vlan):
                    if "4063" in channel_name:
                        vlan = channel_name.split("VLAN")[1]
                        granite_vlan_list.append(vlan)
                    elif any(not c.isalnum() for c in channel_name):
                        name = channel_name.replace(get_special_char(channel_name), "")
                        vlan = get_4_digits(name)
                        if vlan:
                            # if int(vlan) in list(range(1100, 1200)):
                            granite_vlan_list.append(vlan)
                    elif any(c.isalnum() for c in channel_name):
                        vlan = get_4_digits(channel_name)
                        if vlan:
                            # if int(vlan) in list(range(1100, 1200)):
                            granite_vlan_list.append(vlan)
                # This is for type II
                elif len(channel_name.split(":")[0]) == 5:
                    # expand range of subinterfaces to check for existing ethernet services
                    if int(channel_name.split(":")[0]) in list(range(11000, 14000)):
                        if "OV" in channel_name.upper() and outer_vlan:
                            if "//" in channel_name:
                                vlan = channel_name.split("//")[0]
                                if "-" in vlan:
                                    vlan = vlan.split("-")[1]
                                else:
                                    vlan = vlan.split("OV")[1]
                            else:
                                continue
                        else:
                            vlan = channel_name.split(":")[0]
                        granite_vlan_list.append(vlan)
                else:
                    continue

    logger.info(f"Granite VLAN assignments compiled: \n{granite_vlan_list}")

    return {str(vlan) for vlan in granite_vlan_list if vlan}


def get_network_vlans(cid, attempt_onboarding, path_instid, type2=False):
    """Pull available VLANs from MDSO"""
    devices = get_circuit_tid_ports(cid, path_instid)
    # Run commands and find vlans from MDSO
    logger.info(f"Executing MDSO port config lookup for circuit {cid}")
    return _get_device_vlans(devices, type2, attempt_onboarding)


def get_network_outer_vlans(nni, attempt_onboarding, type2=False):
    """Pull available VLANs from MDSO"""
    outer_vlan = True
    device = get_nni_tid_port(nni)
    # Run commands and find vlans from MDSO
    logger.info(f"Executing MDSO port config lookup for circuit {nni}")
    return _get_device_vlans(device, type2, attempt_onboarding, outer_vlan)


def get_network_interfaces(cid, attempt_onboarding, path_instid, type2=True):
    """Pull available VLANs from MDSO"""
    devices = get_circuit_tid_ports(cid, path_instid)
    # Run commands and find vlans from MDSO
    logger.info(f"Executing MDSO port config lookup for circuit {cid}")
    return _get_device_vlans(devices, type2, attempt_onboarding)


def _get_device_vlans(devices: dict, type2: bool, attempt_onboarding, outer_vlan=False) -> set:
    """Add vlans to a unique set"""
    vlans = set()
    mdso_commands = {
        "CISCO": "get-interface-used-vlan-ids.json",
        "JUNIPER": {"MX": "show_interfaces", "QFX/ACX": "agg_vlans"},
        "RAD": "rad_classifiers",
    }
    for host, port in devices.items():
        is_cw = False
        vendor = get_device_vendor(host)
        model = get_device_model(host)

        # ADVA devices are not supported
        if vendor == "ADVA":
            # Skipping...
            continue

        # CISCO devices with host name ending in "ZW" are not supported
        if vendor == "CISCO" and host.endswith("ZW"):
            # Skipping...
            continue
        elif vendor == "CISCO" and host.endswith("CW"):
            port = port.capitalize()

        if "MX" in model and vendor == "JUNIPER":
            is_cw = True
            port = port.lower()

        # Set MDSO command
        mdso_command = ""

        if vendor == "JUNIPER":
            if is_cw:
                mdso_command = mdso_commands[vendor]["MX"]
            else:
                mdso_command = mdso_commands[vendor]["QFX/ACX"]
        elif vendor in ("RAD", "CISCO"):
            mdso_command = mdso_commands[vendor]
        else:
            msg = f"The vendor {vendor} is currently unsupported for VLAN Reservation. Please investigate"
            abort(500, msg)

        # Run MDSO
        mdso_response = onboard_and_exe_cmd(
            command=mdso_command, parameter=port, hostname=host, timeout=120, attempt_onboarding=attempt_onboarding
        )

        vlans.update(_filter_mdso_response(vendor, mdso_response, is_cw, host, port, type2, outer_vlan))

    return vlans


def _filter_mdso_response(
    vendor: str, mdso_response: dict, is_cw: bool, host: str, port: str, type2: bool, outer_vlan=False
):
    """Filter MDSO response for vlans"""
    if vendor == "RAD":
        return [
            property["properties"]["match"][0].split(" ")[-1]
            for property in mdso_response["result"]
            if "OUT" in property["properties"]["name"].upper()
        ]
    elif vendor == "CISCO":
        return mdso_response["result"]
    elif vendor == "JUNIPER":
        if is_cw:
            try:
                response = mdso_response["result"]["data"]["configuration"]["interfaces"]["interface"].get("unit")
            except Exception:
                abort(500, f"Unexpected MDSO response for port: {port} on host: {host}")

            if not response:
                abort(500, f"CW: {host} port: {port} - no units configured")

            if isinstance(response, list):
                if type2 and outer_vlan:
                    try:
                        return [
                            vlan["vlan-tags"]["outer"]
                            for vlan in response
                            if vlan.get("name", "").startswith("11") and len(vlan["name"]) == 5
                        ]
                    except Exception:
                        msg = f"Unable to retrieve outer vlan tag from {host}: {port}"
                        logger.error(msg)
                        abort(500, msg)
                elif type2:
                    return [
                        vlan["name"]
                        for vlan in response
                        if vlan.get("name", "").startswith("11") and len(vlan["name"]) == 5
                    ]

                return [vlan["vlan-id"] for vlan in response if vlan.get("vlan-id")]
            elif isinstance(response, dict):
                # Possibly no config on port, get call to resolve key error
                return [response.get("vlan-id", "")]

        return [vlan["vlan-id"] for _, vlan in mdso_response["result"].items() if vlan.get("vlan-id")]
    else:
        abort(500, f"Vendor {vendor} not supported")


def check_reserved_vlans(vlan):
    # reserve_vlan = list(range(0, 88)) + list(range(89, 99)) + list(range(100, 1000)) + list(range(4000, 4091))
    reserve_vlan = [0, 1, 88, 99, 4000, 4001]

    if int(vlan) in reserve_vlan:
        logger.error(f"Primary VLAN: {vlan} is a reserved VLAN")
        abort(500, f"Primary VLAN: {vlan} is a reserved VLAN. Please investigate")

    return
