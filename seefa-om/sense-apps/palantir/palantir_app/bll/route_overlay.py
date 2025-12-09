import logging

from common_sense.common.errors import abort
from palantir_app.bll.mne_compliance import mne_compliance_stl, run_mne_compliance, send_email
from palantir_app.bll.mne_acceptance import run_mne_acceptance
from palantir_app.bll.rphy_acceptance import run_rphy_acceptance
from palantir_app.bll.rphy_compliance import run_rphy_compliance

logger = logging.getLogger(__name__)


MNE_PRODUCTS = ["Managed Network Edge", "Managed Network Switch", "Managed Network Camera", "Managed Network WiFi"]

RPHY_PRODUCTS = ["Fiber Connect Plus"]


def route_acceptance(payload, product_family):
    cid = payload["cid"]
    eng_id = payload["eng_id"]
    if product_family in MNE_PRODUCTS:
        return run_mne_acceptance(cid, eng_id)
    elif product_family in RPHY_PRODUCTS:
        return run_rphy_acceptance(cid, eng_id)
    else:
        abort(500, f"Product Family {product_family} is not supported by automation for Acceptance")


def route_compliance(payload):
    cid = payload["cid"]
    eng_id = payload["eng_id"]
    product_family = payload["product_family"]
    order_type = payload["order_type"].upper()
    if product_family in MNE_PRODUCTS:
        return run_mne_compliance(cid, eng_id)
    elif product_family in RPHY_PRODUCTS:
        return run_rphy_compliance(cid=cid, order_type=order_type)
    else:
        abort(500, f"Product Family: {product_family} is not supported by automation for Compliance")


def route_compliance_stl(payload):
    product_family = payload["product_family"]
    cid = payload["cid"]
    eng_id = payload["eng_id"]
    if product_family not in MNE_PRODUCTS:
        abort(500, f"Product Family: {payload['product_family']} is not supported by automation for Compliance STL")
    mne_compliance_stl(cid, eng_id)
    email_payload = payload["email_info"]
    customer_name = email_payload.get("customer_name")
    customer_email = email_payload.get("customer_email")
    customer_address = email_payload.get("customer_address")
    customer_poc = email_payload.get("customer_poc")
    account_number = email_payload.get("account_number")
    circuit_id = payload["cid"]
    product_family = payload["product_family"]
    logger.info(f"Overlay Compliance STL Successful, sending email for cid: {payload['cid']}")
    try:
        send_email(
            customer_name, customer_poc, account_number, customer_email, customer_address, circuit_id, product_family
        )
    except Exception as e:
        abort(500, f"Failed to send email: {e}")
    return "MNE Compliance STL Complete. Email sent successfully", 200
