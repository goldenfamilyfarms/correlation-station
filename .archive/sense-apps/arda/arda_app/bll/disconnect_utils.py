import logging
from typing import Any, Dict, Union, List, Tuple

from arda_app.bll.net_new.utils.shelf_utils import switch_sites_for_each_side
from arda_app.bll.utils import compare_ipv6_addresses, compare_models, compare_ipv4_addresses_and_cidr_notation
from common_sense.common.errors import abort
from arda_app.common.truck_roll_list import truck_roll_list
from arda_app.dll.granite import get_path_elements_l1
from arda_app.dll.granite import paths_from_site, get_circuit_site_info, get_circuit_uda_info, get_used_equipment_ports

from copy import deepcopy

logger = logging.getLogger(__name__)


def full_disco_check(job_type: str, path_elements: List[Dict], z_side_cpe_model: str) -> Tuple[str, str]:
    """
    Check if full discovery is required based on the job type, path elements, and CPE model.

    Parameters:
    - job_type: Type of the job
    - path_elements: List of path elements
    - z_side_cpe_model: CPE model information

    Returns:
    - Tuple containing information if hub work is required and if CPE installer is needed.
    """
    hub_work_required = "No"
    cpe_installer_needed = "No"

    if job_type == "full":
        hub_work_required = "Yes"

        for element in path_elements:
            z_site_type = element.get("PATH_Z_SITE_TYPE", None)

            if z_site_type is None:
                logger.error("No Z Site Type in Path Elements")
                abort(500, "No Z Site Type in Path Elements.")

            if z_site_type.lower() == "active mtu":
                hub_work_required = "No"
                break

        if z_side_cpe_model.upper() in truck_roll_list:
            cpe_installer_needed = "Yes"

    return hub_work_required, cpe_installer_needed


def get_db_data_for_e_access(granite_l1_data: List[Dict], granite_l2_data: List[Dict]) -> Tuple[str, Dict[str, str]]:
    """
    Retrieve EVC ID and router IPV4 addresses on either side of the MPLS.

    Parameters:
    - granite_l1_data: List of L1 data
    - granite_l2_data: List of L2 data

    Returns:
    - Tuple containing the EVC ID and a dictionary mapping router name to its IPV4 address.
    evc_id, router_connection_ips = "457663", {
        "a_side_router": "ipv4 of z_side_router",
        "z_side_router": "ipv4 of a_side_router",
    }
    """
    # find EVC ID for E-Access circuit
    evc_id = granite_l1_data[0].get("EVC_ID")

    if not evc_id:
        abort(500, "Unable to retrieve EVC ID")
    logger.debug(f"evc_id - {evc_id}")
    # find the sequence number of the MPLS using L1 pathElements call
    sequence = None

    for elem in granite_l1_data:
        if "MPLS" in elem.get("ELEMENT_CATEGORY"):
            sequence = elem.get("SEQUENCE")
            break

    if not sequence:
        abort(500, "Unable to locate MPLS object")
    logger.debug(f"sequence - {sequence}")
    # look for parent sequence numbers of the routers closest to MPLS using L2 pathElements call
    a_side_router = None
    a_side_ip = None
    z_side_router = None
    z_side_ip = None
    a_router_found = False
    z_router_found = False

    for elem in granite_l2_data:
        if elem.get("PATH_STATUS").upper() == "LIVE":
            parent_sequence_value = elem.get("PARENT_SEQUENCE") if elem.get("PARENT_SEQUENCE") else elem.get("SEQUENCE")

            if (
                (not a_router_found)
                and (elem.get("ELEMENT_CATEGORY") == "ROUTER")
                and (parent_sequence_value < sequence)
            ):
                a_side_router = elem.get("TID")
                a_side_ip = elem.get("IPV4_ADDRESS").split("/")[0]
                a_router_found = True
            elif (
                (not z_router_found)
                and (elem.get("ELEMENT_CATEGORY") == "ROUTER")
                and (parent_sequence_value > sequence)
            ):
                z_side_router = elem.get("TID")
                z_side_ip = elem.get("IPV4_ADDRESS").split("/")[0]
                z_router_found = True

            if all([a_router_found, z_router_found]):
                break

    # construct response object containing the IPs of each router on either side of the MPLS
    data = [a_side_router, a_side_ip, z_side_router, z_side_ip]

    if not all(data):
        data_values = {
            "A side router TID": a_side_router,
            "A side router IP": a_side_ip,
            "Z side router TID": z_side_router,
            "Z side router IP": z_side_ip,
        }
        missing = []

        for k, v in data_values.items():
            if not v:
                missing.append(k)

        if missing:
            logger.debug(f"Missing data for E-Access order - {missing}")
            abort(500, f"Missing data for E-Access order - {missing}")
    # please note the pairing between a router and the IP of the router it's connected with across the MPLS
    router_connection_ips = {a_side_router: z_side_ip, z_side_router: a_side_ip}
    logger.debug(f"router_connection_ips - {router_connection_ips}")
    return evc_id, router_connection_ips


def get_db_data_for_cid(cid: str, devices: Dict[str, str], path_elements: List[Dict]) -> Tuple:
    """
    Obtain database data for the specified CID.

    Parameters:
    - cid: The CID value
    - devices: Dictionary of devices
    - path_elements: List of path elements

    Returns:
    - Tuple with database related information for the CID.
    """
    # obtain list of hostnames making up circuit from input
    if (not cid) and (not devices):
        abort(500, "Unexpected values for input parameters CID and devices")
    elif not cid:
        abort(500, "Unexpected value for input parameter CID")
    elif not devices:
        abort(500, "Unexpected value for input parameter devices")
    logger.debug(f"cid - {cid}")
    logger.debug(f"devices - {devices}")
    dev_list = [[k, v] for k, v in devices.items()]
    logger.debug(f"dev_list - {dev_list}")

    # ensure order of devices from the data center to the customer location is followed
    processed_dev_list = []
    ordered_dev_list = []

    for elem in path_elements:
        if elem.get("LVL") == "2" and elem.get("TID"):
            if elem.get("TID") not in processed_dev_list and elem.get("TID") in devices.keys():
                processed_dev_list.append(elem.get("TID"))

    for dev in processed_dev_list:
        ordered_dev_list.append([dev, devices.get(dev)])

    logger.debug(f"ordered_dev_list - {ordered_dev_list}")

    # pull circuit data from db
    granite_l1_data = []
    granite_l2_data = []

    for elem in path_elements:
        if elem.get("LVL") == "1":
            granite_l1_data.append(elem)
        elif elem.get("LVL") == "2":
            granite_l2_data.append(elem)

    if not granite_l1_data:
        abort(500, f"Unable to acquire L1 data for {cid}")
    if not granite_l2_data:
        msg = f"Unable to acquire L2 data for {cid}"
        logger.error(msg)
        abort(500, msg)

    # save specific circuit data to use
    vlan_id = None

    for elem in granite_l1_data:
        if (elem.get("CHAN_NAME")) and (elem.get("ELEMENT_CATEGORY") == "ETHERNET TRANSPORT"):
            vlan_id = elem.get("CHAN_NAME").replace("VLAN", "")
            break
    else:
        msg = f"Unable to acquire VLAN ID for {cid}"
        logger.error(msg)
        abort(500, msg)

    logger.debug(f"vlan_id - {vlan_id}")
    ipv4_assigned_subnets = granite_l1_data[1].get("IPV4_ASSIGNED_SUBNETS")
    logger.debug(f"ipv4_assigned_subnets - {ipv4_assigned_subnets}")
    ipv4 = granite_l1_data[1].get("IPV4_ASSIGNED_GATEWAY", None)
    logger.debug(f"ipv4 - {ipv4}")
    ipv4_glue_subnet = granite_l1_data[1].get("IPV4_GLUE_SUBNET")

    if ipv4_glue_subnet:
        last_octet_static_ip = str(int(ipv4_glue_subnet.split("/")[0].split(".")[-1]) + 1)
        octets = ipv4_glue_subnet.split("/")[0].split(".")
        ipv4_glue_subnet = f"{'.'.join(octets[0:-1])}.{last_octet_static_ip}"
        ipv4 = ipv4_glue_subnet + "/30"

    logger.debug(f"ipv4_assigned_subnets - {ipv4_glue_subnet}")
    ipv4_service_type = granite_l1_data[1].get("IPV4_SERVICE_TYPE", None)
    logger.debug(f"ipv4_service_type - {ipv4_service_type}")
    ipv6 = granite_l1_data[1].get("IPV6_GLUE_SUBNET", None)
    logger.debug(f"ipv6 - {ipv6}")

    service_type = granite_l1_data[1].get("SERVICE_TYPE", "")
    logger.debug(f"service_type - {service_type}")
    ipv4_assigned_subnet = granite_l1_data[1].get("IPV4_ASSIGNED_SUBNETS")
    logger.debug(f"ipv4_assigned_subnet - {ipv4_assigned_subnet}")
    ipv4_glue_subnet = granite_l1_data[1].get("IPV4_GLUE_SUBNET")
    logger.debug(f"ipv4_glue_subnet - {ipv4_glue_subnet}")

    return (
        ordered_dev_list,
        vlan_id,
        ipv4,
        ipv4_service_type,
        ipv6,
        granite_l1_data,
        granite_l2_data,
        service_type,
        ipv4_assigned_subnet,
        ipv4_glue_subnet,
    )


def get_aw_device(tid: str, granite_data: List[Dict]) -> List[Dict]:
    """
    Retrieve the AW devices from the provided granite data based on tid.

    Parameters:
    - tid: The target TID value
    - granite_data: List of devices from granite data

    Returns:
    - List of AW devices.
    """
    aw_devices = []

    for device in granite_data:
        if device["tid"][-2:] == "AW" and device["tid"][:7] in tid:
            aw_devices.append(device)

    return aw_devices


def get_zw_device(tid: str, granite_data: List[Dict]) -> List[Dict]:
    """
    Retrieve the ZW devices from the provided granite data based on tid.

    Parameters:
    - tid: The target TID value
    - granite_data: List of devices from granite data

    Returns:
    - List of ZW devices.
    """
    zw_devices = []

    for device in granite_data:
        if device["tid"][-2:] == "ZW" and device["tid"][:7] in tid:
            zw_devices.append(device)

    return zw_devices


def get_cisco_network_configs(tid: str) -> Dict[str, str]:
    """
    Placeholder function to get network configurations for Cisco devices based on tid.

    Parameters:
    - tid: The target TID value

    Returns:
    - Dictionary with the TID and other info.
    """
    return {"tid": tid, "vendor": "", "model": "", "vlan_id": "", "port_id": "", "description": False}


def compare_network_and_granite(
    db_dev_list: List[Dict], network_dev_list: List[Dict], skip_tids: List[str] = None, vgw_ipv4: str = "", cid: str = ""
) -> Union[Dict[str, list], bool]:
    if skip_tids is None:
        skip_tids = []
    """
    Compare the network device list and the granite database device list.

    Parameters:
    - db_dev_list: List of devices from the database
    - network_dev_list: List of devices from the network

    Returns:
    - Dictionary with differences if any, otherwise True.
    [
        "Granite Data",
        [
            {
                "tid": "ROCHNYXA1ZW",
                "port_id": "GE-0/3/4",
                "vendor": "JUNIPER",
                "model": "MX480",
                "vlan_id": "565",
                "description": true,
                "evc_id": "457663",
                "e_access_ip": "24.58.26.82"
            },
            {
                "tid": "BFLONYKK1CW",
                "port_id": "AE17",
                "vendor": "JUNIPER",
                "model": "MX960",
                "vlan_id": "565",
                "description": true,
                "evc_id": "457663",
                "e_access_ip": "24.58.26.88"
            },
            {
                "tid": "BFLONYKK0QW",
                "port_id": "XE-0/0/55",
                "vendor": "JUNIPER",
                "model": "QFX5100-96S",
                "vlan_id": "565",
                "description": true
            },
            {
                "tid": "BFLONYGO1AW",
                "port_id": "ETH PORT 0/5",
                "vendor": "RAD",
                "vlan_id": "565",
                "description": true,
                "model": "ETX-2I-10G/4SFPP/4SFP4UTP"
            },
            {
                "tid": "BFLONYGO6ZW",
                "port_id": "ETH PORT 5",
                "vendor": "RAD",
                "model": "ETX203AX/2SFP/2UTP2SFP",
                "vlan_id": "565",
                "description": true,
            }
        ],
        "Network Data",
        [
            {
                "description": true,
                "tid": "ROCHNYXA1ZW",
                "port_id": "GE-0/3/4",
                "vendor": "JUNIPER",
                "model": "MX480",
                "vlan_id": "565",
                "evc_id": "457663",
                "e_access_ip": "24.58.26.82"
            },
            {
                "description": true,
                "tid": "BFLONYKK1CW",
                "port_id": "AE17",
                "vendor": "JUNIPER",
                "model": "MX960",
                "vlan_id": "565",
                "evc_id": "457663",
                "e_access_ip": "24.58.26.88"
            },
            {
                "description": true,
                "tid": "BFLONYKK0QW",
                "port_id": "XE-0/0/55",
                "vendor": "JUNIPER",
                "model": "QFX5100-96S",
                "vlan_id": "E565"
            },
            {
                "tid": "BFLONYGO1AW",
                "vendor": "RAD",
                "model": "ETX-2I-10G/4SFPP/4SFP4UTP",
                "vlan_id": "565",
                "port_id": "ETH PORT 0/5",
                "description": false
            },
            {
                "tid": "BFLONYGO6ZW",
                "vendor": "",
                "model": "",
                "vlan_id": "565",
                "port_id": "",
                "description": true
            }
        ]
    ]

    """
    # Convert the lists into dictionaries for faster lookup
    db_dev_dict = {dev["tid"]: dev for dev in db_dev_list if dev["tid"] not in skip_tids}
    # should we remove None from the list

    while None in network_dev_list:
        network_dev_list.remove(None)

    network_dev_dict = {dev["tid"]: dev for dev in network_dev_list if dev["tid"] not in skip_tids}

    # Check if all tids in db_dev_list are present in network_dev_list
    if set(db_dev_dict.keys()) != set(network_dev_dict.keys()):
        return False

    mismatch_list = {"Granite Data": [], "Network Data": []}

    # Compare the attributes for each device based on the tid
    for tid in db_dev_dict.keys():
        db_dev = db_dev_dict[tid]
        network_dev = network_dev_dict[tid]
        dev1 = deepcopy(db_dev)
        dev2 = deepcopy(network_dev)

        # Check each attribute for differences and add to the mismatch list if they don't match
        for key in db_dev.keys():
            if key == "tid":
                continue

            if key == "ipv4" and vgw_ipv4 and db_dev["tid"].endswith("CW"):
                if compare_ipv4_addresses_and_cidr_notation(db_dev.get(key), network_dev.get(key), cid, vgw_ipv4):
                    dev1.pop(key, None)  # Using None as the default value to handle missing keys
                    dev2.pop(key, None)  # Using None as the default value to handle missing keys
                if db_dev.get(key) is None and network_dev.get(key) is None:
                    dev1.pop(key, None)  # Using None as the default value to handle missing keys
                    dev2.pop(key, None)  # Using None as the default value to handle missing keys
                continue

            if key == "ipv6":
                if compare_ipv6_addresses(db_dev.get(key), network_dev.get(key)):
                    dev1.pop(key, None)  # Using None as the default value to handle missing keys
                    dev2.pop(key, None)  # Using None as the default value to handle missing keys
                if db_dev.get(key) is None and network_dev.get(key) is None:
                    dev1.pop(key, None)  # Using None as the default value to handle missing keys
                    dev2.pop(key, None)  # Using None as the default value to handle missing keys
                continue

            if key == "model":
                if db_dev.get(key) == network_dev.get(key):
                    dev1.pop(key, None)  # Using None as the default value to handle missing keys
                    dev2.pop(key, None)  # Using None as the default value to handle missing keys
                elif compare_models(db_dev.get(key), network_dev.get(key)):
                    dev1.pop(key, None)  # Using None as the default value to handle missing keys
                    dev2.pop(key, None)  # Using None as the default value to handle missing keys
                continue

            if db_dev.get(key) == network_dev.get(key):
                dev1.pop(key, None)  # Using None as the default value to handle missing keys
                dev2.pop(key, None)  # Using None as the default value to handle missing keys

        # Add the mismatched items to the result only if they have any mismatched fields (not for TID field)
        if len(dev1) > 1 or len(dev2) > 1:
            mismatch_list["Granite Data"].append(dev1)
            mismatch_list["Network Data"].append(dev2)

    # Check if "Granite Data" or "Network Data" not empty
    if mismatch_list.get("Granite Data") or mismatch_list.get("Network Data"):
        return mismatch_list

    return True


def get_circuit_device_data_from_db(
    cid: str, devices: Dict[str, str], path_elements: Any
) -> Tuple[List[Dict[str, Union[str, bool, Any]]], str, str, str, str]:
    """
    Fetch circuit device data from the database.

    Args:
        cid (str): The circuit identifier. E.g., '71.L1XX.026306..TWCC'
        devices (Dict[str, str]): Mapping of device TID to its port id.
                                  E.g., {'ROCHNYXA1ZW': 'GE-0/3/4'}
        path_elements (Any): Granite pathElements API

    Returns:
        tuple:
        - device_list (List[Dict[str, Union[str, bool, Any]]]): A list of device profiles containing
          tid, port_id, vendor, vlan_id, description, model, and other related information.
        - ipv4 (str): The IPv4 address
        - ipv4_service_type (str): The IPv4 service type
        - ipv4_assigned_subnet (str): Assigned subnet for IPv4
        - ipv4_glue_subnet (str): Glue subnet for IPv4

    Example:
        Output:

        devices = {
            'ROCHNYXA1ZW': 'GE-0/3/4',
            'BFLONYGO6ZW': 'ETH PORT 5',
            'BFLONYKK1CW': 'AE17',
            'BFLONYKK0QW': 'XE-0/0/55',
            'BFLONYGO1AW': 'ETH PORT 0/5'
        }

        path_elements = Granite pathElements API

    output:
        device_list = [{
            "tid": "ROCHNYXA1ZW",
            "port_id": "GE-0/3/4",
            "vendor": "JUNIPER",
            "vlan_id": "565",
            "description": True,
            "model": "MX480",
            "evc_id": "457663",
            "e_access_ip": "24.58.26.82"
        }, {
            "tid": "BFLONYKK1CW",
            "port_id": "AE17",
            "vendor": "JUNIPER",
            "vlan_id": "565",
            "description": True,
            "model": "MX960",
            "evc_id": "457663",
            "e_access_ip": "24.58.26.88"
        }, {
            "tid": "BFLONYKK0QW",
            "port_id": "XE-0/0/55",
            "vendor": "JUNIPER",
            "vlan_id": "565",
            "description": True,
            "model": "QFX5100-96S"
        }, {
            "tid": "BFLONYGO1AW",
            "port_id": "ETH PORT 0/5",
            "vendor": "RAD",
            "vlan_id": "565",
            "description": True,
            "model": "ETX-2I-10G/4SFPP/4SFP4UTP"
        }, {
            "tid": "BFLONYGO6ZW",
            "port_id": "ETH PORT 5",
            "vendor": "RAD",
            "vlan_id": "565",
            "description": True,
            "model": "ETX203AX/2SFP/2UTP2SFP"
        }]
    """
    (
        ordered_dev_list,
        vlan_id,
        ipv4,
        ipv4_service_type,
        ipv6,
        granite_l1_data,
        granite_l2_data,
        service_type,
        ipv4_assigned_subnet,
        ipv4_glue_subnet,
    ) = get_db_data_for_cid(cid, devices, path_elements)

    # retrieve additional data for E-Access CIDs
    if "E-ACCESS" in service_type:
        evc_id, router_connection_ips = get_db_data_for_e_access(granite_l1_data, granite_l2_data)

    # create a profile for each device in the circuit
    device_list = []

    for dev_data in ordered_dev_list:
        device = {}
        device["tid"] = dev_data[0]
        device["port_id"] = dev_data[1]
        device["vendor"] = ""
        device["vlan_id"] = vlan_id
        device["description"] = True

        for dev in granite_l2_data:
            if dev.get("TID") == dev_data[0]:
                device["vendor"] = dev.get("VENDOR")
                device["model"] = dev.get("MODEL")
                _model_check(device["model"])

                if dev.get("TID")[-2:] == "CW" and ("E-ACCESS" not in service_type):
                    if "EPLAN" in service_type:
                        device["evc_id"] = get_evc_id(cid)
                        device["encapsulation"] = "vlan-vpls"
                    else:
                        device["ipv4"] = ipv4
                        device["ipv6"] = ipv6

                        if ipv4_service_type == "ROUTED":
                            device["IPV4_ASSIGNED_SUBNETS"] = ipv4_assigned_subnet
                            device["IPV4_GLUE_SUBNET"] = ipv4_glue_subnet
                elif (dev.get("TID")[-2:] in ("CW", "ZW")) and ("E-ACCESS" in service_type):
                    if dev.get("ELEMENT_CATEGORY") == "ROUTER":
                        device["evc_id"] = evc_id
                        device["e_access_ip"] = router_connection_ips.get(dev.get("TID", ""), "")

                device_list.append(device)  # save device profile in a list to return
                break
        else:
            device_list.append(device)  # placeholder for device that was NOT found in db
            # Please note: this device will NOT have a vendor

    logger.debug(f"device_list - {device_list}")
    return device_list, ipv4, ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet


def get_evc_id(cid: str) -> str:
    path_elements_l1 = get_path_elements_l1(cid)
    return path_elements_l1[0].get("EVC_ID")


def _model_check(model: str):
    supported_models = [
        "ACX5448",
        "ASR 9001",
        "ASR 9006",
        "ASR 9010",
        "ASR-920-4SZ-A",
        "MX240",
        "MX480",
        "MX960",
        "QFX5100-48S",
        "QFX5100-96S",
        "EX4200-24F",
        "EX4200-24T",
        "EX4200-48T",
        "FSP 150CC-GE114/114S",
        "FSP 150-GE114PRO-C",
        "FSP 150-XG116PRO",
        "FSP 150-XG116PROH",
        "FSP 150-XG120PRO",
        "ETX203AX/2SFP/2UTP2SFP",
        "ETX-203AX/GE30/2SFP/4UTP",
        "ETX-220A",
        "ETX-2I-10G-B/8.5/8SFPP",
        "ETX-2I-10G-B/19/8SFPP",
        "ETX-2I-10G/4SFPP/4SFP4UTP",
        "ETX-2I-10G/4SFPP/24SFP",
        "ME-3400-24TS",
        "ME-3400E-24TS-M",
        "ME-3400-12CS",
        "ME-3400-EG-12CS-M",
        "ME-3400-2CS",
        "ME-3400EG-2CS-A",
    ]

    if model not in supported_models:
        abort(500, f"Unsupported model in the circuit path: {model}")


def is_vgw_installer_needed(vgw_model: str) -> str:
    """
    Determine if a truck roll is needed to recover a VGW shelf
    https://chalk.charter.com/spaces/SESE/pages/1072520684/CND+-+CPE+Truck+Roll+List+for+Disconnects
    Living document of models we need to mark as cpe_installer_needed = "Yes"
    Model names are not exact match of Granite. Must use Granite version.

    Arg:
        vgw_model (str): VGW device model

    Returns:
        str indicating if a VGW installer is needed, based on a VGW device model search and match
        ex. "Yes" a truck roll is needed for a VGW shelf
            "No" a truck roll is not needed for a VGW shelf
    """
    vgw_installer_needed = "No"

    # search to see if a vgw device model needs a truckroll based on a model match
    if vgw_model in truck_roll_list:
        vgw_installer_needed = "Yes"

    return vgw_installer_needed


def get_job_type(cid: str, cpe: str, docsis_or_mne=False, switch_sides=False) -> str:
    """If the decommission date is missing for two or more, return partial, otherwise return full."""
    circuit_site_info = get_circuit_site_info(cid=cid)[0]
    circuit_uda_info = get_circuit_uda_info(cid=circuit_site_info["CIRC_PATH_INST_ID"])

    # for EPL (Fiber) circuits, since current BAU logic is to process the Z-side of an order
    # if processing is needed on the A-side, "swap sides" to allow processing to continue
    if switch_sides:
        switch_site_info = deepcopy([circuit_site_info])
        circuit_site_info = switch_sites_for_each_side(switch_site_info)
        circuit_site_info = circuit_site_info[0]

    site = circuit_site_info["Z_SITE_NAME"]
    vc_class = [circuit for circuit in circuit_uda_info if circuit.get("ATTR_VALUE", "") == "TYPE 2"]
    if vc_class:
        abort(500, "TYPE 2 is unsupported at this time")
    if not cpe:
        abort(500, "No ZW device found")

    if docsis_or_mne:
        paths = paths_from_site(site)

        if isinstance(paths, list):
            count = 0

            # counting number of CIDs related to site in granite
            for path in paths:
                if any(("TWCC" in path.get("PATH_NAME").upper(), "CHTR" in path.get("PATH_NAME").upper())):
                    count += 1

            if count == 1:
                return "full"
            elif count > 1:
                return "partial"

        msg = f"Unable to determine the enginnering job type. No paths related to site name: {site} in granite"
        abort(500, msg)

    circuits = get_used_equipment_ports(cpe)

    # GET a unique list of CURRENT_PATH_NAME ending in "CHTR or TWCC"
    # Exclude the main circuit from path names
    path_names = {
        circuit.get("CURRENT_PATH_NAME", circuit.get("NEXT_PATH_NAME"))
        for circuit in circuits
        if _path_match(cid, cpe, circuit.get("CURRENT_PATH_NAME", circuit.get("NEXT_PATH_NAME", "")))
    }

    # GET all circuit sites
    circuit_sites = [site_info for path in path_names for site_info in get_circuit_site_info(path)]

    # GET circuit sites with a status of "Pending Decommission"
    decom_sites = [site for site in circuit_sites if site["CIRCUIT_STATUS"] == "Pending Decommission"]

    # if number of sites without a status of "Pending Decommission" is zero, return full
    if (len(circuit_sites) - len(decom_sites)) == 0:
        return "full"

    # if number of sites without a status of "Pending Decommission" is one ore more, return partial
    return "partial"


def _path_match(cid: str, zw: str, path_name: str) -> bool:
    """True if the in-use CPE port is assigned to a path that needs to be included in determining full or partial"""
    match_list = [f".{zw}.", "TWCC", "CHTR"]
    if any(cid not in path_name and match in path_name for match in match_list):
        return True
    return False
