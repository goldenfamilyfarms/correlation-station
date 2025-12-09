import logging
import re

from arda_app.bll.assign.enni_utils import _calculate_oversubscription, _is_relevant_router, _edna_check
from arda_app.bll.circuit_design.circuit_design_main import bw_upgrade_assign_gsip
from arda_app.bll.circuit_design.common import (
    _check_granite_bandwidth,
    _granite_create_circuit_revision,
    _validate_payload,
    create_transport_revision,
    express_update_circuit_bw,
    update_transport_bw,
    add_vrfid_link,
    fia_ipv6_check,
    get_cpe_info,
)
from arda_app.bll.circuit_status import update_circuit_status
from arda_app.bll.cpe_swap.cpe_swap_main import cpe_swap_main
from arda_app.bll.disconnect import get_circuit_tid_ports
from arda_app.bll.logical_change import check_enni, check_vlan
from arda_app.bll.net_new.utils.shelf_utils import (
    cpe_service_check,
    get_cpe_services,
    get_cpe_transport_paths,
    get_zsite,
)
from arda_app.common.cd_utils import granite_paths_url, granite_ports_put_url
from arda_app.common.utils import bandwidth_in_bps
from common_sense.common.errors import abort
from arda_app.dll.granite import (
    get_available_equipment_ports,
    get_device_vendor,
    get_granite,
    get_next_zw_shelf,
    get_path_elements_l1,
    get_path_elements,
    put_granite,
    get_path_association,
    assign_association,
    get_path_elements_inst_l1,
    delete_granite,
    insert_card_template,
    get_equipment_buildout_slot,
)
from arda_app.dll.mdso import onboard_and_exe_cmd, get_active_device
from arda_app.dll.sense import get_optic_info
from arda_app.bll.circuit_design.bandwidth_change.utils.granite_util import device_overview, device_details
from arda_app.bll.circuit_design.bandwidth_change.utils.network_utils import validate_customer_vlan_on_network

logger = logging.getLogger(__name__)


def bw_upgrade_main(body):
    """Main upgrade intake from pathid"""
    if body.get("pid"):
        msg = "PRISM ID not allowed in bw_upgrade payload."
        logger.error(msg)
        abort(500, msg)

    pathid = body.get("cid")
    body["bw_value"] = body["bw_speed"]
    engineering_name = body.get("engineering_name")
    prod_name = body.get("product_name")
    connector = "" if not body["connector_type"] else body["connector_type"].replace("N/A", "")
    uni_type = "" if not body["uni_type"] else body["uni_type"].replace("N/A", "")
    spectrum_primary_enni = "" if not body["spectrum_primary_enni"] else body["spectrum_primary_enni"]
    spectrum_secondary_enni = "" if not body["spectrum_secondary_enni"] else body["spectrum_primary_enni"]
    primary_vlan = "" if not body["primary_vlan"] else body["primary_vlan"]
    secondary_vlan = "" if not body["secondary_vlan"] else body["secondary_vlan"]
    type_2 = body.get("type_2", "")
    ec_msg = ""
    ctbh = False
    cea = False

    logger.info(f"Intake validation completed successfully, executing BW Upgrade for {pathid}")

    # checking whitelist of products we support
    if prod_name not in (
        "Fiber Internet Access",
        "Carrier Fiber Internet Access",
        "EP-LAN (Fiber)",
        "Carrier CTBH",
        "Carrier E-Access (Fiber)",
    ):
        abort(500, f"Unsupported Product for Normal BW Upgrades :: {prod_name}")

    # type 2 check not supported yet
    if type_2 == "Y":
        abort(500, "Type 2 circuits are unsupported for normal bandwith upgrades")

    if prod_name == "Carrier E-Access (Fiber)":
        cea = True
    elif prod_name == "Carrier CTBH":
        ctbh = True

    # CTBH only check
    if ctbh:
        if not body.get("class_of_service_type"):
            body["class_of_service_type"] = "GOLD"

        if connector or uni_type:
            if uni_type == "Trunked":  # Trunk ports are allowed for ctbh
                uni_type = ""
            else:
                msg = f"Connector Type: {connector} or UNI Type: {uni_type} values are unsupported for CTBH"
                abort(500, msg)

    # CTBH and CEA only check(carrier)
    if ctbh or cea:
        if spectrum_primary_enni or spectrum_secondary_enni:
            nni_rehome = check_enni(pathid, spectrum_primary_enni, spectrum_secondary_enni)

            if nni_rehome:
                abort(500, nni_rehome)

        if primary_vlan or secondary_vlan:
            vlan_change = check_vlan(pathid, primary_vlan, secondary_vlan)

            if vlan_change:
                abort(500, vlan_change)

        carrier_resp = get_path_elements_l1(pathid)

        if isinstance(carrier_resp, list):
            enni_list = enni_oversub_check(carrier_resp, pathid, body)
        else:
            msg = f"No ENNI path elements found in granite for {pathid}"
            logger.error(msg)
            abort(500, msg)

    # Validate the intake
    req_bw_val, req_bw_unit, mbps_req_bw_val = _validate_payload(body, pathid)

    # Obtain current BW and Instance ID in Granite
    (main_bw_val, main_bw_unit, mbps_main_bw_val, main_inst, main_rev) = _check_granite_bandwidth(pathid)

    # Compare the requested upgrade data against current Granite data
    mbps_delta_bw_val = upgrade_bw_compare(mbps_req_bw_val, mbps_main_bw_val, main_bw_val, main_bw_unit)

    if ctbh or cea:
        # get transport paths for CTBH and CEA
        transport_paths, all_paths = carrier_transport_paths(pathid, ctbh)

        # Analyze the hand-off port to see if it can support the requested bandwidth upgrade value
        cpe_upgrade_needed = _check_handoff_port(all_paths, mbps_req_bw_val, connector, uni_type, ctbh)

        if ctbh:
            edna_check_ctbh(mbps_req_bw_val, all_paths)
            trans_id, trans_name = check_transport_paths_ctbh(transport_paths, enni_list, mbps_delta_bw_val, pathid)
        else:
            trans_id, trans_name = _check_transport_paths(transport_paths, mbps_delta_bw_val, cea=True)

            # making sure we do not upgrade an enni transport
            for enni in enni_list:
                if trans_name == enni["ELEMENT_NAME"]:
                    trans_name = None
                    trans_id = None
                    break
    else:
        # Comparing network data to granite data
        transport_paths, all_paths = _granite_transport_devices_network_checks(pathid)

        # Evaluate each transport path to see if there is capacity to support the requested
        trans_id, trans_name = _check_transport_paths(transport_paths, mbps_delta_bw_val)

        # Analyze the hand-off port to see if it can support the requested bandwidth upgrade value
        cpe_upgrade_needed = _check_handoff_port(all_paths, mbps_req_bw_val, connector, uni_type, trans_id)

    # Comparing IP address salesforce data to granite data for FIA only
    if prod_name in ("Fiber Internet Access", "Carrier Fiber Internet Access"):
        sforce_granite_compare(all_paths, body)

    new_shelf = None
    trans_data = None
    cpe_installer = False
    mw_needed = False
    hub_work_required = False

    # If there is a transport path that needs to be upgraded to 10 Gbps to support bandwith upgrade
    # below functions will need to be run.
    if trans_id:
        mw_needed = True
        hub_work_required = hub_transport_check(trans_id, trans_name)
        trans_data, new_shelf, resp_data = trans_path_upgrade(
            trans_name, trans_id, cpe_upgrade_needed, hub_work_required
        )
    elif cpe_upgrade_needed:
        bad_port = cpe_upgrade_needed["PORT_ACCESS_ID"]
        bad_tid = cpe_upgrade_needed["TID"]

        msg = f"CPE {bad_tid} has a 1 Gbps port: {bad_port} that needs to get upgraded to a 10 Gbps port"
        logger.error(msg)
        abort(500, msg)

    if not ctbh:
        ec_msg = device_check(pathid, mbps_main_bw_val, mbps_req_bw_val, prod_name)

    # create circuit revision
    rev_result, rev_instance, rev_path = _granite_create_circuit_revision(pathid, main_rev)

    if not rev_result:
        msg = f"Unable to create new revision in Granite for {pathid}"
        logger.error(msg)
        abort(500, msg)

    logger.info(f"Revision Create Result: {rev_result} \nRevision Instance ID: {rev_instance}")

    # make sure revision has new instance ID
    if rev_instance == main_inst:
        msg = f"Revision Instance ID {rev_instance} matches current Instance ID {main_inst}"
        logger.error(msg)
        abort(500, msg)

    # add CEA to whitelist for evcid check
    if prod_name in ("EP-LAN (Fiber)", "Carrier CTBH", "Carrier E-Access (Fiber)"):
        evc_assoc_check(main_inst, rev_instance, pathid, prod_name, all_paths)

    if new_shelf:
        ec_msg, cpe_installer = cpe_10g_swap(rev_instance, cpe_upgrade_needed, trans_data, resp_data, pathid)

    # If transport path was upgraded to 10 Gbps to support bandwith upgrade
    # the 1 Gbps transport path will need to be removed to avoid oversubscription error
    if trans_data:
        remove_1G_transport(pathid, rev_instance)

    # This actually runs the BW update against Granite
    update_result = express_update_circuit_bw(pathid, rev_instance, rev_path, req_bw_val, req_bw_unit, engineering_name)

    # Set the circuit to 'Planned' status
    update_circuit_status(pathid, rev_instance, rev_path, "Planned")

    if "Fiber Internet Access" in body["product_name"]:
        fia_ipv6_check(pathid, mw_needed)

    # assign gsip
    bw_upgrade_assign_gsip(pathid, rev_instance, body["product_name"], body.get("class_of_service_type", ""))

    logger.info(f"Bandwidth Upgrade operation completed successfully, returning payload: \n{update_result}")
    update_result["cpe_installer"] = cpe_installer
    update_result["hub_work_required"] = hub_work_required
    update_result["mw_needed"] = "No"

    # changing the maintenance_window_needed and hub work required
    # hub work is being taken care of by MW needed flag, so Hub Work Required does not need to be set to yes as well
    if mw_needed:
        if hub_work_required:
            update_result["mw_needed"] = "Yes - Hub Impacted - Inflight Customer Only Impacted"
        else:
            update_result["mw_needed"] = "Yes - No Hub Impacted - Inflight Customer Only Impacted"

    if ec_msg:
        update_result["circuit_design_notes"] = ec_msg

    return update_result


def _retrieve_transport_paths(pathid):
    """Obtain a list of qualified transport paths and full list of all elements for provided CID
    Input:
      pathid = '21.L1XX.018627..CHTR'

    Output:
      transport_paths = [{71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW}, {71001.GE10.BFLONYKK0QW.BFLRNYZV1AW}]
      data = [{CHTRSE.CEN.NORTHEAST.MPLS}, {71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW},
              {71001.GE10.BFLONYKK0QW.BFLRNYZV1AW}, ...]
    """
    logger.info(f"Obtaining a list of qualified transport paths for {pathid}")
    url = f"/pathElements?LVL=1&CIRC_PATH_HUM_ID={pathid}"

    # Collect raw data from Granite
    try:
        data = get_granite(url, retry=3)
        logger.debug(f"data - {data}")
    except Exception as e:
        logger.exception(
            "Exception while retrieving circuit info from Granite pathElements "
            f"API \nURL: {url} \nPayload: None \nResponse {e}"
        )
        abort(500, f"Unable to retrieve circuit info. Exception while processing Granite response from {url}")

    if "retString" in data:
        msg = f"No circuit found in Granite for {pathid} \nURL: {url}"
        logger.error(msg)
        abort(500, msg)

    # Store ethernet transport paths (while discarding aggregate ones)
    transport_paths = []

    if data:
        for item in data:
            if item["BANDWIDTH"].upper() not in ("AGGREGATE", "10 GBPS"):
                if item["ELEMENT_CATEGORY"].upper() == "ETHERNET TRANSPORT":
                    qualified_path = {
                        "ELEMENT_NAME": item["ELEMENT_NAME"],
                        "ELEMENT_REFERENCE": item["ELEMENT_REFERENCE"],
                        "ELEMENT_STATUS": item["ELEMENT_STATUS"],
                        "BANDWIDTH": item["BANDWIDTH"],
                        "ELEMENT_BANDWIDTH": item["ELEMENT_BANDWIDTH"],
                    }
                    transport_paths.append(qualified_path)
    else:
        msg = f"No data for {pathid} was returned from Granite API call {url}"
        logger.error(msg)
        abort(500, msg)

    logger.debug(f"transport paths - {transport_paths}")

    # Return transport paths and raw data
    if transport_paths:
        return transport_paths, data

    msg = f"No qualified transport paths were found for {pathid}"
    logger.error(msg)
    abort(500, msg)


def _check_transport_paths(transport_paths, mbps_delta_bw_val, ctbh=False, cea=False):
    """Cycle through list of transport paths and check if requested bw can be accommodated\n
    Input:
      Transport_paths = [
        {"ELEMENT_NAME": "26001.GE1.RACNWIWG1QW.KENOWILC1ZW", "CIRC_PATH_INST_ID": "1927899"},
        {"ELEMENT_NAME": "26001.GE40L.RACNWIWG1CW.RACNWIWG1QW", "CIRC_PATH_INST_ID": "1729750"},
    ]
      mbps_delta_bw_val = 500 Mbps

    Output:
      path["CIRC_PATH_INST_ID"] = '125689'
      path["ELEMENT_NAME"] = '71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW'
        or
      None, None
    """
    logger.info("Checking if transport paths have enough bandwidth to support upgrade")

    if len(transport_paths):
        # Retrieve utilization info for each transport path
        for path in transport_paths:
            trans_name = path["ELEMENT_NAME"]
            if ctbh or cea:
                inst_id_key = "ELEMENT_REFERENCE"
            else:
                inst_id_key = "CIRC_PATH_INST_ID"
            inst_id = path[inst_id_key]
            url = f"/pathUtilization?CIRC_PATH_HUM_ID={trans_name}&CIRC_PATH_INST_ID={inst_id}"

            try:
                data = get_granite(url, retry=3)
                logger.debug(f"data - {data}")
            except Exception as e:
                logger.exception(
                    "Exception while retrieving path info from "
                    f"Granite pathUtilization API \nURL: {url} "
                    f"\nPayload: None \nResponse {e}"
                )
                abort(
                    500,
                    f"Unable to retrieve path utilization info. Exception while processing Granite response from {url}",
                )

            # Expect data for one path (while ignoring an aggregate path)
            if isinstance(data, list) and len(data) == 1:
                if data[0]["BANDWIDTH"] == "AGGREGATE":
                    continue

                try:
                    bw_value = int(data[0]["AVAILABLE_BW"])
                except Exception as e:
                    logger.exception(
                        "Exception while retrieving available bandwidth "
                        f"for path {trans_name} from Granite "
                        f"pathUtilization API \nURL: {url} \nPayload: None "
                        f"\n Response {e}"
                    )
                    abort(
                        500,
                        "Unable to retrieve available bandwidth for path "
                        f"{trans_name}. Exception while processing "
                        f"Granite response from {url}",
                    )

                bw_value = bw_value / 1_000_000  # Convert from bytes to Mb
                bw_unit = "Mbps"
                body = {"bw_value": bw_value, "bw_unit": bw_unit}
            elif isinstance(data, list) and len(data) > 1:
                if data[0]["BANDWIDTH"] == "AGGREGATE":
                    continue

                msg = f"Too many sets of path utilization values returned from Granite API call {url}"
                logger.error(msg)
                abort(500, msg)
            else:
                msg = f"There were no path utilization values returned from Granite API call {url}"
                logger.error(msg)
                abort(500, msg)

            # Determine if bw upgrade request exceeds capacity of transport paths
            _, _, avail_mbps_bw_val = _validate_payload(body, trans_name)

            if ctbh:
                perc = 0
                ctbh_dup_bw = mbps_delta_bw_val * 2

                if ctbh_dup_bw > avail_mbps_bw_val:
                    # check channelization on transport before oversubscribing
                    endpoint = "/pathChanAvailability"
                    params = f"?PATH_NAME={trans_name}&CHAN_AVAILABILITY=IN USE&MIN_VLAN=1"
                    channel_availability_resp = get_granite(f"{endpoint}{params}")

                    if len(channel_availability_resp) == 2:
                        if channel_availability_resp[0]["MEMBER_PATH"] == channel_availability_resp[1]["MEMBER_PATH"]:
                            # changing bw from Mbps to bps for oversubcription check
                            ctbh_dup_bw = bandwidth_in_bps(str(ctbh_dup_bw), "mbps")
                            perc = _calculate_oversubscription(trans_name, int(ctbh_dup_bw))

                            if int(perc) > 0:
                                if data[0].get("OVERSUBSCRIPTION"):
                                    perc = int(perc) + int(data[0]["OVERSUBSCRIPTION"])

                                url = granite_paths_url()
                                payload = {"PATH_INST_ID": inst_id, "PATH_MAX_OVER_SUB": str(perc)}
                                put_granite(url, payload)
                        else:
                            msg = "VLAN channel CIDs do not match, which is currently unsupported"
                            logger.error(msg)
                            abort(500, msg)
                    elif len(channel_availability_resp) > 2:
                        # if customer has multiple CTBH services will need to filter channel_availability_resp
                        msg = f"More than 2 VLAN channels on {trans_name} which is currently unsupported"
                        logger.error(msg)
                        abort(500, msg)
                    else:
                        msg = f"Less than 2 VLAN channels on {trans_name} which is currently unsupported"
                        logger.error(msg)
                        abort(500, msg)
            elif mbps_delta_bw_val > avail_mbps_bw_val:
                element_name = trans_name.split(".")[-2]

                if element_name.endswith("CW"):
                    msg = f"Hub transport path upgrades are unsupported: {path['ELEMENT_NAME']}"
                    logger.error(msg)
                    abort(500, msg)

                return inst_id, trans_name

    else:
        msg = "No transport paths to check"
        logger.error(msg)
        abort(500, msg)

    logger.info(f"All transport paths can support bandwidth upgrade difference of {mbps_delta_bw_val}")
    return None, None


def _check_handoff_port(all_paths, mbps_req_bw_val, connector, uni_type, trans_id=None, ctbh=False):
    """Iterate through list of paths to parse for handoff port and check its bandwidth
    Input:
      all_paths = 71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW, 71001.GE10.BFLONYKK0QW.BFLRNYZV1AW
      mbps_req_bw_val = 500 Mbps
      connector = RJ45
      uni_type = ACCESS

    Output:
      current_port = {
          "Z_SIDE_SITE": path["A_SITE_NAME"],
          "ELEMENT_NAME": path["ELEMENT_NAME"],
          "ELEMENT_TYPE": path["ELEMENT_TYPE"],
          "PORT_ACCESS_ID": path["PORT_ACCESS_ID"],
          "ELEMENT_REFERENCE": path["ELEMENT_REFERENCE"],
          "ELEMENT_STATUS": path["ELEMENT_STATUS"],
          "ELEMENT_BANDWIDTH": path["ELEMENT_BANDWIDTH"],
          "BANDWIDTH": path["BANDWIDTH"],
          "TID": path["TID"],
          "VENDOR": path["VENDOR"],
          "MODEL": path["MODEL"],
        }
        or
      False
    """
    logger.info("Checking if handoff port has enough bandwidth to support upgrade")

    if len(all_paths):
        # Search list by checking the last path element (potential handoff port) first
        all_paths.reverse()

        for path in all_paths:
            if path["ELEMENT_TYPE"].upper() == "PORT":
                current_port = {
                    "Z_SIDE_SITE": path["A_SITE_NAME"],
                    "ELEMENT_NAME": path["ELEMENT_NAME"],
                    "ELEMENT_TYPE": path["ELEMENT_TYPE"],
                    "PORT_ACCESS_ID": path["PORT_ACCESS_ID"],
                    "ELEMENT_REFERENCE": path["ELEMENT_REFERENCE"],
                    "ELEMENT_STATUS": path["ELEMENT_STATUS"],
                    "ELEMENT_BANDWIDTH": path["ELEMENT_BANDWIDTH"],
                    "BANDWIDTH": path["BANDWIDTH"],
                    "TID": path["TID"],
                    "VENDOR": path["VENDOR"],
                    "MODEL": path["MODEL"],
                }
                logger.info(f"current port - {current_port}")

                port_connector = path.get("CONNECTOR_TYPE", "").replace("-", "")
                port_channel = path.get("PORT_CHANNELIZATION", "")

                if connector:
                    if connector not in port_connector:
                        msg = f"Salesforce connector: {connector} not equal to granite connector type: {port_connector}"
                        logger.error(msg)
                        abort(500, msg)

                if uni_type:
                    if (port_channel == "DYNAMIC" and uni_type == "Access") or (
                        uni_type == "Trunked" and port_channel != "DYNAMIC"
                    ):
                        msg = f"Salesforce uni type: {uni_type} not equal to granite connector type: {port_channel}"
                        logger.error(msg)
                        abort(500, msg)

                # Process port bandwidth value
                bw_value = None

                if "/" in path["ELEMENT_BANDWIDTH"]:
                    # Get max port bandwidth value from '10/100/1000 BASET'
                    try:
                        bw_value = int(path["ELEMENT_BANDWIDTH"].split("/")[-1].split()[0])
                    except ValueError as e:
                        msg = (
                            f"Exception {e} while obtaining max bandwidth value of handoff port {path['PORT_ACCESS_ID']}"
                        )
                        logger.exception(msg)
                        abort(500, msg)

                    bw_unit = "Mbps"
                else:
                    bw_value, bw_unit = path["ELEMENT_BANDWIDTH"].split()

                body = {"bw_value": bw_value, "bw_unit": bw_unit}

                # Determine if bw upgrade request exceeds capacity of handoff port
                if ctbh:
                    max_mbps_bw_val = ctbh_cpe_check(current_port, mbps_req_bw_val, all_paths)
                else:
                    _, _, max_mbps_bw_val = _validate_payload(body, path["PORT_ACCESS_ID"])

                if mbps_req_bw_val > max_mbps_bw_val or trans_id:
                    if ctbh:
                        msg = f"CTBH handoff port can not support bandwidth upgrade to {mbps_req_bw_val} Mbps"
                        logger.error(msg)
                        abort(500, msg)

                    # normal bw process not for CTBH
                    return current_port

                # We are breaking after looking at first cpe handoff port.
                break
        else:
            msg = "Handoff port not found"
            logger.error(msg)
            abort(500, msg)
    else:
        msg = "No paths found"
        logger.error(msg)
        abort(500, msg)

    logger.info(f"Handoff port can support bandwidth upgrade to {mbps_req_bw_val}")
    return False


def _check_handoff_port_duplex_settings(
    pathid: str, mbps_main_bw_val: int, mbps_req_bw_val: int, prod_name: str
) -> bool:
    """This method collects the devices that make up a CID and identifies its CPE.
    After determining the CPE vendor, the correct MDSO command is executed to retrieve
    the CPE's network configuration data. Targeted data is the duplex rate setting of the CPE.
    From the current bandwidth value, if the requested bandwidth upgrade goes beyond the CPE duplex rate,
    then a maintenance window is required (return True).
    Otherwise, no maintenance window is needed (return False).

    Input:
      pathid = '21.L1XX.018627..CHTR'
      mbps_main_bw_val = 70
      mbps_req_bw_val = 120

    Output:
      True or False
    """
    logger.debug(f"mbps_main_bw_val - {mbps_main_bw_val}")
    logger.debug(f"mbps_req_bw_val - {mbps_req_bw_val}")

    # retrieve zw device
    devices, zw, _, _ = get_circuit_tid_ports(pathid, prod_name)
    zw_vendor = get_device_vendor(zw)

    zw_device = {"tid": zw, "port_id": devices.get(zw), "vendor": zw_vendor}

    logger.debug(f"zw_device - {zw_device}")

    if zw_vendor.upper() == "ADVA":
        duplex_rate_setting = _get_handoff_port_duplex_settings_ADVA(zw_device)
    elif zw_vendor.upper() == "RAD":
        duplex_rate_setting = _get_handoff_port_duplex_settings_RAD(zw_device)
    else:
        msg = f"Device {zw_device} is not supported when checking handoff port duplex settings"
        logger.error(msg)
        abort(500, msg)

    logger.debug(f"duplex_rate_setting - {duplex_rate_setting}")

    maintenance_window_required = _cross_duplex_bw_threshold([duplex_rate_setting], mbps_main_bw_val, mbps_req_bw_val)

    logger.debug(f"maintenance_window_required - {maintenance_window_required}")

    return maintenance_window_required


def _cross_duplex_bw_threshold(threshold_list: list, mbps_main_bw_val: int, mbps_req_bw_val: int) -> bool:
    """This method helps to determine if a requested bandwidth upgrade crosses at least a single threshold value.
    If a threshold is crossed, return True, else return False.

    Input:
      threshold_list = [10, 100, 1000]
      mbps_main_bw_val = 70
      mbps_req_bw_val = 120

    Output:
      True or False
    """
    if mbps_req_bw_val > 1000:
        return False

    for val in threshold_list:
        if mbps_main_bw_val <= val:
            if mbps_req_bw_val <= val:
                # does not cross threshold
                return False
            else:
                # crosses threshold
                return True

    return False


def _get_handoff_port_duplex_settings_ADVA(zw_device: dict) -> str:
    """
    Input:
      zw_device = {
          "tid": "FRBSTXGL2ZW",
          "port_id": "ACCESS-1-1-1-3",
          "vendor": "ADVA"
      }

    Output:
      rate_setting = 1000
    """

    def _get_duplex_config(network_data: dict) -> int:
        """Parsing for ADVA CPE negotiated port speed"""
        try:
            negotiated_port_speed = network_data["properties"]["negotiated_port_speed"]

            if negotiated_port_speed == "None":
                negotiated_port_speed = network_data["properties"]["configured_port_speed"]

                if negotiated_port_speed.lower() == "auto":
                    msg = f"Duplex setting for device {zw_device} is None or Auto"
                    logger.error(msg)
                    abort(500, msg)
        except Exception as e:
            msg = f"Unable to retrieve duplex setting for device {zw_device} - {e}"
            logger.error(msg)
            abort(500, msg)

        return negotiated_port_speed

    if not zw_device:
        msg = "ZW device is missing"
        logger.debug(msg)
        abort(500, msg)

    # Make network call to obtain device config data
    tid = zw_device.get("tid")
    port_access_id = zw_device.get("port_id").lower()
    logger.debug(f"Device {zw_device} vendor is {zw_device.get('vendor')}")
    device_config = onboard_and_exe_cmd(
        command="list_access_ports.json", hostname=tid, timeout=120, attempt_onboarding=False
    )

    logger.debug(f"device_config - {device_config}")

    # Locate the CPE's negotiated port speed
    try:
        network_data = device_config["result"]
    except Exception as e:
        msg = f"Unable to collect device config for {zw_device} - {e}"
        logger.error(msg)
        abort(500, msg)

    logger.debug(f"network_data - {network_data}")

    if isinstance(network_data, dict):
        if network_data.get("label") == port_access_id:
            negotiated_port_speed = _get_duplex_config(network_data)
        else:
            msg = f"Handoff port on {zw_device} not found"
            logger.error(msg)
            abort(500, msg)
    elif isinstance(network_data, list):
        for port in network_data:
            if port.get("label") == port_access_id:
                negotiated_port_speed = _get_duplex_config(port)
                break
        else:
            msg = f"Handoff port on {zw_device} not found"
            logger.error(msg)
            abort(500, msg)

    logger.debug(f"negotiated_port_speed - {negotiated_port_speed}")

    # Parse for the ADVA CPE's duplex rate setting
    # Example: duplex_setting = "auto-1000-full"
    if "auto" in negotiated_port_speed:
        rate_setting = negotiated_port_speed.split("-")[1]
    else:
        # Example: duplex_setting = "100-full"
        rate_setting = negotiated_port_speed.split("-")[0]

    duplex_setting = negotiated_port_speed.split("-")[-1]

    if duplex_setting.upper() != "FULL":
        msg = f"Duplex setting for {zw_device} was found to be {duplex_setting}"
        logger.error(msg)
        abort(500, msg)

    return int(rate_setting)


def _get_handoff_port_duplex_settings_RAD(zw_device: dict) -> int:
    """
    Input:
      zw_device = {
          "tid": "BRHMALFZ1ZW",
          "port_id": "ETH PORT 5",
          "vendor": "RAD"
      }

    Output:
      rate_setting = 1000
    """

    def _get_duplex_config(network_data: dict) -> tuple:
        """Parsing for RAD CPE speed duplex value"""
        try:
            speed_duplex = network_data["result"]["speed-duplex"]
        except Exception as e:
            msg = f"Unable to retrieve duplex setting for device {zw_device} - {e}"
            logger.error(msg)
            abort(500, msg)

        return speed_duplex

    if not zw_device:
        msg = "ZW device is missing"
        logger.debug(msg)
        abort(500, msg)

    logger.debug(f"Device {zw_device} vendor is {zw_device.get('vendor')}")

    # Make network call to obtain device config data
    command = "get-port-info-details.json"
    tid = zw_device.get("tid")
    port_access_id = zw_device.get("port_id")

    # Example: port_id = 5 from "ETH PORT 5"
    port_id = port_access_id.split(" ")[-1]
    logger.debug(f"port_id - {port_id}")

    device_config = onboard_and_exe_cmd(
        command=command, parameter=port_id, hostname=tid, timeout=120, attempt_onboarding=False
    )
    logger.debug(f"device_config - {device_config}")

    # Locate the CPE's speed duplex value
    if isinstance(device_config, dict):
        try:
            network_param = device_config["parameters"]
        except Exception as e:
            msg = f"Unable to check parameters for MDSO command {command} - {e}"
            logger.error(msg)
            abort(500, msg)

        if (network_param.get("type") == "ETHERNET") and (network_param.get("id") == port_id):
            speed_duplex = _get_duplex_config(device_config)
        else:
            msg = f"Unable to retrieve duplex setting on {zw_device}"
            logger.error(msg)
            abort(500, msg)
    else:
        msg = f"Unexpected format of network data from {zw_device} using {command}"
        logger.error(msg)
        abort(500, msg)

    logger.debug(f"speed_duplex - {speed_duplex}")

    # Parse for the RAD CPE's duplex rate setting
    # Example: speed_duplex = "1000-x-full-duplex"
    rate_setting = (re.search("[0-9]+", speed_duplex)).group(0)

    if (re.search("[F|f][U|u][L|l][L|l]", speed_duplex)) is None:
        msg = f"Duplex setting for {zw_device} is not full: {speed_duplex}"
        logger.error(msg)
        abort(500, msg)

    return int(rate_setting)


def _granite_transport_devices_network_checks(cid):
    """Validate underlay devices in Granite path and verify customer VLAN is provisioned
    on CW, QW, AW devices\n
    :param cid: "95.L1XX.802359..CHTR"
    :return transport_paths: [
        {"ELEMENT_NAME": "26001.GE1.RACNWIWG1QW.KENOWILC1ZW", "CIRC_PATH_INST_ID": "1927899"},
        {"ELEMENT_NAME": "26001.GE40L.RACNWIWG1CW.RACNWIWG1QW", "CIRC_PATH_INST_ID": "1729750"},
    ]
    :return path_elements_l1: standard LVL=1 /pathElements response (list of dicts)
    """
    path_elements = get_path_elements(cid)
    path_elements_l1 = [x for x in path_elements if x.get("LVL") == "1"]

    if not path_elements_l1 or isinstance(path_elements_l1, dict):
        msg = "L1 path elements are missing"
        logger.debug(msg)
        abort(500, msg)

    for elem in path_elements_l1:
        if elem.get("ELEMENT_STATUS").upper() != "LIVE" and elem["ELEMENT_TYPE"] in ["PATH", "PORT"]:
            abort(500, f"Path element is not Live: {elem['ELEMENT_NAME']}")
        elif "EPON" in elem["ELEMENT_CATEGORY"]:
            abort(500, "EPON topology is unsupported")

    customer_vlan = ""
    for elem in path_elements_l1:
        if elem.get("CHAN_NAME") and "VLAN" in elem["CHAN_NAME"]:
            customer_vlan = elem["CHAN_NAME"].replace("VLAN", "")
            break

    if not customer_vlan:
        abort(500, "Unable to retrieve customer vlan data from path elements")

    # High-level device info
    distinct_tids, has_cw, has_qw, has_aw, has_zw = device_overview(path_elements)
    logger.debug(distinct_tids)
    logger.debug(f"\nhas_cw = {has_cw}\nhas_qw = {has_qw}\nhas_aw = {has_aw}\nhas_zw = {has_zw}")

    if not distinct_tids:
        abort(500, "No valid device TIDs found in the path")
    if not has_cw:
        abort(500, "Circuit path is missing the CW router")
    if not has_zw:
        abort(500, "Circuit path is missing the ZW CPE")

    # Fill in device details (vendor, model, port, parent transport path)
    devices = device_details(path_elements, distinct_tids)

    # Extract distinct transports and their path inst IDs
    transport_paths = [
        {
            "ELEMENT_NAME": devices[x]["parent_transport_path"],
            "CIRC_PATH_INST_ID": devices[x]["parent_transport_path_inst_id"],
        }
        for x in devices.keys()
        if devices[x].get("parent_transport_path")
    ]

    # Check customer vlan on the network for CW, QW, AW devices
    validate_customer_vlan_on_network(customer_vlan, devices, cid)

    logger.info(transport_paths)
    return transport_paths, path_elements_l1


def granite_port_info(pathid, path_instid):
    """Getting uplink port info from Granite
    Input:
      pathid = "71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW"
      path_instId = "234567"

    Output:
      uplink_port[0] = {GE-0/0/1}
        or
      abort
    """
    logger.info("Getting uplink port info from Granite")
    # url = f"/pathElements?CIRC_PATH_HUM_ID={pathid}&LVL=1&CIRC_PATH_INST_ID={path_instid}"
    url = f"/pathElements?CIRC_PATH_INST_ID={path_instid}&LVL=1"

    try:
        data = get_granite(url, retry=3)
        logger.debug(f"data - {data}")
    except Exception as e:
        logger.exception(
            f"Exception while retrieving transport path info from GraniteAPI \nURL: {url} \nPayload: None \nResponse {e}"
        )
        abort(500, f"Unable to retrieve transport path info. Exception while processing Granite response from {url}")

    if "retString" in data:
        msg = f"No transport path found in Granite for {pathid} \nURL: {url}"
        logger.error(msg)
        abort(500, msg)

    uplink_port = []

    for port in data:
        if port["TID"] == pathid.split(".")[-2]:
            uplink_port.append(port)

    if len(uplink_port) == 1:
        return uplink_port[0]

    msg = "Either multiple or no uplink port found in transport path"
    logger.error(msg)
    abort(500, msg)


def port_check_10G(uplink_device):
    """Checking uplink device for available 10 Gbps port
    Input:
      uplink_device = "BFLRNYZV1AW.999.99.9999.SWT"

    Output:
      port_10G[0] = {XE-0/0/1} or abort
    """
    logger.info("Checking uplink device for available 10 Gbps port")
    data = get_available_equipment_ports(uplink_device)

    port_10G = []

    for port in data:
        if port["BANDWIDTH"] == "10 Gbps":
            port_10G.append(port)

    if len(port_10G) > 0:
        return port_10G[0]

    msg = f"No available 10 Gbps ports on {uplink_device}"
    logger.error(msg)
    abort(500, msg)


def remove_uplink(path_name, path_instid, uplink_port):
    """Removing 1 Gbps uplink port from transport path revision
    Input:
      path_name = '71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW'
      path_instId = "234567"
      uplink_port = {GE-0/0/1}

    Output:
      None or abort
    """
    logger.info("Removing 1 Gbps uplink port from transport path revision")
    url = granite_paths_url()
    payload = {
        "PATH_NAME": path_name,
        "PATH_INST_ID": path_instid,
        "PATH_LEG_INST_ID": uplink_port["LEG_INST_ID"],
        "REMOVE_ELEMENT": "true",
        "ELEMENTS_TO_REMOVE": "1",
    }

    try:
        put_granite(url, payload)
    except Exception as e:
        logger.exception(
            "Exception while parsing revision create response from Granite paths API "
            f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
        )
        abort(500, "Unable to remove 1 Gbps uplink port. Exception while processing Granite response", url=url)


def remove_1G_transport(path_name, path_instid):
    """Removing 1 Gbps transport path from new path revision
    Input:
      path_name = "71.L1XX.013079..CHTR"
      path_instid = "1234567"

    Output:
      None or abort
    """
    logger.info(f"Removing 1 Gbps transport path from new path revision for {path_name}")
    url = f"/pathElements?CIRC_PATH_INST_ID={path_instid}&LVL=1"

    # Collect raw data from Granite
    try:
        data = get_granite(url, retry=3)
        logger.debug(f"data - {data}")
    except Exception as e:
        logger.exception(
            "Exception while retrieving circuit info from Granite pathElements "
            f"API \nURL: {url} \nPayload: None \nResponse {e}"
        )
        abort(500, f"Unable to retrieve circuit info. Exception while processing Granite response from {url}")

    if "retString" in data:
        msg = f"No circuit found in Granite for {path_name} \nURL: {url}"
        logger.error(msg)
        abort(500, msg)

    # Storing 1 Gbps transport paths that will need to be removed from revision CID
    path_to_delete = []

    if data:
        for item in data:
            if item["ELEMENT_BANDWIDTH"].upper() == "1 GBPS":
                if item["ELEMENT_CATEGORY"].upper() == "ETHERNET TRANSPORT":
                    path_to_delete.append(item)
    else:
        msg = f"No data for {path_name} was returned from Granite API call {url}"
        logger.error(msg)
        abort(500, msg)

    if len(path_to_delete) > 1:
        msg = "There are more than one transport paths to remove"
        logger.error(msg)
        abort(500, msg)
    elif len(path_to_delete) == 0:
        msg = "There are no transport paths to remove"
        logger.error(msg)
        abort(500, msg)

    url = granite_paths_url()
    payload = {
        "PATH_NAME": path_name,
        "PATH_INST_ID": path_instid,
        "PATH_LEG_INST_ID": path_to_delete[0]["LEG_INST_ID"],
        "REMOVE_ELEMENT": "true",
        "ELEMENTS_TO_REMOVE": path_to_delete[0]["SEQUENCE"],
    }

    try:
        put_granite(url, payload)
    except Exception as e:
        logger.exception(
            "Exception while parsing revision create response from Granite paths API "
            f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
        )
        abort(500, "Unable to remove 1 Gbps uplink port. Exception while processing Granite response", url=url)


def add_uplink_port(path_name, path_instid, uplink_port, leg_inst_id):
    """Adding 10 Gbps uplink port to transport path revision
    Input:
      path_name = "71001.GE1.BFLRNYZV1AW.BFLRNYZV3ZW"
      path_instid = "234567"
      uplink_port = {GE-0/0/1}
      leg_inst_id = "67890"

    Output:
      None or abort
    """
    logger.info("Adding 10 Gbps uplink port to transport path revision")
    url = granite_paths_url()
    payload = {
        "PATH_NAME": path_name,
        "PATH_INST_ID": path_instid,
        "PATH_LEG_INST_ID": leg_inst_id,
        "ADD_ELEMENT": "true",
        "PATH_ELEM_SEQUENCE": "1",
        "PATH_ELEMENT_TYPE": "EQUIPMENT_PORT",
        "PORT_INST_ID": uplink_port["PORT_INST_ID"],
    }

    try:
        put_granite(url, payload)
    except Exception as e:
        logger.exception(
            "Exception while parsing revision create response from Granite paths API "
            f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
        )
        abort(500, "Unable to create circuit revision. Exception while processing Granite response", url=url)


def new_cpe(cpe_swap):
    """Checking the vendor of the current device to determine which cpe to swap
    Input:
      cpe_swap_payload = {
          "cid": pathid,
          "device_tid": cpe_upgrade_needed["TID"],
          "new_vendor": cpe_upgrade_needed["VENDOR"],
          "path_inst_id": rev_instance,
          "trans_inst_id": trans_data["pathInstanceId"],
          "transport_10G": resp_data["pathId"],
      }

    Output:
      cpe_swap = {
          "cid": pathid,
          "device_tid": cpe_upgrade_needed["TID"],
          "new_vendor": cpe_upgrade_needed["VENDOR"],
          "path_inst_id": rev_instance,
          "trans_inst_id": trans_data["pathInstanceId"],
          "transport_10G": resp_data["pathId"],
          "new_model" = "ADVA FSP 150-XG108"
      }
        or
      abort
    """
    if cpe_swap["new_vendor"] == "ADVA":
        cpe_swap["new_model"] = "FSP 150-XG108"
    elif cpe_swap["new_vendor"] == "RAD":
        cpe_swap["new_model"] = "ETX-2I-10G-B/8.5/8SFPP"
    else:
        msg = f"{cpe_swap['new_vendor']} Vendor unsupported for 10 Gbps cpe swap"
        logger.error(msg)
        abort(500, msg)

    return cpe_swap


def multiple_paths_check(transport_path_id, cpe_swap_payload):
    """Check if more than one channel is built on the transport path to the CPE
    Input:
      transport_path_id = 71001.GE10.BFLRNYZV1AW.BFLRNYZV4ZW
      cpe_swap_payload["CID"] = 21.L1XX.123456..TWCC

    Output:
      None
    """
    endpoint = "/pathChanAvailability"
    params = f"?PATH_NAME={transport_path_id}&CHAN_AVAILABILITY=IN USE&MIN_VLAN=1"
    channel_availability_resp = get_granite(f"{endpoint}{params}")

    if len(channel_availability_resp) > 1:
        for channel in channel_availability_resp:
            if cpe_swap_payload["cid"] != channel["MEMBER_PATH"]:
                remove_1G_transport(channel["NEXT_PATH"], channel["NEXT_INST_ID"])


def sforce_granite_compare(all_paths, body):
    usable_ip = body.get("usable_ip_addresses_requested", "")
    subnet = all_paths[0].get("IPV4_ASSIGNED_SUBNETS", "")
    gateway = all_paths[0].get("IPV4_ASSIGNED_GATEWAY", "")

    if usable_ip:
        if usable_ip.split("=")[0].replace("/", "") != subnet.split("/")[-1]:
            msg = f"Requested IP subnets: {usable_ip} not equal to granite subnets: {subnet}"
            logger.error(msg)
            abort(500, msg)

    ip_service_type = body.get("primary_fia_service_type", "")
    service_type = all_paths[0].get("IPV4_SERVICE_TYPE", "")

    if ip_service_type:
        if ip_service_type.upper() != service_type:
            msg = f"Primary FIA Service type: {ip_service_type} not equal to granite IP service type: {service_type}"
            logger.error(msg)
            abort(500, msg)

    ip_address = body.get("ip_address", "")

    if ip_address:
        ip_address = remove_ip_bad_stuff(ip_address)

        if ip_address not in subnet and ip_address not in gateway:
            msg = f"Salesforce IP address: {ip_address} not equal to granite IP address: {subnet}"
            logger.error(msg)
            abort(500, msg)


def remove_ip_bad_stuff(ip_string):
    """
    Input:
      ip_string = 'ip: 127.0.0.1/20'

    Output:
      '127.0.0.1/20'
    """
    ip_string = ip_string.replace("IPv4", "").replace("IPv6", "")

    pattern = r"[^0-9./,]"
    result = re.sub(pattern, "", ip_string)

    return result


def enni_oversub_check(carrier_resp, pathid, body):
    enni_list = []
    prod_name = body["product_name"]

    # changing bw to bps for oversubcription check
    bw_req = bandwidth_in_bps(body["bw_speed"], body["bw_unit"])

    tid_list = []

    for enni_port in carrier_resp:
        if enni_port["ELEMENT_TYPE"] == "PORT" and enni_port["PORT_ROLE"] == "ENNI":
            tid_list.append(enni_port["ELEMENT_NAME"].split("/")[0])

    # looking for ENNI
    for element in carrier_resp:
        if element["ELEMENT_TYPE"] == "PATH":
            enni_name = element["ELEMENT_NAME"]

            if enni_name.endswith("CHTR") or enni_name.endswith("TWCC"):
                enni_list.append(element)
            elif enni_name.split(".")[2] in tid_list:
                enni_list.append(element)
            # elif look at lowest sequence number to find enni

    if (len(enni_list) == 2 and prod_name == "Carrier CTBH") or (
        len(enni_list) == 1 and prod_name == "Carrier E-Access (Fiber)"
    ):
        for enni in enni_list:
            e_name = enni["ELEMENT_NAME"]
            enni_instid = enni["ELEMENT_REFERENCE"]

            # Check ENNI utilization for over-subscription % and update, if needed
            over_sub_perc = _calculate_oversubscription(e_name, int(bw_req))

            if int(over_sub_perc) > 0:
                url = granite_paths_url()
                payload = {"PATH_INST_ID": enni_instid, "PATH_MAX_OVER_SUB": over_sub_perc}
                put_granite(url, payload)

        return enni_list
    elif len(enni_list) > 2:
        msg = f"There are more than 2 ENNIs on {pathid} which is currently unsupported. Please investigate"
        logger.error(msg)
        abort(500, msg)

    # will fallout if ctbh has less than 2 ENNIs and cea has 0 ENNIs
    msg = f"There are {len(enni_list)} ENNIs on {pathid} which is currently unsupported. Please investigate"
    logger.error(msg)
    abort(500, msg)


def carrier_transport_paths(pathid, ctbh=False):
    transport_paths, all_paths = _retrieve_transport_paths(pathid)

    if ctbh:
        cpe_list = []
        cpe_trans_list = []

        # AW-DSW0 check in element name
        for path in all_paths:
            ename = path["ELEMENT_NAME"]

            if "AW-DSW0" in ename:
                msg = f"AW-DSW0 found in {ename} which is currently unsupported"
                logger.error(msg)
                abort(500, msg)
            elif path["ELEMENT_TYPE"] == "PORT" and path["PORT_ROLE"] in ("UNI-EVP", "UNI-EP"):
                cpe_list.append(ename.split("/")[0])

        for t_path in transport_paths:
            if t_path["ELEMENT_NAME"].split(".")[-1] in cpe_list:
                cpe_trans_list.append(t_path)
        # for ctbh only
        return cpe_trans_list, all_paths

    # for all other products
    return transport_paths, all_paths


def check_transport_paths_ctbh(transport_paths, enni_list, mbps_delta_bw_val, pathid):
    transport_list = []

    for transport in transport_paths:
        # Looking for CPE transport paths only
        ename = transport["ELEMENT_NAME"]

        if (
            ename != enni_list[0]["ELEMENT_NAME"]
            and ename != enni_list[1]["ELEMENT_NAME"]
            and transport not in transport_list
        ):
            transport_list.append(transport)

    if len(transport_list):
        return _check_transport_paths(transport_list, mbps_delta_bw_val, ctbh=True)

    # may need to look through all transports but can only oversubscribe cpe transport for ctbh
    msg = f"No CPE transport found on path {pathid} during CTBH BW upgrade"
    logger.error(msg)
    abort(500, msg)


def ctbh_cpe_check(current_port, mbps_req_bw_val, all_paths):
    vendor = current_port["VENDOR"]
    model = current_port["MODEL"]
    tid = current_port["ELEMENT_NAME"].split("/")[0]

    if vendor == "CISCO" and "3400" in model:
        if mbps_req_bw_val > 500:
            msg = f"Cisco {model} has a max BW of 500 Mbps for CTBH"
            logger.error(msg)
            abort(500, msg)
    elif vendor == "ALCATEL" and "7705" in model:
        if mbps_req_bw_val > 300:
            msg = f"Alcatel {model} has a max BW of 300 Mbps for CTBH"
            logger.error(msg)
            abort(500, msg)

    for path in all_paths:
        if path["ELEMENT_TYPE"] == "PATH" and tid in path["ELEMENT_NAME"]:
            if path["ELEMENT_BANDWIDTH"] == "1 Gbps":
                return 1000

            # returning 10000 Mbps as max cpe bw if not 1 Gbps transport
            return 10000

    msg = f"Unable to find Max BW for CTBH device: {current_port['TID']}"
    logger.error(msg)
    abort(500, msg)


def upgrade_bw_compare(mbps_req_bw_val, mbps_main_bw_val, main_bw_val, main_bw_unit):
    if mbps_req_bw_val > mbps_main_bw_val:
        mbps_delta_bw_val = mbps_req_bw_val - mbps_main_bw_val
        return mbps_delta_bw_val
    elif mbps_main_bw_val == mbps_req_bw_val:
        abort_bw = f"{main_bw_val}{main_bw_unit}"
        msg = f"No change required - requested bandwidth {abort_bw} matches current bandwidth on path"
        logger.error(msg)
        abort(500, msg)
    else:
        message = f"Requested bandwidth {mbps_req_bw_val} is less than current bandwidth {mbps_main_bw_val}"
        logger.error(message)
        abort(500, message)


def trans_path_upgrade(trans_name, trans_id, cpe_upgrade_needed, hub_transport):
    """Upgrading transport path from 1G to 10G"""
    new_shelf = None
    if hub_transport:
        uplink_port = granite_port_info(trans_name, trans_id)
        remove_uplink(trans_name, trans_id, uplink_port)

        # remove sfp and add in SFP+ card into uplink port and update Port access id
        ten_gig_port = card_swap(uplink_port)
        add_uplink_port(trans_name, trans_id, ten_gig_port, uplink_port["LEG_INST_ID"])
        trans_data = create_transport_revision(trans_name, trans_id)
        trans_rev_instid = trans_data["pathInstanceId"]
    else:
        trans_data = create_transport_revision(trans_name, trans_id)

        trans_rev_instid = trans_data["pathInstanceId"]
        uplink_port = granite_port_info(trans_data["pathId"], trans_rev_instid)

        uplink_device = uplink_port["ELEMENT_NAME"]
        ten_gig_port = port_check_10G(uplink_device)

        remove_uplink(trans_name, trans_rev_instid, uplink_port)

        add_uplink_port(trans_name, trans_rev_instid, ten_gig_port, uplink_port["LEG_INST_ID"])

    if cpe_upgrade_needed:
        new_shelf = get_next_zw_shelf(cpe_upgrade_needed["Z_SIDE_SITE"])

    resp_data = update_transport_bw(trans_name, trans_rev_instid, new_shelf)

    return trans_data, new_shelf, resp_data


def device_check(pathid, mbps_main_bw_val, mbps_req_bw_val, prod_name):
    supported_cpe = ("ADVA", "RAD")
    tid, vendor, model = get_cpe_info(pathid)

    # cpe vendor check
    if vendor not in supported_cpe:
        msg = f"Unsupported CPE vendor :: {vendor}"
        logger.error(msg)
        abort(500, msg)

    # verifying the device is active on the network to perform BW change later
    try:
        _, _ = get_active_device(tid)
    except Exception:
        msg = f"Unable to login into the device: {tid} - {vendor} - {model}"
        logger.error(msg)
        abort(500, msg)

    # validate services on CPE shelf
    z_site_info = get_zsite(pathid)
    shelf_dict = get_cpe_transport_paths(tid, z_site_info)
    shelf_info, cids = get_cpe_services(shelf_dict)
    cpe_service_check(shelf_info, cids)

    # Check CPE handoff port duplex settings to determine if a maintenance window and CPE install is needed
    duplex_threshold = [10, 100, 1000]

    # Starting from the current bandwidth, determine if the bandwidth upgrade request crosses a duplex threshold
    check_network_data = _cross_duplex_bw_threshold(duplex_threshold, mbps_main_bw_val, mbps_req_bw_val)

    # If a duplex threshold is crossed, see if the bandwidth upgrade request crosses the current CPE duplex rate
    # ceiling on the network
    if check_network_data:
        mw_needed = _check_handoff_port_duplex_settings(pathid, mbps_main_bw_val, mbps_req_bw_val, prod_name)
        logger.debug(f"maintenance_window_required - {mw_needed}")

        # changing exit criteria message for port/duplex update being needed
        if mw_needed:
            return "Customer coordination is required for Port Speed/Duplex change on handoff."


def evc_assoc_check(main_inst, rev_instance, pathid, prod_name, all_paths):
    association = get_path_association(main_inst)

    if isinstance(association, dict):
        if association.get("retString"):
            # some evcid values are to long so no association is created in granite
            granite_evc = all_paths[0]["EVC_ID"]

            if granite_evc:
                if len(granite_evc) > 6:
                    return

            msg = f"Missing association in granite for {pathid}"
            logger.error(msg)
            abort(500, msg)

    for evc in association:
        # adding path association to revision
        evcid = evc["associationValue"]
        association_name = evc["associationName"]
        range_name = evc["numberRangeName"]

        assoc_result = assign_association(rev_instance, evcid, association_name, range_name)

        if not assoc_result:
            msg = f"Unable to add path association {evcid} to new revision in Granite for {pathid}"
            logger.error(msg)
            abort(500, msg)

        if prod_name == "EP-LAN (Fiber)":
            # link revision to VRFID network link
            add_vrfid_link(pathid, rev_instance)


def cpe_10g_swap(rev_instance, cpe_upgrade_needed, trans_data, resp_data, pathid):
    # changing exit criteria message when cpe is being swapped
    ec_msg = "Customer coordination is required for CPE shelf swap."
    cpe_installer = True

    cpe_swap_payload = {
        "cid": pathid,
        "device_tid": cpe_upgrade_needed["TID"],
        "new_vendor": cpe_upgrade_needed["VENDOR"],
        "path_inst_id": rev_instance,
        "trans_inst_id": trans_data["pathInstanceId"],
        "transport_10G": resp_data["pathId"],
    }

    cpe_swap = new_cpe(cpe_swap_payload)

    cpe_swap_main(cpe_swap)

    # remove 1 Gbps transport path from related CID revisions
    multiple_paths_check(resp_data["pathId"], cpe_swap_payload)

    return ec_msg, cpe_installer


def edna_check_ctbh(req_bw, all_paths):
    """Adding EDNA network check for ctbh HUB devices when requested BW is over 3 Gbps and port role is ENNI"""

    if req_bw > 3000:
        cid = all_paths[0]["PATH_NAME"]

        cid_info = get_path_elements(cid)

        edna_list = []

        for element in reversed(cid_info):
            hub_device = element["ELEMENT_NAME"]
            # checking CW hub device has EDNA NETWORK
            if _is_relevant_router(element):
                if _edna_check(element.get("ELEMENT_REFERENCE")):
                    edna_list.append(hub_device)
            else:
                network = element.get("DEVICE_INFO_NETWORK", "")
                port_role = element.get("PORT_ROLE", "")
                tid = element.get("TID", "")

                # checking ENNI device has EDNA NETWORK
                if port_role == "ENNI" and network == "EDNA":
                    edna_list.append(tid)

        if len(set(edna_list)) < 3:
            msg = "Unsupported BW request over 3 Gbps & ENNI or HUB device not on EDNA network"
            abort(500, msg)


def hub_transport_check(trans_id, trans_name, serviceable_shelf=False):
    """Checking the transport path to determine if it can be upgraded to 10Gbps"""
    start_element_name = trans_name.split(".")[-2]
    end_element_name = trans_name.split(".")[-1]

    if start_element_name.endswith("QW"):
        # if Hub transport with an MTU - Abort
        if end_element_name.endswith("AW"):
            abort(500, f"Hub transport upgrade is currently unsupported MTU in hub transport path: {trans_name}")

        if not serviceable_shelf:
            # if more than one CID on the transport - Abort
            endpoint = "/pathChanAvailability"
            params = f"?PATH_NAME={trans_name}&CHAN_AVAILABILITY=IN USE&MIN_VLAN=1"
            channel_availability_resp = get_granite(f"{endpoint}{params}")

            if len(channel_availability_resp) != 1:
                abort(
                    500,
                    f"Hub transport upgrade is currently unsupported more than one CID on transport path: {trans_name}",
                )

        # if circuit is on CWDM and wavelengths are 1430nm or 1450nm  - Abort
        response = get_path_elements_inst_l1(trans_id)

        if isinstance(response, list):
            pe_port_number = response[0]["PORT_ACCESS_ID"]
            port = get_optic_info(start_element_name, pe_port_number)
            vendor_name = port.get("vendor", "")
            wavelength = port.get("wavelength", "").replace("nm", "").strip()
            receive_power = float(port.get("receive_power", ""))

            if wavelength in ("1430", "1450", "1430.00", "1450.00"):
                abort(500, f"Hub transport upgrade is currently unsupported CWDM wavelength: {wavelength}")

            # if circuit is on a Champion Optic - Abort
            if "CHAMPION" in vendor_name.upper():
                abort(500, f"Hub transport upgrade is currently unsupported optic vendor: {vendor_name}")

            # fallout if the Laser receiver power is -21 or below
            if not serviceable_shelf and receive_power <= -21:
                abort(500, f"Hub transport upgrade is currently unsupported optic receive power: {receive_power}")
            return True
        else:
            abort(500, f"No path elements found on transport path: {trans_name}")

    else:
        return False


def card_swap(uplink_port):
    """Changing 1G SFP card template to 10G SFP+ card template and updating port access ID"""
    card_template = "GENERIC SFP+ LEVEL 1"
    equipment_name = uplink_port.get("ELEMENT_NAME", "").replace("#", "%23")
    port_id = uplink_port.get("PORT_ACCESS_ID", "").replace("GE", "XE")
    resp = get_equipment_buildout_slot(equipment_name, uplink_port.get("SLOT", ""))

    if len(resp) == 1:
        resp = resp[0]
        delete_payload = {"SHELF_NAME": resp.get("EQUIP_NAME"), "SLOT_INST_ID": resp.get("SLOT_INST_ID")}
        delete_granite("/cards", delete_payload)
        insert_card_template(resp, card_template)
        port = get_equipment_buildout_slot(equipment_name, uplink_port.get("SLOT", ""))[0]

        payload = {"PORT_INST_ID": port.get("PORT_INST_ID", ""), "PORT_STATUS": "Assigned", "PORT_ACCESS_ID": port_id}
        put_url = granite_ports_put_url()
        put_granite(put_url, payload)

        return port
    else:
        abort(500, "Unable to determine which SLOT to remove/add card template")
