import logging
from common_sense.common.errors import abort
from arda_app.dll.sense import post_sense, put_sense, get_sense

logger = logging.getLogger(__name__)


class SrvcProdEligibilityTemplate:
    def __init__(self, payload: object):
        self.payload = payload
        self.supported_product_api = "POST /arda/v1/supported_product"

    # Supported service types and product names
    supported_services_1 = ("net_new_cj", "net_new_qc")
    supported_services_2 = ("net_new_cj", "net_new_qc", "net_new_serviceable", "net_new_no_cj")

    supported_products = {
        "FC + Remote PHY": supported_services_2,
        "Fiber Internet Access": supported_services_2,
        "Carrier E-Access (Fiber)": supported_services_2,
        "EP-LAN (Fiber)": supported_services_2,
        "EPL (Fiber)": supported_services_2,
        "Carrier Fiber Internet Access": supported_services_2,
        "Hosted Voice - (Fiber)": supported_services_2,
        "Hosted Voice - (DOCSIS)": supported_services_2,
        "Hosted Voice - (Overlay)": supported_services_2,
        "PRI Trunk (Fiber)": supported_services_2,
        "PRI Trunk(Fiber) Analog": supported_services_2,
        "PRI Trunk (DOCSIS)": supported_services_2,
        "SIP - Trunk (Fiber)": supported_services_2,
        "SIP Trunk(Fiber) Analog": supported_services_2,
        "SIP - Trunk (DOCSIS)": supported_services_2,
        "Wireless Internet Access-Primary": supported_services_2,
        "Wireless Internet Access-Primary-Out of Footprint": supported_services_2,
        "Wireless Internet Access-Backup": supported_services_2,
        "Wireless Internet Access": supported_services_2,
        "Wireless Internet Access - Off-Net": supported_services_2,
        "Wireless Internet Backup": supported_services_2,
    }

    def get_payload_for_each_side(self):
        payload_list = []
        if "a_side_info" in self.payload.keys():
            payload_list.append(("a_side_info", self.payload.get("a_side_info")))
        if "z_side_info" in self.payload.keys():
            payload_list.append(("z_side_info", self.payload.get("z_side_info")))
        return payload_list

    def check_service_and_product_eligibility(self):
        payload_list = self.get_payload_for_each_side()
        logger.debug(
            f"SrvcProdEligibilityTemplate.check_service_and_product_eligibility - Payload list - {payload_list}"
        )
        for payload in payload_list:
            if not payload[1]:
                continue
            if all(
                (
                    payload[0] == "a_side_info",
                    payload[1].get("service_type") == "net_new_no_cj",
                    payload[1].get("product_name") == "Carrier E-Access (Fiber)",
                )
            ):
                payload[1]["service_type"] = "net_new_cj"

            supported_services = self.supported_products.get(payload[1].get("product_name"))
            if not supported_services:
                abort(
                    500,
                    f"SrvcProdEligibilityTemplate.check_service_and_product_eligibility - "
                    f"Product '{payload[1].get('product_name')}' in {payload[0]} is unsupported",
                )

            if payload[1].get("service_type") not in supported_services:
                abort(
                    500,
                    f"SrvcProdEligibilityTemplate.check_service_and_product_eligibility - "
                    f"Service '{payload[1].get('service_type')}' in {payload[0]} is unsupported",
                )

    def call_supported_product_endpoint(self):
        http, url = self.supported_product_api.split(" ")
        if http == "GET":
            resp = get_sense(url, self.payload, 300, False)
        elif http == "POST":
            resp = post_sense(url, self.payload, 300, False)
        else:
            resp = put_sense(url, self.payload, 300, False)
        return resp
