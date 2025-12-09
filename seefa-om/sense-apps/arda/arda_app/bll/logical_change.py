import re

from arda_app.bll.models.payloads import LogicalChangePayloadModel
from arda_app.dll.granite import (
    get_granite,
    put_granite,
    get_circuit_site_info,
    get_path_association,
    assign_association,
    get_path_elements_l1,
    get_path_elements_inst_l1,
)
from arda_app.bll.circuit_design.circuit_design_main import bw_upgrade_assign_gsip
from arda_app.common.cd_utils import granite_paths_url
import logging
from common_sense.common.errors import abort
from arda_app.bll.circuit_design.common import _granite_create_circuit_revision, add_vrfid_link
from arda_app.bll.net_new.vlan_reservation.vlan_reservation_main import vlan_reservation_main
from arda_app.bll.net_new.ip_reservation.utils.granite_utils import granite_assignment
from arda_app.bll.assign.enni import assign_enni_main
from arda_app.bll.models.payloads.vlan_reservation import VLANReservationPayloadModel


logger = logging.getLogger(__name__)


def get_circuit_path_inst_id(cid):
    circuit_data = get_circuit_site_info(cid)
    try:
        circuit_path_inst_id = circuit_data[0].get("CIRC_PATH_INST_ID")
        return circuit_path_inst_id
    except (KeyError, IndexError):
        abort(500, f"No circuit_path_inst_id found in Granite for cid: {cid}")


def get_granite_data(cid, circuit_path_inst_id):
    endpoint = f"/circuitUDAs?CIRC_PATH_INST_ID={circuit_path_inst_id}"
    granite_resp = get_granite(endpoint)
    granite_cos = None
    rev_nbr = None
    if isinstance(granite_resp, list):
        for attribute in granite_resp:
            if attribute["ATTR_NAME"] == "CLASS OF SERVICE":
                granite_cos = attribute["ATTR_VALUE"]
                rev_nbr = attribute["REV_NBR"]

    if granite_cos and rev_nbr:
        return granite_cos, rev_nbr
    else:
        abort(500, f"No CLASS OF SERVICE Type found in Granite for cid: {cid}")


def add_association(cid, circuit_path_inst_id, prod_name, rev_instance):
    association = None

    if prod_name in ("EP-LAN (Fiber)", "EPL (Fiber)", "Carrier E-Access (Fiber)"):
        association = get_path_association(circuit_path_inst_id)

        if isinstance(association, dict):
            if association.get("retString"):
                abort(500, f"Missing association in granite for {cid}")

        # adding path association to revision
        evcid = association[0]["associationValue"]
        association_name = association[0]["associationName"]
        range_name = association[0]["numberRangeName"]

        assoc_result = assign_association(rev_instance, evcid, association_name, range_name)

        if not assoc_result:
            abort(500, f"Unable to add path association {evcid} to new revision in Granite for {cid}")

        if prod_name == "EP-LAN (Fiber)":
            # link revision to VRFID network link
            add_vrfid_link(cid, rev_instance)


def update_class_of_service_type(cid, rev_instance, class_of_service_type, engineering_name):
    put_granite_url = granite_paths_url()
    payload = {
        "PATH_NAME": cid,
        "PATH_INST_ID": rev_instance,
        "PATH_ORDER_NUM": engineering_name,
        "UDA": {"CIRCUIT SOAM PM": {"CLASS OF SERVICE": class_of_service_type, "SLM ELIGIBILITY": "ELIGIBLE DESIGN"}},
    }
    put_granite(put_granite_url, payload)


def logical_change_process(body, nni_rehome, vlan_change, spectrum_primary_enni, primary_vlan):
    cid = body["cid"]
    prod_name = body["product_name"]

    circuit_path_inst_id = get_circuit_path_inst_id(cid)

    salesforce_cos = body["class_of_service_type"] if body.get("class_of_service_type") else ""

    granite_cos, rev_nbr = get_granite_data(cid, circuit_path_inst_id)

    granite_cos_split = granite_cos.split()
    granite_cos_level = granite_cos_split[0]
    granite_cos_type = granite_cos_split[1]

    if not salesforce_cos and (not nni_rehome and not vlan_change):
        abort(500, f"Unsupported, no CLASS OF SERVICE Type provided in Salesforce payload for cid: {cid}")

    if (granite_cos_level.upper() == salesforce_cos.upper()) and (not nni_rehome and not vlan_change):
        abort(500, "Class of Service Type in Granite and Salesforce matches")

    rev_result, rev_instance, rev_path = _granite_create_circuit_revision(cid, rev_nbr)

    if nni_rehome:
        nni_rehome_change(cid, spectrum_primary_enni, rev_instance)

    if vlan_change:
        change_vlan(cid, prod_name, primary_vlan, rev_instance)

    add_association(cid, circuit_path_inst_id, prod_name, rev_instance)

    if salesforce_cos:
        updated_cos = f"{salesforce_cos.upper()} {granite_cos_type}"
        update_class_of_service_type(cid, rev_instance, updated_cos, body["engineering_name"])

    # assign gsip
    bw_upgrade_assign_gsip(cid, rev_instance, body["product_name"], body.get("class_of_service_type", "Gold"))

    return rev_instance


def hosted_voice_upgrade(body):
    cid = body["cid"]
    circuit_path_inst_id = get_circuit_path_inst_id(cid)

    bw_upgrade_assign_gsip(cid, circuit_path_inst_id, body["product_name"], body.get("class_of_service_type", "Gold"))

    if body["product_name"] in {"Hosted Voice - (Fiber)"}:
        path_elements = get_path_elements_l1(cid)
        if not isinstance(path_elements, list):
            abort(500, "No elements found for product: Hosted Voice - (Fiber). Please investigate")

        ipv4_subnets = path_elements[0].get("IPV4_ASSIGNED_SUBNETS", None)
        ipv4_gateway = path_elements[0].get("IPV4_ASSIGNED_GATEWAY", None)
        if ipv4_gateway is None or ipv4_subnets is None:
            abort(502, f"No IPV4_ASSIGNED_SUBNETS or IPV4_ASSIGNED_GATEWAY found for cid: {cid}")

        if not ipv4_subnets.endswith("/30") or not ipv4_gateway.endswith("/30"):
            if "/" in ipv4_subnets:
                ipv4_subnets = ipv4_subnets.split("/")[0]
            if "/" in ipv4_gateway:
                ipv4_gateway = ipv4_gateway.split("/")[0]
            params = {
                "PATH_INST_ID": circuit_path_inst_id,
                "UDA": {
                    "INTERNET SERVICE ATTRIBUTES": {
                        "IPv4 ASSIGNED SUBNET(s)": f"{ipv4_subnets}/30",
                        "IPv4_ASSIGNED_GATEWAY": f"{ipv4_gateway}/30",
                    }
                },
            }
            granite_assignment(params)

    return circuit_path_inst_id


def check_enni(cid, primary_enni: str, secondary_enni: str = "") -> None:
    """Check if primary and secondary E-NNI on EPR matches Granite."""
    # Validate Primary E-NNI format
    primary = _validate_enni(primary_enni)

    # Validate Secondary E-NNI format
    secondary = _validate_enni(secondary_enni, secondary=True)

    if primary or secondary:
        path_elements = get_path_elements_l1(cid)
        check_circuit_revisions(path_elements)
        primary_enni_match = False
        secondary_enni_match = False

        for path in path_elements:
            if path.get("ELEMENT_NAME") == primary:
                primary_enni_match = True

            if path.get("ELEMENT_NAME") == secondary:
                secondary_enni_match = True

        if primary and not primary_enni_match:
            return "Spectrum Primary E-NNI provided on EPR does not match Granite"

        if secondary and not secondary_enni_match:
            return "Spectrum Secondary E-NNI provided on EPR does not match Granite"


def _validate_enni(enni: str, secondary: bool = False) -> None:
    """Validate E-NNI format for primary and secondary E-NNI on EPR."""
    # Identify E-NNI type
    enni_type = "Secondary" if secondary else "Primary"

    # list of user values that result in no enni check being needed
    bad_enni = (
        "upgrade / no change",
        "(no change)",
        "no change",
        "existing/upgrade",
        "existing nni/vlan",
        "existing",
        "n/a",
        "na",
    )

    # enni with empty string or enni in bad enni list
    if not enni or enni.lower() in bad_enni:
        return ""
    elif enni:  # checking to see if any bad enni values in enni
        for bad in bad_enni:
            if bad in enni.lower():
                enni = enni.replace(bad, "").strip()

    # Regex patterns for E-NNI format
    cid_pattern = re.compile(r"(\d{2}\.[KGFD|KFFD]{4}\.\d{6}\.[A-Z0-9]{0,3}\.[TWCC|CHTR]{4})")
    path_pattern = re.compile(r"(\d{5}\.GE\d(\d?){2}\.[A-Z0-9]{11}\.[A-Z0-9]{11})")

    # Abort if E-NNI does not match CID or Path format
    if enni and not (cid_pattern.match(enni) or path_pattern.match(enni)):
        abort(502, f"{enni_type} E-NNI on EPR is not a valid E-NNI format: {enni}")

    return enni


def check_vlan(cid, primary_vlan, secondary_vlan=""):
    """Checking primary and secondary VLAN on EPR."""

    # removing letters and special characters leaving only digits
    primary = re.sub(r"\D", "", primary_vlan) if primary_vlan else ""
    secondary = re.sub(r"\D", "", secondary_vlan) if secondary_vlan else ""

    if primary or secondary:
        path_elements = get_path_elements_l1(cid)

        primary_vlan_match = False
        secondary_vlan_match = False

        for path in path_elements:
            chan_name = "" if not path["CHAN_NAME"] else path["CHAN_NAME"]

            if primary in chan_name:
                primary_vlan_match = True

            if secondary in chan_name:
                secondary_vlan_match = True

        if primary and not primary_vlan_match:
            return "Spectrum Primary VLAN provided on EPR does not match Granite"

        if secondary and not secondary_vlan_match:
            return "Spectrum Secondary VLAN provided on EPR does not match Granite"


def nni_rehome_change(cid, nni, rev_instance):
    """Removing and adding ENNI and CW port to path revision"""

    # remove NNI and CW port
    find_and_remove_enni(cid, rev_instance)

    # insert new NNI and CW port
    assign_enni_main({"cid": cid, "spectrum_primary_enni": nni, "rev_instance": rev_instance})

    # add vlan info to CW port and New ENNI CHAN
    update_enni_vlan(nni, rev_instance, cid)


def update_enni_vlan(nni, rev_instance, cid):
    """Updating the ENNI and CW port VLAN information"""
    elements = get_path_elements_inst_l1(rev_instance)

    if isinstance(elements, list):
        nni_list = []
        nni_port_list = []
        vlan_list = []

        for elem in elements:
            if nni == elem["ELEMENT_NAME"]:
                nni_list.append(elem)
            elif elem["ELEMENT_TYPE"] == "PORT" and elem["PORT_ROLE"] == "ENNI":
                nni_port_list.append(elem)
            elif elem["ELEMENT_TYPE"] == "PATH":
                vlan_list.append(elem)

        if len(nni_port_list) == 1 and len(nni_list) == 1 and vlan_list:
            vlan = vlan_list[0]["CHAN_NAME"].replace("VLAN", "")
            port_inst_id = nni_port_list[0]["PORT_INST_ID"]

            # Assign VLAN to NNI
            put_granite_url = granite_paths_url()
            put_granite_payload = {
                "PATH_NAME": nni_list[0]["ELEMENT_NAME"],
                "PATH_INST_ID": nni_list[0]["ELEMENT_REFERENCE"],
                "CHANNEL_INST_ID": nni_list[0]["CHAN_INST_ID"],
                "CHANNEL_NAME": f"VLAN{vlan}",
                "UPDATE_CHANNEL": "true",
            }

            put_granite(put_granite_url, put_granite_payload, timeout=60)

            #  Add VLAN info to ENNI CW Port:
            put_granite_url = f"/ports?PORT_INST_ID={port_inst_id}"
            payload = {
                "PORT_INST_ID": port_inst_id,
                "SET_CONFIRMED": "TRUE",
                "UDA": {"VLAN INFO": {"S-VLAN": vlan, "CUSTOMER S-VLAN": vlan}},
            }
            put_granite(put_granite_url, payload)
        else:
            abort(500, "Circuit designed in an unsupported format, unable to update VLAN")
    else:
        abort(500, f"No path elements found in granite for cid: {cid}")


def change_vlan(cid, prod_name, vlan, path_instid):
    """Updating VLAN information on transport paths and ports"""

    payload = VLANReservationPayloadModel
    payload.cid = cid
    payload.product_name = prod_name
    payload.primary_vlan = vlan
    payload.path_instid = path_instid
    payload.service_type = "change_logical"
    payload.vlan_requested = ""
    payload.service_provider_vlan = ""
    vlan_reservation_main(payload)


def find_and_remove_enni(pathid, path_instid):
    """Finding ENNI and CW port and removing from the path revision"""
    enni_list = []
    tid_list = []
    tid_sequence = []
    carrier_resp = get_path_elements_inst_l1(path_instid)

    for enni_port in carrier_resp:
        if enni_port["ELEMENT_TYPE"] == "PORT" and enni_port["PORT_ROLE"] == "ENNI":
            tid_list.append(enni_port["ELEMENT_NAME"].split("/")[0])
            tid_sequence.append(enni_port["SEQUENCE"])

    # looking for ENNI
    for element in carrier_resp:
        if element["ELEMENT_TYPE"] == "PATH":
            enni_name = element["ELEMENT_NAME"]

            if enni_name.endswith("CHTR") or enni_name.endswith("TWCC"):
                enni_list.append(element)
            elif enni_name.split(".")[2] in tid_list:
                enni_list.append(element)

    if len(enni_list) == 1 and len(tid_sequence) == 1:
        # remove enni from circuit ID
        url = granite_paths_url()
        payload = {
            "PATH_NAME": pathid,
            "PATH_INST_ID": path_instid,
            "PATH_LEG_INST_ID": enni_list[0]["LEG_INST_ID"],
            "REMOVE_ELEMENT": "true",
            "ELEMENTS_TO_REMOVE": f"{enni_list[0]['SEQUENCE']}, {tid_sequence[0]}",
        }

        try:
            put_granite(url, payload)
        except Exception as e:
            logger.exception(
                "Exception while parsing revision create response from Granite paths API "
                f"\nURL: {url} \nPayload: {payload} \nResponse: \n{e}"
            )
            abort(500, "Unable to remove enni. Exception while processing Granite response", url=url)
    else:
        # will fallout if cea has more than 1 ENNI or cea has 0 ENNIs
        msg = f"There are {len(enni_list)} ENNIs on {pathid} which is currently unsupported. Please investigate"
        logger.error(msg)
        abort(500, msg)


def check_circuit_revisions(path_elements):
    """Check if circuit has multiple revisions"""
    if isinstance(path_elements, list):
        first_id = path_elements[0].get("CIRC_PATH_INST_ID")
        for item in path_elements[1:]:
            if item.get("CIRC_PATH_INST_ID") != first_id:
                abort(500, "Unsupported: Circuit has multiple revisions which is currently unsupported")
    else:
        abort(500, "No path elements found for circuit in granite")


def logical_change_main(payload: LogicalChangePayloadModel) -> dict:
    """Process Logical Change Orders"""
    body = payload.model_dump()
    product_name = body.get("product_name", "")
    cid = body.get("cid", "")

    if body.get("service_type") not in {"change_logical"}:
        abort(500, "Only orders with service_type of change_logical are supported")

    if product_name not in (
        "EPL (Fiber)",
        "EP-LAN (Fiber)",
        "Carrier E-Access (Fiber)",
        "Hosted Voice - (Fiber)",
        "Hosted Voice - (DOCSIS)",
        "Hosted Voice - (Overlay)",
        "Carrier CTBH",
    ):
        abort(500, f"Unsupported Product :: {product_name}")

    if body.get("third_party_provided_circuit") == "Y":
        abort(500, "Unsupported Logical Change :: 3rd Party Circuit")

    change_reason = body.get("change_reason")
    if (
        change_reason
        not in ("Upgrading Service", "HV - Complex", "Feature Change-No MRC Impact", "Feature Change-MRC Impact")
    ) or (
        change_reason == "Feature Change-MRC Impact"
        and body.get("product_name")
        not in ("Hosted Voice - (Fiber)", "Hosted Voice - (DOCSIS)", "Hosted Voice - (Overlay)")
    ):
        abort(500, f"Unsupported Logical Change :: {body['change_reason']}")

    spectrum_primary_enni = body.get("spectrum_primary_enni", None)
    spectrum_secondary_enni = body.get("spectrum_secondary_enni", None)
    primary_vlan = body.get("primary_vlan", "")
    nni_rehome = None
    vlan_change = None

    if product_name in ("Carrier E-Access (Fiber)", "Carrier CTBH") and (
        spectrum_primary_enni or spectrum_secondary_enni
    ):
        nni_rehome = check_enni(cid, spectrum_primary_enni, spectrum_secondary_enni)

        if nni_rehome and product_name == "Carrier CTBH":
            abort(500, nni_rehome)

        if product_name == "Carrier E-Access (Fiber)":
            vlan_change = check_vlan(cid, primary_vlan)

    if body.get("product_name") in ("Hosted Voice - (Fiber)", "Hosted Voice - (DOCSIS)", "Hosted Voice - (Overlay)"):
        circ_path_inst_id = hosted_voice_upgrade(body)
    else:
        circ_path_inst_id = logical_change_process(body, nni_rehome, vlan_change, spectrum_primary_enni, primary_vlan)

    return {
        "circ_path_inst_id": circ_path_inst_id,
        "engineering_job_type": "Logical Change",
        "maintenance_window_needed": (
            "Yes - No Hub Impact - Inflight Customer Only Impacted" if nni_rehome or vlan_change else "No"
        ),
        "message": "Logical Change updated successfully",
    }
