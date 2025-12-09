import logging
import ipaddress
from typing import Dict, List, Any, Union

from arda_app.dll.blacklist import is_blacklisted

from arda_app.bll.net_new.utils.shelf_utils import get_vgw_shelf_info
from arda_app.bll.disconnect_utils import (
    compare_network_and_granite,
    full_disco_check,
    get_aw_device,
    get_circuit_device_data_from_db,
    get_job_type,
    get_zw_device,
    is_vgw_installer_needed,
)
from arda_app.bll.logical_change import get_circuit_path_inst_id
from arda_app.bll.models.payloads.disconnect import DisconnectPayloadModel
from arda_app.bll.net_new.utils.shelf_utils import get_circuit_side_info, get_cpe_side_info, get_cpe_at_service_location
from arda_app.bll.net_new.meraki_services import update_meraki_status
from common_sense.common.errors import abort
from arda_app.common.cd_utils import granite_paths_get_url, granite_mne_url
from arda_app.common.utils import path_regex_match
from arda_app.common.products import mne_products
from arda_app.common.truck_roll_list import truck_roll_list
from arda_app.dll.granite import get_granite, get_circuit_uda_info, get_path_elements, get_network_association
from arda_app.dll.mdso import onboard_and_exe_cmd, _get_network_device, get_active_device, get_resource_result
from arda_app.bll.remedy.remedy_ticket import RemedyTicket

logger = logging.getLogger(__name__)


def disconnect(
    payload: DisconnectPayloadModel,
) -> Dict[str, Union[Union[Dict[str, Union[Union[List[Any], bool], Any]], str, Dict[str, Union[str, bool]]], Any]]:
    # if voice product, collect data on a vgw shelf
    voice_products = [
        # "Hosted Voice - (Fiber)",  treat Hosted Voice like FIA
        # "Hosted Voice - (Overlay)",  treat Hosted Voice like FIA
        "Hosted Voice - (DOCSIS)",
        "Hosted Voice - Trunk (DOCSIS)",
        "PRI Trunk (Fiber)",
        "PRI Trunk (DOCSIS)",
        "PRI Trunk(Fiber) Analog",
        "SIP - Trunk (Fiber)",
        "SIP - Trunk (DOCSIS)",
        "SIP Trunk(Fiber) Analog",
    ]

    # Extract CID from SF string
    cid = path_regex_match(payload.cid)
    if isinstance(cid, list) and cid:
        if len(cid) == 1 or payload.product_name in voice_products:
            payload.cid = cid[0]
        else:
            abort(500, f"Multiple different CIDs detected within: {payload.cid}")
    else:
        abort(500, f"Unable to determine CID from: {payload.cid}")

    vgw_ipv4 = ""
    mne = False

    if payload.product_name in voice_products or "Hosted Voice" in payload.product_name:
        vgw_shelf = get_vgw_shelf_info(payload.cid)
        vgw_model = vgw_shelf["MODEL"]
        vgw_installer_needed = is_vgw_installer_needed(vgw_model)
        if "DOCSIS" not in payload.product_name.upper() and vgw_shelf["IPV4_ADDRESS"] != "DHCP":
            # Hosted voice prodcuts below do not need this check
            if payload.product_name not in ("Hosted Voice - (Fiber)", "Hosted Voice - (Overlay)"):
                vgw_ipv4 = vgw_shelf["IPV4_ADDRESS"]
                try:
                    if "/" not in vgw_ipv4:
                        vgw_ipv4 = f"{vgw_ipv4}/32"
                except Exception:
                    abort(500, f"Cannot find vgw ipv4 for circuit: {payload.cid}")

    devices, cpe, circ_path_inst_id, path_elements = get_circuit_tid_ports(payload.cid, payload.product_name)
    skip_network_and_granite_checks = False
    switch_sides = False

    if payload.product_family in mne_products:
        mne = True
        cpe_installer_needed, mne_device = update_mne_status(circ_path_inst_id, path_elements, payload.product_family)

    # for a voice DOCSIS product, designate vgw shelf as a zw device
    docsis_or_mne = False
    if "DOCSIS" in payload.product_name.upper():
        cpe = vgw_shelf["SHELF_NAME"]
        docsis_or_mne = True
    elif payload.product_name in voice_products and not cpe:
        cpe = vgw_shelf["SHELF_NAME"]
    elif mne:
        cpe = mne_device
        docsis_or_mne = True

    # for EPL (Fiber), additional processing to determine correct ZW device at service location
    if payload.product_name.upper() in ("EPL (FIBER)"):
        # collect data about circuit
        circuit_data = get_circuit_side_info(payload.cid)
        cpe_per_side = get_cpe_side_info(devices, path_elements, circuit_data)
        service_loc = (
            payload.service_location_address
            if payload.service_location_address
            else abort(500, "Service location address is undefined")
        )
        # select which ZW device to process based on the service location address
        cpe = get_cpe_at_service_location(service_loc, circuit_data, cpe_per_side)
        cpe_side = list(cpe.keys())[0]
        switch_sides = True if cpe_side == "a_side_cpe" else False
        cpe, cpe_model = list(cpe.values())[0]
        if not all([cpe, cpe_model]):
            msg = f"Unable to retrieve necessary ZW device info located at {service_loc}"
            abort(500, msg)
        # check circuit status to direct business logic
        if circuit_data["status"].upper() == "PENDING DECOMMISSION":
            skip_network_and_granite_checks = True
            result = True
        elif circuit_data["status"].upper() == "LIVE":
            skip_network_and_granite_checks = False
        else:
            msg = f"Unsupported {payload.product_name} circuit status: {circuit_data['status']}"
            abort(500, msg)

    job_type = get_job_type(payload.cid, cpe, docsis_or_mne=docsis_or_mne, switch_sides=switch_sides)

    # No network or blacklist check needed
    if "DOCSIS" in payload.product_name.upper() or mne:
        return {
            "networkcheck": {"passed": True},
            "circ_path_inst_id": circ_path_inst_id,
            "engineering_job_type": job_type,
            "cpe_model": cpe if mne else vgw_model,
            "blacklist": {"passed": True, "ips": []},
            "hub_work_required": "No",
            "cpe_installer_needed": cpe_installer_needed if mne else vgw_installer_needed,
        }

    # Network check
    if not skip_network_and_granite_checks:
        skip_cpe_check = True if all((job_type == "full", cpe.endswith("ZW"))) else False

        (result, cpe_model, ipv4, ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet) = (
            get_comparison_db_and_network_data(
                payload.cid, payload.product_name, devices, path_elements, cpe, skip_cpe_check, vgw_ipv4=vgw_ipv4
            )
        )

    hub_work_required, cpe_installer_needed = full_disco_check(job_type, path_elements, cpe_model)

    # Blacklist check
    blacklisted = []
    blacklist_remedy_inc = ""
    # checking for multiple IP's in granite by count of dots as comma is not always used in field
    resp_blacklist = {
        "networkcheck": {
            "passed": result if isinstance(result, bool) else False,
            "granite": [] if isinstance(result, bool) else result["Granite Data"],
            "network": [] if isinstance(result, bool) else result["Network Data"],
        },
        "cpe_model": cpe_model,
        "blacklist": {"passed": False, "ips": "Multiple IP's are unsupported"},
        "circ_path_inst_id": circ_path_inst_id,
        "engineering_job_type": job_type,
        "hub_work_required": hub_work_required,
        "cpe_installer_needed": cpe_installer_needed,
    }

    # if voice product, use IP address of vgw shelf
    if payload.product_name in voice_products:
        # Hosted Voice is the exception that can be treated the same as an FIA where we pull the info in granite
        # using the /pathElements call
        if "HOSTED VOICE" not in payload.product_name.upper():
            ipv4 = vgw_ipv4

    if payload.product_name.upper() not in ("CARRIER E-ACCESS (FIBER)", "EP-LAN (FIBER)", "EVPL (FIBER)", "EPL (FIBER)"):
        if ipv4:
            if ipv4.count(".") > 3:
                if (payload.product_name in voice_products) and (resp_blacklist["cpe_installer_needed"].upper() == "NO"):
                    resp_blacklist["cpe_model"] = vgw_model
                    resp_blacklist["cpe_installer_needed"] = vgw_installer_needed

                return resp_blacklist

            # skip blacklist check if ipv4 is a part of the private IP block space
            if not ipaddress.ip_address(ipv4.split("/")[0]).is_private:
                blacklist_result = is_blacklisted(ip_address=ipv4)
                if blacklist_result.get("blacklist_status"):
                    blacklisted = blacklist_result["blacklist_ip's"]
                    blacklisted_reason = blacklist_result["blacklist_reason"]

                if ipv4_assigned_subnet and not blacklisted:
                    blacklist_result = is_blacklisted(ip_address=ipv4_assigned_subnet)
                    if blacklist_result.get("blacklist_status"):
                        blacklisted = blacklist_result["blacklist_ip's"]
                        blacklisted_reason = blacklist_result["blacklist_reason"]

                if ipv4_glue_subnet and not blacklisted:
                    blacklist_result = is_blacklisted(ip_address=ipv4_glue_subnet)
                    if blacklist_result.get("blacklist_status"):
                        blacklisted = blacklist_result["blacklist_ip's"]
                        blacklisted_reason = blacklist_result["blacklist_reason"]

                if blacklisted:
                    data = {
                        "epr": payload.engineering_name,
                        "cid": payload.cid,
                        "ip_block": ipv4_assigned_subnet,
                        "blacklisted": blacklisted,
                        "blacklisted_reason": blacklisted_reason,
                    }
                    rm = RemedyTicket({})
                    blacklist_remedy_inc = rm.create_blacklist_inc(data)

    resp = {
        "networkcheck": {
            "passed": result if isinstance(result, bool) else False,
            "granite": [] if isinstance(result, bool) else result["Granite Data"],
            "network": [] if isinstance(result, bool) else result["Network Data"],
        },
        "cpe_model": cpe_model,
        "blacklist": {"passed": True if not blacklisted else False, "ips": [] if not blacklisted else blacklisted},
        "circ_path_inst_id": circ_path_inst_id,
        "engineering_job_type": job_type,
        "hub_work_required": hub_work_required,
        "cpe_installer_needed": cpe_installer_needed,
    }

    if blacklist_remedy_inc:
        resp["cosc_blacklist_ticket"] = blacklist_remedy_inc

    if (payload.product_name in voice_products or "Hosted Voice" in payload.product_name) and (
        resp["cpe_installer_needed"].upper() == "NO"
    ):
        resp["cpe_model"] = vgw_model
        resp["cpe_installer_needed"] = vgw_installer_needed

    return resp


def get_circuit_tid_ports(cid: str, product: str) -> tuple:
    """Get the circuit tid ports."""
    url = granite_paths_get_url(cid)
    resp = get_granite(url)
    path_status = ""
    if not isinstance(resp, list) and resp.get("retString") and "No records found" in resp.get("retString"):
        abort(500, f"No records found in Granite for cid: {cid}")
    elif len(resp) > 1:
        for path in resp:
            if path.get("status") == "Live":
                path_status = "Live"
                break
        if not path_status:
            abort(500, f"Circuit has multiple revisions in Granite and none are Live: {cid}")
    else:
        path_status = resp[0].get("status")

    path_elements = get_path_elements(cid, f"&PATH_STATUS={path_status}")

    devices = {}
    zw_device = ""
    a_side_site_name = resp[0].get("aSideSiteName") if resp[0].get("aSideSiteName") else ""
    eligible_status = ["LIVE", "DO-NOT-USE", "PENDING DECOMMISSION"]
    for elem in path_elements:
        if elem.get("ELEMENT_CATEGORY") == "OPTICAL LINE TERMINAL":
            abort(500, "EPON topology is unsupported")
        if elem.get("ELEMENT_STATUS").upper() in eligible_status:
            tid = elem.get("TID")
            if tid:
                if elem["LVL"] == "1":
                    if "ZW" in tid[-2:] or "01W" in tid[-3:] or "AW" in tid[-2:]:
                        if elem["PORT_ROLE"] == "UNI-EVP" and "EVPL" not in product:
                            abort(500, "Trunked handoff circuits are unsupported at this time")
                        devices[tid] = elem["PORT_ACCESS_ID"]
                        if elem["PORT_ROLE"] == "UNI-EP" or (elem["PORT_ROLE"] == "UNI-EVP" and "EVPL" in product):
                            if a_side_site_name and a_side_site_name != elem["A_SITE_NAME"]:
                                zw_device = tid
                elif elem["LVL"] == "2":
                    if "CW" in tid[-2:]:
                        if (elem["LEG_NAME"] != "1") and ("/" in elem["LEG_NAME"]):
                            devices[tid] = elem["LEG_NAME"].split("/")[0]
                        else:
                            devices[tid] = elem["PORT_ACCESS_ID"]
                    elif "AW" in tid[-2:] or "QW" in tid[-2:]:
                        transport_path_device_handoff_index = 2
                        if elem["PATH_NAME"].split(".")[transport_path_device_handoff_index] == tid:
                            devices[tid] = elem["PORT_ACCESS_ID"]
                    elif "ZW" in tid[-2:]:
                        if not devices.get(tid):
                            devices[tid] = elem["PORT_ACCESS_ID"]
                            zw_device = tid
    return devices, zw_device, path_elements[0]["CIRC_PATH_INST_ID"], path_elements


def get_juniper_network_configuration(device_info, granite_data, cid, ipv4_service_type=""):
    juniper_dev = {
        "tid": device_info["tid"],
        "vendor": "",
        "model": "",
        "vlan_id": "",
        "port_id": "",
        "description": True,
    }
    if not device_info.get("port_id"):
        return juniper_dev
    elif (len(device_info.get("tid")) == 11) and device_info.get("tid")[-2:] == "CW":
        try:
            device_config = onboard_and_exe_cmd(
                command="show_interfaces",
                parameter=device_info["port_id"].lower(),
                hostname=device_info.get("tid"),
                timeout=120,
                attempt_onboarding=False,
            )
        except Exception:
            juniper_dev["Error"] = "Device communication: show_interfaces"
            return juniper_dev
        juniper_dev["vendor"] = "JUNIPER"
        juniper_dev["model"] = device_info.get("model")
        try:
            device_port_info = device_config["result"]["data"]["configuration"]["interfaces"]["interface"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            logger.error(f"Error when retrieving data from MDSO - RESPONSE: {device_config.get('command')}")
            return juniper_dev

        if device_port_info.get("unit") and isinstance(device_port_info["unit"], list):
            for x in device_port_info["unit"]:
                if x.get("vlan-id") == device_info.get("vlan_id"):
                    juniper_dev["vlan_id"] = x.get("vlan-id")
                    juniper_dev["port_id"] = device_info.get("port_id")
                    try:
                        if cid in x.get("description"):
                            juniper_dev["description"] = True
                        else:
                            juniper_dev["description"] = False
                        juniper_dev["ipv4"] = x.get("family").get("inet").get("address").get("name")
                        juniper_dev["ipv6"] = x.get("family").get("inet6").get("address").get("name").upper()
                        if ipv4_service_type == "ROUTED":
                            try:
                                static_routes = onboard_and_exe_cmd(
                                    command="show_route",
                                    parameter=device_info.get("IPV4_ASSIGNED_SUBNETS"),
                                    hostname=device_info.get("tid"),
                                    timeout=120,
                                    attempt_onboarding=False,
                                )
                            except Exception:
                                juniper_dev["Error"] = "Device communication: show_route"
                                return juniper_dev

                            juniper_dev["IPV4_ASSIGNED_SUBNETS"] = None
                            juniper_dev["IPV4_GLUE_SUBNET"] = None

                            if static_routes["result"]["route-information"].get("route-table"):
                                if isinstance(
                                    static_routes["result"]["route-information"]["route-table"]["rt"], list
                                ) or isinstance(
                                    static_routes["result"]["route-information"]["route-table"]["rt"]["rt-entry"], list
                                ):
                                    return juniper_dev
                                else:
                                    if (
                                        static_routes["result"]["route-information"]["route-table"]["rt"]["rt-entry"][
                                            "nh"
                                        ]["via"]
                                        == f"{device_info['port_id'].lower()}.{device_info['vlan_id']}"
                                    ):
                                        juniper_dev["IPV4_ASSIGNED_SUBNETS"] = device_info["IPV4_ASSIGNED_SUBNETS"]
                                        juniper_dev["IPV4_GLUE_SUBNET"] = device_info["IPV4_GLUE_SUBNET"]
                    except (AttributeError, KeyError, TypeError):
                        pass
                    return juniper_dev
            else:
                juniper_dev["port_id"] = "VLAN NOT FOUND"
            return juniper_dev

    elif (
        (len(device_info.get("tid")) == 11)
        and (device_info.get("tid")[-2:] == "QW")
        and ("QFX" in device_info.get("model").upper())
    ):
        juniper_dev = get_juniper_network_configuration_qfx(juniper_dev, device_info, cid)
        return juniper_dev

    elif (
        (len(device_info.get("tid")) == 11)
        and (device_info.get("tid")[-2:] in "QW")
        and ("ACX" in device_info.get("model").upper())
    ):
        juniper_dev = get_juniper_network_configuration_acx(juniper_dev, device_info, cid)
        return juniper_dev

    elif (len(device_info.get("tid")) == 11) and (device_info.get("tid")[-2:] == "AW"):
        try:
            device_config = onboard_and_exe_cmd(
                command="show_interfaces",
                parameter=device_info["port_id"].lower(),
                hostname=device_info.get("tid"),
                timeout=120,
                attempt_onboarding=False,
            )
        except Exception:
            juniper_dev["Error"] = "Device communication: show_interfaces"
            return juniper_dev
        juniper_dev["vendor"] = "JUNIPER"
        juniper_dev["model"] = device_info.get("model")
        try:
            device_port_info = device_config["result"]["data"]["configuration"]["interfaces"]["interface"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            return juniper_dev
        if isinstance(device_port_info, dict):
            if device_port_info.get("description"):
                if "AW" in device_port_info["description"]:
                    aw_devices = get_aw_device(device_port_info["description"], granite_data)
                    for device in aw_devices:
                        if device.get("tid") in device_port_info.get("description"):
                            juniper_dev["description"] = True
                            break
                if "ZW" in device_port_info["description"]:
                    zw_devices = get_zw_device(device_port_info["description"], granite_data)
                    for device in zw_devices:
                        if device.get("tid") in device_port_info.get("description"):
                            juniper_dev["description"] = True
                            break

            if device_port_info.get("name") and device_info.get("port_id", "").lower() in device_port_info["name"]:
                juniper_dev["tid"] = device_info.get("tid")
                juniper_dev["port_id"] = device_info.get("port_id")

                try:
                    if isinstance(device_port_info["unit"]["family"]["ethernet-switching"]["vlan"]["members"], list):
                        for vlan in device_port_info["unit"]["family"]["ethernet-switching"]["vlan"]["members"]:
                            if device_info.get("vlan_id") in vlan:
                                juniper_dev["vlan_id"] = device_info.get("vlan_id")
                                break
                    elif isinstance(device_port_info["unit"]["family"]["ethernet-switching"]["vlan"]["members"], str):
                        if (
                            device_info.get("vlan_id")
                            in device_port_info["unit"]["family"]["ethernet-switching"]["vlan"]["members"]
                        ):
                            juniper_dev["vlan_id"] = device_info.get("vlan_id")
                except Exception:
                    if isinstance(device_port_info.get("unit"), list):
                        for vlan in device_port_info["unit"]:
                            if vlan.get("name") == device_info.get("vlan_id"):
                                juniper_dev["vlan_id"] = vlan.get("name")

            return juniper_dev

    elif (len(device_info.get("tid")) == 11) and (device_info.get("tid")[-2:] == "ZW"):
        try:
            device_config = onboard_and_exe_cmd(
                command="show_interfaces",
                parameter=device_info["port_id"].lower(),
                hostname=device_info.get("tid"),
                timeout=120,
                attempt_onboarding=False,
            )
        except Exception:
            juniper_dev["Error"] = "Device communication: show_interfaces"
            return juniper_dev
        juniper_dev["vendor"] = "JUNIPER"
        juniper_dev["model"] = device_info.get("model")
        try:
            device_port_info = device_config["result"]["data"]["configuration"]["interfaces"]["interface"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            return juniper_dev
        device_filtered_info = []
        if isinstance(device_port_info, dict):
            for v in device_port_info.values():
                if v and device_info.get("port_id", "").lower() in v:
                    # pull data from MX240 as a ZW device
                    if isinstance(device_port_info.get("unit", ""), list):
                        for unit in device_port_info["unit"]:
                            if unit.get("vlan-id") == device_info.get("vlan_id"):
                                juniper_dev["tid"] = device_info.get("tid")
                                juniper_dev["port_id"] = device_info.get("port_id")
                                juniper_dev["vlan_id"] = unit.get("vlan-id")
                                juniper_dev["description"] = True if cid in unit.get("description", "") else False
                                return juniper_dev
                    else:
                        try:
                            device_filtered_info.append(
                                device_port_info["unit"]["family"]["ethernet-switching"]["vlan"]["members"]
                            )
                        except Exception:
                            logger.info("No VLAN info for device %s", device_info.get("tid"))
                    juniper_dev["tid"] = device_info.get("tid")
                    juniper_dev["port_id"] = device_info.get("port_id")
        if device_filtered_info:
            for x in device_filtered_info[0]:
                if isinstance(x, dict) and cid in x.get("description"):
                    juniper_dev["description"] = True
                else:
                    juniper_dev["description"] = False
                if device_info.get("vlan_id") in x:
                    juniper_dev["vlan_id"] = device_info.get("vlan_id")
                    return juniper_dev
    return juniper_dev


def get_juniper_network_configuration_qfx(juniper_dev: dict, device_info: dict, cid: str) -> dict:
    juniper_dev["vendor"] = "JUNIPER"
    juniper_dev["model"] = device_info.get("model")
    juniper_dev["tid"] = device_info.get("tid")

    # first network call to check port ID, description, and vlan ID
    matched_vlan = ""
    try:
        dev_config = onboard_and_exe_cmd(
            command="get_interfaces",
            parameter=device_info.get("port_id").lower(),
            hostname=device_info.get("tid"),
            timeout=120,
            attempt_onboarding=False,
        )
    except Exception:
        logger.error("Device communication: get_interfaces")
        return juniper_dev
    # parse network data for port ID and description info
    try:
        dev_port_info = dev_config["result"]["configuration"]["interfaces"][f"{device_info.get('port_id').lower()}"]
    except (TypeError, AttributeError, KeyError):
        return juniper_dev
    juniper_dev["port_id"] = device_info.get("port_id")
    juniper_dev["description"] = True if cid in dev_port_info.get("description", "") else False
    try:
        vlan_data = dev_port_info["unit"][0]["family"]["ethernet-switching"]["vlan"]["members"]
    except (TypeError, AttributeError, KeyError):
        return juniper_dev
    if isinstance(vlan_data, list):
        for vlan in vlan_data:
            if device_info.get("vlan_id") in vlan:
                juniper_dev["vlan_id"] = device_info.get("vlan_id")
                matched_vlan = vlan
                break
    elif isinstance(vlan_data, str):
        if device_info.get("vlan_id") in vlan_data:
            juniper_dev["vlan_id"] = device_info.get("vlan_id")
            matched_vlan = vlan_data

    # only if needed, make a second network call and parse its data response for description
    if juniper_dev["description"] is False and matched_vlan:
        try:
            dev_config = onboard_and_exe_cmd(
                command="agg_vlans", hostname=device_info.get("tid"), timeout=120, attempt_onboarding=False
            )
        except Exception:
            logger.error("Device communication: agg_vlans")
            return juniper_dev
        # parse network data to see if description can be verified
        try:
            dev_port_info = dev_config["result"]
        except (TypeError, AttributeError, KeyError):
            return juniper_dev
        if isinstance(dev_port_info, dict):
            for service_data in dev_port_info.items():
                if service_data[0] == matched_vlan:
                    juniper_dev["description"] = True if cid in service_data[1].get("description", "") else False
                    break
            else:
                msg = f"Unable to verify description for {device_info.get('tid')} - {device_info.get('port_id')}"
                logger.error(msg)
                return juniper_dev

    return juniper_dev


def get_juniper_network_configuration_acx(juniper_dev: dict, device_info: dict, cid: str) -> dict:
    juniper_dev["vendor"] = "JUNIPER"
    juniper_dev["model"] = device_info.get("model")
    juniper_dev["tid"] = device_info.get("tid")
    juniper_dev["port_id"] = device_info.get("port_id")

    # network call to obtain device config data
    try:
        dev_config = onboard_and_exe_cmd(
            command="show_interfaces",
            parameter=device_info["port_id"].lower(),
            hostname=device_info.get("tid"),
            timeout=120,
            attempt_onboarding=False,
        )
    except Exception:
        juniper_dev["Error"] = "Device communication: show_interfaces"
        return juniper_dev

    # parse section of data containing vlan ID and description value for QFX device
    try:
        dev_port_info = dev_config["result"]["data"]["configuration"]["interfaces"]["interface"]["unit"]
    except (TypeError, AttributeError, KeyError):
        # If MDSO error, stop and return device dict as-is
        return juniper_dev

    if isinstance(dev_port_info, dict):
        juniper_dev["description"] = True if cid in dev_port_info.get("description", "") else False
        juniper_dev["vlan_id"] = dev_port_info.get("vlan-id", "")

    return juniper_dev


def get_juniper_network_configuration_e_access(device_info, granite_data, cid):
    juniper_dev = {
        "tid": device_info["tid"],
        "vendor": "",
        "model": "",
        "vlan_id": device_info["vlan_id"],
        "port_id": "",
        "description": True,
    }
    if not device_info.get("port_id"):
        return juniper_dev
    paired_router = None
    is_cpe = False
    # Distinguish paired/non-paired routers and CPEs
    if (len(device_info.get("tid")) == 11) and (device_info.get("tid")[-2:] in ["CW", "ZW"]):
        if "evc_id" in device_info.keys():  # paired router
            paired_router = True
            cmd = "get-l2-circuits-full.json"
            param = (
                device_info.get("e_access_ip", "")
                + ":"
                + device_info.get("port_id", "").lower()
                + "."
                + device_info.get("vlan_id", "")
            )
        elif "ipv4" in device_info.keys():  # unpaired router
            paired_router = False
        elif (device_info.get("tid")[-2:] == "ZW") and ("ipv4" not in device_info.keys()):  # CPE
            is_cpe = True

        if paired_router:
            try:
                device_config = onboard_and_exe_cmd(
                    command=cmd, parameter=param, hostname=device_info.get("tid"), timeout=120, attempt_onboarding=False
                )
            except Exception:
                juniper_dev["Error"] = "Device communication: get-l2-circuits-full"
                return juniper_dev

            try:
                device_port_info = device_config["result"]["properties"]
            except (TypeError, AttributeError, KeyError):
                # If MDSO error, stop and return device dict as-is
                logger.error(f"Error when retrieving data from MDSO - RESPONSE: {device_config.get('command')}")
                return juniper_dev
            if isinstance(device_port_info, dict):
                juniper_dev["description"] = False
                juniper_dev["tid"] = device_info.get("tid")
                juniper_dev["e_access_ip"] = device_info.get("e_access_ip", "")
                juniper_dev["model"] = device_info.get("model")
                if device_info.get("port_id", "").lower() in device_port_info.get("name"):
                    juniper_dev["port_id"] = device_info.get("port_id")
                    juniper_dev["vendor"] = "JUNIPER"
                if device_port_info.get("description") and cid in device_port_info.get("description"):
                    juniper_dev["description"] = True
                if device_info.get("vlan_id") in device_port_info.get("name"):
                    juniper_dev["vlan_id"] = device_info.get("vlan_id")
                if device_info.get("evc_id") in str(device_port_info.get("virtual-circuit-id")):
                    juniper_dev["evc_id"] = str(device_port_info.get("virtual-circuit-id"))
            return juniper_dev
        elif (paired_router is False) and (device_info.get("tid")[-2:] == "CW"):  # singleton router
            return get_juniper_network_configuration(device_info, granite_data, cid)
        elif is_cpe:
            return get_juniper_network_configuration(device_info, granite_data, cid)
        else:
            return juniper_dev
    return juniper_dev


def get_juniper_network_configuration_elan(device_info, granite_data, cid):
    juniper_dev = {
        "tid": device_info["tid"],
        "vendor": "",
        "model": "",
        "vlan_id": device_info["vlan_id"],
        "port_id": "",
        "description": False,
    }
    if not device_info.get("port_id"):
        return juniper_dev

    # Begin collecting network data for juniper device profile
    if (len(device_info.get("tid")) == 11) and (device_info.get("tid")[-2:] == "CW"):
        # make path elements call
        path_elements = get_path_elements(cid)
        element_reference = ""
        evc_id = ""
        for element in path_elements:
            try:
                if "NETWORK" in element["ELEMENT_TYPE"] and "VPLS SVC" in element["ELEMENT_CATEGORY"]:
                    element_reference = element["ELEMENT_REFERENCE"]
                    evc_id = element["EVC_ID"]
                    break
            except (AttributeError, KeyError, TypeError):
                pass

        else:
            logger.error("Can't find correct path element to process")
            juniper_dev["evc_id"] = evc_id
            juniper_dev["Error"] = "Can't find correct path element to process"
            return juniper_dev

        if element_reference:
            try:
                network_associations = get_network_association(element_reference)
                network_association_id = None
                if isinstance(network_associations, list):
                    for associaction in network_associations:
                        if associaction.get("associationType") == "NETWORK TO EVC ID":
                            network_association_id = associaction.get("associationValue").lstrip("0")
                if not network_association_id:
                    raise Exception
                if network_association_id != evc_id:
                    logger.error(f"Network association ID {network_association_id} does not match EVC ID {evc_id}")
                    juniper_dev["evc_id"] = ""
                    juniper_dev["Error"] = (
                        f"Granite network associate ID {network_association_id} did not match Granite EVC ID {evc_id}"
                    )
                    return juniper_dev
            except Exception:
                logger.error("Network association ID not available")
                juniper_dev["evc_id"] = ""
                juniper_dev["Error"] = "Granite network association ID is not available"
                return juniper_dev
        else:
            logger.error(f"Unable to determine correct element reference {element_reference}")
            juniper_dev["evc_id"] = ""
            juniper_dev["Error"] = "Granite network instance ID is unavailable"
            return juniper_dev

        try:
            device_config = onboard_and_exe_cmd(
                command="show_interfaces",
                parameter=device_info.get("port_id").lower(),
                hostname=device_info.get("tid"),
                timeout=120,
                attempt_onboarding=False,
            )
        except Exception:
            juniper_dev["Error"] = "Device communication: show_interfaces"
            return juniper_dev

        try:
            device_port_info = device_config["result"]["data"]["configuration"]["interfaces"]["interface"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            logger.error(f"Error when retrieving data from MDSO - RESPONSE: {device_config.get('command')}")
            return juniper_dev
        if device_port_info.get("unit") and isinstance(device_port_info["unit"], list):
            for x in device_port_info["unit"]:
                if x.get("vlan-id") == device_info.get("vlan_id"):
                    juniper_dev["vlan_id"] = x.get("vlan-id")
                    juniper_dev["vendor"] = "JUNIPER"
                    juniper_dev["port_id"] = device_info.get("port_id")
                    juniper_dev["model"] = device_info.get("model")
                    juniper_dev["encapsulation"] = x.get("encapsulation")
                    try:
                        if cid in x.get("description"):
                            juniper_dev["description"] = True
                        else:
                            juniper_dev["description"] = False
                        juniper_dev["ipv6"] = x.get("family").get("inet6").get("address").get("name").upper()
                        juniper_dev["ipv4"] = x.get("family").get("inet").get("address").get("name")
                    except (AttributeError, KeyError, TypeError):
                        pass

        # Encapsulation check
        expected_encapsulation = "vlan-vpls"
        if juniper_dev.get("encapsulation") != expected_encapsulation:
            logger.error(
                f"Unexpected encapsulation setting {juniper_dev.get('encapsulation')} for {device_info.get('tid')}"
            )
            juniper_dev["Error"] = (
                f"Unexpected encapsulation setting {juniper_dev.get('encapsulation')} for {device_info.get('tid')}"
            )
            return juniper_dev

        # EVC ID check
        try:
            device_config = onboard_and_exe_cmd(
                command="show_routing_instances", hostname=device_info.get("tid"), timeout=120, attempt_onboarding=False
            )
        except Exception:
            juniper_dev["Error"] = "Device communication: show_routing_instances"
            return juniper_dev

        juniper_dev["evc_id"] = ""
        try:
            device_port_info = device_config["result"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            logger.error(f"Error when retrieving data from MDSO - RESPONSE: {device_config.get('command')}")
            return juniper_dev
        port_vlanid = juniper_dev["port_id"] + "." + juniper_dev["vlan_id"]
        for x in device_port_info:
            try:
                interfaces = x.get("properties").get("interfaces")
                for y in interfaces:
                    try:
                        if y.get("config").get("interface") == port_vlanid.lower():
                            juniper_dev["evc_id"] = x.get("properties").get("config").get("routeTarget").split(":")[-1]
                            return juniper_dev
                    except (TypeError, AttributeError, KeyError):
                        pass
            except (TypeError, AttributeError, KeyError):
                pass
        tid_interface = f"{device_info.get('tid')}:{device_info.get('port_id')}.{device_info.get('vlan_id')}"
        logger.error(f"EVC ID {device_info.get('evc_id')} was not found in the config route target of {tid_interface}")
        juniper_dev["evc_id"] = ""
        juniper_dev["Error"] = (
            f"EVC ID {device_info.get('evc_id')} was not found in the config route target of {tid_interface}"
        )
        return juniper_dev
    elif (len(device_info.get("tid")) == 11) and any(
        [
            device_info.get("tid").endswith("AW"),
            device_info.get("tid").endswith("QW"),
            device_info.get("tid").endswith("ZW"),
        ]
    ):
        return get_juniper_network_configuration(device_info, granite_data, cid)
    else:
        return juniper_dev


def get_adva_network_configs(device: Dict[str, Any], device_list: List[Dict[str, Any]], cid: str) -> Dict[str, Any]:
    network_info = {
        "tid": device["tid"],
        "vendor": "",
        "model": "",
        "vlan_id": device["vlan_id"],
        "port_id": "",
        "description": True,
    }

    # If MTU, get connected CPE TID according to Granite
    zw_devices = None
    if len(device["tid"]) == 11 and device["tid"][-2:] == "AW":
        zw_devices = get_zw_device(device["tid"], device_list)

    # Different MDSO commands based on model
    if "114" in device["model"]:
        command = "1g_adva_flows"
    else:
        command = "seefa-cd-list_eth_ports.json"

    try:
        network_resp = onboard_and_exe_cmd(device["tid"], command=command)
        device_info = _get_network_device(device["tid"], timeout=180)

        network_info["vendor"] = device["vendor"]
    except Exception:
        # for 116PRO, try command "10g_adva_flows"
        try:
            command = "10g_adva_flows"
            network_resp = onboard_and_exe_cmd(device["tid"], command=command)
            device_info = _get_network_device(device["tid"], timeout=180)
            network_info["vendor"] = device["vendor"]
        except Exception:
            logger.error(f"Error when retrieving data from MDSO - RESPONSE: {command}")
            network_info["Error"] = f"Device communication: {command}"
            network_info["description"] = False
            return network_info

    if device_info:
        # Parse 1G ADVA flows for CID and get port
        if "114" in device_info["properties"]["type"]:
            if device_info["properties"]["type"] == "GE114Pro":
                network_info["model"] = "FSP 150-GE114PRO-C"
            elif device_info["properties"]["type"] == "GE114":
                network_info["model"] = "FSP 150CC-GE114/114S"
            if network_resp:
                for flow in network_resp["result"]:
                    if flow["properties"]["epAccessFlowEVCName"] == cid:
                        network_info["port_id"] = flow["properties"]["epAccessFlowAccessInterface"].upper()
                        break
        else:
            # Set model to what MDSO found on the network for the TID
            if device_info["properties"]["type"] == "XG116PRO":
                network_info["model"] = "FSP150CC-XG116PRO"
            if device_info["properties"]["type"] == "XG120PRO":
                network_info["model"] = "FSP 150-XG120PRO"
            # Parse 10G ADVA flows for CID and get port
            if network_resp.get("result"):
                for flow in network_resp["result"][-1]["flow_point"]:
                    if ("eth_port-1-1-1-8" in flow["properties"]["interface"] and "116" in device["model"]) or (
                        "eth_port-1-1-1-26" in flow["properties"]["interface"] and "120" in device["model"]
                    ):
                        continue  # ignore uplink flows which also have the CID
                    if flow["properties"]["alias"] == cid:
                        network_info["port_id"] = flow["properties"]["interface"].upper()
                        break
                # If MTU, parse ports for CPE TID
                if zw_devices:
                    for port in network_resp["result"][0]["eth"]:
                        if ("eth_port-1-1-1-8" in port["properties"]["name"] and "116" in device["model"]) or (
                            "eth_port-1-1-1-26" in port["properties"]["name"] and "120" in device["model"]
                        ):
                            continue  # ignore uplinks
                        for zw_tid in zw_devices:
                            if zw_tid["tid"] in port["properties"]["alias"]:
                                if port["properties"]["name"].upper() != network_info["port_id"]:
                                    network_info["description"] = False
                                    if port["properties"]["name"].upper() == device["port_id"]:
                                        if cid in port["properties"]["alias"]:
                                            network_info["description"] = True
                                            network_info["port_id"] = device["port_id"]
                                break
    return network_info


def get_rad_network_configs(device: Dict[str, Any], device_list: List[Dict[str, Any]], cid: str) -> Dict[str, Any]:
    network_info = {
        "tid": device["tid"],
        "vendor": "",
        "model": "",
        "vlan_id": device["vlan_id"],
        "port_id": "",
        "description": True,
    }

    # If MTU, get connected CPE TID according to Granite
    zw_devices = None
    if len(device["tid"]) == 11 and device["tid"][-2:] in ["AW", "ZW"]:
        zw_devices = get_zw_device(device["tid"], device_list)

    if len(device["tid"]) == 11 and device["tid"].endswith("AW"):
        model = device["model"].split("/")[0]
        if "ETX-2I-10G" in model:
            network_data = get_rad_network_configs_etx_2i_10g(device, network_info, cid)
            return network_data

    try:
        command = "rad_flows"
        network_resp = onboard_and_exe_cmd(device["tid"], command)
        device_info = _get_network_device(device["tid"], timeout=180)
        network_info["vendor"] = device["vendor"]
        if zw_devices:
            # Additional call for port info if MTU
            command = "seefa-cd-list-ports.json"
            network_port_resp = onboard_and_exe_cmd(device["tid"], command)
    except Exception:
        # If MDSO error, stop and return device dict as-is
        logger.error(f"Error when retrieving data from MDSO - RESPONSE: {command}")
        network_info["Error"] = f"Device communication: {command}"
        return network_info

    # Parse flows for CID and get port
    for flow in network_resp["result"]:
        if (cid in flow["properties"]["name"] and "IN" in flow["properties"]["name"].upper()) or (
            ("IN" in flow["properties"]["name"].upper() and device["vlan_id"] in flow["properties"]["name"])
            and (int(device["vlan_id"]) >= 1000)
        ):
            if "ETX-203" in device_info["properties"]["type"]:
                network_info["model"] = "ETX203AX/2SFP/2UTP2SFP"
                network_info["port_id"] = f"ETH PORT {flow['properties']['ingressPortId']}"
                break
            elif device_info["properties"]["type"].upper() in ["ETX-2I", "ETX-220"]:
                network_info["model"] = device["model"]
                if flow["properties"]["ingressPortId"] in device["port_id"]:
                    network_info["port_id"] = device["port_id"]
                break
    # If MTU, parse ports for CPE TID
    if zw_devices:
        for port in network_port_resp["result"]:
            for zw_tid in zw_devices:
                try:
                    if zw_tid["tid"] in port["details"]["name"]:
                        if port["id"] not in network_info["port_id"]:
                            network_info["description"] = False
                except (AttributeError, KeyError):
                    continue
    return network_info


def get_rad_network_configs_etx_2i_10g(device: dict, network_info: dict, cid: str) -> dict:
    try:
        command = "rad_classifiers"
        network_resp = onboard_and_exe_cmd(device["tid"], command)
        device_info = _get_network_device(device["tid"], timeout=180)
        network_info["vendor"] = device["vendor"]
    except Exception:
        logger.error(f"Error when retrieving data from MDSO - RESPONSE: {command}")
        network_info["Error"] = f"Device communication: {command}"
        return network_info

    try:
        device_type = device_info["properties"]["type"]
    except Exception:
        return network_info

    if (device_type.upper() in device["model"]) and isinstance(network_resp.get("result", ""), list):
        network_resp_list = network_resp["result"]
        for data in network_resp_list:
            if (cid in data.get("label", "")) and ("IN" in data.get("label", "")):
                if isinstance(data.get("properties", ""), dict):
                    if isinstance(data["properties"].get("match", ""), list):
                        for vlan_str in data["properties"]["match"]:
                            if device["vlan_id"] in vlan_str:
                                network_info["vlan_id"] = device["vlan_id"]
                                network_info["model"] = device["model"]
                                network_info["port_id"] = device["port_id"]
                                network_info["description"] = device["description"]
                                return network_info
                    elif isinstance(data["properties"].get("match", ""), str):
                        if device["vlan_id"] in data["properties"]["match"]:
                            network_info["vlan_id"] = device["vlan_id"]
                            network_info["model"] = device["model"]
                            network_info["port_id"] = device["port_id"]
                            network_info["description"] = device["description"]
    return network_info


def me3400_check_vlan(vlan, device_port_info):
    if (
        device_port_info["switchport"]["mode"] != "trunk"
        and vlan in device_port_info["switchport"]["vlan"]["access_vlan"]
    ):
        return True
    elif (
        device_port_info["switchport"]["mode"] == "trunk"
        and vlan in device_port_info["switchport"]["vlan"]["trunk"]["allowed_vlans"]
    ):
        return True
    return False


def get_asr920_vlan(device_info: dict) -> dict:
    instance_id = None
    try:
        device_config = onboard_and_exe_cmd(
            command="get_service_instances",
            parameter=device_info["port_id"].lower(),
            hostname=device_info.get("tid"),
            timeout=120,
        )
    except Exception:
        return {"error": "Device communication: get_service_instances"}
    logger.debug(f"device_config - {device_config}")

    try:
        data = device_config["result"]
    except Exception:
        return {"error": "Device communication: get_service_instances"}
    logger.debug(f"data - {data}")

    if data and isinstance(data, list):
        try:
            instance_id = data[0]["instance_id"]
        except Exception:
            return {"error": f"Unable to retrieve vlan ID from {device_info['tid']}:{device_info['port_id']}"}
    else:
        return {"error": f"Unable to retrieve vlan ID from {device_info['tid']}:{device_info['port_id']}"}

    if instance_id:
        return {"pass": instance_id}
    else:
        return {"error": f"Unable to retrieve vlan ID from {device_info['tid']}:{device_info['port_id']}"}


def get_cisco_asr920_configuration(device_info, cid, circ_path_inst_id=""):
    cisco_dev = {"tid": device_info["tid"], "vendor": "", "model": "", "vlan_id": "", "port_id": "", "description": None}

    if not device_info.get("port_id"):
        return cisco_dev

    if len(device_info.get("tid")) == 11 and device_info.get("tid").endswith("ZW"):
        try:
            device_config = onboard_and_exe_cmd(
                command="show_running_config_interface",
                parameter=device_info["port_id"].lower(),
                hostname=device_info.get("tid"),
                timeout=120,
            )
        except Exception:
            cisco_dev["Error"] = "Device communication: show_running_config_interface"
            return cisco_dev

        try:
            device_port_info = device_config["result"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            logger.error(f"Error when retrieving data from MDSO - RESPONSE: {device_config.get('command')}")
            return cisco_dev

        if cid in device_port_info.get("description") or uda_legacy_id_matches_cid(
            circ_path_inst_id, device_port_info.get("description")
        ):
            cisco_dev["description"] = True
        else:
            cisco_dev["description"] = False

        vlan_check = get_asr920_vlan(device_info)
        if "pass" in vlan_check.keys():
            cisco_dev["vlan_id"] = vlan_check["pass"]
        else:
            cisco_dev["Error"] = vlan_check["error"]

        cisco_dev["vendor"] = "CISCO"
        cisco_dev["port_id"] = device_info.get("port_id")
        cisco_dev["model"] = device_info.get("model")
        return cisco_dev
    else:
        logger.error(f"Unexpected Cisco device tid: {device_info.get('tid')}")
        return cisco_dev


def get_cisco_me3400_configuration(device_info):
    cisco_dev = {
        "tid": device_info["tid"],
        "vendor": "",
        "model": "",
        "vlan_id": device_info["vlan_id"],
        "port_id": "",
        "description": None,
    }
    if not device_info.get("port_id"):
        return cisco_dev
    if len(device_info.get("tid")) == 11 and device_info.get("tid").endswith("ZW"):
        try:
            device_config = onboard_and_exe_cmd(
                command="show_running_config_interface",
                parameter=device_info["port_id"].lower(),
                hostname=device_info.get("tid"),
                timeout=120,
            )
        except Exception:
            cisco_dev["Error"] = "Device communication: show_running_config_interface"
            return cisco_dev
        try:
            device_port_info = device_config["result"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            logger.error(f"Error when retrieving data from MDSO - RESPONSE: {device_config.get('command')}")
            return cisco_dev
        if me3400_check_vlan(cisco_dev["vlan_id"], device_port_info):
            cisco_dev["vendor"] = "CISCO"
            cisco_dev["port_id"] = device_info.get("port_id")
            cisco_dev["model"] = device_info.get("model")
            cisco_dev["description"] = True
            return cisco_dev
    else:
        logger.error(f"Unexpected Cisco device tid: {device_info.get('tid')}")
        return cisco_dev


def get_cisco_network_configuration(device_info, cid, circ_path_inst_id="", ipv4_service_type=""):
    cisco_dev = {
        "tid": device_info["tid"],
        "vendor": "",
        "model": "",
        "vlan_id": device_info["vlan_id"],
        "port_id": "",
        "description": None,
    }
    if not device_info.get("port_id"):
        return cisco_dev
    if (len(device_info.get("tid")) == 11) and (device_info.get("tid")[-2:] == "CW"):
        try:
            device_config = onboard_and_exe_cmd(
                command="show_interfaces",
                parameter=device_info["port_id"].lower(),
                hostname=device_info.get("tid"),
                timeout=120,
                attempt_onboarding=False,
            )
        except Exception:
            cisco_dev["Error"] = "Device communication: show_interfaces"
            return cisco_dev

        try:
            device_port_info = device_config["result"]
        except (TypeError, AttributeError, KeyError):
            # If MDSO error, stop and return device dict as-is
            logger.error(f"Error when retrieving data from MDSO - RESPONSE: {device_config.get('command')}")
            return cisco_dev
        if isinstance(device_port_info, list):
            for x in device_port_info:
                if device_info.get("vlan_id") in x.get("interface") or device_info.get("vlan_id").split(":")[0] in x.get(
                    "interface"
                ):
                    cisco_dev["vlan_id"] = device_info.get("vlan_id")
                    cisco_dev["vendor"] = "CISCO"
                    cisco_dev["port_id"] = device_info.get("port_id")
                    cisco_dev["model"] = device_info.get("model")
                    try:
                        if cid in x.get("description"):
                            cisco_dev["description"] = True
                        elif uda_legacy_id_matches_cid(circ_path_inst_id, x.get("description")):
                            cisco_dev["description"] = True
                        else:
                            cisco_dev["description"] = False
                        cisco_dev["ipv6"] = device_info.get("ipv6")
                        cisco_dev["ipv4"] = device_info.get("ipv4")
                        if ipv4_service_type == "ROUTED":
                            cisco_dev["IPV4_ASSIGNED_SUBNETS"] = None
                            cisco_dev["IPV4_GLUE_SUBNET"] = None
                            return cisco_dev
                    except (AttributeError, KeyError):
                        pass
                    return cisco_dev
            return cisco_dev
        else:
            return cisco_dev
    else:
        logger.error(f"Unexpected Cisco device tid: {device_info.get('tid')}")
        return cisco_dev


def get_cisco_network_configuration_e_access(device_info, cid, circ_path_inst_id="", ipv4_service_type=""):
    if not device_info:
        logger.error(f"Missing device info for {cid}")
        abort(500, f"Missing device info for {cid}")

    cisco_dev = {
        "tid": device_info.get("tid"),
        "vendor": "",
        "model": "",
        "vlan_id": "",
        "port_id": "",
        "description": None,
    }
    if not device_info.get("port_id"):
        return cisco_dev

    # Distinguish between paired and non-paired routers
    paired_router = None
    if (len(device_info.get("tid")) == 11) and (device_info["tid"].endswith("CW")):
        if "evc_id" in device_info.keys():
            paired_router = True
            cmd = "show_cisco_router_evc"
            param = f"{device_info.get('port_id', '')}.{device_info.get('vlan_id', '')}"
        elif "ipv4" in device_info.keys():
            paired_router = False

        if paired_router:
            try:
                cisco_data = onboard_and_exe_cmd(
                    command=cmd, parameter=param, hostname=device_info.get("tid"), timeout=120, attempt_onboarding=False
                )
            except Exception:
                cisco_dev["Error"] = "Device communication: show_cisco_router_evc"
                return cisco_dev

            if isinstance(cisco_data, dict):
                try:
                    evc_data = cisco_data.get("result")
                except (TypeError, AttributeError, KeyError):
                    logger.error(f"Unexpected data format from MDSO - RESPONSE: {cisco_data.get('command')}")
                    return cisco_dev
                if evc_data and (device_info.get("evc_id") == evc_data.get("evcid")):
                    cisco_dev["evc_id"] = evc_data.get("evcid")
                else:
                    cisco_dev["evc_id"] = ""

            cisco_data = None
            try:
                cisco_data = onboard_and_exe_cmd(
                    command="show_interfaces",
                    parameter=param,
                    hostname=device_info.get("tid"),
                    timeout=120,
                    attempt_onboarding=False,
                )
            except Exception:
                cisco_dev["Error"] = "Device communication: show_interfaces"
                return cisco_dev
            logger.debug(f"cisco_data - {cisco_data}")

            try:
                interface_data = cisco_data["result"]
            except (TypeError, AttributeError, KeyError):
                logger.error(f"Unexpected data format from MDSO - RESPONSE: {interface_data.get('command')}")
                return cisco_dev

            if isinstance(interface_data, list):
                cisco_dev["description"] = False
                cisco_dev["model"] = device_info.get("model")
                cisco_dev["e_access_ip"] = device_info.get("e_access_ip", "")
                for item in interface_data:
                    if device_info.get("vlan_id") in item.get("interface"):
                        cisco_dev["vlan_id"] = device_info.get("vlan_id")
                        if item.get("description") and (cid in item.get("description")):
                            cisco_dev["description"] = True
                        elif uda_legacy_id_matches_cid(circ_path_inst_id, item.get("description")):
                            cisco_dev["description"] = True
                        if device_info.get("port_id") in cisco_data["parameters"]["interface"]:
                            cisco_dev["port_id"] = device_info.get("port_id")
                            cisco_dev["vendor"] = "CISCO"
            return cisco_dev
        elif (paired_router is False) and (device_info["tid"].endswith("CW")):
            return get_cisco_network_configuration(device_info, cid, circ_path_inst_id, ipv4_service_type)
        else:
            return cisco_dev
    else:
        return cisco_dev


def get_z_side_cpe(db_dev_list: List[Dict[str, Any]], zw: str) -> Dict[str, Any]:
    """
    Get the Z-side CPE (Customer Premises Equipment) from the given device list based on the provided 'zw' identifier.

    Args:
        db_dev_list (List[Dict[str, Any]]): A list of devices with associated information.
        zw (str): The identifier used to search for the Z-side CPE.

    Returns:
        Dict[str, Any]: The Z-side CPE device information if found, or an empty dictionary if not found.
    """
    z_side_cpe = {}
    for dev in db_dev_list:
        if dev.get("tid") == zw:
            z_side_cpe = dev
    return z_side_cpe


def get_network_data(db_dev_list: List[Dict[str, Any]], cid: str, product_name: str, ipv4_service_type: str) -> list:
    """
    Get network data for a list of devices based on specific criteria.

    Args:
        db_dev_list (List[Dict[str, Any]]): A list of devices with associated information.
        cid (str): Customer ID.
        product_name (str): Name of the product.
        ipv4_service_type (str): Type of IPv4 service.

    Returns:
        List[Dict[str, Any]]: A list of network data for the selected devices.
    """
    network_dev_list = []
    circ_path_inst_id = get_circuit_path_inst_id(cid)
    for dev in db_dev_list:
        if dev.get("vendor") == "JUNIPER" and product_name.upper() in (
            "CARRIER E-ACCESS (FIBER)",
            "EVPL (FIBER)",
            "EPL (FIBER)",
        ):
            if dev.get("tid")[-2:] in ["AW", "QW"]:
                network_data = get_juniper_network_configuration(dev, db_dev_list, cid)
            else:
                network_data = get_juniper_network_configuration_e_access(dev, db_dev_list, cid)
            network_dev_list.append(network_data)
        elif dev.get("vendor") == "JUNIPER" and product_name == "EP-LAN (Fiber)":
            network_data = get_juniper_network_configuration_elan(dev, db_dev_list, cid)
            network_dev_list.append(network_data)
        elif dev.get("vendor") == "JUNIPER":
            network_data = get_juniper_network_configuration(dev, db_dev_list, cid, ipv4_service_type)
            network_dev_list.append(network_data)
        elif dev.get("vendor") == "CISCO":
            if "ME-3400" in dev.get("model"):
                network_data = get_cisco_me3400_configuration(dev)
            elif product_name.upper() in ("CARRIER E-ACCESS (FIBER)", "EVPL (FIBER)", "EPL (FIBER)"):
                network_data = get_cisco_network_configuration_e_access(dev, cid, circ_path_inst_id, ipv4_service_type)
            elif "ASR-920" in dev.get("model"):
                network_data = get_cisco_asr920_configuration(dev, cid, circ_path_inst_id)
            else:
                network_data = get_cisco_network_configuration(dev, cid, circ_path_inst_id, ipv4_service_type)
            network_dev_list.append(network_data)
        elif dev.get("vendor") == "ADVA":
            network_data = get_adva_network_configs(dev, db_dev_list, cid)
            network_dev_list.append(network_data)
        elif dev.get("vendor") == "RAD":
            network_data = get_rad_network_configs(dev, db_dev_list, cid)
            network_dev_list.append(network_data)

    return network_dev_list


def check_vendor(db_dev_list: List[Dict[str, Any]]):
    """
    Check if the vendor of each device in the list is supported.

    Args:
        db_dev_list (List[Dict[str, Any]]): A list of devices with associated information.

    Raises:
        abort: If an unsupported vendor is found in the device list.
    """
    for dev in db_dev_list:
        if dev.get("vendor") not in ["JUNIPER", "CISCO", "ADVA", "RAD"]:
            abort(500, f"Unsupported Vendor: {dev.get('vendor')}")


def check_active_devices(db_dev_list: List[Dict[str, Any]], skip_cpe_check: bool) -> list:
    """
    Check the status of active devices in the device list.

    Args:
        db_dev_list (List[Dict[str, Any]]): A list of devices with associated information.
        skip_cpe_check (bool): Whether to skip checking CPE devices.

    Returns:
        list: A list of not active devices.

    Raises:
        Exception: If an error occurs while checking device status (unless skip_cpe_check is True).
        abort: If not active devices are found.
    """

    TRIES_FOR_RESULT = 36

    active_devices = {}
    not_active_devices = []

    logger.debug("Check if the devices are active")
    for dev in db_dev_list:
        try:
            dev_id = get_active_device(
                hostname=dev["tid"], timeout=30, polling=False, model=dev.get("model"), device_vendor=dev.get("vendor")
            )
            if dev_id[1]:
                active_devices[dev_id[1]] = dev["tid"]
        except Exception as e:
            if skip_cpe_check:
                not_active_devices.append(dev["tid"])
            else:
                raise e

    logger.debug("Verify that resources are being received from the devices")
    for dev_id, dev_tid in active_devices.items():
        tries = 1
        while tries <= TRIES_FOR_RESULT:
            try:
                res = get_resource_result(dev_id, dev_tid, tries=1)
                if res:
                    break
            except Exception as e:
                logger.error(
                    f"Error when retrieving data from MDSO for attempt {tries} - RESPONSE: {e.data.get('message')}"
                )

            if tries == TRIES_FOR_RESULT:
                abort(502, f"No resource results for device_id: {dev_id}, device_tid: {dev_tid}")
            tries += 1

    logger.debug(f"Inactive devices list: {not_active_devices}")
    return not_active_devices


def filter_devices(db_dev_list: List[Dict[str, Any]]) -> list:
    """
    Filter out MUX devices from the device list.

    Args:
        db_dev_list (List[Dict[str, Any]]): A list of devices with associated information.

    Returns:
        list: A filtered list of devices without MUX devices.
    """
    result = []
    for dev in db_dev_list:
        if all((dev.get("vendor", "") != "GENERIC", "MUX" not in dev.get("model", ""))):
            result.append(dev)
    return result


def get_comparison_db_and_network_data(
    cid: str,
    product_name: str,
    devices: dict,
    path_elements: list,
    zw: str,
    skip_cpe_check: bool = False,
    vgw_ipv4: str = "",
) -> Union[Dict[str, list], bool, str, None]:
    """
    Get a comparison between database and network data for a specific circuit.

    Args:
        cid (str): Customer ID.
        product_name (str): Name of the product.
        devices (dict): Device information.
        path_elements (list): List of path elements.
        zw (str): Identifier used to search for the Z-side CPE.
        skip_cpe_check (bool, optional): Whether to skip checking CPE devices. Defaults to False.
        vgw_ipv4 (str, optional): default to None if not passed in

    Returns:
        Union[Dict[str, list], bool, str, None]: Comparison result, model, IPv4, IPv4 service type,
            IPv4 assigned subnet, and IPv4 glue subnet.
    """

    (db_dev_list, ipv4, ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet) = get_circuit_device_data_from_db(
        cid, devices, path_elements
    )

    if vgw_ipv4:
        ip = vgw_ipv4.split("/")[0]
        cidr = vgw_ipv4.split("/")[1]
        ip = str(ipaddress.ip_interface(ip).ip - 1)
        ipv4 = f"{ip}/{cidr}"
        for device in db_dev_list:
            if device.get("tid").endswith("CW"):
                device["ipv4"] = ipv4

    logger.debug(f"device list from db - {db_dev_list}")

    db_dev_list = filter_devices(db_dev_list)

    check_vendor(db_dev_list)
    inactive_devices = []
    inactive_devices = check_active_devices(db_dev_list, skip_cpe_check)

    z_side_cpe = get_z_side_cpe(db_dev_list, zw)
    network_dev_list = get_network_data(db_dev_list, cid, product_name, ipv4_service_type)
    logger.debug(f"device list from network - {network_dev_list}")

    result = compare_network_and_granite(db_dev_list, network_dev_list, inactive_devices, vgw_ipv4=vgw_ipv4, cid=cid)
    model = z_side_cpe.get("model", "").lower()

    return (result, model, ipv4, ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet)


def uda_legacy_id_matches_cid(circ_path_inst_id: str, device_desc: str) -> bool:
    """This method determines if a legacy ID is part of the description of a device in a circuit"""
    if not circ_path_inst_id:
        logger.error("Unknown circuit path instance ID")
        abort(500, "Unknown circuit path instance ID")
    circuit_uda_info = get_circuit_uda_info(circ_path_inst_id)
    if not circuit_uda_info:
        return False
    if isinstance(circuit_uda_info, list):
        for legacy_data in circuit_uda_info:
            if legacy_data.get("ATTR_NAME") == "L-ID":
                ids = legacy_data.get("ATTR_VALUE").split(",")
                break
        else:
            return False
    for id in ids:
        if id.upper() in device_desc.upper():
            return True


def get_cpe_model(cid: str, devices: dict, path_elements: list, zw: str) -> str:
    """
    Get device list from DB and return the ZW CPE model name that matches the provided ZW

    Args:
        cid (str), devices(dict), path_elements (list), zw (str).

    Returns:
        String: Model name.
    """
    (db_dev_list, ipv4, ipv4_service_type, ipv4_assigned_subnet, ipv4_glue_subnet) = get_circuit_device_data_from_db(
        cid, devices, path_elements
    )
    db_dev_list = filter_devices(db_dev_list)
    z_side_cpe = get_z_side_cpe(db_dev_list, zw)
    model = z_side_cpe.get("model", "").lower()
    return model


def mne_service_check(resp, path_elements, update_path_status=False):
    cpe_installer = "No"
    mne_model = "N/A"
    tid = ""

    # 1 is for the parent org as the product family category status is being updated before update path status
    mne_status_count = len(resp) - 1 if update_path_status else len(resp) - 2
    decomm_list = []

    if mne_status_count > 0:
        # check status of resp to ensure all remaining mne categories are not pending decomm
        # if all are pending decomm check truck roll list and return cpe installer as Yes else No
        for mne_status in resp:
            if mne_status["STATUS"] == "Pending Decommission":
                decomm_list.append(mne_status)

    if mne_status_count == len(decomm_list):
        path_elements.reverse()
        # check path elements to determine mne device

        for device in path_elements:
            if device["ELEMENT_TYPE"] == "PORT":
                if device.get("MODEL", "") in truck_roll_list:
                    cpe_installer = "Yes"
                    mne_model = device["MODEL"]
                    tid = device["TID"]
                    break

    return cpe_installer, mne_model, tid


def update_mne_status(circ_path_inst_id, path_elements, product_family):
    """Finding and updating the status of the MNE Service"""
    mne_name = ""

    mne_dict = {
        "Managed Network Edge": "Meraki Network-Edge",
        "Managed Network Switch": "Meraki Network-Switch",
        "Managed Network Camera": "Meraki Network-Camera",
        "Managed Network IoT Sensor": "Meraki Network-Sensors",
        "Managed Network Additional": "Meraki Network-Teleworker",
        "Managed Network WiFi": "Meraki Network-WiFi",
        "Managed Network Per Room": "Meraki Network-Hospitality WiFi",
    }

    url = granite_mne_url(circ_path_inst_id)
    resp = get_granite(url)

    if isinstance(resp, list):
        for mne in resp:
            if product_family in mne_dict:
                if mne_dict[product_family] == mne["CATEGORY"]:
                    mne_name = mne["NAME"]
                    break

        if mne_name:
            cpe_installer, mne_model, _ = mne_service_check(resp, path_elements)

            update_meraki_status(mne_name)

            return cpe_installer, mne_model
        else:
            abort(500, f"Product family: {product_family} does not match any MNE parent services")

    else:
        abort(500, "Unable to find MNE objects in granite")
