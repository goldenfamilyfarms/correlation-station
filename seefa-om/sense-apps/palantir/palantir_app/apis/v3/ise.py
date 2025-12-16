import logging

from flask import request
from flask_restx import Namespace, Resource, fields, reqparse

from palantir_app.bll.ise import (
    delete_ise_device,
    get_ise_record_by_id_cluster,
    id_lookup_cluster,
    onboard_device_in_ise,
)
from palantir_app.bll.isin import is_tid_in_isin
from sense_common.observability import get_tracer, add_span_event, set_span_error
from sense_common.observability.mdso_patterns import ErrorCategorizer
from common_sense.common.errors import abort


api: Namespace = Namespace("v3/ise", description="Locate ISE records for network devices")

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
error_categorizer = ErrorCategorizer()


ok_request = api.model(
    "Successful_retrieval",
    {
        "id": fields.String(example="7b28fa60-db3a-11e9-a2d2-02429363e93c"),
        "name": fields.String(example="CMTNCACX70W"),
        "description": fields.String(example="CMTNCACX70W"),
        "link": fields.Raw(
            example={
                "rel": "self",
                "href": "https://clboh-ise-pan-w01.chtrse.com:9060/"
                "ers/config/networkdevice/"
                "7b28fa60-db3a-11e9-a2d2-02429363e93c",
                "type": "application/xml",
            }
        ),
    },
)

bad_request = api.model(
    "Invalid_URI_Parameter",
    {"message": fields.String(example="missing or invalid parameter specified", description="reason for exception")},
)

# 404 NOT FOUND
not_found_request = api.model(
    "The_record_was_not_found",
    {
        "message": fields.String(
            example="no records found",
            description="No records matching the specified criteria were found in the database.",
        )
    },
)

# 500 SERVER INT
data_error = api.model(
    "issue_processing_request",
    {"error": fields.String(example="issue processing request", description="There was an issue within the api")},
)

# 503 SERVICE UNAVAILABLE
upstream_error = api.model(
    "Issue_with_upstream_data_source",
    {
        "error": fields.String(
            example="issue with upstream data source",
            description="There was an issue with the upstream data source for the API",
        )
    },
)


@api.route("/id_lookup")
@api.response(200, "OK", ok_request)
@api.response(400, "Bad Request", bad_request)
@api.response(404, "Resource Not Found", not_found_request)
@api.response(500, "Application Error", data_error)
@api.response(503, "Data Error", upstream_error)
class IDLookup(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument(
        "type",
        required=True,
        choices=["ipaddress", "name"],
        type=str,
        help="How to find the device, by hostname or by IP address",
    )
    parser.add_argument("device", required=True, help="Device ID to look up - TID or IP")

    @api.doc(parser=parser)
    @api.doc(
        params={"type": "The lookup type - hostname or IP address", "device": "The device we are attempting to verify."}
    )
    def get(self):
        """Query ISE for specified device across the cluster using IP or HostName, and retrieve the IDs"""
        lookup_type = request.args.get("type")
        device_id = request.args.get("device")
        
        with tracer.start_as_current_span("palantir.ise.id_lookup") as span:
            span.set_attribute("ise.operation", "id_lookup")
            span.set_attribute("ise.lookup_type", lookup_type or "unknown")
            span.set_attribute("ise.device_id", device_id or "unknown")
            
            try:
                add_span_event("ise.id_lookup.start", lookup_type=lookup_type, device_id=device_id)
                ise_ids, results = id_lookup_cluster(lookup_type, device_id, delete_device=False)
                span.set_attribute("ise.ids_count", len(ise_ids) if ise_ids else 0)
                span.set_attribute("ise.results_count", len(results) if results else 0)
                add_span_event("ise.id_lookup.complete", ids_count=len(ise_ids) if ise_ids else 0)
                return {"results": results, "ids": ise_ids}
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "ISE_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                raise


@api.route("/device")
@api.response(400, "Bad Request", bad_request)
@api.response(404, "Resource Not Found", not_found_request)
@api.response(500, "Application Error", data_error)
@api.response(501, "Not Implemented")
@api.response(502, "Bad Gateway", data_error)
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout", upstream_error)
class Device(Resource):
    @api.response(201, "Success", ok_request)
    @api.doc(params={"ip": "IP address", "tid": "TID of the device"})
    def post(self):
        """Add device to ISE"""
        tid = request.args.get("tid")
        ip = request.args.get("ip")
        if not ip or not tid:
            abort(400, "provide an IP and TID.")
        
        with tracer.start_as_current_span("palantir.ise.onboard_device") as span:
            span.set_attribute("ise.operation", "onboard_device")
            span.set_attribute("network.device.tid", tid)
            span.set_attribute("network.device.ip", ip)
            
            try:
                add_span_event("ise.onboard.start", tid=tid, ip=ip)
                result, success = onboard_device_in_ise(tid, ip)
                span.set_attribute("ise.onboard.success", success)
                add_span_event("ise.onboard.complete", tid=tid, success=success)
                status_code = 200 if success else 400
                return result, status_code
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "ISE_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                raise

    @api.response(200, "OK", ok_request)
    @api.doc(params={"id": "The ISE ID for the target device"})
    def get(self):
        """Query ISE for specified device using ISE ID"""
        ise_id = request.args.get("id")
        if not ise_id:
            abort(400, "necessary parameter missing")
        
        with tracer.start_as_current_span("palantir.ise.get_record") as span:
            span.set_attribute("ise.operation", "get_record")
            span.set_attribute("ise.id", ise_id)
            
            try:
                add_span_event("ise.get_record.start", ise_id=ise_id)
                result = get_ise_record_by_id_cluster(ise_id)
                add_span_event("ise.get_record.complete", ise_id=ise_id)
                return result, 200
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "ISE_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                raise

    @api.response(200, "OK")
    @api.doc(params={"ip": "IP address", "hostname": "TID of the device"})
    def delete(self):
        """Query ISE for specified device across the cluster, and delete the IDs"""
        if "ip" not in request.args or "hostname" not in request.args:
            abort(400, "Missing ip or hostname")
        hostname = request.args["hostname"]
        ip = request.args["ip"]
        ise_ids, results = delete_ise_device(hostname, ip)
        if not ise_ids:
            return {"message": "Delete Failed - Inout is a core device"}
        else:
            return {"deleted_results": results, "deleted_ids": ise_ids}


@api.route("/isin")
@api.response(400, "Bad request", fields.String(example="Missing IP or TID"))
@api.response(502, "Upstream error")
@api.response(504, "Gateway timeout")
class Isin(Resource):
    @api.response(200, "Found")
    @api.response(201, "Not Found Remediation Started")
    @api.doc(params={"ip": "IP address", "tid": "TID of the device"})
    def get(self):
        ip = request.args.get("ip")
        tid = request.args.get("tid")
        if not ip or not tid:
            abort(400, "Invalid Payload - TID and IP are required")
        
        with tracer.start_as_current_span("palantir.ise.isin_check") as span:
            span.set_attribute("ise.operation", "isin_check")
            span.set_attribute("network.device.tid", tid)
            span.set_attribute("network.device.ip", ip)
            
            try:
                add_span_event("ise.isin_check.start", tid=tid, ip=ip)
                isin = is_tid_in_isin(ip, tid)
                span.set_attribute("ise.isin.found", isin)
                add_span_event("ise.isin_check.complete", found=isin)
                return ("Found in ISE", 200) if isin else ("Not Found Remediation Started", 201)
            except Exception as e:
                set_span_error(e)
                error_context = error_categorizer.extract_error_context(str(e))
                span.set_attribute("error.category", error_context.get("category", "ISE_ERROR"))
                span.set_attribute("error.severity", error_context.get("severity", "ERROR"))
                raise
