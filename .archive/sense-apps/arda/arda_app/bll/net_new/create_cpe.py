import logging
from typing import Tuple, Any

from arda_app.bll.models.device_topology import (
    ADVA_114PRO_1G,
    CRADLEPOINT_ARC,
    CRADLEPOINT_E100,
    CRADLEPOINT_W1850,
    RAD_203AX_1G,
)
from arda_app.bll.models.device_topology.underlay import UnderlayDeviceTopologyModel
from arda_app.bll.net_new.utils.shelf_utils import (
    check_and_add_existing_transport,
    get_device_bw,
    get_path_elements_data,
    get_shelf_names,
    get_type2_path_elements_data,
)
from arda_app.common.cd_utils import (
    get_circuit_site_url,
    granite_paths_url,
    granite_ports_put_url,
    granite_shelves_post_url,
)
from common_sense.common.errors import abort
from arda_app.dll.granite import (
    delete_granite,
    get_equipment_buildout,
    get_equipment_buildout_v2,
    get_granite,
    get_next_zw_shelf,
    insert_card_template,
    post_granite,
    put_granite,
)

logger = logging.getLogger(__name__)


def create_cpe_shelf(payload: dict) -> dict:
    """Create Customer Premise Equipment shelf."""
    # abort(500, "Planned abort test")
    type2 = payload.get("third_party_provided_circuit")
    cid = payload.get("cid")
    side = payload.get("side")
    product_name = payload.get("product_name")
    uni_type = payload.get("uni_type")
    build_type = payload.get("build_type")
    connector_type = payload.get("connector_type")
    cpe_gear = payload.get("cpe_gear", "")

    check_and_add_existing_transport(cid)

    # will need to pass out CW to ZW transport path for type 2
    if product_name == "Fiber Internet Access" and type2 == "Y":
        # adding check for uni type for type II FIA
        if uni_type in ("N/A", None):
            uni_type = "Access"

        cpe_trans, _ = get_type2_path_elements_data(cid)
    else:
        cpe_trans, _ = get_path_elements_data(cid, side)

    # Check for existing RAD CPE on RPHY
    if product_name == "FC + Remote PHY":
        if cpe_trans["BANDWIDTH"] != "5 Gbps":
            msg = f"Circuit bandwidth: {cpe_trans['BANDWIDTH']} does not equal 5 Gbps for {product_name}"
            logger.error(msg)
            abort(500, msg)
        _check_existing_cpe(cpe_trans)
    elif not cpe_trans["ELEMENT_BANDWIDTH"]:
        abort(500, "No ELEMENT_BANDWIDTH on cpe transport path")
    # adding abort for cpe transport paths that do not have bw speed and unit
    elif cpe_trans["ELEMENT_BANDWIDTH"].upper() == "AGGREGATE":
        abort(500, "CPE transport path has bandwidth value of AGGREGATE which is currently unsupported")

    if cpe_trans["ELEMENT_CATEGORY"] != "ETHERNET TRANSPORT":
        abort(500, f"First LVL 1 element in path: {cpe_trans['ELEMENT_NAME']} is not an ETHERNET TRANSPORT")

    # Check for build type change since ISP
    shelf_type = cpe_trans["ELEMENT_NAME"][-2:]
    abt_msg = (
        "Manual Intervention detected at create_cpe:"
        f" Transport {cpe_trans['ELEMENT_NAME']} does not align with build_type {build_type}"
    )
    if shelf_type == "ZW" and build_type == "MTU New Build":
        abort(500, abt_msg)
    elif shelf_type == "AW" and build_type != "MTU New Build":
        abort(500, abt_msg)

    # GET element bandwidth speed and unit
    bw_speed, bw_unit = cpe_trans["BANDWIDTH"].split()

    # checking cid bandwidth and product to determine if a 10 Gbps cpe is needed
    if product_name == "FC + Remote PHY":
        bw_speed, bw_unit = "10", "Gbps"
    elif cpe_trans["ELEMENT_NAME"].endswith("AW"):
        if bw_unit == "Gbps" or (bw_unit == "Mbps" and int(bw_speed) >= 1000):
            bw_speed, bw_unit = "10", "Gbps"
    else:
        bw_speed, bw_unit = cpe_trans["ELEMENT_BANDWIDTH"].split()

    # GET device bandwidth -> 1G, 10G, or RF
    device_bw = get_device_bw(bw_speed, bw_unit)

    if device_bw not in {"1 Gbps", "10 Gbps", "RF"}:
        msg = f"Invalid device bandwidth: {device_bw}"
        logger.error(msg)
        abort(500, msg)

    # SET connector type
    if product_name == "FC + Remote PHY":
        logger.info("Detected FC + Remote PHY, setting connector type to LC")
        connector_type = "LC"
    elif connector_type in {"RJ45", "RJ48", "N/A"}:
        connector_type = "RJ-45"
    else:
        connector_type = connector_type

    site_name = ""

    # GET site name based on side
    if product_name == "EPL (Fiber)" and side == "z_side":
        if cpe_trans["SEQUENCE"] in ("1", "2"):
            site_name = cpe_trans["PATH_Z_SITE"]
    else:
        # GET the correct site name based on side
        if cpe_trans["SEQUENCE"] == "1":
            if side == "z_side":
                site_name = cpe_trans["PATH_Z_SITE"]
            else:
                site_name = cpe_trans["PATH_A_SITE"]

    # GET next zw shelf tid IF MTU New Build -> tid
    if build_type == "MTU New Build":
        tid = get_next_zw_shelf(site_name)
    else:
        tid = cpe_trans["ELEMENT_NAME"].split(".")[-1]

    # existing WIA equipment check tid name will change to next ZW
    tid = wia_check(tid, cpe_trans)

    cpe_site = get_equipment_buildout_v2(tid)

    vendor = "ADVA" if type2 == "Y" else ""
    model = ""
    existing_cpe = False

    if isinstance(cpe_site, list):
        # Checking CPE status to fallout for equipment that is live on the network
        if cpe_site[0]["EQUIP_STATUS"] not in ("Planned", "Auto-Planned", "Designed", "Auto-Designed") and type2 != "Y":
            msg = f"Found existing cpe with an unsupported status of {cpe_site[0]['EQUIP_STATUS']}"
            logger.error(msg)
            abort(500, msg)
        elif (
            cpe_trans.get("PATH_Z_SITE") == cpe_site[0]["SITE_NAME"]
            or cpe_trans.get("PATH_A_SITE") == cpe_site[0]["SITE_NAME"]
        ):
            # SET vendor based on if CPE site if found
            vendor = cpe_site[0]["VENDOR"]
            existing_cpe = True
            model = cpe_site[0]["MODEL"]
        else:
            # to prevent creating duplicate shelves
            msg = f"Attempt to create a duplicate device ID involving {cpe_trans.get('ELEMENT_NAME', '')}"
            logger.error(msg)
            abort(500, msg)

    # checking if cpe_gear was given in SF
    if cpe_gear:
        if "ADVA" in cpe_gear:
            vendor = "ADVA"
        else:
            vendor = "RAD"

    # GET device topology for a CPE device
    # IF vendor is empty, then device topology will reach out to granite to get the vendor
    device_topology = UnderlayDeviceTopologyModel(
        role="cpe", connector_type=connector_type, device_bw=device_bw, vendor=vendor, model=model
    )  # type: ignore

    # GET shelf name
    shelf_name, tid = get_shelf_names(
        element_name=cpe_trans["ELEMENT_NAME"], vendor=device_topology.vendor, tid=tid if tid else ""
    )

    # Create CPE shelf payload
    shelf_create_payload = {
        "SHELF_NAME": shelf_name,
        "SHELF_TEMPLATE": device_topology.device_template,
        "SITE_NAME": cpe_trans["PATH_Z_SITE" if side == "z_side" else "PATH_A_SITE"],
        "SHELF_FQDN": f"{tid}.CML.CHTRSE.COM",
        "UDA": {
            "Purchase Info": {"PURCHASING GROUP": "ENTERPRISE", "TRANSPORT MEDIA TYPE": "FIBER"},
            "RESPONSIBLE ORGANIZATION": {"RESPONSIBLE TEAM": "ENT-SVC-IP"},
            "Device Config-Equipment": {
                "TARGET ID (TID)": tid,
                "IPv4 ADDRESS": "DHCP",
                "IP MGMT": "ENTERPRISE",
                "IP MGMT TYPE": "DHCP",
                "OAM PROTOCOL": "y.1731",
            },
            "Device Info": {"NETWORK ROLE": "CUSTOMER PREMISE EQUIPMENT", "DEVICE ID": f"{tid}.CML.CHTRSE.COM"},
        },
    }

    if existing_cpe:
        if type2 == "Y":
            port_inst_id = type2_uplink(cpe_site, device_topology, tid)
        else:
            port_inst_id = "".join(e.get("PORT_INST_ID") for e in cpe_site if e["SLOT"] == device_topology.uplink.slot)

        cpe_uplink_pid = port_inst_id
        cpe_handoff_pid = _build_handoff(
            shelf_name, cpe_trans["BANDWIDTH"], device_topology, cpe_site, existing_cpe=True
        )
    else:
        # POST Create CPE shelf from template to granite
        _create_shelf(shelf_create_payload)

        # PUT build uplink card
        cpe_uplink_pid = _build_uplink(shelf_name, device_topology)

        # PUT build handoff card
        cpe_handoff_pid = _build_handoff(shelf_name, cpe_trans["BANDWIDTH"], device_topology)

    # set response
    resp = {
        "cpe_shelf": shelf_name,
        "cpe_tid": tid,
        "cpe_uplink": cpe_uplink_pid,
        "cpe_handoff": cpe_handoff_pid,
        "cpe_handoff_paid": device_topology.handoff.port_access_id if device_topology.handoff else "",
        "zw_path": cpe_trans["ELEMENT_REFERENCE"],
        "circ_path_inst_id": cpe_trans["CIRC_PATH_INST_ID"],
        "cpe_model_number": device_topology.model,
    }

    # SET UNI type
    if uni_type == "Access" or product_name == "FC + Remote PHY":
        # set uni type to access if Access in payload or product name is FC + Remote PHY
        _set_uni_type(cpe_handoff_pid, "UNI-EP")
    elif uni_type == "Trunked":
        # set uni type to trunked if Trunked in payload
        _set_uni_type(cpe_handoff_pid, "UNI-EVP", trunked=True)
        resp["cpe_trunked_path"] = _create_trunked_handoff(
            connector=payload.get("connector_type"),
            handoff_pid=cpe_handoff_pid,
            cid=cid,
            z_site_name=cpe_trans.get("Z_SITE_NAME", ""),
            tid=tid,
            circuit_bw=cpe_trans["BANDWIDTH"],
        )

    return resp


def create_shelf_WIA(payload: dict) -> dict:
    """Create Customer Premise Equipment shelf."""
    cid = payload.get("cid")
    service_code = payload.get("service_code")

    paths_url = get_circuit_site_url(cid)
    path_payload = get_granite(paths_url)

    # Grab z side site name to make tid will need to check on first available shelf name 1zw, 2zw, etc
    model = "E100 C4D/C7C"
    device_template = CRADLEPOINT_E100

    # determine if we use 4g or 5g device
    if service_code:
        if service_code == "RW702":
            model = "W1850"
            device_template = CRADLEPOINT_W1850
        elif service_code == "WISIM":
            abort(500, "Unsupported WIA service code: WISIM")

    # SET device topology
    device_topology = UnderlayDeviceTopologyModel(
        role="cpe",
        connector_type="RJ-45",
        device_bw="RF",
        vendor="CRADLEPOINT",
        model=model,
        device_template=device_template,
    )

    # GET site name based on side
    site_name = path_payload[0]["Z_SITE_NAME"]

    tid = get_next_zw_shelf(site_name)
    # GET shelf name
    shelf_name = f"{tid}/999.9999.999.99/RTR"

    # Create CPE shelf payload
    shelf_create_payload = {
        "SHELF_NAME": shelf_name,
        "SHELF_TEMPLATE": device_topology.device_template,
        "SITE_NAME": site_name,
        "SHELF_FQDN": f"{tid}.CML.CHTRSE.COM",
        "UDA": {
            "Purchase Info": {
                "PURCHASING GROUP": "ENTERPRISE",
                "TRANSPORT MEDIA TYPE": "5G" if model == "W1850" else "LTE",
            },
            "RESPONSIBLE ORGANIZATION": {"RESPONSIBLE TEAM": "ENT-SVC-IP"},
            "Device Config-Equipment": {
                "TARGET ID (TID)": tid,
                "IPv4 ADDRESS": "DHCP",
                "IP MGMT": "ENTERPRISE",
                "IP MGMT TYPE": "DHCP",
                "OAM PROTOCOL": "y.1731",
            },
            "Device Info": {"DEVICE ID": f"{tid}.CML.CHTRSE.COM", "NETWORK ROLE": "CUSTOMER PREMISE EQUIPMENT"},
        },
    }

    # POST Create CPE shelf from template to granite
    _create_shelf(shelf_create_payload)

    # PUT build uplink card
    cpe_uplink_pid = _build_uplink(shelf_name, device_topology)

    # PUT build handoff card
    cpe_handoff_pid = _build_handoff(shelf_name, "RF", device_topology)

    # set response
    resp = {
        "cpe_shelf": shelf_name,
        "cpe_tid": tid,
        "cpe_uplink": cpe_uplink_pid,
        "cpe_handoff": cpe_handoff_pid,
        "cpe_handoff_paid": "LAN 1",
        "circ_path_inst_id": path_payload[0]["CIRC_PATH_INST_ID"],
        "zw_path": path_payload[0]["CIRC_PATH_INST_ID"],
    }

    return resp


def _create_shelf(shelf_create_payload: dict) -> None:
    """
    Create Customer Premise Equipment shelf in Granite.

    TODO: fallout when an existing shelf with a different vendor is found (SWT vs. NIU).
    """
    shelf_create_url = granite_shelves_post_url()
    shelf_create_data = post_granite(shelf_create_url, shelf_create_payload)

    if shelf_create_data["retString"] == "Shelf has nothing to update":
        logger.error(f"Unsupported existing shelf found.\nURL: {shelf_create_url} \nResponse: {shelf_create_data}")
        abort(
            500,
            message="Unsupported existing shelf found. Must be no prior CPE shelf at site for this customer",
            url=shelf_create_url,
            response=shelf_create_data,
        )

    if shelf_create_data["retString"] != "Shelf Added":
        logger.error(
            f"Unexpected Granite response, could not find 'Shelf Added' message. "
            f"\nURL: {shelf_create_url} \nResponse: {shelf_create_data}"
        )
        abort(500, message="Incorrect shelf data payload from Granite", url=shelf_create_url, response=shelf_create_data)

    logger.info(f"CPE shelf created \nGranite shelf create response: \n{shelf_create_data}")


def _build_uplink(shelf_name: str, device_topology: UnderlayDeviceTopologyModel) -> str:
    """add uplink card"""
    if not device_topology.uplink:
        msg = "device topology is missing uplink port data"
        logger.error = msg
        abort(500, msg)

    equipment_data = get_equipment_buildout(shelf_name)

    for item in equipment_data:
        if all(
            (not item.get("PORT_USE"), item.get("SLOT") == device_topology.uplink.slot, not item.get("PORT_INST_ID"))
        ):
            insert_card_template(item, device_topology.uplink.template)
            break

    if device_topology.model in ("ARC CBA850", "E100 C4D/C7C", "W1850"):
        port_inst_id = "".join(
            e.get("PORT_INST_ID")
            for e in equipment_data
            if e["PORT_NAME"] == device_topology.uplink.slot and e["EQUIP_STATUS"] == "Planned"
        )
    else:
        # run get equipment buildout again to retrieve latest data
        equipment_data = get_equipment_buildout(shelf_name)

        # get port_inst_id
        port_inst_id = "".join(
            e.get("PORT_INST_ID")
            for e in equipment_data
            if e["SLOT"] == device_topology.uplink.slot and e["EQUIP_STATUS"] == "Planned"
        )

    payload = {
        "PORT_ACCESS_ID": device_topology.uplink.port_access_id,
        "PORT_INST_ID": port_inst_id,
        "PORT_STATUS": "Assigned",
    }

    ports_url = granite_ports_put_url()
    put_granite(ports_url, payload)

    return port_inst_id


def _build_handoff(
    shelf_name: str,
    circuit_bandwidth: str,
    device_topology: UnderlayDeviceTopologyModel,
    cpe_site: list = None,
    existing_cpe: bool = False,
) -> str:
    """add hand off cards"""
    if circuit_bandwidth == "RF":
        equipment_data = get_equipment_buildout(shelf_name)
    else:
        if existing_cpe:
            equipment_data = [item for item in cpe_site if item.get("PORT_USE") != "IN USE"]
        else:
            equipment_data = get_equipment_buildout(shelf_name)

        device_topology.set_handoff(circuit_bandwidth, equipment_data, existing_cpe)

        if not device_topology.handoff:
            abort(500, "device topology is missing uplink port data")

        # Check if card needs to be deleted and/or inserted
        for item in equipment_data:
            if item.get("SLOT") == device_topology.handoff.slot and device_topology.handoff.slot not in (
                "FIXED PORTS",
                "CHASSIS PORTS",
            ):
                if item.get("CARD_TEMPLATE") and item.get("CARD_TEMPLATE") != device_topology.handoff.template:
                    delete_payload = {"SHELF_NAME": item.get("EQUIP_NAME"), "SLOT_INST_ID": item.get("SLOT_INST_ID")}
                    delete_granite("/cards", delete_payload)
                    insert_card_template(item, device_topology.handoff.template)
                elif not item.get("CARD_TEMPLATE"):
                    insert_card_template(item, device_topology.handoff.template)

                # run get equipment buildout again to retrieve latest data
                equipment_data = get_equipment_buildout(shelf_name)
                break

    port_inst_id = ""

    if device_topology.device_template == RAD_203AX_1G:
        try:
            port_inst_id = [
                e.get("PORT_INST_ID")
                for e in equipment_data
                if e.get("PORT_ACCESS_ID") == device_topology.handoff.port_access_id
            ][0]
        except IndexError:
            # if port_inst_id is not found using port_access_id, then try using slot
            port_inst_id = [
                e.get("PORT_INST_ID") for e in equipment_data if e.get("SLOT") == device_topology.handoff.slot
            ][0]

        if port_inst_id:
            # get port_inst_ids
            payload = {
                "PORT_ACCESS_ID": device_topology.handoff.port_access_id,
                "PORT_INST_ID": port_inst_id,
                "PORT_STATUS": "Assigned",
            }
            put_url = granite_ports_put_url()
            put_granite(put_url, payload)
    elif device_topology.device_template == ADVA_114PRO_1G and device_topology.handoff.connector == "RJ-45":
        port_inst_id = [
            e.get("PORT_INST_ID")
            for e in equipment_data
            if e.get("PORT_ACCESS_ID") == device_topology.handoff.port_access_id
        ][0]

        if port_inst_id:
            # get port_inst_ids
            payload = {
                "PORT_ACCESS_ID": device_topology.handoff.port_access_id,
                "PORT_INST_ID": port_inst_id,
                "PORT_STATUS": "Assigned",
            }
            put_url = granite_ports_put_url()
            put_granite(put_url, payload)
    elif device_topology.device_template in (CRADLEPOINT_ARC, CRADLEPOINT_E100, CRADLEPOINT_W1850):
        wia_handoff_name = "LAN 1" if device_topology.device_template == CRADLEPOINT_ARC else "LAN 01"
        port_inst_id = "".join(e.get("PORT_INST_ID") for e in equipment_data if e["PORT_NAME"] == wia_handoff_name)

        if port_inst_id:
            # get port_inst_ids
            payload = {
                "PORT_ACCESS_ID": "LAN 01" if device_topology.device_template == CRADLEPOINT_W1850 else "LAN 1",
                "PORT_INST_ID": port_inst_id,
                "PORT_STATUS": "Assigned",
            }

            put_url = granite_ports_put_url()
            put_granite(put_url, payload)
    else:
        if not device_topology.handoff:
            abort(500, "No device_topology handoff for /ports payload")

        # get port_inst_ids
        payload = [
            {
                "PORT_ACCESS_ID": device_topology.handoff.port_access_id,
                "PORT_INST_ID": e.get("PORT_INST_ID"),
                "PORT_STATUS": "Assigned",
            }
            for e in equipment_data
            if e["SLOT"] == device_topology.handoff.slot
        ][0]

        put_url = granite_ports_put_url()
        put_granite(put_url, payload)
        port_inst_id = payload["PORT_INST_ID"]

    return port_inst_id


def _set_uni_type(handoff_pid: str, port_role: str, trunked=False) -> None:
    """Set UNI type based on payload, uni_type."""
    put_url = f"{granite_ports_put_url()}?PORT_INST_ID={handoff_pid}"
    granite_payload = {
        "PORT_INST_ID": handoff_pid,
        "UDA": {"VLAN INFO": {"PORT-ROLE": port_role}},
        "SET_CONFIRMED": "TRUE",
    }

    if trunked:
        granite_payload["PORT_CHANNEL_ASSIGN"] = "Dynamic"
        granite_payload["SET_CONFIRMED"] = "TRUE"

    put_granite(put_url, granite_payload)


def _create_trunked_handoff(
    connector: str, handoff_pid: str, cid: str, z_site_name: str, tid: str, circuit_bw: str
) -> str:
    """
    Build trunked ZW path,
    assign the trunked handoff port to Trunked Path,
    identify new trunked variables.
    """
    # Get first two digits from cid to use in the trunked path name
    npa_nxx = cid.split(".")[0]

    bw_speed, bw_unit = circuit_bw.split()
    bw = get_device_bw(bw_speed, bw_unit, for_path_name=True)

    trunked_path_name = f"{npa_nxx}001.{bw}.{tid}.{tid}"

    service_media = "COPPER" if connector == "RJ45" else "FIBER"
    post_payload = {
        "PATH_NAME": trunked_path_name,
        "PATH_TEMPLATE_NAME": "WS ETHERNET TRANSPORT",
        "PATH_BANDWIDTH": get_device_bw(bw_speed, bw_unit),
        "UPDATE_LEG": "true",
        "LEG_NAME": "1",
        "LEG_A_SITE_NAME": z_site_name,
        "LEG_Z_SITE_NAME": z_site_name,
        "Topology": "Point to Point",
        "A_SITE_NAME": z_site_name,
        "Z_SITE_NAME": z_site_name,
        "PATH_STATUS": "Planned",
        "UDA": {"SERVICE_TYPE": {"PRODUCT/SERVICE": "INT-CUSTOMER HANDOFF", "SERVICE MEDIA": service_media}},
    }

    paths_url = granite_paths_url()
    post_resp = post_granite(paths_url, post_payload)

    put_payload = {
        "PATH_NAME": trunked_path_name,
        "PATH_INST_ID": post_resp["pathInstanceId"],
        "PATH_LEG_INST_ID": "1",
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
        "PORT_INST_ID": handoff_pid,
    }
    resp = put_granite(paths_url, put_payload)

    return resp["pathInstanceId"] if isinstance(resp, dict) else ""


def _check_existing_cpe(cpe_path_elements: dict) -> Tuple[bool, str, Any]:
    tid = cpe_path_elements["ELEMENT_NAME"].split(".")[-1]

    ten_gig_models = (
        "FSP 150-XG116PRO",
        "FSP 150-XG116PROH",
        "FSP 150-XG120PRO",
        "FSP 150-XG108",
        "ETX-220A",
        "ETX-2I-10G-B/8.5/8SFPP",
        "ETX-2I-10G-B/19/8SFPP",
        "ETX-2I-10G/4SFPP/4SFP4UTP",
        "ETX-2I-10G/4SFPP/24SFP",
    )

    cpe_site = get_equipment_buildout_v2(tid)

    if isinstance(cpe_site, list) and cpe_site[0]["SITE_NAME"] == cpe_path_elements.get("PATH_Z_SITE"):
        if cpe_site[0]["MODEL"] not in ten_gig_models:
            msg = "Unable to swap 1 Gbps cpe for 10 Gbps cpe: FC + Remote PHY"
            logger.error(msg)
            abort(500, msg)


def type2_uplink(cpe_site, device_topology, tid):
    for item in cpe_site:
        if item.get("SLOT") == device_topology.secondary.slot and not item.get("PORT_INST_ID"):
            insert_card_template(item, device_topology.secondary.template)
            break

    cpe_site = get_equipment_buildout_v2(tid)

    port_inst_id = "".join(e.get("PORT_INST_ID") for e in cpe_site if e["SLOT"] == device_topology.secondary.slot)

    payload = {
        "PORT_ACCESS_ID": device_topology.secondary.port_access_id,
        "PORT_INST_ID": port_inst_id,
        "PORT_STATUS": "Assigned",
    }

    ports_url = granite_ports_put_url()
    put_granite(ports_url, payload)

    return port_inst_id


def wia_check(tid, cpe_trans):
    # checking if ZW tid is a cradlepoint
    cpe = get_equipment_buildout_v2(tid)

    if isinstance(cpe, list):
        if cpe[0]["VENDOR"] == "CRADLEPOINT":
            site_name = cpe[0]["SITE_NAME"]
            new_tid = get_next_zw_shelf(site_name)

            new_trans = cpe_trans["ELEMENT_NAME"].replace(tid, new_tid)

            # updating transport path from 1ZW to 2ZW
            url = granite_paths_url()

            update_parameters = {
                "PATH_NAME": new_trans,
                "PATH_INST_ID": cpe_trans["ELEMENT_REFERENCE"],
                "SET_CONFIRMED": "TRUE",
            }

            resp_data = put_granite(url, update_parameters)

            if resp_data.get("retString") == "Path Updated":
                return new_tid

            msg = f"Unable to update transport path to {new_trans}"
            logger.error(msg)
            abort(500, msg)

    return tid
