import logging

from fuzzywuzzy import fuzz

from common_sense.common.errors import abort
from palantir_app.common.compliance_utils import ComplianceStages
from palantir_app.common.constants import ISP_INFO, ISP_STAGE
from palantir_app.dll.sense import post_sense

logger = logging.getLogger(__name__)


def create_remedy_disconnect_ticket(
    cid: str, endpoint_data: dict, design_data: dict, site_order_data: dict, compliance_status: dict
):
    compliance_status.update({ISP_INFO: []})
    validated_full_sites = correlate_eng_page_to_full_disco_address(endpoint_data, site_order_data, compliance_status)
    isp_required_sites = endpoint_data["isp_required_sites"]
    for site in isp_required_sites:
        engineering_page = get_engineering_page(site, site_order_data, validated_full_sites)
        payload = create_remedy_payload(
            site, cid, isp_required_sites, engineering_page, design_data, endpoint_data, validated_full_sites
        )
        logger.debug(f"Payload for Arda Remedy Ticket: {payload}")
        remedy_response = post_sense("arda/v2/remedy_ticket/disconnect_ticket", payload=payload)
        if remedy_response.status_code == 201:
            remedy_ticket = remedy_response.json()["work_order"]
        else:
            msg = f"Error creating Remedy Disconnect Ticket: {remedy_response.text}"
            compliance_status.update({ISP_STAGE: msg})
            abort(502, compliance_status)
        compliance_status[ISP_INFO].append(
            {
                "ispDisconnectTicket": remedy_ticket,
                "site": isp_required_sites[site]["address"],
                "engineeringPage": engineering_page,
            }
        )

    compliance_status.update({ISP_STAGE: ComplianceStages.SUCCESS_STATUS})


def correlate_eng_page_to_full_disco_address(endpoint_data, site_order_data, compliance_status):
    full_site_order_data = []
    z_type = endpoint_data["z_side_disconnect"]
    z_side_data = None
    both_sides_data = None
    if z_type == "FULL":
        z_side_data = create_full_site_order_data(compliance_status, endpoint_data, site_order_data, side="z")
    if endpoint_data.get("a_side_disconnect"):
        a_type = endpoint_data["a_side_disconnect"]
        if a_type == "FULL":
            both_sides_data = create_full_site_order_data(
                compliance_status, endpoint_data, site_order_data, side="a", full_data=z_side_data
            )
    if both_sides_data:
        full_site_order_data.append(both_sides_data)
    elif z_side_data:
        full_site_order_data.append(z_side_data)
    return full_site_order_data


def create_full_site_order_data(compliance_status, endpoint_data, site_order_data, side, full_data=None):
    if full_data is None:
        full_data = {}
    full_data[side] = {}
    granite_address = endpoint_data[f"{side}_side_address"]
    full_data[side]["address"] = granite_address
    for order in site_order_data:
        confidence_address = fuzz.partial_ratio(granite_address, order["service_location_address"])
        if confidence_address >= 80:
            full_data[side]["engineering_page"] = order["engineering_page"]
            break
    if not full_data[side].get("engineering_page"):
        msg = f"Unable to correlate full disconnect address. Designed record: {granite_address},\
order requested {site_order_data}"
        compliance_status.update({ISP_STAGE: msg})
        abort(502, compliance_status)
    return full_data


def create_remedy_payload(
    site, cid, isp_required_sites, engineering_page, design_data, endpoint_data, validated_full_sites=None
):
    address = get_full_disco_address(site, isp_required_sites, validated_full_sites)
    return {
        "circuit_id": cid,
        "address": address,
        "customer_name": design_data[site]["element_data"]["customer_name"],
        "hub_clli": design_data[site]["element_data"]["hub_clli"],
        "equipment_id": design_data[site]["element_data"]["upstream_device"],
        "port_access_id": design_data[site]["element_data"]["port_access_id"],
        "order_number": engineering_page,
        "notes": create_notes(cid, design_data[site]["element_data"], address),
        "summary": f"{design_data[site]['transport_data'][0]['aSideSiteName']} :: Single-Customer Disconnect",
        "additional_details": None,
        "wavelength": endpoint_data.get(f"{site}_side_target_wavelength"),
    }


def get_engineering_page(site, site_order_data, validated_full_sites=None):
    if validated_full_sites:
        for validated in validated_full_sites:
            if validated.get(site):
                return validated[site]["engineering_page"]
    # 1 sided orders do not require validation
    return site_order_data[0]["engineering_page"]


def get_full_disco_address(site, isp_required_sites, validated_full_sites):
    if validated_full_sites:
        for validated in validated_full_sites:
            if validated.get(site):
                return validated[site]["address"]
    # 1 sided orders do not require validation
    return isp_required_sites[site]["address"]


def create_notes(cid, element_data, address):
    customer_name = element_data["customer_name"]
    upstream_handoff = element_data["upstream_handoff"]
    return f"{customer_name} :: {address} :: Single-Customer Disconnect :: {cid} :: {upstream_handoff}"
