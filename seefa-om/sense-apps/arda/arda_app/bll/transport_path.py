import logging
import re

from math import ceil

from arda_app.bll.cid.site import create_mtu_site
from arda_app.bll.models.device_topology.underlay import UnderlayDeviceTopologyModel
from arda_app.common.cd_utils import (
    get_l1_url,
    granite_cards_url,
    granite_paths_url,
    granite_ports_put_url,
    get_circuit_site_url,
    validate_values,
    will_transport_be_oversubscribed,
)
from common_sense.common.errors import abort
from arda_app.common.utils import convert_bandwidth, bandwidth_in_bps
from arda_app.dll.granite import (
    delete_granite,
    get_available_uplink_ports,
    get_aw_shelf,
    get_circuit_site_info,
    get_equipid,
    get_equipment_buildout,
    get_existing_shelf,
    get_existing_ctbh_cpe_shelf,
    get_equipment_buildout_v2,
    get_granite,
    get_hub_site,
    get_next_available_zw_shelf,
    get_next_zw_shelf,
    get_npa,
    get_qc_available_uplink_ports,
    get_shelf_udas,
    get_sites,
    insert_card_template,
    post_granite,
    put_granite,
    put_port_access_id,
)
from arda_app.dll.mdso import port_available_on_network, qc_port_available_on_network
from arda_app.bll.net_new.ip_reservation.utils.mdso_utils import confirm_router_supports_rphy

logger = logging.getLogger(__name__)


def update_port_access_id(port_inst_id, port_access_id):
    granite_url = granite_ports_put_url()
    params = {"PORT_INST_ID": port_inst_id, "PORT_ACCESS_ID": port_access_id}
    logger.debug(f"UPDATE PORT ACCESS - INST ID: {port_inst_id}")
    logger.debug(f"UPDATE PORT ACCESS - ACCESS ID: {port_access_id}")

    try:
        granite_resp = put_granite(granite_url, params)
        logger.debug(f"GRANITE_UPDATE_PORT_ACCESS_ID: {granite_resp}")
        return granite_resp
    except Exception:
        abort(
            500,
            "Received error when updating port access ID in Granite. "
            "Port Access ID has not been updated. Error Code: G016",
        )


def get_existing_path_elements(cid):
    """get existing transport paths for a circuit ID from Granite"""
    """Return false if no transport paths exist for given circuit ID"""
    endpoint = (
        "/pathElements"
        f"?CIRC_PATH_HUM_ID={cid}&"
        "ELEMENT_CATEGORY=ROUTER,SWITCH,NIU&LVL=2&"
        "SERVICE_TYPE_NOT=NNI&wildCardFlag=1&PATH_A_SITE_TYPE=HUB,HEAD END, HE-HUB"
    )

    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_TRANSPORT_RESPONSE: {granite_resp}")
        path_elements = granite_resp[0]

        if "PATH_NAME" not in path_elements or "PATH_STATUS" not in path_elements:
            return

        return granite_resp
    except Exception:
        return


def get_existing_transports(body):
    target_clli, target_site_name, _ = get_circuit_path_info(body)
    transport_path_template = f"{target_clli}_ZW"
    transport_circuit_sites_resp = get_circuit_site_info(transport_path_template, 1)
    if isinstance(transport_circuit_sites_resp, dict):
        return

    # Filter for valid transports (exclude trunked handoffs and transports to overlay devices)
    transport_circuit_sites_resp = [
        path for path in transport_circuit_sites_resp if path.get("SERVICE_TYPE") == "INT-ACCESS TO PREM TRANSPORT"
    ]

    for transport in transport_circuit_sites_resp:
        transport_path_name = transport.get("CIRCUIT_NAME")
        transport_z_site_name = transport.get("Z_SITE_NAME")
        transport_status = transport["CIRCUIT_STATUS"]

        if transport_z_site_name == target_site_name:
            if "Planned" in transport_status or "Designed" in transport_status:
                if use_existing_transport(body, transport_path_name):
                    logger.debug("Found existing transport path that passes checks to be use for CID")
                    return {"transport_path": transport_path_name, "transport_status": "use_existing_transport"}
            logger.debug("Found existing transport path (circuit sites) with matching z-side site name")
            return {"transport_path": transport_path_name, "transport_status": transport_status}


def get_circuit_path_info(payload):
    cid = payload["circuit_id"]
    service_location_address = payload["service_location_address"]
    granite_site_name = payload.get("granite_site_name")

    granite_resp = get_circuit_site_info(cid)

    if isinstance(granite_resp, dict) and "retString" in granite_resp:
        abort(500, f"Error Code: G001 - Circuit site info not found in Granite for Circuit ID {cid}")
    elif isinstance(granite_resp, list):
        if len(granite_resp) == 1:
            z_site = granite_resp[0]["Z_SITE_NAME"]
            z_clli = granite_resp[0]["Z_CLLI"]
            a_site = granite_resp[0].get("A_SITE_NAME")
            a_clli = granite_resp[0].get("A_CLLI")

            if granite_site_name:
                if a_site and a_clli and granite_site_name == a_site:
                    return a_clli, a_site, granite_resp[0]
                elif granite_site_name == z_site:
                    return z_clli, z_site, granite_resp[0]
                logger.info(
                    f"No Granite A or Z site name match for CID: {cid} with Granite Site Name: {granite_site_name}"
                )

            if a_site and a_clli and service_location_address in a_site:
                return a_clli, a_site, granite_resp[0]
            else:
                return z_clli, z_site, granite_resp[0]
        else:
            abort(500, f"Multiple revisions found for cid: {cid}")


def use_existing_transport(body, transport_path):
    needed_bw = bandwidth_in_bps(body["bandwidth_value"], body["bandwidth_type"])
    order_account_id = get_order_account_id(body["circuit_id"])
    # Check existing customers in channels
    if not account_id_match(transport_path, order_account_id):
        return
    else:
        if not will_transport_be_oversubscribed(transport_path, needed_bw):
            # check for DO NOT USE status on CW.QW path
            cw_path = f"CW.{transport_path.split('.')[2]}"
            check_transport_status(cw_path)

            circuit_path_data = create_circuit_path_data(body["circuit_id"])
            transport_path_data = get_transport_path_data(transport_path)
            granite_add_path_elements(body["circuit_id"], circuit_path_data, transport_path_data)
            return transport_path
        else:
            abort(500, f"Found Existing Transport {transport_path} would be oversubscribed")


def account_id_match(transport_path, order_account_id):
    endpoint = f"/pathChanAvailability?PATH_NAME={transport_path}"
    granite_resp = get_granite(endpoint)
    if isinstance(granite_resp, dict):
        # Orphaned transport with no channels that we will go ahead and use
        return True
    for chan in granite_resp:
        if chan.get("NEXT_CUSTOMER", chan.get("MEMBER_CUSTOMER")) == order_account_id:
            return True


def get_order_account_id(cid):
    granite_resp = get_granite(f"/paths?CIRC_PATH_HUM_ID={cid}")
    if isinstance(granite_resp, dict):
        abort(500, f"No Paths found for CID {cid} - Error Code: G021")
    return granite_resp[0]["orderingCustomer"]


def create_circuit_path_data(cid):
    """populates site info for a circuit path given circuit ID"""
    granite_resp = get_circuit_site_info(cid)
    circuit_path_data = {}

    try:
        logger.debug(f"CIRCUIT ID CIRCUIT SITE RESP: {granite_resp}")
        data = granite_resp[0]
        circuit_path_data["z_site_name"] = data.get("Z_SITE_NAME")
        circuit_path_data["CIRC_PATH_INST_ID"] = data.get("CIRC_PATH_INST_ID")
        circuit_path_data["leg_name"] = data.get("LEG_NAME")
        circuit_path_data["leg_inst_id"] = data.get("LEG_INST_ID")
        circuit_path_data["z_clli"] = data.get("Z_CLLI")
        circuit_path_data["a_site_name"] = data.get("A_SITE_NAME", "")
        circuit_path_data["A_ADDRESS"] = data.get("A_ADDRESS", "")
        circuit_path_data["Z_ADDRESS"] = data.get("Z_ADDRESS", "")
        return circuit_path_data
    except (IndexError, KeyError):
        abort(500, f"Error Code: G001 - Circuit site info not found in Granite for Circuit ID {cid}")
    except Exception:
        abort(500, f"Error parsing circuit site info for Circuit ID {cid} - Error Code: G002")


def get_transport_path_data(transport_path_name):
    """populates site info for a transport path given transport ID"""
    transport_path_data = {}
    granite_resp = get_circuit_site_info(transport_path_name)

    try:
        logger.debug(f"TRANSPORT PATH CIRCUIT SITE RESP: {granite_resp}")
        data = granite_resp[0]
        transport_path_data["path_inst_id"] = data.get("CIRC_PATH_INST_ID")
        transport_path_data["leg_name"] = data.get("LEG_NAME")
        transport_path_data["leg_inst_id"] = data.get("LEG_INST_ID")
        transport_path_data["z_site_name"] = data.get("Z_SITE_NAME")
        return transport_path_data
    except (IndexError, KeyError):
        abort(500, f"Circuit site info not found in Granite for Transport Path {transport_path_name}. Error Code: G003")
    except Exception:
        abort(500, f"Error parsing circuit site info for Transport Path {transport_path_name}. Error Code: G004")


def get_port_access_id(slot, equipment):
    shelf = int(equipment.split("#")[1])
    port_access_id = f"{shelf}/0/{slot}"
    return port_access_id


def _get_next_available_port(port_dict):
    """
    Description:

    loops through a list of uplink ports, checking if the port is available on the Network
    loop stops at first port that is available and returns that port

    @return uplink_port and circuit_path_data
    """

    attempt_onboarding = port_dict["attempt_onboarding"]
    build_type_mtu = port_dict["build_type_mtu"]
    bw_type = port_dict["bandwidth_type"]
    bw_value = port_dict["bandwidth_value"]
    cid = port_dict["cid"]
    hub_clli_code = port_dict["hub_clli_code"]
    product = port_dict["product"]

    timeout = 180
    bandwidth_string, optic, card_template = convert_bandwidth(bw_type, bw_value, build_type_mtu)
    port_list = get_available_uplink_ports(hub_clli_code, bandwidth_string)

    if product == "FC + Remote PHY":
        port_list = filter_rphy(port_list, cid)

    new_port_list = filter_edr(port_list)

    for port in range(len(new_port_list)):
        uplink_port = new_port_list[port]

        # check for DO NOT USE status on equipment
        check_equipment_status(uplink_port)

        if uplink_port["MODEL"].startswith("ACX"):
            optic = "XE"

        logger.debug(f"PORT #{port}: {uplink_port}")

        if port_available_on_network(uplink_port, optic, hub_clli_code, timeout, attempt_onboarding):
            if not uplink_port.get("OPTIC_TEMPLATE") or (uplink_port["OPTIC_TEMPLATE"] != card_template):
                if uplink_port.get("OPTIC_TEMPLATE"):
                    # Existing card template doesn't match determined template. Delete existing
                    delete_payload = {
                        "SHELF_NAME": uplink_port["EQUIP_NAME"],
                        "SLOT_INST_ID": uplink_port["SLOT_INST_ID"],
                    }
                    delete_granite("/cards", delete_payload)

                # Add card template
                if uplink_port.get("VENDOR") == "JUNIPER" and uplink_port.get("TYPE") == "ROUTER":
                    # Change to LEVEL 2 card template for MXs
                    if card_template == "GENERIC SFP LEVEL 1":
                        card_template = "GENERIC SFP LEVEL 2"
                    else:
                        card_template = "GENERIC XFP LEVEL 2"

                insert_card_template(uplink_port, card_template)

                # Go get new PORT_INST_ID after loading card
                device_ports = get_equipment_buildout(uplink_port["EQUIP_NAME"].split("/")[0])

                for port in device_ports:
                    if port["SLOT_INST_ID"] == uplink_port["SLOT_INST_ID"]:
                        uplink_port["PORT_INST_ID"] = port["PORT_INST_ID"]
                        break

            # Set port access ID
            update_port_access_id(uplink_port["PORT_INST_ID"], f"{optic}-{uplink_port['PORT_ACCESS_ID']}")

            return uplink_port


def check_equipment_status(uplink_port):
    if uplink_port.get("PORT_STATUS") in {"DO-NOT-USE", "DO NOT USE"}:
        abort(500, f"Found status 'DO NOT USE' for equipment {uplink_port['EQUIP_NAME']}")

    equip_name = uplink_port["EQUIP_NAME"].split("/")[0]
    equipment_build_data = get_equipment_buildout(equip_name)

    if equipment_build_data[0].get("EQUIP_STATUS") in {"DO-NOT-USE", "DO NOT USE"}:
        abort(500, f"found status 'DO NOT USE' for equipment {equip_name}")


def check_transport_status(circuit_name):
    transport_data = get_circuit_site_info(circuit_name, wild_card_flag=1)

    if isinstance(transport_data, list):
        if transport_data[0].get("CIRCUIT_STATUS") in {"DO-NOT-USE", "DO NOT USE"}:
            abort(500, f"found status 'DO NOT USE' for transport {transport_data[0].get('CIRCUIT_NAME')}")


def filter_edr(port_list):
    # get distinct cllis
    qw_tid_set = set()

    for item in port_list:
        qw_tid_set.add(item["EQUIP_NAME"].split("/")[0])

    # get cw_transport_paths CW.{clli}.
    new_port_set = set()

    for tid in qw_tid_set:
        granite_url = f"/circuitSites?CIRCUIT_NAME=CW.{tid}&WILD_CARD_FLAG=1&PATH_CLASS=P"
        granite_resp = get_granite(granite_url)

        if isinstance(granite_resp, list):
            for transport_path in granite_resp:
                # EDR check
                qw = transport_path["CIRCUIT_NAME"].split(".")[-1]
                cw = transport_path["CIRCUIT_NAME"].split(".")[-2]

                resp = edna_check_w_equipid(cw)

                if resp:
                    new_port_set.add(qw)
        elif isinstance(granite_resp, dict):
            logger.info(f"No transport_path found for {tid}.")

    new_port_list = []

    if new_port_set:
        for item in port_list:
            if item["EQUIP_NAME"].split("/")[0] in new_port_set:
                new_port_list.append(item)

        return new_port_list

    return port_list


def edna_check_w_equipid(equip_name: str) -> bool:
    """
    Check if device has NETWORK ROLE of ENTERPRISE DISTRIBUTION ROUTER.

    Returns:
    - bool: True if the device has the specified role, False otherwise.
    """
    a_device_udas = get_equipid(equip_name)

    if not isinstance(a_device_udas, list):
        return False

    for device in a_device_udas:
        uda_list = get_shelf_udas(device["EQUIP_INST_ID"])

        if not isinstance(uda_list, list):
            return False

        a_network_role = [uda.get("ATTR_VALUE") for uda in uda_list if uda.get("ATTR_NAME") == "NETWORK"]

        if "EDNA" in a_network_role:
            return True

        return False


def find_or_create_mtu_site(clli):
    """
    Looks for an MTU site. If MTU is not found, uses building site data to create MTU site.
    Falls out if no building site is found.
    """
    sites = get_sites(clli)
    building_site = None
    try:
        for site in sites:
            if site["siteType"] == "ACTIVE MTU":
                return site["siteName"]

            if site["siteType"] == "BUILDING":
                building_site = site

        if building_site is None:
            abort(500, "Building site not found when trying to create MTU site.")

        name = f"{building_site['clli']}-MTU//{building_site['address']}"
        site_clli = building_site["clli"]
        mtu_site = {
            "name": name,
            "site_clli": site_clli,
            "lat": building_site["latitude"],
            "lon": building_site["longitude"],
            "zip_code": building_site["zip1"],
            "parent": building_site["clli"],
            "type": "ACTIVE MTU",
            "address": building_site["address"],
            "city": building_site["city"],
            "state": building_site["state"],
            "gems_key": building_site["gemBuildingKeyUda"],
        }
        create_mtu_site(mtu_site)
        return name
    except Exception:
        abort(500, f"Error creating MTU site for CLLI: {clli}")


def _create_transport_path_at_granite(transport_path_name, bandwidth_string, a_site_name, z_site_name, build_type_mtu):
    """post new transport path to Granite"""
    granite_url = granite_paths_url()

    if build_type_mtu:
        uda_product_service = "INT-EDGE TRANSPORT"
    else:
        uda_product_service = "INT-ACCESS TO PREM TRANSPORT"

    params = {
        "PATH_NAME": transport_path_name,
        "PATH_TEMPLATE_NAME": "WS ETHERNET TRANSPORT",
        "PATH_BANDWIDTH": bandwidth_string,
        "TOPOLOGY": "Point to point",
        "A_SITE_NAME": a_site_name,
        "Z_SITE_NAME": z_site_name,
        "PATH_STATUS": "Planned",
        "PATH_MAX_OVER_SUB": "0",
        "UDA": {"SERVICE TYPE": {"PRODUCT/SERVICE": uda_product_service, "SERVICE MEDIA": "FIBER"}},
        "UPDATE_LEG": "true",
        "LEG_NAME": "1",
        "LEG_A_SITE_NAME": a_site_name,
        "LEG_Z_SITE_NAME": z_site_name,
        "SET_CONFIRMED": "TRUE",
    }
    return post_granite(granite_url, params)


def _create_transport_path_at_granite_for_qc(
    transport_path_name, bandwidth_string, a_site_name, transport_z_site, service_type
):
    """post new transport path to Granite for qc"""
    granite_url = granite_paths_url()

    params = {
        "PATH_NAME": transport_path_name,
        "PATH_TEMPLATE_NAME": "WS ETHERNET TRANSPORT",
        "PATH_BANDWIDTH": bandwidth_string,
        "TOPOLOGY": "Point to point",
        "A_SITE_NAME": a_site_name,
        "Z_SITE_NAME": transport_z_site,
        "PATH_STATUS": "Planned",
        "PATH_MAX_OVER_SUB": "0",
        "UDA": {"SERVICE TYPE": {"PRODUCT/SERVICE": service_type, "SERVICE MEDIA": "FIBER"}},
        "UPDATE_LEG": "true",
        "LEG_NAME": "1",
        "LEG_A_SITE_NAME": a_site_name,
        "LEG_Z_SITE_NAME": transport_z_site,
        "SET_CONFIRMED": "TRUE",
    }
    return post_granite(granite_url, params)


def _reserve_port_on_granite(transport_path_data, uplink_port):
    """reserve uplink port in Granite"""
    granite_url = granite_paths_url()

    payload = {
        "PATH_NAME": transport_path_data["transport_path_name"],
        "PATH_REV_NBR": "1",
        "PATH_INST_ID": transport_path_data["path_inst_id"],
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
        "PORT_INST_ID": uplink_port["PORT_INST_ID"],
        "LEG_NAME": transport_path_data["leg_name"],
        "PATH_LEG_INST_ID": transport_path_data["leg_inst_id"],
    }
    return put_granite(granite_url, payload)


def update_port_status(port_inst_id, port_status):
    """update port status in Granite"""
    granite_url = granite_ports_put_url()
    payload = {"PORT_INST_ID": port_inst_id, "PORT_STATUS": port_status}
    return put_granite(granite_url, payload)


def granite_add_path_elements(cid, circuit_path_data, transport_path_data, path_elem_sequence="1"):
    granite_url = granite_paths_url()

    payload = {
        "PATH_NAME": cid,
        "PATH_REV_NBR": "1",
        "PATH_INST_ID": circuit_path_data["CIRC_PATH_INST_ID"],
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": path_elem_sequence,
        "PATH_ELEMENT_TYPE": "CIRC_PATH_CHANNEL",
        "PARENT_PATH_INST_ID": transport_path_data["path_inst_id"],
        "LEG_NAME": transport_path_data["leg_name"],
        "PATH_LEG_INST_ID": transport_path_data["leg_inst_id"],
    }
    return put_granite(granite_url, payload)


def create_transport_path_main(body, attempt_onboarding):
    """compose ethernet transport path using construction data and calls to Granite"""
    target_clli, target_site_name, circuit_path_data = get_circuit_path_info(body)

    transport_z_site = target_site_name
    build_type_mtu = False

    if "MTU" in body.get("build_type", ""):
        build_type_mtu = True
        shelf = get_aw_shelf(target_clli)

        if shelf[-3:] != "1AW":
            abort(500, "1AW MTU shelf exists, please investigate")

        transport_z_site = find_or_create_mtu_site(target_clli)
    else:
        if "CTBH" in body["product_name_order_info"]:
            shelf = get_existing_ctbh_cpe_shelf(target_clli, target_site_name)

            if isinstance(shelf, dict):  # no equipment found in granite
                # CTBH CPE TIDs are CLLI + 7(n)W where n is numeric between 0-9 starting at 1
                # https://chalk.charter.com/display/public/NPD/Equipment+Naming+Standards#EquipmentNamingStandards-EntityCodes
                range_list = [str(i) for i in range(1, 10)] + ["0"]
                shelf = ""

                for x in range_list:
                    a_shelf = f"{target_clli}7{x}W"
                    shelf_exists_check = get_equipment_buildout_v2(a_shelf)

                    if isinstance(shelf_exists_check, dict):
                        shelf = a_shelf
                        break

                if not shelf:
                    msg = f"All CTBH CPE shelf TIDs of 71W to 70W are in use at site: {target_site_name}"
                    logger.error(msg)
                    abort(500, msg)
        else:
            shelf = get_existing_shelf(target_clli, target_site_name)

            # existing equipment check for Cradlepoint
            if isinstance(shelf, list) and shelf[0]["EQUIP_VENDOR"] != "CRADLEPOINT":
                msg = "Found existing cpe that is not tied to a transport path"
                logger.error(msg)
                abort(500, msg)

            shelf = get_next_available_zw_shelf(target_clli, target_site_name)

    hub_clli_code = body["hub_clli_code"]
    bandwidth_type = body["bandwidth_type"]
    bandwidth_value = body["bandwidth_value"]
    product = body["product_name_order_info"]

    # updating bandwith to 10 Gbps for any circuit BW over 500 Mbps
    if bandwidth_type == "Gbps" or int(bandwidth_value) >= 500 or product == "FC + Remote PHY":
        bandwidth_value = "10"
        bandwidth_type = "Gbps"

    bandwidth_string, _, _ = convert_bandwidth(bandwidth_type, bandwidth_value, build_type_mtu)
    npa_nxx = get_npa(hub_clli_code)

    port_dict = {
        "hub_clli_code": hub_clli_code,
        "bandwidth_type": bandwidth_type,
        "bandwidth_value": bandwidth_value,
        "build_type_mtu": build_type_mtu,
        "attempt_onboarding": attempt_onboarding,
        "cid": body["circuit_id"],
        "product": product,
    }

    uplink_port = _get_next_available_port(port_dict)

    if uplink_port is None:
        abort(
            500,
            "Error Code: G018 - No available ports. CLLI Code: "
            f"{hub_clli_code}, Bandwidth: {bandwidth_value} {bandwidth_type}",
        )

    circuit_path_data["A_SITE_NAME"] = uplink_port["SITE_NAME"]
    equip_name = uplink_port["EQUIP_NAME"].split("/")[0]

    if equip_name.endswith("QW"):
        # check for DO NOT USE status on CW.QW path
        cw_path = f"CW.{equip_name}"
        check_transport_status(cw_path)

    transport_path_name = f"{npa_nxx[:2]}001.GE{bandwidth_string.split(' ')[0]}.{equip_name}.{shelf}"

    _create_transport_path_at_granite(
        transport_path_name, bandwidth_string, circuit_path_data["A_SITE_NAME"], transport_z_site, build_type_mtu
    )

    transport_path_data = get_transport_path_data(transport_path_name)
    transport_path_data["transport_path_name"] = transport_path_name

    _reserve_port_on_granite(transport_path_data, uplink_port)

    """update_port_status(uplink_port['PORT_INST_ID'], "Assigned") """
    existing_path_elements = get_existing_path_elements(body["circuit_id"])

    if not existing_path_elements:
        granite_add_path_elements(body["circuit_id"], circuit_path_data, transport_path_data)
    else:
        abort(
            500,
            f"Circuit path duplication attempted - transport path found: {existing_path_elements[0].get('PATH_NAME')}",
        )

    return transport_path_data["transport_path_name"]  # Created/mocked


def quick_connect_create_transport_path(cid, agg_bandwidth, side="z_side"):
    """Create and post transport path to Granite"""
    result = _get_parent_site(cid)

    clli = result["z_clli" if side == "z_side" else "a_clli"]
    site_name = result["z_site_name" if side == "z_side" else "a_site_name"]
    next_zw_shelf = ""
    good_status = ("Live", "Designed", "Planned", "Auto-Designed", "Auto-Planned")
    good_vendor = ("RAD", "ADVA")

    resp = get_existing_shelf(clli, site_name)

    # vendor equipment check may be needed
    if isinstance(resp, list):
        if len(resp) > 1:  # checking response for multiple devices
            logger.error("Multiple equipment exist at the customer's site")
            abort(500, "Multiple equipment exist at the customer's site")
        elif resp[0]["EQUIP_STATUS"] not in good_status:  # single device in unsupported status(pending decommission)
            logger.error("Existing equipment status is unsupported")
            abort(
                500,
                f"Existing cpe {resp[0]['TARGET_ID']} has a status of {resp[0]['EQUIP_STATUS']} which is unsupported",
            )
        elif resp[0]["EQUIP_VENDOR"] not in good_vendor:  # single device in unsupported vendor(Cisco)
            logger.error("Existing equipment vendor is unsupported")
            abort(
                500,
                f"Existing cpe {resp[0]['TARGET_ID']} has a vendor of {resp[0]['EQUIP_VENDOR']} which is unsupported",
            )
        else:  # single device in good status and good vendor
            next_zw_shelf = resp[0]["TARGET_ID"]

    if not next_zw_shelf:
        next_zw_shelf = get_next_zw_shelf(clli)

    bandwidth = agg_bandwidth.lower()

    if "gbps" in bandwidth:
        bandwidth_value_type = re.split(r"(gbps)", bandwidth)
    elif "mbps" in bandwidth:
        bandwidth_value_type = re.split(r"(mbps)", bandwidth)
    else:
        abort(500, f"Payload agg_bandwidth field {agg_bandwidth} is invalid")

    bandwidth_value = bandwidth_value_type[0].strip()

    if "." in bandwidth_value:
        # Always round up
        bandwidth_value = str(ceil(float(bandwidth_value)))
    bandwidth_type = bandwidth_value_type[1].strip()

    bandwidth_string = (
        "10 Gbps" if bandwidth_type == "gbps" or (bandwidth_type == "mbps" and int(bandwidth_value) >= 500) else "1 Gbps"
    )

    mtu_ports = get_qc_available_uplink_ports(clli, bandwidth_string)

    uplink = get_qc_uplink_port_for_tp(mtu_ports, clli, bandwidth_string)

    if uplink is None:
        abort(
            500,
            "Error Code: G018 - No available ports for Circuit ID: "
            f"{cid}, CLLI Code: {clli}, Bandwidth: {bandwidth_string}",
        )
    # TODO reformat Juniper vendor logic to use mtu_ports from above and slide line 744 over under assign_card_qc
    if mtu_ports[0]["VENDOR"] == "JUNIPER":
        mtu_ports = get_qc_available_uplink_ports(clli, bandwidth_string)
        for x in mtu_ports:
            if uplink.casefold() in x.get("EXPECTED_PAID").casefold():
                if "PORT_INST_ID" not in x:
                    assign_card_qc(x)

    mtu_ports = get_qc_available_uplink_ports(clli, bandwidth_string)

    npa_nxx = get_npa(clli, "MTU")

    equip_name = ""
    site_name = ""
    uplink_port = ""

    for x in mtu_ports:
        if uplink.casefold() in x.get("EXPECTED_PAID").casefold():
            equip_name = x.get("EQUIP_NAME")
            site_name = x.get("SITE_NAME")
            uplink_port = x
            put_port_access_id(x.get("PORT_INST_ID"), x.get("EXPECTED_PAID"))
            break

    transport_path_name = (
        f"{npa_nxx[:2]}001.GE{bandwidth_string.split(' ')[0]}.{equip_name.split('/')[0]}.{next_zw_shelf}"
    )
    circuit_path_data = create_circuit_path_data(cid)
    build_type_mtu = "INT-ACCESS TO PREM TRANSPORT"

    # granite_path_elements_l1 = get_existing_path_elements_for_qc(cid)
    transport_site = circuit_path_data["z_site_name" if side == "z_side" else "a_site_name"]
    # transport_z_site = find_or_create_mtu_site(circuit_path_data["z_clli"])

    _create_transport_path_at_granite_for_qc(
        transport_path_name, bandwidth_string, site_name, transport_site, build_type_mtu
    )
    transport_path_data = get_transport_path_data(transport_path_name)
    transport_path_data["transport_path_name"] = transport_path_name

    _reserve_port_on_granite(transport_path_data, uplink_port)
    update_port_status(uplink_port["PORT_INST_ID"], "Assigned")
    granite_add_path_elements(cid, circuit_path_data, transport_path_data)

    return transport_path_name


def get_qc_uplink_port_for_tp(mtu_ports, z_clli, bandwidth_string):
    """Find and return the uplink port that matched Granite, Network and Device topology"""
    if bandwidth_string == "1 Gbps":
        card_template = ["GENERIC SFP LEVEL 1", "GENERIC SFP"]
    else:
        card_template = ["GENERIC SFP+", "GENERIC SFP+ LEVEL 1", "GENERIC XFP LEVEL 1", "GENERIC 10GE SFP+ LEVEL 1"]

    for port in range(len(mtu_ports)):
        try:
            mtu_port = mtu_ports[port]
            logger.debug(f"PORT #{port}: {mtu_port}")
        except Exception:
            abort(500, f"No MTU ports found in Granite for CLLI: {z_clli}. Bandwidth: {bandwidth_string}")

        if "CARD_TEMPLATE_NAME" in mtu_port:
            # Check to see if the optic matches our bandwidth
            if mtu_port["CARD_TEMPLATE_NAME"] not in card_template:
                logger.debug("OPTIC does not match bandwidth, skipping port")
                continue

            # calling MDSO for available network ports
            network_ports = qc_port_available_on_network(mtu_port, z_clli, 180, False)

            if mtu_port["VENDOR"] == "RAD":
                port = qc_port_for_rad(mtu_ports, network_ports, bandwidth_string)

                if port:
                    return port
                else:
                    abort(500, "no supported ports found for RAD device")

            elif mtu_port["VENDOR"] == "ADVA":
                port = qc_port_for_adva(mtu_ports, network_ports, bandwidth_string)

                if port:
                    return port
                else:
                    abort(500, "no supported ports found for Adva device")

            elif mtu_port["VENDOR"] == "JUNIPER":
                equip_name = mtu_port["EQUIP_NAME"].split("/")[0]
                port = f"{mtu_port['EXPECTED_PAID'].lower()}"

                if not network_ports:
                    logger.error(
                        f"No data returned from MDSO 'show_interface_config' operation for {equip_name} and {port}"
                    )
                    continue

                # check for valid configuration values in the returned data; if not present fallout
                configuration = None

                try:
                    configuration = network_ports.get("result").get("data").get("configuration")
                except AttributeError:
                    logger.exception(
                        f"Invalid data returned from MDSO 'show_interface_config' operation for {equip_name} and "
                        f"{port} \nResponse: {network_ports}"
                    )
                    continue

                # configuration should be present but should be None if no port assignment, so check is complete
                if not configuration:
                    if port in underlay_topology_model_available_handoffs(
                        mtu_port["MODEL"], bandwidth_string, "JUNIPER"
                    ):
                        return port

                # if configuration present but has values, get 'interfaces' item to make the rest of this more readable
                try:
                    interface = (
                        network_ports.get("result").get("data").get("configuration").get("interfaces").get("interface")
                    )
                except AttributeError:
                    # do not need to log or take any action here because this means no values exist,
                    # so our check is complete
                    if port in underlay_topology_model_available_handoffs(
                        mtu_port["MODEL"], bandwidth_string, "JUNIPER"
                    ):
                        return port

                # if we do have an interface object, validate whether there are any possible port assignments
                unit = None

                try:
                    unit = interface.get("unit")
                except AttributeError:
                    # no need to log or abort, if no existing value our check is complete
                    if port in underlay_topology_model_available_handoffs(
                        mtu_port["MODEL"], bandwidth_string, "JUNIPER"
                    ):
                        return port

                """ If we do have a 'unit' object that isn't None, we need to check if there is more than one unit
                 (fallout) If only one unit object check it for possible assignments. """
                if not unit:
                    if port in underlay_topology_model_available_handoffs(
                        mtu_port["MODEL"], bandwidth_string, "JUNIPER"
                    ):
                        return port

                if unit:
                    try:
                        possible_assignment = unit.get("family").get("ethernet-switching")
                    except AttributeError:
                        # no need to log or abort, if no existing value our check is complete
                        if port in underlay_topology_model_available_handoffs(
                            mtu_port["MODEL"], bandwidth_string, "JUNIPER"
                        ):
                            return port

                    if possible_assignment:
                        logger.info(
                            f"Possible assignment found in MDSO for {port} on {equip_name}MDSO Assignment Data: {unit}"
                        )
                        continue

                    if isinstance(unit, list):
                        logger.error(
                            f"Possible assignment found in MDSO for {port} on {equip_name} "
                            f"\nList value returned for 'unit' implying multiple entries: \n{unit}"
                        )
                        continue
        else:
            abort(500, "card template mismatch or no ports matched on Granite, Network and device topology")


def underlay_topology_model_available_handoffs(model, bandwidth, vendor):
    device_topology = UnderlayDeviceTopologyModel(
        role="mtu", device_bw=bandwidth, connector_type="LC", vendor=vendor, model=model
    )
    handoff_ports = device_topology.get_available_handoff_ports(circuit_bandwidth=bandwidth)
    supported_ports = []

    if vendor == "RAD":
        for port in handoff_ports:
            supported_ports.append(port[0])
    elif vendor == "ADVA":
        for port in handoff_ports:
            supported_ports.append(port[1])
    elif vendor == "JUNIPER":
        for port in handoff_ports:
            supported_ports.append(port[1].lower())

    return supported_ports


def qc_port_for_rad(uplink_ports, network_ports, bandwidth):
    port_data = network_ports["result"]
    ports = {p["name"].replace("ETH-", ""): p for p in port_data}

    ports_cleaned = {}

    for x, v in ports.items():
        try:
            if v["details"]["oper"] and v["details"]["admin"]:
                ports_cleaned[x] = v
        except KeyError:
            pass

    supported_ports = {
        k: v
        for k, v in ports_cleaned.items()
        if v["details"]["admin"] not in ("active", "up") and v["details"]["oper"] not in ("in use", "up")
    }
    for p in range(len(uplink_ports)):
        try:
            # if uplink_ports[p]["CARD_STATUS"] == "Planned" and uplink_ports[p]["PORT_STATUS"] == "Ok":
            # if uplink_ports[p]["PORT_STATUS"] == "Ok":
            gport = uplink_ports[p]["EXPECTED_PAID"].replace("ETH PORT ", "")

            for nport in supported_ports:
                if gport.casefold() == supported_ports[nport]["name"].replace("ETH-", "").casefold():
                    if gport in underlay_topology_model_available_handoffs(uplink_ports[p]["MODEL"], bandwidth, "RAD"):
                        try:
                            if uplink_ports[p]["PORT_STATUS"] in ("Ok", "AVAILABLE", "Assigned", "Unassigned"):
                                return gport
                        except (KeyError, AttributeError):
                            card_template = "GENERIC SFP LEVEL 1"

                            if bandwidth == "10 Gbps":
                                card_template = "GENERIC SFP+ LEVEL 1"

                            insert_card_template(uplink_ports[p], card_template)
                            return gport
        except (KeyError, AttributeError):
            pass

    logger.error("No matching ports found on the Network and Granite for Rad device")
    return False


def qc_port_for_adva(uplink_ports, network_ports, bandwidth):
    ports = {p["properties"]["name"][-1]: p["properties"] for p in network_ports["result"][0]["eth"]}

    try:
        supported_ports = {k: v for k, v in ports.items() if (v["admin_state"] == "unassigned")}
    except KeyError:
        pass

    for p in range(len(uplink_ports)):
        try:
            # if uplink_ports[p]["CARD_STATUS"] == "Planned" and uplink_ports[p]["PORT_STATUS"] == "Ok":
            # if uplink_ports[p]["PORT_STATUS"] == "Ok":
            gport = uplink_ports[p]["EXPECTED_PAID"]

            for nport in supported_ports:
                if gport.casefold() == supported_ports[nport]["name"].casefold():
                    if gport in underlay_topology_model_available_handoffs(uplink_ports[p]["MODEL"], bandwidth, "ADVA"):
                        try:
                            if uplink_ports[p]["PORT_STATUS"] in ("Ok", "AVAILABLE", "Assigned", "Unassigned"):
                                return gport
                        except (KeyError, AttributeError):
                            card_template = "GENERIC SFP LEVEL 1"

                            if bandwidth == "10 Gbps":
                                card_template = "GENERIC SFP+ LEVEL 1"

                            insert_card_template(uplink_ports[p], card_template)
                            return gport
        except (KeyError, AttributeError):
            pass

    logger.error("No matching ports found on the Network and Granite for Adva device")
    return False


def get_existing_path_elements_for_qc(cid):
    """get existing transport paths for a circuit ID from Granite for quick connect"""
    endpoint = get_l1_url(cid)

    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"GRANITE_L1_PATH_ELEMENTS_RESPONSE: {granite_resp}")
        path_elements = granite_resp[0]

        if "PATH_Z_SITE" not in path_elements:
            return

        return granite_resp
    except Exception:
        return


def assign_card_qc(mtu_port):
    card_assign_payload = {
        "SHELF_NAME": mtu_port["EQUIP_NAME"],
        "CARD_TEMPLATE_NAME": mtu_port["CARD_TEMPLATE_NAME"],
        "SLOT_INST_ID": mtu_port["SLOT_INST_ID"],
    }
    _card_the_slot(card_assign_payload)


def lookup_hub_clli(hub_clli_code):
    """Attempt to find hub CLLI based on bad payload CLLI"""
    # Replace non-alphanumeric with spaces
    parsed_clli = re.sub("[^a-zA-Z\\d\\s:]", " ", hub_clli_code)
    parsed_clli = parsed_clli.split()[0].upper()

    if len(parsed_clli) <= 3:
        abort(500, f"Unable to determine hub with hub_clli_code: {hub_clli_code}")

    resp = get_hub_site(parsed_clli)

    if resp and len(resp) == 8:
        return resp

    abort(500, f"Unable to determine hub with hub_clli_code: {hub_clli_code}")


def _card_the_slot(slot_vals):
    """Puts a card in the slot. Returns None on success."""
    logger.info(f"Assigning card to slot \nPayload: \n{slot_vals}")
    url = granite_cards_url()
    data = post_granite(url, slot_vals, timeout=60)

    if not data:
        logger.error(f"No data returned from Granite, unable to assign card. \nURL: {url} \nPayload: {slot_vals}")
        abort(500, "No data returned from Granite, unable to assign card.", url=url, payload=slot_vals)

    # validate response from Granite
    try:
        if data["retString"].lower() != "card added":
            logger.error(
                f"Assigning card failed, error code {data['httpCode']} received from Granite. "
                f"\nURL: {url} \nPayload: \n{slot_vals} \nResponse: \n{data}"
            )
            abort(
                500,
                f"Assigning card failed, error code {data['httpCode']} received from Granite.",
                url=url,
                payload=slot_vals,
                response=data,
            )
    except Exception:
        logger.exception(
            "Unexpected Granite response, card assignment failed \n"
            f"URL: {url} \nPayload: {slot_vals} \nResponse: \n{data}"
        )
        abort(
            500, "Card assignment unsuccessful, unexpected Granite response", url=url, payload=slot_vals, response=data
        )


def _get_parent_site(cid):
    """Retrieves initial site data for the parent path"""
    logger.info(f"Obtaining site data for {cid}")

    # Set up and make the call
    url = get_circuit_site_url(cid=cid)
    res = get_granite(url)

    # Validate that a list (and not a dict) of results are returned; assign the one and only expected entry to a var
    csip_data = None

    try:
        csip_data = res[0]
    except Exception:
        logger.exception(f"No records found in Granite circuitSites call for {cid} \nURL: {url} \nResponse: \n{res}")
        abort(500, f"No circuit site data found in Granite for {cid}", url=url, response=res)

    # Validate expected values
    expected = [
        "CIRC_PATH_INST_ID",
        "Z_ADDRESS",
        "Z_CITY",
        "Z_STATE",
        "Z_ZIP",
        "LEG_NAME",
        "LEG_INST_ID",
        "Z_CLLI",
        "Z_SITE_NAME",
        "A_CLLI",
        "A_SITE_NAME",
    ]

    missing = validate_values(csip_data, expected)

    if missing:
        logger.error(f"Granite circuitSites response for {cid} missing {missing}. \nURL: {url} \nResponse: \n{res}")
        abort(500, f"Granite site data response for {cid} missing {missing}", url=url, response=res)

    # Make the keys lowercase and return
    csip_vals = {k.lower(): v for (k, v) in csip_data.items() if k in expected}
    logger.info(
        f"Granite circuitSites lookup completed successfully for {cid}, returning:"
        f"\ncsip_vals: \n{csip_vals}"
        f"\nz_clli: {csip_vals['z_clli']}"
    )
    return csip_vals


def filter_rphy(port_list, cid):
    # get distinct cllis
    qw_tid_set = set()

    for item in port_list:
        qw_tid_set.add(item["EQUIP_NAME"].split("/")[0])

    # get cw_transport_paths CW.{clli}.
    rphy_port_set = set()

    for tid in qw_tid_set:
        granite_url = f"/circuitSites?CIRCUIT_NAME=CW.{tid}&WILD_CARD_FLAG=1&PATH_CLASS=P"
        granite_resp = get_granite(granite_url)

        if isinstance(granite_resp, list):
            for transport_path in granite_resp:
                # RPHY check
                qw = transport_path["CIRCUIT_NAME"].split(".")[-1]
                cw = transport_path["CIRCUIT_NAME"].split(".")[-2]
                leg_name = transport_path["LEG_NAME"].split("/")[0]

                # sending isp as true there will be different logic in function when isp is False
                rphy_resp = confirm_router_supports_rphy(cid, cw, leg_name, isp=True)

                if rphy_resp:
                    rphy_port_set.add(qw)
        elif isinstance(granite_resp, dict):
            logger.info(f"No transport_path found for {tid}.")

    new_port_list = []

    if rphy_port_set:
        for item in port_list:
            if item["EQUIP_NAME"].split("/")[0] in rphy_port_set:
                new_port_list.append(item)

        return new_port_list

    msg = "No FC + Remote PHY capable hub routers found. Please investigate"
    logger.error(msg)
    abort(500, msg)


def qc_transport_path_main(payload):
    # Checking payload keys
    intake_put_vals = ["cid", "agg_bandwidth", "service_type"]
    missing = [key for key in intake_put_vals if key not in payload]

    if not all(key in payload for key in intake_put_vals):
        logger.error(f"Intake payload missing {missing}")
        abort(500, f"Payload missing field(s): {missing}")

    cid, service_type, product, side = (
        payload["cid"].upper(),
        payload["service_type"],
        payload["product_name"],
        payload["side"],
    )

    existing_path_elements = get_existing_path_elements(cid)
    if existing_path_elements is not None and product != "EPL (Fiber)":
        abort(
            500,
            f"QC - Found existing transport path {existing_path_elements[0].get('PATH_NAME')} with "
            f"status {existing_path_elements[0].get('PATH_STATUS')}, please investigate",
        )

    service = service_type.lower().strip()
    if service != "net_new_qc":
        abort(500, f"Service type {service} in not supported")
    return {"transport_path": quick_connect_create_transport_path(cid, payload["agg_bandwidth"], side)}
