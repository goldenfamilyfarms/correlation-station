import logging

from arda_app.common.srvc_prod_eligibility_template import SrvcProdEligibilityTemplate
from arda_app.common.supported_prod_template import SupportedProdTemplate
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


supported_products = (
    "Carrier E-Access (Fiber)",
    "Carrier Fiber Internet Access",
    "EP-LAN (Fiber)",
    "FC + Remote PHY",
    "EPL (Fiber)",
    "Fiber Internet Access",
    "Hosted Voice - (Fiber)",
    "Hosted Voice - (DOCSIS)",
    "Hosted Voice - (Overlay)",
    "PRI Trunk (Fiber)",
    "PRI Trunk(Fiber) Analog",
    "SIP - Trunk (Fiber)",
    "SIP Trunk(Fiber) Analog",
    "Wireless Internet Access-Primary",
    "Wireless Internet Access-Primary-Out of Footprint",
    "Wireless Internet Access",
    "Wireless Internet Access - Off-Net",
)


class BuildCircuitDesignTemplate:
    def __init__(self, payload: object):
        self.payload = payload

    def check_service_product_eligibility(self):
        order = SrvcProdEligibilityTemplate(self.payload)
        order.check_service_and_product_eligibility()

    def run_supported_product(self):
        order = SupportedProdTemplate(self.payload)
        return order.product_uniqueness_identifier()


def build_circuit_design_main(payload):
    for side in payload:
        if not payload.get(side):
            continue

        product_name = payload[side].get("product_name")

        if product_name not in supported_products:
            abort(500, f"Unsupported product :: {product_name}")
        elif payload[side].get("third_party_provided_circuit") == "Y":
            if product_name == "Fiber Internet Access":
                payload[side]["build_type"] = "type2_hub"
            elif "Wireless Internet Access" not in product_name:
                abort(500, "3rd_party_provided_circuit is unsupported.")
        elif (
            payload[side].get("retain_ip_addresses", "") and payload[side]["retain_ip_addresses"].lower() == "yes"
        ):  # remove this elif clause to support retain IP addresses functionality
            abort(500, "Unsupported product :: Retain IPs Yes")

        # abort early if network platform is not supported for SIP products
        if payload[side].get("network_platform") != "Apollo" and product_name in {
            "SIP - Trunk (Fiber)",
            "SIP Trunk(Fiber) Analog",
        }:
            abort(500, f"network platform, {payload[side]['network_platform']}, not supported for SIP products")

        if product_name == "Carrier Fiber Internet Access":
            product_name = "Fiber Internet Access"

        if product_name == "Carrier E-Access (Fiber)":
            # static assign the service type if build type and pid exist
            if payload[side].get("build_type") and not payload[side].get("service_type") and payload[side].get("pid"):
                payload[side]["service_type"] = "net_new_cj"

            if not payload[side].get("service_type"):
                abort(500, "service type missing, CEA requires build type and prism id to exist")

        # force customers_elan_name to be "Null" is it is missing from payload
        if "EP-LAN" in product_name:
            if not payload[side].get("customers_elan_name"):
                payload[side]["customers_elan_name"] = "Null"

        if "Wireless Internet Access" in product_name:
            payload[side]["service_type"] = "net_new_cj"
            payload[side]["build_type"] = "Home Run"

        if payload[side].get("service_type", "no_service_type") in (
            "net_new_qc",
            "net_new_serviceable",
            "net_new_no_cj",
        ):
            # Default build type to Null for net_new_qc, net_new_serviceable, net_new_no_cj
            build_type = payload[side].get("build_type", "Null")  # create and set build_type, if missing

            if payload[side].get("build_type") not in (
                "Null",
                "type2_hub",
            ):  # force build_type to be "Null" if not type2
                build_type = "Null"

            payload[side]["build_type"] = build_type

        if product_name == "Hosted Voice - (Fiber)":
            # hard coding static values for each product name
            payload[side]["connector_type"] = "RJ45"
            payload[side]["uni_type"] = "Trunked"

        if payload[side].get("product_name") == "FC + Remote PHY":
            payload[side]["connector_type"] = "LC"
            payload[side]["uni_type"] = "Access"

        if "SIP" in payload[side].get("product_name") or "PRI" in payload[side].get("product_name"):
            payload[side]["uni_type"] = "Access"

    # Call SEnSE service_product_eligibility endpoint
    bcd = BuildCircuitDesignTemplate(payload)
    bcd.check_service_product_eligibility()
    return bcd.run_supported_product()
