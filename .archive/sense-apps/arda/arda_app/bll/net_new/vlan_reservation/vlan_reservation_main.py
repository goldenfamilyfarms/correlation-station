import logging

from arda_app.bll.models.payloads.vlan_reservation import VLANReservationPayloadModel, Type2OuterVLANRequestPayloadModel
from common_sense.common.errors import abort

from arda_app.bll.utils import get_4_digits, get_special_char
from arda_app.bll.net_new.vlan_reservation.collect_vlans import (
    get_granite_vlans,
    get_network_vlans,
    get_network_outer_vlans,
    get_next_available_vlan_or_subinterface,
)
from arda_app.dll.granite import get_granite, put_granite, get_path_elements, get_path_elements_inst_l1
from arda_app.common.cd_utils import (
    get_l1_port_url,
    get_l1_port_inst_url,
    get_l1_url,
    granite_paths_url,
    granite_ports_put_url,
)


logger = logging.getLogger(__name__)


def get_circuit_data(cid, path_instid):
    logger.info("Executing Granite pathElements lookups")

    if path_instid:
        circuit_info_data = get_path_elements_inst_l1(path_instid)
    else:
        circuit_info_data = get_path_elements(cid)

    transport_elements = [
        element
        for element in circuit_info_data
        if (
            element["ELEMENT_CATEGORY"] == "ETHERNET TRANSPORT"
            or (element["ELEMENT_CATEGORY"] == "ETHERNET" and element["ELEMENT_TYPE"] == "PATH")
        )
    ]

    if len(transport_elements) < 1:
        msg = f"No elements found in Granite for {cid}"
        abort(500, msg)
        logger.info(f"Granite pathElements lookups completed successfully.\n Transport Elements: {transport_elements}")

    return transport_elements


def assign_vlans(vlan, elements, payload, type2):
    cid = payload.cid
    product_name = payload.product_name
    logger.info(f"Assiging VLAN {vlan} to {cid} and {elements}")

    # updating dynamic router port access id
    enni_paid = ""

    if type2:
        ov_vlan = payload.service_provider_vlan
        enni = payload.spectrum_buy_nni_circuit_id
        path_elements = get_path_elements(enni)

        for port in path_elements:
            if "CW" in port.get("TID"):
                enni_paid = port.get("PORT_ACCESS_ID")
                break

    for element in elements:
        logger.info(f"ELEMENT_NAME: {element}")
        rphy_vlan_num = 0

        if product_name == "FC + Remote PHY":
            # Skip DEV to DEV transport for RPHY products
            elem_name = element["ELEMENT_NAME"].split(".")

            if len(set(elem_name)) != len(elem_name):
                continue

            if "-" in vlan and not ("CW" in elem_name[2] and "QW" in elem_name[3]):
                rphy_vlan_num = vlan.split("-")[1]
                vlan = vlan.split("-")[0]

        # Assign VLAN to element
        put_granite_url = granite_paths_url()
        put_granite_payload = {
            "PATH_NAME": element["ELEMENT_NAME"],
            "PATH_INST_ID": element["ELEMENT_REFERENCE"],
            "CHANNEL_INST_ID": element["CHAN_INST_ID"],
            "CHANNEL_NAME": f"VLAN{vlan}",
            "UPDATE_CHANNEL": "true",
        }

        if type2:
            if enni == element["ELEMENT_NAME"]:
                put_granite_payload["CHANNEL_NAME"] = f"{vlan}:OV-{ov_vlan}//IV-1100"
            else:
                put_granite_payload["CHANNEL_NAME"] = "VLAN1100"

        try:
            put_granite(put_granite_url, put_granite_payload, timeout=60)
        except Exception as e:
            if rphy_vlan_num:
                put_granite_payload["CHANNEL_NAME"] = f"VLAN{vlan}-{rphy_vlan_num}"
                put_granite(put_granite_url, put_granite_payload, timeout=60)
            else:
                logger.error(
                    f"VLAN {vlan} assignment to {element['ELEMENT_NAME']} failed "
                    f"\nURL: {put_granite_url} \nResponse: \n{e}"
                )
                abort(500, f"Unable to assign VLAN {vlan} to Granite path {element['ELEMENT_NAME']}")

        logger.info(f"Assigned VLAN {vlan} to {element['ELEMENT_NAME']}")

    logger.info(f"VLANs successfully assigned to {len(elements)} elements")

    # removing any special characters from vlan and only using the first 4 digits
    if not isinstance(vlan, int):
        vlan_name = vlan
        special_char = get_special_char(vlan)

        if special_char:
            vlan_name = vlan.replace(special_char, "")

        vlan = get_4_digits(vlan_name)

    logger.info(f"{cid}: Obtaining PORT_INST_ID for port UDA updates")

    # using inst id when avaiable to provide correct port count (VLAN change logic)
    if payload.path_instid:
        url = get_l1_port_inst_url(payload.path_instid)
    else:
        url = get_l1_port_url(cid)

    get_data = get_granite(url)

    if not isinstance(get_data, list):
        msg = f"Unable to locate port info for {cid}"
        logger.error(f"{msg}: \n{get_data}")
        abort(500, msg)

    # Remove any AUDIOCODES elements in list
    get_data = [port for port in get_data if port["VENDOR"] != "AUDIOCODES"]

    if len(get_data) == 2 and product_name != "EPL (Fiber)":
        try:
            port_inst = get_data[1]["PORT_INST_ID"]
        except KeyError:
            msg = f"Unable to locate 'PORT_INST_ID' value for {cid}"
            logger.exception(f"{msg}: \n{get_data}")
            abort(500, msg)

        payload = {
            "SET_CONFIRMED": True,
            "PORT_INST_ID": port_inst,
            "UDA": {
                "VLAN INFO": {
                    "INCOMING VLAN OPERATION": "" if type2 else "PUSH",
                    "S-VLAN": "1100" if type2 else str(vlan),
                }
            },
        }

        put_url = granite_ports_put_url()

        # Additional logic to address Trunked handoffs
        if get_data[0]["PORT_ROLE"] == "UNI-EVP":
            payload["SET_CONFIRMED"] = True
            payload["UDA"]["VLAN INFO"]["PORT-ROLE"] = "UNI-EVP"
            payload["UDA"]["VLAN INFO"]["BUNDLED C-VLAN"] = str(vlan)
            port_access_id = get_trunked_port_access_id(cid, elements)
            payload["PORT_ACCESS_ID"] = port_access_id

        # Default logic supports Access handoffs
        put_data = put_granite(put_url, payload, timeout=60)

        logger.info(f"Updating port information for {cid} with payload \n{payload}")
        logger.info(f"Port info update completed successfully. Granite response: \n{put_data}")

        try:
            port_inst = get_data[0]["PORT_INST_ID"]
        except KeyError:
            logger.exception(f"Unable to locate 'PORT_INST_ID' value for {cid}: \n{get_data}")
            abort(500, f"Unable to locate 'PORT_INST_ID' value for {cid}")

        payload = {
            "SET_CONFIRMED": True,
            "PORT_INST_ID": port_inst,
            "UDA": {
                "VLAN INFO": {
                    "S-VLAN": "1100" if type2 else str(vlan),
                    "CUSTOMER S-VLAN": ov_vlan if type2 else str(vlan),
                }
            },
        }

        # adding port role and PAID for ENNI router port for type II FIA
        if type2:
            if enni_paid:
                payload["PORT_ACCESS_ID"] = enni_paid

            payload["UDA"]["VLAN INFO"]["PORT-ROLE"] = "ENNI"

        # Additional logic to address Trunked handoffs
        if get_data[0]["PORT_ROLE"] == "UNI-EVP":
            payload["SET_CONFIRMED"] = True
            payload["UDA"]["VLAN INFO"]["PORT-ROLE"] = "UNI-EVP"
            payload["UDA"]["VLAN INFO"]["BUNDLED C-VLAN"] = str(vlan)
            port_access_id = get_trunked_port_access_id(cid, elements)
            payload["PORT_ACCESS_ID"] = port_access_id

        # Default logic supports Access handoffs
        put_data = put_granite(put_url, payload, timeout=60)

        logger.info(f"Updating port information for {cid} with payload \n{payload}")
        logger.info(f"Port info update completed successfully. Granite response: \n{put_data}")
    elif len(get_data) == 1 or (product_name == "EPL (Fiber)" and len(get_data) == 2):
        for port in get_data:
            try:
                port_inst = port["PORT_INST_ID"]
            except KeyError:
                msg = f"Unable to locate 'PORT_INST_ID' value for {cid}"
                logger.exception(f"{msg}: \n{port}")
                abort(500, msg)

            payload = {
                "SET_CONFIRMED": True,
                "PORT_INST_ID": port_inst,
                "UDA": {"VLAN INFO": {"INCOMING VLAN OPERATION": "PUSH", "S-VLAN": str(vlan)}},
            }

            put_url = granite_ports_put_url()

            # Additional logic to address Trunked handoffs
            if port["PORT_ROLE"] == "UNI-EVP":
                payload["SET_CONFIRMED"] = True
                payload["UDA"]["VLAN INFO"]["PORT-ROLE"] = "UNI-EVP"
                payload["UDA"]["VLAN INFO"]["BUNDLED C-VLAN"] = str(vlan)
                port_access_id = get_trunked_port_access_id(cid, elements)
                payload["PORT_ACCESS_ID"] = port_access_id

            # Default logic supports Access handoffs
            put_data = put_granite(put_url, payload, timeout=60)

            logger.info(f"Updating port information for {cid} with payload \n{payload}")
            logger.info(f"Port info update completed successfully. Granite response: \n{put_data}")


def get_trunked_port_access_id(cid, transports):
    """Retrieve port access ID of trunked handoff port"""
    logger.info(f"Retrieve port access ID from ZW to ZW transport path for {cid}")
    rtransports = list(reversed(transports))

    # Find ZW to ZW ethernet transport path
    port_access_id = ""

    for path in rtransports:
        cpe1, cpe2 = "", ""

        try:
            _, _, cpe1, cpe2 = path["ELEMENT_NAME"].split(".")
        except (ValueError, KeyError, AttributeError) as e:
            msg = f"Unrecognized format for transport path {path['ELEMENT_NAME']}"
            logger.error(f"{msg}: {e}")
            abort(500)

        if cpe1.endswith("ZW"):
            if cpe1 == cpe2:
                port_access_id = get_paid_from_zw_to_zw_path(path["ELEMENT_NAME"])
                break
            else:
                msg = "ZW to ZW transport path not found"
                logger.error(msg)
                abort(500, f"{msg} in {cid}")
    else:
        msg = "ZW to ZW transport path not found"
        logger.error(msg)
        abort(500, f"{msg} in {cid}")

    logger.info(f"Port access ID = {port_access_id}")

    if port_access_id:
        return port_access_id

    msg = "Port access ID from ZW to ZW transport path not found"
    logger.error(msg)
    abort(500, f"{msg} in {cid}")


def get_paid_from_zw_to_zw_path(element_name):
    """Parse for port access ID from ZW to ZW transport pathElements call"""
    logger.info(f"Find port access ID from ZW to ZW transport path {element_name}")
    get_url = f"/pathElements?LVL=1&CIRC_PATH_HUM_ID={element_name}"
    handoff_port_data = get_granite(get_url)

    if "retString" in handoff_port_data:
        msg = f"No record found in Granite for {element_name}"
        logger.error(msg)
        abort(500, msg)

    port_access_id = handoff_port_data[0]["PORT_ACCESS_ID"]
    logger.info(f"Port access ID = {port_access_id}")

    if not port_access_id:
        msg = f"Unable to determine Port access ID for {element_name}"
        logger.error(msg)
        abort(500, msg)

    return port_access_id


def get_assigned_vlan_or_subinterface(payload: VLANReservationPayloadModel, transports, attempt_onboarding, type2):
    """Get the lowest vlan."""
    # For Type 2
    if type2:
        # Type 2 vlan will always be unique on a new subinterface
        primary_vlan = ""
    else:  # For Normal BAU circuits
        primary_vlan = payload.primary_vlan if payload.primary_vlan else ""

    # FC + Remote PHY
    if payload.product_name == "FC + Remote PHY":
        primary_vlan = "4063"
        network_vlans_or_subinterfaces = set()
    else:
        # Get network vlans if product name is not FC + Remote PHY
        network_vlans_or_subinterfaces = get_network_vlans(payload.cid, attempt_onboarding, payload.path_instid, type2)

    # this will be placed here when /pathChanAvailability? logic is updated in granite
    granite_vlans_or_subinterfaces = get_granite_vlans(transports, primary_vlan, type2)

    # this will be placed here when /pathChanAvailability? logic is updated in granite
    # granite_vlans_or_subinterfaces = get_granite_vlans(transports, primary_vlan)

    # Feed in MDSO data to determine lowest VLAN
    return get_next_available_vlan_or_subinterface(
        network_vlans_or_subinterfaces, granite_vlans_or_subinterfaces, payload.product_name, primary_vlan, type2
    )


def get_outer_vlan(payload: Type2OuterVLANRequestPayloadModel, transports, attempt_onboarding, type2):
    """Get the lowest vlan."""
    outer_vlan = True
    # Type 2 vlan will always be unique on a new subinterface
    primary_vlan = ""
    # for a Type 2 design order, please include the VLANs on the exclusion list
    exclusion_list = [str(vlan) for vlan in payload.exclusion_list]
    granite_outer_vlans = set(exclusion_list)

    # Get network vlans
    network_outer_vlans = get_network_outer_vlans(payload.nni, attempt_onboarding, type2)

    # this will be placed here when /pathChanAvailability? logic is updated in granite
    granite_outer_vlans.update(get_granite_vlans(transports, primary_vlan, type2, outer_vlan))

    # Feed in MDSO data to determine lowest VLAN
    return get_next_available_vlan_or_subinterface(
        network_outer_vlans, granite_outer_vlans, payload.product_name, primary_vlan, type2, outer_vlan
    )


def vlan_reservation_main(payload: VLANReservationPayloadModel, attempt_onboarding=False):
    # Fallout if both vlan_requested and primary_vlan are provided
    if payload.vlan_requested and payload.primary_vlan:
        msg = "Both vlan_requested and primary_vlan detected. Aborting."
        logger.error(msg)
        abort(500, msg)

    if payload.vlan_requested and payload.vlan_requested.isdigit():
        payload.primary_vlan = payload.vlan_requested

    # GET calls to Granite pathElements API
    transports = get_circuit_data(payload.cid, payload.path_instid)

    type2 = False

    # For Type 2
    if payload.service_provider_vlan:
        type2 = True

    assigned_vlan_or_subinterface = get_assigned_vlan_or_subinterface(payload, transports, attempt_onboarding, type2)

    logger.info(f"VLAN or subinterface: {assigned_vlan_or_subinterface}")

    assign_vlans(assigned_vlan_or_subinterface, transports, payload, type2)


def type_2_outer_vlan_request(payload: Type2OuterVLANRequestPayloadModel, attempt_onboarding=False):
    type2 = True
    # payload checks
    if not payload.nni:
        msg = f"Unsupported NNI: {payload.nni}"
        logger.error(msg)
        abort(500, msg)
    # get circuit data on NNI
    get_url = get_l1_url(payload.nni)
    circuit_info_data = get_granite(get_url)
    if "retString" in circuit_info_data:
        msg = f"No record found in Granite for {payload.nni}"
        logger.error(f"{msg}\nURL: {get_url} \nResponse: \n{circuit_info_data}")
        abort(500, message=msg, url=get_url, response=circuit_info_data)
    # get representative transport path for NNI
    if len(circuit_info_data) > 0:
        transports = [circuit_info_data[0]]
    # get next available outer VLAN
    next_outer_vlan = get_outer_vlan(payload, transports, attempt_onboarding, type2)
    return {"vlan": next_outer_vlan}
