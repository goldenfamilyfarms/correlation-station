import logging

from flask import request
from flask_restx import Namespace, Resource

from beorn_app.bll.topologies import Topologies
from common_sense.common.errors import abort
from beorn_app.common.otel import get_tracer, set_mdso_correlation, add_span_event, set_span_error

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
api = Namespace("v3/topologies", description="topology of a circuit")


@api.route("")
@api.response(200, "OK")
@api.response(404, "Not Found")
@api.response(400, "Bad Request")
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented")
@api.response(502, "Bad Gateway")
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout")
@api.doc(params={"cid": "A cid"})  # Order type for developer use
class TopologiesAPI(Resource):
    def get(self):
        """Provide a CID to get the topology for that circuit"""
        cid = request.args.get("cid")
        if not cid:
            abort(400, "Please provide a cid - /topologies?cid=51.L1XX.000000..TWCC")

        with tracer.start_as_current_span("beorn.topology.get") as span:
            set_mdso_correlation(circuit_id=cid)
            span.set_attribute("topology.operation", "get")
            
            try:
                add_span_event("topology.creation.start", circuit_id=cid)
                topology = Topologies(cid).create_topology()
                
                # Extract topology metadata
                if isinstance(topology, dict):
                    if "PRIMARY" in topology:
                        span.set_attribute("topology.multi_leg", True)
                        span.set_attribute("topology.legs", 2)
                    else:
                        span.set_attribute("topology.multi_leg", False)
                        span.set_attribute("topology.legs", 1)
                    
                    # Extract service type if available
                    service_data = topology.get("service") or topology.get("PRIMARY", {}).get("service")
                    if service_data and len(service_data) > 0:
                        service_type = service_data[0].get("data", {}).get("service_type")
                        if service_type:
                            span.set_attribute("topology.service_type", service_type)
                
                add_span_event("topology.creation.complete", circuit_id=cid)
                return topology
            except Exception as e:
                set_span_error(e)
                raise
