from arda_app.dll.mdso import onboard_and_exe_cmd
from common_sense.common.errors import abort


def validate_customer_vlan_on_network(customer_vlan: str, devices: dict, cid: str):
    """Get port configs of underlay devices up to but not including the ZW CPE (CW, QW, AW)
    and verify the customer VLAN is configured on the downstream port (towards customer handoff)\n
    :param cid: "23.L1XX.989074..CHTR"
    :param customer_vlan: "1100"
    :param devices: response from bll/circuit_design/bandwidth_change/utils/granite_util.py -> device_details()
    """
    for device_type in devices.keys():
        vendor = devices[device_type]["vendor"]
        tid = devices[device_type]["tid"]
        port = devices[device_type]["downstream_port"]
        model = devices[device_type]["model"]
        if vendor == "CISCO":
            abort(500, f"Unsupported hub device vendor: CISCO for TID: {tid}")
        elif vendor == "JUNIPER":
            if "QFX" in model or "EX4200" in model:
                network_vlans = get_vlans_on_qfx_port(tid, port)
                is_customer_vlan_found(customer_vlan, network_vlans, tid, port)
            elif "MX" in model or "ACX" in model:
                network_vlans = get_vlans_on_mx_or_acx_port(tid, port)
                is_customer_vlan_found(customer_vlan, network_vlans, tid, port)
        elif device_type == "AW":
            if vendor == "RAD":
                network_vlans = get_vlans_on_aw_rad_port(tid, port, cid)
                is_customer_vlan_found(customer_vlan, network_vlans, tid, port)
            if vendor == "ADVA" and "116PRO" in model or "120PRO" in model:
                network_vlans = get_vlans_on_aw_adva_port(tid, port)
                is_customer_vlan_found(customer_vlan, network_vlans, tid, port)


def is_customer_vlan_found(customer_vlan: str, network_vlans: list, tid: str, port: str):
    """Look for customer VLAN in provisioned network VLANs and fall out if not found\n
    :param customer_vlan: "1100"
    :param network_vlans: ["1100", "4063"]
    :param tid: "ANHMCAPJ0QW"
    :param port: "xe-0/0/0"
    """
    if not network_vlans:
        abort(500, f"No VLANs found provisioned on device port: {tid} - {port}")
    elif customer_vlan not in network_vlans:
        abort(500, f"Customer VLAN {customer_vlan} not found provisioned on Granite device: {tid} - {port}")


def get_vlans_on_mx_or_acx_port(tid: str, port: str) -> list:
    """Get VLANs provisioned on an MX or ACX port\n
    :param tid: "ANHMCAPJ2CW"
    :param port: "xe-0/0/0" or "AE17"
    :return: ["1100", "4063"]
    """
    network_data = onboard_and_exe_cmd(command="show_interfaces", parameter=port.lower(), hostname=tid, timeout=120)

    if not network_data:
        abort(500, f"Error retrieving network data: {tid} - {port} - show_interfaces")
    else:
        try:
            subinterfaces = network_data["result"]["data"]["configuration"]["interfaces"]["interface"].get("unit")
        except Exception:
            abort(500, f"No interface config found on device port: {tid} - {port}")

        if isinstance(subinterfaces, list):
            return [vlan["vlan-id"] for vlan in subinterfaces if vlan.get("vlan-id")]
        elif isinstance(subinterfaces, dict) and subinterfaces.get("vlan-id"):
            return [subinterfaces["vlan-id"]]
        else:
            return []


def get_vlans_on_qfx_port(tid: str, port: str) -> list:
    """Get VLANs provisioned on a QFX or EX4200 port\n
    :param tid: "ANHMCAPJ0QW"
    :param port: "xe-0/0/0"
    :return: ["1100", "4063"]
    """
    network_data = onboard_and_exe_cmd(command="get_interfaces", parameter=port.lower(), hostname=tid, timeout=120)

    if not network_data:
        abort(500, f"Error retrieving network data: {tid} - {port} - get_interfaces")
    elif network_data["result"].get("configuration"):
        port_vlans = None
        try:
            port_vlans = network_data["result"]["configuration"]["interfaces"][port.lower()]["unit"][0]["family"][
                "ethernet-switching"
            ]["vlan"]["members"]
        except Exception:
            abort(500, f"No VLAN members provisioned on device port: {tid} - {port}")

        if not port_vlans:
            abort(500, f"No VLAN members provisioned on device port: {tid} - {port}")
        elif isinstance(port_vlans, str):
            return sanitize_vlans([port_vlans])
        elif isinstance(port_vlans, list):
            return sanitize_vlans(port_vlans)
    else:
        abort(500, f"No interface config found on device port: {tid} - {port}")


def sanitize_vlans(network_vlans: list) -> list:
    """Remove product type from VLAN name and return just VLAN number as str\n
    :param network_vlans: ["FIA1100", "VIDEO4063"]
    :return: ["1100", "4063"]
    """
    vlans = []
    for vlan in network_vlans:
        vlans.append("".join(filter(str.isdigit, vlan)))
    return vlans


def get_vlans_on_aw_rad_port(tid: str, port: str, cid: str) -> list:
    """Get VLANs provisioned on an AW RAD port\n
    :param tid: "ONTUCACK1AW"
    :param port: "ETH PORT 0/5"
    :return: ["1100", "4063"]
    """
    # First, match the CPE facing port to the CID and get the classifier
    network_data = onboard_and_exe_cmd(command="rad_flows", hostname=tid)

    vlans = []
    if not network_data:
        abort(500, f"Error retrieving RAD network data: {tid} - {port} - rad_flows")
    elif network_data["result"] and isinstance(network_data["result"], list):
        port = port.split()[-1]
        network_flows = network_data["result"]

        classifier_name = ""
        for flow in network_flows:
            if flow["properties"]["ingressPortId"] == port and cid in flow["properties"]["classifierProfile"]:
                classifier_name = flow["properties"]["classifierProfile"]
                break

        # Then get the provisioned VLANs on the classifier
        network_data = onboard_and_exe_cmd(command="rad_classifiers", hostname=tid)

        if not network_data:
            abort(500, f"Error retrieving RAD network data: {tid} - {port} - rad_flows")
        elif network_data["result"] and isinstance(network_data["result"], list):
            network_classifiers = network_data["result"]

            for classifier in network_classifiers:
                if classifier["label"] == classifier_name:
                    vlan = classifier["properties"]["match"][0]
                    return ["".join(filter(str.isdigit, vlan))]
    return vlans


def get_vlans_on_aw_adva_port(tid: str, port: str) -> list:
    """Get VLANs provisioned on an AW ADVA port\n
    :param tid: "CNCTOHQI1AW"
    :param port: "ETH_PORT-1-1-1-3"
    :return: ["1100", "4063"]
    """
    network_data = onboard_and_exe_cmd(command="seefa-cd-list_eth_ports.json", hostname=tid)

    port = port.lower()
    vlans = []
    if not network_data:
        abort(500, f"Error retrieving ADVA network data: {tid} - {port} - seefa-cd-list_eth_ports")
    elif network_data["result"][1]["flow_point"]:
        network_flowpoints = network_data["result"][1]["flow_point"]

        for flow in network_flowpoints:
            if flow["properties"]["vlan_members_list"] not in ["None", "0:4095"]:
                vlans.append(flow["properties"]["vlan_members_list"].split("-")[0])
    return vlans
