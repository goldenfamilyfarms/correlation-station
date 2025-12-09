import logging
from common_sense.common.errors import (
    abort,
    error_formatter,
    get_standard_error_summary,
    GRANITE,
    MISSING_DATA,
    MDSO,
    AUTOMATION_UNSUPPORTED,
)
from palantir_app.bll.mdso import get_active_resource
from palantir_app.bll.compliance_provisioning_housekeeping import set_to_live
from palantir_app.common.compliance_utils import ComplianceStages, NetworkCompliance, validate_network_data_exists
from palantir_app.common.constants import (
    COMPLIANT,
    NETWORK_COMPLIANCE_STAGE,
    DESIGN_COMPLIANCE_STAGE,
    GRANITE_STATUS_LIVE,
    NEW_ORDER_TYPE,
    ADD_ORDER_TYPE,
    WIA_MODEL_TO_MEDIA_TYPE_MAP,
)
from palantir_app.dll import granite
from palantir_app.dll.mdso import mdso_post, product_query, mdso_get

logger = logging.getLogger(__name__)


class Initialize(NetworkCompliance):
    def __init__(self, cid, request, order_type):
        super().__init__(cid, request, order_type)
        self.product_name = request.get("product_name")
        self.service_data = request.get("service_data")
        self.order_type = order_type
        self.set_granite_device_info()
        self.set_wia_constants()
        self.set_service_data_codes()
        self.set_salesforce_device_info()

    def set_granite_device_info(self):
        total_device_info = granite.get_devices_from_cid(self.cid)
        for device in total_device_info:
            routers_on_circuit = [
                device for device in total_device_info if device.get("ELEMENT_CATEGORY").upper() == "ROUTER"
            ]
            if not routers_on_circuit:
                msg = error_formatter(GRANITE, MISSING_DATA, "No routers found", detail=f"WIA Circuit: {self.cid}")
                abort(502, msg, summary=get_standard_error_summary(msg))
            if device.get("ELEMENT_CATEGORY").upper() == "ROUTER":
                self.tid = device.get("TID")
                self.granite_device_model = device.get("MODEL")
                self.bandwidth = device.get("BANDWIDTH")
                self.equipment_id = device.get("ELEMENT_REFERENCE")
                self.transport_media_type = granite.get_transport_media_type_by_equipment_id(self.equipment_id)
                break

    def set_wia_constants(self):
        """Goes to MDSO to retrieve the WIA Constants resource containing the necessary service codes"""
        endpoint = "/bpocore/market/api/v1/resources?resourceTypeId=charter.resourceTypes.WIAConstants"
        self.wia_constants = mdso_get(endpoint=endpoint)["items"][0]["properties"]

    def set_service_data_codes(self):
        """Goes through the data sent by EXPO to check for the necessary service codes
        RW600 - RW604 : Bandwidth codes
        RW700, RW702 : Device codes
        RW510 - RW 550 : Legacy codes

        Logic:
        - If Active Service Code is found, Device Service Code is required
        - If Legacy Service Code is found, Device Service Code is NOT required
        """
        self.active_service_code = None
        self.device_service_code = None
        self.legacy_service_code = None

        supported_rate_plan_service_codes = ["RW600", "RW601", "RW602", "RW603", "RW604"]
        supported_device_service_codes = ["RW700", "RW702"]
        supported_legacy_service_codes = ["RW510", "RW520", "RW530", "RW540", "RW550"]

        for data in self.service_data:
            service_code = data.get("serviceCode")
            if service_code in supported_rate_plan_service_codes:
                self.active_service_code = service_code
            elif service_code in supported_device_service_codes:
                self.device_service_code = service_code
            elif service_code in supported_legacy_service_codes:
                self.legacy_service_code = service_code

        if not self.active_service_code and not self.legacy_service_code:
            abort(400, "The payload data did not contain an active service code or legacy service code")
        if self.active_service_code and not self.device_service_code:
            abort(400, "The payload data did not contain a supported device code")
        if self.device_service_code and self.legacy_service_code:
            abort(400, "The payload data contains both a device service code and a legacy service code")

        logger.info(f"Service code: {self.active_service_code}")
        logger.info(f"Device code: {self.device_service_code}")
        logger.info(f"Legacy service code: {self.legacy_service_code}")

    def set_salesforce_device_info(self):
        """Goes through WIA Constants using the service code from EXPO to find the matching"""
        supported_device_code_data = self.wia_constants.get("supported_device_service_codes").get(
            self.device_service_code
        )
        active_service_code_data = self.wia_constants.get("active_service_codes").get(self.active_service_code)
        legacy_service_code_data = self.wia_constants.get("legacy_service_codes").get(self.legacy_service_code)
        if not supported_device_code_data and not (active_service_code_data or legacy_service_code_data):
            abort(502, f"Unable to retrieve data for service code {self.device_service_code}")
        if supported_device_code_data and active_service_code_data:
            self.salesforce_device_model = supported_device_code_data.get("desc")[0].split(" ")[1]
            self.rate_plan = active_service_code_data.get("desc")[0]
        elif legacy_service_code_data:
            self.salesforce_device_model = legacy_service_code_data.get("desc")[0].split(" ")[0]
            self.rate_plan = legacy_service_code_data.get("desc")[0]

    def create_wia_mapper(self):
        if self.product_name.upper() not in [
            "WIA PRIMARY",
            "WIRELESS INTERNET ACCESS",
            "WIRELESS INTERNET ACCESS-PRIMARY",
            "WIRELESS INTERNET ACCESS-PRIMARY-OUT OF FOOTPRINT",
            "WIRELESS INTERNET ACCESS - OFF-NET",
            "WIRELESS INTERNET ACCESS - OFF NET",
        ]:
            msg = error_formatter(MDSO, AUTOMATION_UNSUPPORTED, "Unexpected Product Name", self.product_name)
            abort(500, msg, summary=get_standard_error_summary(msg))
        payload = self._create_payload()
        resource = mdso_post("/bpocore/market/api/v1/resources?validate=false&obfuscate=true", payload)
        return {"resource_id": resource["id"]}

    def _create_payload(self):
        gathered_payload_info = {
            "productId": product_query("WIAMapper"),
            "label": self.cid,
            "properties": {
                "device_properties": {
                    "rate_plan": self.rate_plan,
                    "service_code": self.active_service_code,
                    "tid": self.tid,
                    "salesforce_device_model": self.salesforce_device_model,
                    "device_model": self.granite_device_model,
                    "equipment_id": self.equipment_id,
                    "bandwidth": self.bandwidth,
                    "transport_media_type": self.transport_media_type,
                },
                "circuit_id": self.cid,
            },
        }

        return gathered_payload_info


def is_valid_request(order_type):
    return NEW_ORDER_TYPE or ADD_ORDER_TYPE in order_type.upper()


def check_compliance_wia(compliance_status, resource_id):
    logger.info("Beginning data compliance evaluation")
    stl_additional_attributes = {}
    mdso_resource = get_active_resource(resource_id)
    validate_network_data_exists(compliance_status, resource_id=resource_id, network_data=mdso_resource)
    service_differences = mdso_resource["properties"].get("service_differences")
    failure_status = mdso_resource["properties"].get("failure_status")
    if service_differences or failure_status:
        _abort_with_compliance_issue(compliance_status, service_differences, failure_status)
    design_data = mdso_resource.get("properties").get("device_properties")
    stl_additional_attributes["serial_number"] = design_data.get("serial_number")
    stl_additional_attributes["tid"] = design_data.get("tid")
    cid = mdso_resource["properties"]["circuit_id"]
    path_data = granite.get_path_details_by_cid(cid)
    design_data["service_media_type"] = path_data[0].get("serviceMedia")
    check_design_data(design_data, compliance_status)
    if path_data[0].get("status").upper() != GRANITE_STATUS_LIVE:
        set_to_live(
            cid,
            NEW_ORDER_TYPE,
            compliance_status,
            product_name=None,
            path_data=path_data,
            additional_attributes=stl_additional_attributes,
        )
    logger.info("Data compliance evaluation complete!")
    compliance_status.update({NETWORK_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS})
    compliance_status.update({COMPLIANT: True})


def _abort_with_compliance_issue(compliance_status, differences=None, failure_status=None):
    if differences:
        msg = f"Service differences found- {differences}"
    if failure_status:
        msg = f"Failure status - {failure_status}"
    compliance_status.update({NETWORK_COMPLIANCE_STAGE: msg})
    abort(502, compliance_status)


def check_design_data(design_data, compliance_status):
    error_msg = ""
    if design_data["bandwidth"].upper() != "RF":
        error_msg = f"The given bandwidth is incorrect: {design_data['bandwidth']}"
    if not _confirm_service_media_type(design_data):
        error_msg = f"The service media type is incorrect: {design_data['service_media_type']}"
    if design_data["transport_media_type"] != design_data["service_media_type"]:
        error_msg = f"The transport media type is incorrect: {design_data['transport_media_type']}"
    if design_data["salesforce_device_model"] != design_data["device_model"].split()[0]:
        error_msg = (
            "The device models do not match.  "
            f"SalesForce model: {design_data['salesforce_device_model']}  "
            f"Granite model: {design_data['device_model']}"
        )

    if error_msg:
        compliance_status.update({DESIGN_COMPLIANCE_STAGE: error_msg})
        abort(502, error_msg)

    compliance_status.update({DESIGN_COMPLIANCE_STAGE: ComplianceStages.SUCCESS_STATUS})


def _confirm_service_media_type(design_data):
    """Confirm that the device model has its proper corresponding media type - LTE or 5G"""
    for model in WIA_MODEL_TO_MEDIA_TYPE_MAP:
        if model in design_data["device_model"]:
            if WIA_MODEL_TO_MEDIA_TYPE_MAP[model] == design_data["service_media_type"]:
                return True
    return False
