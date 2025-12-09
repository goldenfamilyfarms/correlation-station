import re
import logging

from common_sense.common.errors import abort
from arda_app.common.utils import create_bw_string, path_regex_match, bandwidth_in_bps
from arda_app.dll.granite import (
    get_granite,
    insert_card_template,
    put_port_access_id,
    put_granite,
    delete_granite,
    get_shelves_at_site,
    get_site_available_ports,
    get_shelf_used_ports,
    get_equipment_buildout,
    get_equipment_buildout_v2,
    get_port_udas,
)
from arda_app.common.cd_utils import granite_ports_put_url, will_transport_be_oversubscribed
from arda_app.dll.mdso import serviceable_shelf_port_available_on_network
from arda_app.bll.circuit_design.bandwidth_change.normal_bw_upgrade import (
    hub_transport_check,
    trans_path_upgrade,
    cpe_10g_swap,
    remove_1G_transport,
)
from arda_app.bll.circuit_design.common import _granite_create_circuit_revision
from arda_app.bll.models.device_topology.underlay import UnderlayDeviceTopologyModel
from arda_app.bll.net_new.utils.shelf_utils import cpe_service_check
from arda_app.bll.net_new.create_cpe import _build_handoff, _create_trunked_handoff
from arda_app.common.cd_constants import IGNORED_SHELF_PORTS

logger = logging.getLogger(__name__)


def serviceable_shelf_handoff(cid, bandwidth_type, bandwidth_value, connector_type, uni_type, side):
    if connector_type == "RJ45":
        connector_type = "RJ-45"
    bandwidth_string = create_bw_string(bandwidth_type, bandwidth_value)

    endpoint = f"/circuitSites?CIRCUIT_NAME={cid}&PATH_CLASS=P"
    circuitSites_resp = get_granite(endpoint)

    if isinstance(circuitSites_resp, dict):
        abort(500, f"No path found for cid {cid}")
    elif isinstance(circuitSites_resp, list) and len(circuitSites_resp) > 1:
        abort(500, f"More than one path found for cid {cid}")
    else:
        circuitSites_resp = circuitSites_resp[0]
        if not circuitSites_resp.get("Z_SITE_NAME" if side == "z_side" else "A_SITE_NAME"):
            abort(500, f"No site name found in Granite for cid {cid}")
        if circuitSites_resp.get("Z_SITE_TYPE" if side == "z_side" else "A_SITE_TYPE") == "COLO":
            abort(500, "Unsupported site type COLO")

    cid_path_inst_id = circuitSites_resp["CIRC_PATH_INST_ID"]
    clli = circuitSites_resp.get("Z_CLLI" if side == "z_side" else "A_CLLI")
    site_name = circuitSites_resp.get("Z_SITE_NAME" if side == "z_side" else "A_SITE_NAME")
    # Adding for bandwidth that cannot be split (Ex: "RF")
    try:
        bw_value, bw_type = circuitSites_resp["CIRCUIT_BANDWIDTH"].split()
    except ValueError:
        abort(
            500,
            f"Unsupported: Circuit bandwidth: {circuitSites_resp['CIRCUIT_BANDWIDTH']} is unsupported "
            "for serviceable shelf. Please Investigate",
        )

    bw_bps = bandwidth_in_bps(bw_value, bw_type)

    # Check for existing shelves at Z site
    potential_shelves = []
    if clli and site_name:
        site_shelves = get_shelves_at_site(clli, site_name)
        if isinstance(site_shelves, list):
            # Existing shelves at Z site. Determine which to use
            for shelf in site_shelves:
                if shelf.get("EQUIP_STATUS") in ["Live", "Designed", "Auto-Designed", "Planned"] and potential_cpe_model(
                    shelf.get("EQUIP_MODEL")
                ):
                    potential_shelves.append(shelf)
            if not potential_shelves:
                site_models = [shelf["EQUIP_MODEL"] for shelf in site_shelves if shelf.get("EQUIP_MODEL")]
                abort(500, f"No potential CPE shelves at {side}. Models {site_models}")
        else:
            abort(500, f"No shelves found at CID {side}: {site_name}")
    else:
        abort(500, f"Unable to find {side} site name and CLLI for CID")

    chosen_shelf = None
    abort_msg = ""
    orphaned_shelves = []
    if len(potential_shelves) == 1:
        chosen_shelf = potential_shelves[0]
        site_info = get_site_available_ports(site_name)
        if isinstance(site_info, dict):
            abort(500, f"No available ports found at site: {site_name}")
        elif isinstance(site_info, list):
            # Filter for ports on selected shelf
            site_info = [port for port in site_info if port.get("EQUIP_NAME") == chosen_shelf["EQUIP_NAME"]]
        if not site_info:
            abort(500, f"No available ports on determined shelf: {chosen_shelf['EQUIP_NAME']}")
    elif len(potential_shelves) > 1:
        # Multiple potential shelves found. Check each to see if any are orphaned (no ports tied to paths)
        filtered_potential_shelves = []
        for shelf in potential_shelves:
            tid = shelf["EQUIP_NAME"].split("/")[0]
            in_use_ports = get_shelf_used_ports(clli, tid)
            if isinstance(in_use_ports, dict):
                # Shelf has no IN USE ports, shelf is orphaned
                orphaned_shelves.append(shelf)
            else:
                filtered_potential_shelves.append(shelf)

        if len(filtered_potential_shelves) == 1:
            chosen_shelf = filtered_potential_shelves[0]
        elif len(filtered_potential_shelves) > 1:
            abort_msg = f"More than one potential CPE shelf found at {side}"
        else:
            abort_msg = f"All shelves at {side} were orphaned"

    if orphaned_shelves:
        for shelf in orphaned_shelves:
            delete_orphan_shelf(shelf["EQUIP_INST_ID"])

    if abort_msg:
        abort(500, abort_msg)

    # Serviceable shelf determined
    equip_name = chosen_shelf["EQUIP_NAME"]
    tid = chosen_shelf["EQUIP_NAME"].split("/")[0]
    vendor = chosen_shelf["EQUIP_VENDOR"]
    model = chosen_shelf["EQUIP_MODEL"]

    if chosen_shelf and not supported_model(model):
        abort(500, f"Determined serviceable shelf model is currently unsupported: {tid} - {model}")

    # Begin looking for available port by checking Granite and the network
    shelf_ports = get_equipment_buildout(tid)

    designed_cids = cids_on_shelf(shelf_ports)
    cpe_service_check([tid, vendor, model], designed_cids)

    # Get network port config
    network_ports = serviceable_shelf_port_available_on_network(equip_name, vendor)
    network_ports = network_ports["result"]

    # UnderlayDeviceTopologyModel available handoffs
    handoff_ports = underlay_topology_model_available_handoffs(model, bandwidth_string, vendor, connector_type)

    if vendor == "RAD":
        network_topology_matched_ports = rad_admin_down_network_ports(network_ports, handoff_ports)
    elif vendor == "ADVA":
        network_topology_matched_ports = adva_admin_down_network_ports(network_ports, handoff_ports, model)

    if not network_topology_matched_ports:
        abort(500, f"No available ports on the network for serviceable shelf {chosen_shelf['EQUIP_NAME']}")

    updated_site = assign_port(shelf_ports, network_topology_matched_ports, connector_type)
    if not updated_site:
        abort(
            500,
            "No usable ports after comparing Granite and the network "
            f"for serviceable shelf {chosen_shelf['EQUIP_NAME']}",
        )

    transport_path_inst_id, transport_path_name = get_transport_path(equip_name)
    transport_upgrade, hub_work_required = validate_transport_path(
        transport_path_inst_id, transport_path_name, bw_bps, chosen_shelf
    )

    # Transport upgrade logic
    cpe_upgrade_needed = {}
    if transport_upgrade:
        cpe_upgrade_needed = {
            "Z_SIDE_SITE": chosen_shelf["SITE_NAME"],
            "TID": chosen_shelf["TARGET_ID"],
            "VENDOR": chosen_shelf["EQUIP_VENDOR"],
        }

        trans_data, new_shelf, resp_data = trans_path_upgrade(
            transport_path_name, transport_path_inst_id, cpe_upgrade_needed, hub_work_required
        )
        # new function to get related cid and main_rev
        related_cid, related_cid_revision = get_related_cid(transport_path_name)

        rev_result, rev_instance, rev_path = _granite_create_circuit_revision(related_cid, related_cid_revision)
        if new_shelf:
            cpe_10g_swap(rev_instance, cpe_upgrade_needed, trans_data, resp_data, related_cid)

        if trans_data:
            remove_1G_transport(related_cid, rev_instance)

        cpe_site = get_equipment_buildout_v2(new_shelf)

        # SET vendor based on new 10 Gbps CPE
        if isinstance(cpe_site, list):
            vendor = cpe_site[0]["VENDOR"]
            existing_cpe = True
            model = cpe_site[0]["MODEL"]
        else:
            abort(500, f"No CPE found in granite for {new_shelf}")

        device_topology = UnderlayDeviceTopologyModel(
            role="cpe", connector_type=connector_type, device_bw="10 Gbps", vendor=vendor, model=model
        )
        cpe_handoff_pid = _build_handoff(
            new_shelf, circuitSites_resp["CIRCUIT_BANDWIDTH"], device_topology, cpe_site, existing_cpe=existing_cpe
        )
        port_resp = get_port_udas(cpe_handoff_pid)

        # switching equipment and transport information to match new 10 gig transport and CPE
        updated_site["EQUIP_NAME"] = port_resp[0]["EQUIP_NAME"]
        updated_site["PORT_INST_ID"] = cpe_handoff_pid
        updated_site["PORT_ACCESS_ID"] = port_resp[0]["PORT_ACCESS_ID"]
        transport_path_name = resp_data["pathId"]
        transport_path_inst_id = resp_data["pathInstanceId"]

    resp = {
        "cpe_shelf": updated_site["EQUIP_NAME"],
        "cpe_tid": updated_site["EQUIP_NAME"].split("/")[0],
        "cpe_handoff": updated_site["PORT_INST_ID"],
        "cpe_handoff_paid": updated_site["PORT_ACCESS_ID"],
        "zw_transport_path_name": transport_path_name,
        "zw_transport_path_inst_id": transport_path_inst_id,
        "circ_path_inst_id": cid_path_inst_id,
        "transport_upgrade": transport_upgrade,
        "hub_work_required": hub_work_required,
    }

    if uni_type == "Access" and side in ("a_side", "z_side"):
        _set_uni_type(updated_site.get("PORT_INST_ID"), "UNI-EP")
    elif uni_type == "Trunked":
        # set uni type to trunked if Trunked in payload
        _set_uni_type(updated_site.get("PORT_INST_ID"), "UNI-EVP", trunked=True)
        resp["cpe_trunked_path"] = _create_trunked_handoff(
            connector=connector_type,
            handoff_pid=resp["cpe_handoff"],
            cid=cid,
            z_site_name=circuitSites_resp["Z_SITE_NAME"],
            tid=resp["cpe_tid"],
            circuit_bw=circuitSites_resp["CIRCUIT_BANDWIDTH"],
        )

    return resp


def cids_on_shelf(shelf_ports):
    designed_cids = []
    for port in shelf_ports:
        designed_path = port.get("MEMBER_PATH", port.get("NEXT_PATH", ""))
        if designed_path and path_regex_match(designed_path):
            designed_cids.append(designed_path)
    return designed_cids


def delete_orphan_shelf(shelf_inst_id):
    delete_url = "/shelves"
    granite_payload = {"SHELF_INST_ID": shelf_inst_id, "ARCHIVE_STATUS": "Canceled"}
    resp = delete_granite(delete_url, granite_payload)
    return resp


def _set_uni_type(handoff_pid, port_role, trunked=False) -> None:
    """Set UNI type based on payload, uni_type."""
    put_url = f"{granite_ports_put_url()}"
    granite_payload = {
        "PORT_INST_ID": handoff_pid,
        "PORT_STATUS": "Assigned",
        "UDA": {"VLAN INFO": {"PORT-ROLE": port_role}},
        "SET_CONFIRMED": "TRUE",
    }
    if trunked:
        granite_payload["PORT_CHANNEL_ASSIGN"] = "Dynamic"
        granite_payload["SET_CONFIRMED"] = "TRUE"
    put_granite(put_url, granite_payload)


def assign_port(shelf_ports, network_ports, connector_type):
    for network_port in network_ports:
        network_slot = network_port[0]
        network_port_access_id = network_port[1]
        network_card_template = network_port[2]
        for shelf_port in shelf_ports:
            if shelf_port.get("PORT_NAME") and shelf_port.get("PORT_NAME") in IGNORED_SHELF_PORTS:
                continue
            updated_shelf = []
            if shelf_port.get("SLOT") == network_slot:
                if (
                    shelf_port.get("PORT_ACCESS_ID") == network_port_access_id
                    and shelf_port.get("CONNECTOR_TYPE") == connector_type
                ):
                    return card_template_check(shelf_port, network_port_access_id, network_card_template)
                elif shelf_port.get("PORT_INST_ID") and not shelf_port.get("PORT_ACCESS_ID"):
                    put_port_access_id(shelf_port.get("PORT_INST_ID"), network_port_access_id)
                    updated_shelf = get_equipment_buildout(shelf_port.get("EQUIP_NAME"))
                    for updated_port in updated_shelf:
                        if updated_port.get("PORT_INST_ID") == shelf_port.get("PORT_INST_ID"):
                            return card_template_check(updated_port, network_port_access_id, network_card_template)
                elif not shelf_port.get("PORT_INST_ID"):
                    insert_card_template(shelf_port, network_card_template)
                    updated_shelf = get_equipment_buildout(shelf_port.get("EQUIP_NAME"))
                    for updated_port in updated_shelf:
                        if updated_port.get("SLOT_INST_ID") == shelf_port.get("SLOT_INST_ID"):
                            port_inst_id = updated_port.get("PORT_INST_ID")
                            put_port_access_id(updated_port.get("PORT_INST_ID"), network_port_access_id)
                            updated_shelf = get_equipment_buildout(shelf_port.get("EQUIP_NAME"))
                            for updated_port in updated_shelf:
                                if updated_port.get("PORT_INST_ID") == port_inst_id:
                                    return updated_port


def card_template_check(port, port_access_id, card_template):
    """Checks if the existing card template matches the one needed.
    If no match or no template, insert card template"""
    if port.get("SLOT") in ["FIXED PORTS", "CHASSIS PORTS", "CHASSIS"]:
        # These are built-in and can't use card/optic templates
        return port
    if port.get("CARD_TEMPLATE") and port.get("CARD_TEMPLATE") != card_template:
        delete_payload = {"SHELF_NAME": port["EQUIP_NAME"], "SLOT_INST_ID": port["SLOT_INST_ID"]}
        delete_granite("/cards", delete_payload)
        updated_shelf = get_equipment_buildout(port.get("EQUIP_NAME"))
        for updated_port in updated_shelf:
            if updated_port.get("SLOT_INST_ID") == port.get("SLOT_INST_ID"):
                port = updated_port
                break
    if not port.get("CARD_TEMPLATE"):
        insert_card_template(port, card_template)
        updated_shelf = get_equipment_buildout(port.get("EQUIP_NAME"))
        for updated_port in updated_shelf:
            if updated_port.get("SLOT_INST_ID") == port.get("SLOT_INST_ID"):
                port_inst_id = updated_port.get("PORT_INST_ID")
                put_port_access_id(updated_port.get("PORT_INST_ID"), port_access_id)
                updated_shelf = get_equipment_buildout(port.get("EQUIP_NAME"))
                for updated_port in updated_shelf:
                    if updated_port.get("PORT_INST_ID") == port_inst_id:
                        return updated_port
    return port


def adva_admin_down_network_ports(network_ports, handoff_ports, model):
    if "114PRO" in model or "114S" in model or "XG108" in model:
        ports = {p["properties"]["name"][-1]: p["properties"] for p in network_ports}
    else:
        ports = {p["properties"]["name"][-1]: p["properties"] for p in network_ports[0]["eth"]}
    matched_ports = []
    filtered_network_ports = {}
    for k, v in ports.items():
        try:
            if v["admin_state"] == "unassigned":
                filtered_network_ports[k] = v
        except KeyError:
            pass
    for p in range(len(handoff_ports)):
        for nport in filtered_network_ports:
            if handoff_ports[p][1].casefold() == filtered_network_ports[nport]["name"].casefold():
                matched_ports.append(handoff_ports[p])
    return matched_ports


def rad_admin_down_network_ports(network_ports, handoff_ports):
    ports = {p["name"].replace("ETH-", ""): p for p in network_ports}
    ports_cleaned = {}
    for x, v in ports.items():
        try:
            if v["details"]["oper"] == "Down" and v["details"]["admin"] == "Down" and "ETH" in v["name"]:
                ports_cleaned[x] = v
        except KeyError:
            pass
    matched_ports = []
    for p in range(len(handoff_ports)):
        for nport in ports_cleaned:
            if handoff_ports[p][1].split()[-1] == ports_cleaned[nport]["name"].replace("ETH-", ""):
                matched_ports.append(handoff_ports[p])
    return matched_ports


def get_transport_path(equip_name):
    equip_name = equip_name.split("/")[0]
    endpoint = f"/circuitSites?CIRCUIT_NAME={equip_name}&WILD_CARD_FLAG=1&PATH_CLASS=P"
    granite_resp = get_granite(endpoint)
    if isinstance(granite_resp, dict):
        abort(500, f"No transport path found for device: {equip_name}")
    elif isinstance(granite_resp, list):
        # Filter out invalid service types and only get Live paths that end with the CPE tid
        live_transports = [
            x
            for x in granite_resp
            if x["CIRCUIT_STATUS"] == "Live"
            and x.get("SERVICE_TYPE") not in ["INT-CUSTOMER HANDOFF", "INT-CPE TRANSPORT"]
            and x.get("CIRCUIT_NAME").endswith(equip_name)
        ]
        if len(live_transports) == 0:
            abort(500, f"No Live transports found for serviceable shelf {equip_name}")
        elif len(live_transports) == 1:
            return live_transports[0]["CIRC_PATH_INST_ID"], live_transports[0]["CIRCUIT_NAME"]
        elif len(live_transports) > 1:
            abort(
                500,
                "More than one Live parent path found to serviceable shelf. "
                f"Transports: {[x['CIRCUIT_NAME'] for x in live_transports]}",
            )


def validate_transport_path(transport_path_inst_id, transport_path_name, bw_bps, chosen_shelf):
    # Fall out if parent device is an EPON or OLT PON
    parent_device = transport_path_name.split(".")[-2]  # will the transport path always contain two "." ?
    last_three_char = parent_device[-3:]
    if any(x for x in ["O9", "LT"] if x in last_three_char):
        abort(500, f"Unsupported EPON parent device found in transport {transport_path_name}")
    parent_equip_buildout = get_equipment_buildout(parent_device)
    if isinstance(parent_equip_buildout, dict):
        abort(500, f"No shelf found for parent device in transport {transport_path_name}")
    elif isinstance(parent_equip_buildout, list):
        if parent_equip_buildout[0].get("EQUIP_TYPE") == "OPTICAL LINE TERMINAL":
            abort(500, f"Unsupported EPON parent device found in transport {transport_path_name}")
    # Fall out if parent path would be oversubscribed by adding the new service
    # and CPE transport path does not route to a hub (QW)
    transport_upgrade, hub_work_required = False, False
    if will_transport_be_oversubscribed(transport_path_name, bw_bps):
        transport_upgrade = True
        # Check if shelf is live
        if chosen_shelf.get("EQUIP_STATUS") != "Live":
            abort(500, f"Customer existing CPE is not Live: {chosen_shelf.get('EQUIP_STATUS')}")
        # Perform hub transport checks
        hub_work_required = hub_transport_check(transport_path_inst_id, transport_path_name, True)
        if not hub_work_required:
            abort(500, f"Unsupported serviceable shelf CPE upgrade required for CPE transport {transport_path_name}")

    return transport_upgrade, hub_work_required


def underlay_topology_model_available_handoffs(model, bandwidth, vendor, connector_type):
    device_topology = UnderlayDeviceTopologyModel(
        role="cpe", device_bw=bandwidth, connector_type=connector_type, vendor=vendor, model=model
    )
    return device_topology.get_available_handoff_ports(circuit_bandwidth=bandwidth)


def potential_cpe_model(model):
    models = (
        # Adva
        "FSP 150CCF-825",
        "FSP 150CC-GE114/114S",
        "FSP 150-GE114PRO-C",
        "FSP 150-GE114PRO-HE",
        "FSP 150-XG116PRO",
        "FSP 150-XG116PROH",
        "FSP 150-XG118PRO (SH)",
        "FSP 150-XG120PRO",
        "FSP 150CC-GE206",
        "FSP 150CC-GE206V",
        "FSP150CC-GO102PRO",
        "ADVA FSP 150-XG404",
        "FSP 150CC-XG210",
        "FSP 150-XG108",
        # Rad
        "ETX203AX/2SFP/2UTP2SFP",
        "ETX-203AX/GE30/2SFP/4UTP",
        "ETX-220A",
        "ETX-2I-10G/4SFPP/4SFP4UTP",
        "ETX-2I-10G/4SFPP/24SFP",
        "ETX-2I-10G-B/8.5/8SFPP",
        "ETX-2I-10G-B/19/8SFPP",
        # Cisco
        "ME-3400-12CS",
        "ME-3400-24TS-A",
        "ME-3400-2CS",
        "ME-3400-EG-12CS-M",
        "ME-3400E-24TS-M",
        "ASR-920-12CZ",
        "ASR-920-24SZ",
        "ASR-920-4SZ-A",
        # Juniper
        "MX960",
        "MX480",
        "MX240",
        "MX204",
        "MX80 MODULAR",
    )

    if model in models:
        return True


def supported_model(model):
    models = (
        # Adva
        "FSP 150CC-GE114/114S",
        "FSP 150-GE114PRO-C",
        "FSP 150-XG116PRO",
        "FSP 150-XG116PROH",
        "FSP 150-XG120PRO",
        "FSP 150-XG108",
        # Rad
        "ETX203AX/2SFP/2UTP2SFP",
        "ETX-203AX/GE30/2SFP/4UTP",
        "ETX-220A",
        "ETX-2I-10G/4SFPP/4SFP4UTP",
        "ETX-2I-10G/4SFPP/24SFP",
        "ETX-2I-10G-B/8.5/8SFPP",
        "ETX-2I-10G-B/19/8SFPP",
    )

    if model in models:
        return True


def get_related_cid(trans_name):
    endpoint = "/pathChanAvailability"
    params = f"?PATH_NAME={trans_name}&CHAN_AVAILABILITY=IN USE&MIN_VLAN=1"
    channel_availability_resp = get_granite(f"{endpoint}{params}")

    if isinstance(channel_availability_resp, list):
        related_cid = channel_availability_resp[0]["MEMBER_PATH"]
        granite_resp = get_granite(f"/paths?CIRC_PATH_HUM_ID={related_cid}")
        if isinstance(granite_resp, list):
            related_cid_revision = granite_resp[0]["pathRev"]

            return related_cid, related_cid_revision
        else:
            abort(500, f"Unable to retreive path information for: {related_cid}")
    else:
        abort(500, f"Unable to find any circuits in Granite related to: {trans_name}")


def serviceable_shelf_main(payload):
    # Checking payload keys
    intake_put_vals = ["cid", "connector_type", "uni_type", "side"]
    missing = [key for key in intake_put_vals if key not in payload]

    if not all(key in payload for key in intake_put_vals):
        logger.error(f"Intake payload missing {missing}")
        abort(500, f"ARDA - Payload missing field(s): {missing}")

    if "agg_bandwidth" not in payload:
        agg_bandwidth = "10Gbps" if payload["product_name"] == "FC + Remote PHY" else "1Gbps"
    elif not payload["agg_bandwidth"]:
        agg_bandwidth = "10Gbps" if payload["product_name"] == "FC + Remote PHY" else "1Gbps"
    else:
        agg_bandwidth = payload["agg_bandwidth"]

    cid, connector_type, uni_type, side = (
        payload["cid"].upper(),
        payload["connector_type"],
        payload["uni_type"],
        payload["side"],
    )
    bandwidth = agg_bandwidth.lower()
    if "gbps" in bandwidth:
        bandwidth_value_type = re.split(r"(gbps)", bandwidth)
    elif "mbps" in bandwidth:
        bandwidth_value_type = re.split(r"(mbps)", bandwidth)
    else:
        abort(500, f"ARDA - Payload agg_bandwidth field {agg_bandwidth} is invalid")
    bandwidth_value = bandwidth_value_type[0].strip()
    bandwidth_type = bandwidth_value_type[1].strip()
    return serviceable_shelf_handoff(cid, bandwidth_type, bandwidth_value, connector_type, uni_type, side)
