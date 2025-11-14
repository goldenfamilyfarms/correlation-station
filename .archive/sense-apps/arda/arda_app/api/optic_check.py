import re
import logging

from fastapi import Depends

from arda_app.bll.models.payloads import OpticCheckPayloadModel
from arda_app.bll.optic_check import (
    check_optic,
    format_wavelength,
    get_port_connection_info,
    get_port_from_mdso_cisco,
    get_port_from_mdso_juniper,
    get_wavelengths,
    match_optic,
    match_wavelength,
    set_interface_bw,
    scenario_check,
    wavelength_check,
)
from arda_app.common import url_config
from arda_app.common.http_auth import verify_password
from common_sense.common.errors import abort
from arda_app.api._routers import v1_isp_router

logger = logging.getLogger(__name__)


@v1_isp_router.post("/optic_check_validation", summary="Optic Validation Check")
def optic_check(payload: OpticCheckPayloadModel, authenticated: bool = Depends(verify_password)):
    """Optic Validation Check"""
    try:
        pat_link = ""
        body = payload.model_dump()

        # Ensures that all parameters are met before continuing
        missing = {"remedy_fields", "sales_force_fields", "prism_fields"}.difference(body.keys())

        if len(missing) > 0:
            abort(500, "Required query parameter(s) not specified: {}".format(", ".join(missing)))

        # grab remedy fields and check they all exist if not return scenario 10
        remedy_fields = body["remedy_fields"] if body.get("remedy_fields") else {}
        required_fields = (
            "cid",
            "work_order_id",
            "pe_device",
            "pe_port_number",
            "optic_format",
            "target_wavelength",
            "prism_id",
            "completed_date",
            "construction_complete",
        )
        for field in required_fields:
            if not remedy_fields.get(field, None):
                error_payload = {
                    "scenario": "10",
                    "message": (
                        "SOVA Optic Validation and Remedy Work Order monitoring can not begin because "
                        f"the following required information is not provided. remedy_fields - {field}"
                    ),
                    "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
                    "summary": "SENSE | Missing Payload Keys",
                }
                return error_payload

        if not remedy_fields.get("actual_wavelength_used", ""):
            remedy_fields["actual_wavelength_used"] = remedy_fields["target_wavelength"]

        pe_device = remedy_fields.get("pe_device").replace("#", "%23")
        tid = pe_device.split("/")[0]
        cid = remedy_fields["cid"] if remedy_fields.get("cid") else ""
        port_id = remedy_fields.get("pe_port_number")
        prism_id = remedy_fields.get("prism_id")
        requested_optic_format = remedy_fields.get("optic_format", "")
        construction_complete = re.sub(r"\s+", "", remedy_fields.get("construction_complete").lower(), flags=re.UNICODE)

        wavelength = remedy_fields["target_wavelength"]

        # create pat link
        pat_link = f"{url_config.LIGHT_TEST_URL}{tid}/{prism_id}/{port_id}"

        sales_force_fields = body.get("sales_force_fields", "")
        if not (sales_force_fields.get("email") or sales_force_fields.get("prism_construction_coord_email")):
            abort(500, "Payload requires either prism_construction_coord_email or email fields")

        port_level = 2

        if re.match(r"\d{5}\.\w{3,4}\.\w{11}\.\w{11}", cid):
            port_level = 1

        hostname, vendor = get_port_connection_info(cid, pe_device, port_level)

        # Removing %23 from HUB devices
        pe_device = pe_device.split("%")[0]

        # Wavelength comparision check
        (actual_wavelength, wavelength_match, acceptable_change, wavelength_change) = wavelength_check(remedy_fields)

        opticwave = {
            "interface_bandwidth": "unknown",
            "wavelength_change": wavelength_change,
            "wavelength_match": wavelength_match,
            "construction_complete": construction_complete,
            "acceptable_change": acceptable_change,
            "pat_link": "unknown",
            "optic_size_match": "unknown",
            "mdso_port_info": "unknown",
            "actual_wavelength": actual_wavelength,
            "target_wavelength": remedy_fields["target_wavelength"],
            "pe_device": pe_device,
            "pe_port_number": port_id,
            "email": sales_force_fields.get("email"),
            "prism_construction_coord_email": sales_force_fields["prism_construction_coord_email"],
            "prism_id": remedy_fields["prism_id"],
            "work_order_id": remedy_fields["work_order_id"],
            "order_number": remedy_fields["order_number"],
        }

        if vendor == "JUNIPER":
            ports_info = get_port_from_mdso_juniper(hostname, port_id)
        elif vendor == "CISCO":
            return get_port_from_mdso_cisco(hostname, port_id)
        else:
            abort(500, f"Vendor must be either CISCO or JUNIPER. Vendor found for cid in Granite was: {vendor}")

        opticwave["pat_link"] = pat_link

        if not ports_info:
            return {
                "scenario": "9",
                "circuit_design_notes": "scenario: 9 - Optic check failed. Automation was unable to verify the "
                f"optic. \nA manual check of the optic is required. Please investigate. {pat_link}",
                "error_message": f"MDSO failed to pull port info for device {hostname} with port {port_id}",
                "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            }

        port_matched = check_optic(port_id, ports_info)

        # revert actual wavelength to isp input
        # ex: remedy_fields["actual_wavelength_used"]  = "1470/1490"
        # we only used 1470 earlier to check the optic but now have to send back the original
        if "/" in remedy_fields["actual_wavelength_used"] and len(remedy_fields["actual_wavelength_used"]) == 9:
            opticwave["actual_wavelength"] = remedy_fields["actual_wavelength_used"]

        if not port_matched:
            return scenario_check(opticwave)

        pe_device_wavelength = port_matched["wavelength"]
        port_sfp_wavelength = pe_device_wavelength
        opticwave["pat_link"] = f"{url_config.LIGHT_TEST_URL}{hostname}/{prism_id}/{port_id}"
        port_speed = port_matched["cable-type"]

        opticwave["interface_bandwidth"] = set_interface_bw(port_speed)

        # check that optic size matches
        opticwave["optic_size_match"] = match_optic(opticwave["interface_bandwidth"], requested_optic_format)

        # check wavelength
        _, wavelength = get_wavelengths(port_sfp_wavelength, wavelength)
        opticwave["wavelength_match"], formatted_wavelength = match_wavelength(actual_wavelength, port_matched)
        opticwave["mdso_port_info"] = format_wavelength(port_matched, formatted_wavelength)

        return scenario_check(opticwave, optic_slotted=True)
    except Exception as e:
        error_message = {}
        try:
            error_message = e.data
        except Exception as e:
            logger.debug(f"Issue readding error message: {e}")

        # most of the time we will have the patlink unless it errors outbefore we can build it
        if pat_link:
            if "ACR" in pat_link:
                # Ciscos are not supported and will get the call message instead
                pat_link = "Installs contact SAS 7am-7pm C M-F DL-Port-Turn-Up-Request@charter.com 844-896-5784 opt 1, 2"
            error_payload = {
                "scenario": "8",
                "circuit_design_notes": "Optic check failed. Automation was unable to verify the optic.\n"
                f"A manual check of the optic is required. Please investigate. {pat_link}",
                "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
                "port_activation_link": pat_link,
            }

        else:
            error_payload = {
                "scenario": "8",
                "circuit_design_notes": "Optic check failed. Automation was unable to verify the optic.\n"
                "A manual check of the optic is required. Please investigate. \n"
                "The PAT Link was not created becuase it ran into an issue",
                "isp_request_issue_flags": "Automation: Unsupported Scenario - Investigation Required",
            }
        # if there is an additinal error we will pass that back and
        # EXPO will use it to populate the error message field
        # the summary is created on the EXPO side and can be updated at any time
        if error_message:
            error_payload["error_message"] = error_message["message"]

        return error_payload
