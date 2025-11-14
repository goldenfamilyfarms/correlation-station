import logging
import re

from common_sense.common.errors import abort
from arda_app.dll.granite import get_granite
from arda_app.dll.mdso import onboard_and_exe_cmd

logger = logging.getLogger(__name__)


def get_port_connection_info(cid, pe_device, port_level):
    """get FQDN for a given circuit ID from Granite"""
    endpoint = (
        f"/pathElements?CIRC_PATH_HUM_ID={cid}&LVL={port_level}"
        f"&ELEMENT_TYPE=PORT&ELEMENT_NAME={pe_device}&wildCardFlag=1"
    )

    try:
        granite_resp = get_granite(endpoint)
        logger.debug(f"PATH ELEMENTS RESPONSE: {granite_resp}")
        path_elements = granite_resp[0]
        missing_fields = {"FQDN", "VENDOR"}.difference(path_elements.keys())

        if len(missing_fields) > 0:
            abort(500, f"Could not get the following keys for circuit id {cid}: {'', ''.join(missing_fields)}")

        fqdn = path_elements.get("FQDN", None)
        vendor = path_elements.get("VENDOR", None)
        hostname = fqdn.split(".")[0]
        logger.debug(f"FQDN: {fqdn}, VENDOR: {vendor}, HOSTNAME: {hostname}")

        return hostname, vendor
    except (IndexError, KeyError):
        abort(404, f"No ports found on Path Elements call to Granite for circuit id: {cid} and pe_device: {pe_device}")


def get_port_from_mdso_juniper(hostname, pe_port_number):
    try:
        mdso_response = onboard_and_exe_cmd(hostname, "show_chassis", pe_port_number, attempt_onboarding=True)
        pic_detail = mdso_response["result"]["fpc-information"]["fpc"]["pic-detail"]
        ports = pic_detail["port-information"]["port"]
    except (KeyError, IndexError):
        # Optic check failed - No Optic Slotted
        return

    return ports


def get_port_from_mdso_cisco(hostname, pe_port_number):
    # CISCO devices not supported yet
    msg = "CISCO devices are currently unsupported"
    logger.error(msg)
    abort(500, msg)


def check_optic(pe_port_number, ports_info, source=None):
    # check that optic is slotted
    port_number = pe_port_number.split("/")[2]

    for optic in ports_info:
        if optic["port-number"] == port_number:
            logger.debug(f"PORT INFO FROM MDSO: {optic}")
            return optic
    if source == "light_test":
        abort(500, f"Optic not slotted for port {pe_port_number}")


def set_interface_bw(port_speed):
    port_bw = port_speed.split(" ")[0]

    if port_bw == "10GBASE":
        interface_bw = 10000
    elif port_bw == "GIGE":
        interface_bw = 1000
    else:
        logger.error("Unable to determine interface bandwidth for port")
        abort(500, f"Unable to determine interface bandwidth for {port_speed}")

    return interface_bw


def wavelength_check(remedy_fields):
    wavelength_change = False
    wavelength_match = True
    acceptable_change = True

    formatted_construction = re.sub(r"\s+", "", remedy_fields.get("construction_complete").lower(), flags=re.UNICODE)

    if formatted_construction == "yes":
        construction_complete = True
    elif formatted_construction == "no":
        construction_complete = False
    else:
        abort(
            500,
            "construction_complete must be either 'yes' or 'no'; value entered: "
            f"{remedy_fields.get('construction_complete')}",
        )
    # format ISP actual_wavelength that is sent back from the ISP ticket
    actual_wavelength = remedy_fields.get("actual_wavelength_used", "")
    if actual_wavelength:
        actual_wavelength = actual_wavelength.replace("nm", "")
        if "/" in actual_wavelength:
            actual_wavelength = actual_wavelength.split("/")[0]
        actual_wavelength = actual_wavelength[:7]
        if actual_wavelength.endswith("0") and "." in actual_wavelength:
            actual_wavelength = actual_wavelength.split("0")[0]

    target_wavelength = remedy_fields.get("target_wavelength")
    if "/" in target_wavelength:
        target_wavelength = target_wavelength.split("/")[0]

    if not actual_wavelength:
        actual_wavelength = target_wavelength

    if target_wavelength != actual_wavelength:
        wavelength_change = True

    if wavelength_change and construction_complete:
        acceptable_change = False

    return actual_wavelength, wavelength_match, acceptable_change, wavelength_change


def get_wavelengths(portSFPwavelength, wavelength):
    palantir_wavelength = ""

    if portSFPwavelength.endswith("nm"):
        palantir_wavelength = portSFPwavelength[:-3]

    if wavelength.endswith("nm"):
        wavelength = wavelength[:-2]

    return palantir_wavelength, wavelength


def format_wavelength(port, formatted_wavelength):
    if "." in formatted_wavelength:
        formatted_wavelength = formatted_wavelength.replace("nm", "")
    elif "." not in formatted_wavelength and "nm" not in formatted_wavelength:
        formatted_wavelength = formatted_wavelength + " nm"

    mdso_port_info = f"""Cable Type: {port["cable-type"]}
    Fiber Type: {port["fiber-mode"]}
    Vendor: {port["sfp-vendor-name"]}
    Model: {port["sfp-vendor-pno"]}
    Wavelength: {formatted_wavelength}"""

    return mdso_port_info


def opticwave_scenarios(opticwave, scenario):
    optic_size_match = opticwave["optic_size_match"]
    wavelength_change = opticwave["wavelength_change"]
    wavelength_match = opticwave["wavelength_match"]
    construction_complete = opticwave["construction_complete"]
    acceptable_change = opticwave["acceptable_change"]
    new_wavelength = opticwave["actual_wavelength"]
    wavelength = opticwave["target_wavelength"]
    mdso_port_info = opticwave["mdso_port_info"]
    port_activation_link = opticwave["pat_link"]

    if scenario == "1":
        # Optic check passed
        # optic slotted, optic size matches, and no wavelength change
        return {
            "scenario": scenario,
            "optic_slotted": True,
            "optic_size_match": optic_size_match,
            "wavelength_change": wavelength_change,
            "wavelength_match": wavelength_match,
            "construction_complete": construction_complete,
            "circuit_design_notes": f"scenario: {scenario} - Optic check passed\n"
            "Wavelength Match and Optic Size Match. 1Remedy Successfully Completed.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "optic_validation_notes": f"scenario: {scenario} - Optic check passed\n"
            "Wavelength Match and Optic Size Match. 1Remedy Successfully Completed.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "port_activation_link": port_activation_link,
            "optic_check": "pass",
        }
    elif scenario == "2":
        # Optic check passed
        # optic slotted, optic size matches, wavelength change, and construction not complete
        return {
            "scenario": scenario,
            "optic_slotted": True,
            "optic_size_match": optic_size_match,
            "wavelength_change": wavelength_change,
            "wavelength_match": wavelength_match,
            "construction_complete": construction_complete,
            "acceptable_change": acceptable_change,
            "new_wavelength": new_wavelength,
            "circuit_design_notes": f"scenario: {scenario} - Optic check passed\n"
            f"Wavelength changed from {wavelength} to {new_wavelength}.\n"
            "Optic slotted, optic size matches, isp wavelength change, and construction not complete.\n"
            "PRISM updated. Emailed construction and SDM about the change.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "optic_validation_notes": f"scenario: {scenario} - Optic check passed\n"
            f"Wavelength changed from {wavelength} to {new_wavelength}.\n"
            "Optic slotted, optic size matches, isp wavelength change, and construction not complete.\n"
            "PRISM updated. Emailed construction and SDM about the change.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "port_activation_link": port_activation_link,
            "email_recipients": f"{opticwave['email']},{opticwave['prism_construction_coord_email']}",
            "email_bcc": "DL-SENOE-SEEFA-CD-Wave-Change@charter.com",
            "email_subject": f"PID{opticwave['prism_id']} - {opticwave['work_order_id']} - "
            f"{opticwave['order_number']} - Wavelength Change",
            "email_body": f"ISP has changed the Wavelength from {wavelength} to "
            f"{new_wavelength} in the Hub. Prism has been updated to reflect the latest "
            "change. Please update the team that is responsible for building this project.",
            "email_from": "DL-SEE&O-ECD-Prism-Design-Update@charter.com",
            "optic_check": "pass",
        }
    if scenario == "3":
        # Optic check failed
        # optic slotted and optic size does not match
        slotted_optic_int = int(opticwave["interface_bandwidth"]) / 1000
        slotted_optic = str(int(slotted_optic_int)) + "G"

        return {
            "scenario": scenario,
            "optic_slotted": True,
            "optic_size_match": optic_size_match,
            "wavelength_change": wavelength_change,
            "wavelength_match": wavelength_match,
            "construction_complete": construction_complete,
            "acceptable_change": acceptable_change,
            "new_wavelength": new_wavelength,
            "circuit_design_notes": f"scenario: {scenario} - Optic check failed\n"
            f"Slotted {slotted_optic} Optic does not match requested ISP "
            "Please verify optic size and engage ISP if necessary.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "optic_validation_notes": f"scenario: {scenario} - Optic check failed\n"
            f"Slotted {slotted_optic} Optic does not match requested ISP "
            "Please verify optic size and engage ISP if necessary.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "port_activation_link": port_activation_link,
            "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            "optic_check": "failed",
        }
    elif scenario == "4":
        # Optic check failed
        # optic slotted, optic size matches, and wavelength does not match
        return {
            "scenario": scenario,
            "optic_slotted": True,
            "optic_size_match": optic_size_match,
            "wavelength_change": wavelength_change,
            "wavelength_match": wavelength_match,
            "construction_complete": construction_complete,
            "acceptable_change": acceptable_change,
            "new_wavelength": new_wavelength,
            "circuit_design_notes": f"scenario: {scenario} - Optic check failed\n"
            f"Requested wavelength {opticwave['actual_wavelength']} "
            "does not match ISP slotted wave. Please verify and engage ISP if necessary.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "optic_validation_notes": f"scenario: {scenario} - Optic check failed\n"
            f"Requested wavelength {opticwave['actual_wavelength']} "
            "does not match ISP slotted wave. Please verify and engage ISP if necessary.\n",
            f"{mdso_port_info}\nport_activation_link": port_activation_link,
            "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            "optic_check": "failed",
        }
    elif scenario == "5":
        # Optic check failed
        # optic slotted, optic size matches, wavelength change, and construction complete
        return {
            "scenario": scenario,
            "optic_slotted": True,
            "optic_size_match": optic_size_match,
            "wavelength_change": wavelength_change,
            "wavelength_match": wavelength_match,
            "construction_complete": construction_complete,
            "acceptable_change": acceptable_change,
            "circuit_design_notes": f"scenario: {scenario} - Optic check failed\n"
            f"The requested Wavelength {opticwave['actual_wavelength']} was changed by ISP, "
            "but construction is complete.\n"
            "ISP cannot change the Wavelength once the construction job is complete.\n "
            "Please investigate and engage ISP if necessary.\n"
            f"{mdso_port_info}\n",
            "optic_validation_notes": f"scenario: {scenario} - Optic check failed\n"
            f"The requested Wavelength {opticwave['actual_wavelength']} was changed by ISP, "
            "but construction is complete.\n"
            "ISP cannot change the Wavelength once the construction job is complete.\n "
            "Please investigate and engage ISP if necessary.\n"
            f"{mdso_port_info}\n"
            f"{port_activation_link}\n",
            "port_activation_link": port_activation_link,
            "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            "optic_check": "failed",
        }
    elif scenario == "6":
        # Optic check failed
        # optic not slotted, wavelength change, and construction complete
        return {
            "scenario": scenario,
            "optic_slotted": False,
            "optic_size_match": "Unknown",
            "wavelength_change": "True",
            "wavelength_match": "Unknown",
            "construction_complete": "True",
            "acceptable_change": "Unknown",
            "new_wavelength": opticwave["actual_wavelength"],
            "circuit_design_notes": f"scenario: {scenario} - Optic check failed\n"
            "It was undetermined if the optic has been slotted for "
            f"{opticwave['pe_device']} / {opticwave['pe_port_number']}.\n"
            "Optic not slotted, isp wavelength change, and construction complete.\n"
            f"Please investigate and update the EPR per process - port_activation_link: {port_activation_link}",
            "optic_validation_notes": f"scenario: {scenario} - Optic check failed\n"
            "It was undetermined if the optic has been slotted for "
            f"{opticwave['pe_device']} / {opticwave['pe_port_number']}, "
            "Optic not slotted, isp wavelength change, and construction complete.\n"
            f"Please investigate and update the EPR per process - port_activation_link: {port_activation_link}",
            "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            "optic_check": "failed",
        }
    elif scenario == "7":
        # Optic check failed
        # optic not slotted, no wavelength change, and construction complete
        return {
            "scenario": scenario,
            "optic_slotted": False,
            "optic_size_match": "Unknown",
            "wavelength_change": wavelength_change,
            "wavelength_match": "Unknown",
            "construction_complete": construction_complete,
            "acceptable_change": "Unknown",
            "new_wavelength": new_wavelength,
            "circuit_design_notes": f"scenario: {scenario} - Optic check failed\n"
            "It was undetermined if the optic has been slotted for "
            f"{opticwave['pe_device']} / {opticwave['pe_port_number']}\n"
            "Optic not slotted, no isp wavelength change, and construction complete.\n"
            f"Please investigate and update the EPR per process - port_activation_link: {port_activation_link}",
            "optic_validation_notes": f"scenario: {scenario} - Optic check failed\n"
            "It was undetermined if the optic has been slotted for "
            f"{opticwave['pe_device']} / {opticwave['pe_port_number']}\n"
            "Optic not slotted, no isp wavelength change, and construction complete.\n"
            f"Please investigate and update the EPR per process - port_activation_link: {port_activation_link}",
            "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            "optic_check": "failed",
        }
    elif scenario == "8":
        # Optic check failed
        # optic not slotted and construction not complete
        return {
            "scenario": scenario,
            "optic_slotted": False,
            "optic_size_match": "Unknown",
            "wavelength_change": wavelength_change,
            "wavelength_match": "Unknown",
            "construction_complete": construction_complete,
            "acceptable_change": "Unknown",
            "new_wavelength": new_wavelength,
            "circuit_design_notes": f"scenario: {scenario} - Optic check failed\n"
            "It was undetermined if the optic has been slotted for "
            f"{opticwave['pe_device']} / {opticwave['pe_port_number']}\n"
            "Optic not slotted and construction not complete.\n"
            f"Please investigate and update the EPR per process - port_activation_link: {port_activation_link}",
            "optic_validation_notes": f"scenario: {scenario} - Optic check failed\n"
            "It was undetermined if the optic has been slotted for "
            f"{opticwave['pe_device']} / {opticwave['pe_port_number']}\n"
            "Optic not slotted and construction not complete.\n"
            f"Please investigate and update the EPR per process - port_activation_link: {port_activation_link}",
            "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            "optic_check": "failed",
        }


def scenario_check(opticwave, optic_slotted=False):
    optic_size_match = opticwave["optic_size_match"]
    wavelength_change = opticwave["wavelength_change"]
    wavelength_match = opticwave["wavelength_match"]

    if opticwave["construction_complete"] == "yes":
        construction_complete = True
    else:
        construction_complete = False

    if optic_slotted:
        if optic_size_match:
            if wavelength_match:
                if wavelength_change:
                    if not construction_complete:
                        scenario = "2"
                    else:
                        scenario = "5"
                elif not wavelength_change:
                    scenario = "1"
            elif not wavelength_match:
                scenario = "4"
        elif not optic_size_match:
            scenario = "3"
    elif not optic_slotted:
        if construction_complete:
            if wavelength_change:
                scenario = "6"
            elif not wavelength_change:
                scenario = "7"
        elif not construction_complete:
            scenario = "8"

    return opticwave_scenarios(opticwave, scenario)


def match_wavelength(actual_wavelength, port):
    wave_match = False

    try:
        actual_wavelength = re.findall(r"\d+\.?\d+", actual_wavelength)[0]
        port_wavelength = port.get("wavelength", None)

        if port_wavelength is None:
            abort("Error parsing wavelength from port info")

        port_wavelength = re.findall(r"\d+\.?\d+", port_wavelength)[0]

        if "." in actual_wavelength:
            aw_split = actual_wavelength.split(".")
            aw_decimal_right = aw_split[1]
            if len(aw_decimal_right) < 2:
                aw_decimal_right = f"{aw_split[1]}0"
                actual_wavelength = f"{aw_split[0]}.{aw_decimal_right}"
            aw_decimal_right = int(aw_decimal_right)
            aw_decimal_left = int(aw_split[0])

            if "." not in port_wavelength:
                sfp_vendor_pno = port.get("sfp-vendor-pno", None)  # TODO check port variable.
                if sfp_vendor_pno is None:
                    abort("Error parsing sfp-vendor-pno from port info")
                port_wave_end = port_wavelength[-2:]

                port_wavelength_left = int(port_wavelength)

                if (
                    port_wavelength in {"1563", "1558", "1554", "1550", "1546", "1542", "1538", "1535", "1531"}
                    and "EXSFP" not in sfp_vendor_pno
                ):
                    if "." in sfp_vendor_pno:
                        split_wave = sfp_vendor_pno.split(f"{port_wave_end}.", 1)[1]
                    else:
                        split_wave = sfp_vendor_pno.split(port_wave_end, 1)[1]

                    wave_decimal = split_wave[:3]
                    wave_decimal = int(re.findall(r"\d+", wave_decimal)[0])
                    port_wavelength = f"{port_wavelength}.{wave_decimal}"

                    """this if statement checks if the port wavelength value matches actual wavelength value
                        within a range of +- 2 on the wave decimal value"""
                    if (
                        port_wavelength_left == aw_decimal_left
                        and wave_decimal - 2 <= aw_decimal_right <= wave_decimal + 2
                    ):
                        wave_match = True
                else:
                    if port_wavelength_left == aw_decimal_left:
                        wave_match = True
                    return wave_match, port_wavelength

        logger.debug(f"ACTUAL WAVE: {actual_wavelength}, PORT WAVE: {port_wavelength}")

        if actual_wavelength == port_wavelength:
            wave_match = True

        return wave_match, port_wavelength
    except Exception:
        abort(500, "Error occured while trying to determine wavelength match")


def match_optic(slotted_bw, requested_optic_format):
    match = False

    try:
        if "SFP+" in requested_optic_format or "XFP" in requested_optic_format:
            requested_bw = 10000
        else:
            requested_bw = 1000

        logger.debug(f"slotted bw: {slotted_bw}, requested bw: {requested_bw}")

        if requested_bw == slotted_bw:
            match = True

        return match
    except Exception:
        abort(500, "Error occured while trying to determine optic size match")
