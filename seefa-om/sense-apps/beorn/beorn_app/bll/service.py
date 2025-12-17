import logging

from beorn_app.bll.eligibility import automation_eligibility
from beorn_app.bll.topologies import Topologies
from beorn_app.bll.eligibility.mdso_eligible import (
    UPDATE_TYPES,
    NEW_SERVICE_REQUEST_ORDER_TYPE,
    CHANGE_SERVICE_REQUEST_ORDER_TYPE,
    NEW_ENGINEERING_JOB_TYPE,
    CHANGE_ENGINEERING_JOB_TYPE,
)
from beorn_app.dll.mdso import (
    clean_name_value_filter,
    create_service,
    mdso_get,
    mdso_post,
    product_query,
    service_details,
    service_id_lookup,
)
#from common_sense.common.device import verify_device_connectivity
from common_sense.common.errors import (
    abort,
    format_unsupported_service_error,
    format_unsupported_equipment_error,
    mdso_msg,
    error_formatter,
    get_standard_error_summary,
)
from sense_common.observability import (
from opentelemetry.trace import Status, StatusCode
    traced,
    get_tracer,
    set_mdso_correlation,
    add_span_event,
    set_span_error,
    add_topology_span_attrs,
)
from sense_common.observability.mdso_patterns import ErrorCategorizer
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


# query_criteria is a json dictionary of elements necessary to be included in the info
def _get_resource_type_resource_list(resource_type, query_criteria=None):
    """Call to MDSO for all resource instances of a resource type ...with optional filters"""

    endpoint = "/bpocore/market/api/v1/resources"
    if query_criteria is None:
        query = f"{endpoint}?resourceTypeId={resource_type}&offset=0&limit=1000"
    else:
        criteria = clean_name_value_filter(query_criteria)
        query = f"{endpoint}?resourceTypeId={resource_type}&q={criteria}&offset=0&limit=1000"
    return mdso_get(query)


def _service_update(body):
    """Update a service
    This relies on Granite already having the updated data.
    Provide at least one option (bw, ip, dsc) to update using the body payload."""
    prod_id = product_query("Provisioning")
    resource_id_name = None
    bandwidth_update = body.get("bw", False)
    if bandwidth_update:
        resource_id_name = "bw_resource_id"
    ip_update = body.get("ip", False)
    if ip_update:
        resource_id_name = "ip_resource_id"
    description_update = body.get("dsc", False)
    if description_update:
        resource_id_name = "dsc_resource_id"
    if not resource_id_name:
        abort(400, "Unsupported update request")

    # only one property can be updated at a time
    data = {
        "label": body["cid"],
        "resourceTypeId": "charter.resourceTypes.Provisioning",
        "productId": prod_id,
        "properties": {
            "ip": ip_update,
            "description": description_update,
            "bandwidth": bandwidth_update,
            "serviceStateenable": False,
            "circuit_id": body["cid"],
            "serviceStatedisable": False,
            "operation_type": "UPDATE",
        },
        "desiredOrchState": "active",
    }

    successes = {}
    update_mdso_route = "/bpocore/market/api/v1/resources?validate=false"
    successes[resource_id_name] = mdso_post(update_mdso_route, data)["id"]

    return successes


def is_supported_update_type(body):
    update_fields = ["ip", "dsc", "bw"]
    for update_type in update_fields:
        if body.get(update_type) and update_type not in UPDATE_TYPES:
            return False, update_type
    if not body.get("bw") and not body.get("ip") and not body.get("dsc"):
        return False, "no change request specified"
    return True, "supported"


def filter_out_unsupported_salesforce_order(body, endpoint):
    service_request_order_type = body.get("service_request_order_type")
    engineering_job_type = body.get("engineering_job_type")
    details = f"{service_request_order_type}/{engineering_job_type}"
    msg = error_formatter("MDSO", "Automation Unsupported", "Order/Job Type unsupported", details)
    if endpoint == "new":
        if (
            service_request_order_type not in NEW_SERVICE_REQUEST_ORDER_TYPE
            and engineering_job_type not in NEW_ENGINEERING_JOB_TYPE
        ):
            abort(400, msg, summary=get_standard_error_summary(msg))
    elif endpoint == "update":
        if body.get("maintenance_window") is True:
            msg = "This order requires customer coordination & is ineligible for automation"
            abort(400, msg, summary="MDSO | Automation Unsupported | Maintenance Window Required")
        if (
            service_request_order_type not in CHANGE_SERVICE_REQUEST_ORDER_TYPE
            and engineering_job_type not in CHANGE_ENGINEERING_JOB_TYPE
        ):
            abort(400, msg, summary=get_standard_error_summary(msg))


@traced("beorn.service.create_core", {"operation": "create_core_service"})
def create_core_service(body):
    workstream = "Provisioning"
    cid = body["cid"]
    service_request_order_type = body.get("service_request_order_type")
    engineering_job_type = body.get("engineering_job_type")
    
    with tracer.start_as_current_span("beorn.service.create_core_service") as span:
        set_mdso_correlation(
            circuit_id=cid,
            service_type=service_request_order_type,
            product_id=body.get("product_name"),
        )
        span.set_attribute("service.workstream", workstream)
        span.set_attribute("service.order_type", service_request_order_type or "unknown")
        span.set_attribute("service.engineering_job_type", engineering_job_type or "unknown")
        
        try:
            # create topology and check for mdso eligibility
            add_span_event("service.topology.creation.start", circuit_id=cid)
            topology_data = Topologies(cid)
            topology = topology_data.create_topology()
            add_span_event("service.topology.creation.complete", circuit_id=cid)
            if service_request_order_type and engineering_job_type:
                filter_out_unsupported_salesforce_order(body, endpoint="new")
            
            multi_leg = is_multi_leg(topology)
            span.set_attribute("topology.multi_leg", multi_leg)
            
            add_span_event("service.eligibility.check.start", circuit_id=cid)
            if multi_leg:
                primary_leg = topology_data.primary_leg_elements
                primary_eligibility_data, _ = automation_eligibility.Provisioning(
                    topology["PRIMARY"], primary_leg
                ).check_automation_eligibility()
                secondary_leg = topology_data.secondary_leg_elements
                secondary_eligiblity_data, _ = automation_eligibility.Provisioning(
                    topology["SECONDARY"], secondary_leg
                ).check_automation_eligibility()
                eligibility_data = {
                    "eligible": primary_eligibility_data["eligible"] and secondary_eligiblity_data["eligible"],
                    "data": [primary_eligibility_data["data"], secondary_eligiblity_data["data"]],
                }
                span.set_attribute("eligibility.primary", primary_eligibility_data["eligible"])
                span.set_attribute("eligibility.secondary", secondary_eligiblity_data["eligible"])
                
                if not eligibility_data["eligible"]:
                    data = eligibility_data["data"]
                    span.set_attribute("eligibility.eligible", False)
                    for ineligible_leg in data:
                        if ineligible_leg.get("unsupportedService"):
                            msg = format_unsupported_service_error(ineligible_leg["unsupportedService"], workstream)
                            error_context = error_categorizer.extract_error_context(msg)
                            span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                            abort(502, msg)
                        elif ineligible_leg.get("unsupportedEquipment"):
                            msg = format_unsupported_equipment_error(ineligible_leg["unsupportedEquipment"], workstream)
                            error_context = error_categorizer.extract_error_context(msg)
                            span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                            abort(502, msg)
                    abort(502, mdso_msg(eligibility_data["data"]))
            else:
                circuit_elements = topology_data.circuit_elements
                eligibility_data, _ = automation_eligibility.Provisioning(
                    topology, circuit_elements
                ).check_automation_eligibility()
            
            span.set_attribute("eligibility.eligible", eligibility_data["eligible"])
            if not eligibility_data["eligible"]:
                data = eligibility_data["data"]
                span.set_attribute("eligibility.eligible", False)
                if data.get("unsupportedService"):
                    msg = format_unsupported_service_error(data["unsupportedService"], workstream)
                    error_context = error_categorizer.extract_error_context(msg)
                    span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                    abort(502, msg)
                elif data.get("unsupportedEquipment"):
                    msg = format_unsupported_equipment_error(data["unsupportedEquipment"], workstream)
                    error_context = error_categorizer.extract_error_context(msg)
                    span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                    abort(502, msg)
                abort(502, mdso_msg(eligibility_data["data"]))
            
            add_span_event("service.eligibility.check.passed", circuit_id=cid)

            resource_type = workstream
            # Check circuit for validation only CORE(CW, QW) need to pass
            # verify_device_connectivity(cid=cid, core_only=True)

            add_span_event("service.id.lookup.start", circuit_id=cid)
            service_id = service_id_lookup(cid, resource_type)
            if service_id is not None:
                span.set_attribute("mdso.resource_id", service_id)
                span.set_attribute("service.existing", True)
                add_span_event("service.id.lookup.found", resource_id=service_id, circuit_id=cid)
                return service_id, 200

            add_span_event("service.creation.start", circuit_id=cid)
            product_id = product_query(resource_type)
            data = {
                "label": cid,
                "description": "CID from sense CLI",
                "productId": product_id,
                "properties": {"circuit_id": cid, "operation_type": "CREATE"},
                "autoclean": True,
            }
            resource_id = create_service(data)
            span.set_attribute("mdso.resource_id", resource_id)
            span.set_attribute("service.existing", False)
            add_span_event("service.created", resource_id=resource_id, circuit_id=cid)

            return resource_id, 201
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "UNKNOWN_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise


@traced("beorn.service.update", {"operation": "update_service"})
def update_service(body):
    workstream = "Provisioning Update"
    cid = body.get("cid")
    service_request_order_type = body.get("service_request_order_type")
    engineering_job_type = body.get("engineering_job_type")
    
    with tracer.start_as_current_span("beorn.service.update_service") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("service.workstream", workstream)
        span.set_attribute("service.order_type", service_request_order_type or "unknown")
        span.set_attribute("service.engineering_job_type", engineering_job_type or "unknown")
        span.set_attribute("service.update_types", {
            "bandwidth": body.get("bw", False),
            "ip": body.get("ip", False),
            "description": body.get("dsc", False),
        })
        
        try:
            required_fields = ["cid", "product_name"]
            for f, k in zip(body, required_fields):
                if f in required_fields and not body[f]:
                    abort(400, f"Missing required value for field: {f}")
                if k not in body:
                    abort(400, f"Missing required field: {k}")
            supported_update, msg = is_supported_update_type(body)
            if not supported_update:
                span.set_attribute("error.unsupported_update", msg)
                abort(400, f"Unsupported change requested: {msg}")
            if service_request_order_type and engineering_job_type:
                filter_out_unsupported_salesforce_order(body, endpoint="update")
            # create topology and check for mdso eligibility
            add_span_event("service.update.topology.creation.start", circuit_id=cid)
            topology_data = Topologies(cid)
            topology = topology_data.create_topology()
            circuit_elements = topology_data.circuit_elements
            multi_leg = is_multi_leg(topology)
            span.set_attribute("topology.multi_leg", multi_leg)
            add_span_event("service.update.topology.creation.complete", circuit_id=cid)
            add_span_event("service.update.eligibility.check.start", circuit_id=cid)
            if multi_leg:
                primary_leg = topology_data.primary_leg_elements
                primary_eligibility_data, _ = automation_eligibility.ProvisioningChange(
                    topology["PRIMARY"], primary_leg
                ).check_automation_eligibility()
                secondary_leg = topology_data.secondary_leg_elements
                secondary_eligiblity_data, _ = automation_eligibility.ProvisioningChange(
                    topology["SECONDARY"], secondary_leg
                ).check_automation_eligibility()
                eligibility_data = {
                    "eligible": primary_eligibility_data["eligible"] and secondary_eligiblity_data["eligible"],
                    "data": [primary_eligibility_data["data"], secondary_eligiblity_data["data"]],
                }
                span.set_attribute("eligibility.primary", primary_eligibility_data["eligible"])
                span.set_attribute("eligibility.secondary", secondary_eligiblity_data["eligible"])
                
                if not eligibility_data["eligible"]:
                    data = eligibility_data["data"]
                    span.set_attribute("eligibility.eligible", False)
                    for ineligible_leg in data:
                        if ineligible_leg.get("unsupportedService"):
                            msg = format_unsupported_service_error(ineligible_leg["unsupportedService"], workstream)
                            error_context = error_categorizer.extract_error_context(msg)
                            span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                            abort(502, msg)
                        elif ineligible_leg.get("unsupportedEquipment"):
                            msg = format_unsupported_equipment_error(ineligible_leg["unsupportedEquipment"], workstream)
                            error_context = error_categorizer.extract_error_context(msg)
                            span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                            abort(502, msg)
                    abort(502, mdso_msg([primary_eligibility_data["data"], secondary_eligiblity_data["data"]]))
            else:
                eligibility_data, _ = automation_eligibility.ProvisioningChange(
                    topology, circuit_elements
                ).check_automation_eligibility()
            
            span.set_attribute("eligibility.eligible", eligibility_data["eligible"])
            if not eligibility_data["eligible"]:
                data = eligibility_data["data"]
                span.set_attribute("eligibility.eligible", False)
                if data.get("unsupportedService"):
                    msg = format_unsupported_service_error(data["unsupportedService"], workstream)
                    error_context = error_categorizer.extract_error_context(msg)
                    span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                    abort(502, msg)
                elif data.get("unsupportedEquipment"):
                    msg = format_unsupported_equipment_error(data["unsupportedEquipment"], workstream)
                    error_context = error_categorizer.extract_error_context(msg)
                    span.set_attribute("error.category", error_context.get("category", "ELIGIBILITY_ERROR"))
                    abort(502, msg)
                abort(502, mdso_msg(eligibility_data["data"]))
            
            add_span_event("service.update.eligibility.check.passed", circuit_id=cid)
            # create mdso resource
            add_span_event("service.update.mdso.start", circuit_id=cid)
            result = _service_update(body)
            if "ip_resource_id" in result:
                span.set_attribute("mdso.ip_resource_id", result["ip_resource_id"])
            if "bw_resource_id" in result:
                span.set_attribute("mdso.bw_resource_id", result["bw_resource_id"])
            add_span_event("service.update.complete", circuit_id=cid)
            return result
        except Exception as e:
            set_span_error(e)
            error_context = error_categorizer.extract_error_context(str(e))
            span.set_attribute("error.category", error_context.get("category", "UNKNOWN_ERROR"))
            span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
            raise


@traced("beorn.service.get_info", {"operation": "get_service_info"})
def get_service_info(cid):
    with tracer.start_as_current_span("beorn.service.get_service_info") as span:
        set_mdso_correlation(circuit_id=cid)
        span.set_attribute("service.operation", "get_info")
        
        try:
            service_details_items = service_details(cid, "charter.resourceTypes.NetworkService")["items"]
            svc_info = ""
            if service_details_items:
                for i in service_details_items:
                    site_msgs = []
                    if "site_status" in i["properties"]:
                        for site in i["properties"]["site_status"]:
                            site_msgs.append({"Host": site["host"], "Site": site["site"], "State": site["state"]})
                    svc_info = {
                        "MDSO service ID": i["id"],
                        "Stage": i["properties"]["stage"],
                        "Site state": i["properties"]["state"],
                        "Site status": site_msgs,
                        "Current service state": i["orchState"],
                        "Desired service state": i["desiredOrchState"],
                        "Reason": i["reason"],
                    }
                    span.set_attribute("mdso.resource_id", i["id"])
                    span.set_attribute("service.stage", i["properties"].get("stage", "unknown"))
                    span.set_attribute("service.state", i.get("orchState", "unknown"))
                    span.set_attribute("service.desired_state", i.get("desiredOrchState", "unknown"))
                    if i.get("reason"):
                        error_context = error_categorizer.extract_error_context(i["reason"])
                        span.set_attribute("error.category", error_context.get("category", "UNKNOWN_ERROR"))
            else:
                span.set_attribute("service.found", False)
                abort(404, "No service detail items found")
            
            span.set_attribute("service.found", True)
            add_span_event("service.info.retrieved", circuit_id=cid)
            return svc_info
        except Exception as e:
            set_span_error(e)
            raise


def get_service_map_info(cid):
    filters = {"label": cid, "properties.circuit_id": cid}
    resource_list = _get_resource_type_resource_list("charter.resourceTypes.ServiceMapper", filters)
    # iterate through items[] array and look for an orchState == active
    for item in resource_list["items"]:
        if "orchState" in item and item["orchState"] in "active":
            # already a mapping resource instantiated and either in process or completed
            # good! just return the resource id of this entry
            if len(item["id"]) > 0:
                # there is a resource that can already be queried for status and diffs
                return item
    abort(502, "Service Map Info Invalid or Missing")


def is_multi_leg(topology):
    return True if topology.get("PRIMARY") else False
