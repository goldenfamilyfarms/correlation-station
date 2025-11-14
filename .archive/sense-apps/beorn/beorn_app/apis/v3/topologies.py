import logging

from flask import request
from flask_restx import Namespace, Resource

from beorn_app.bll.topologies import Topologies
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)
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
        if not request.args.get("cid"):
            abort(400, "Please provide a cid - /topologies?cid=51.L1XX.000000..TWCC")

        cid = request.args.get("cid")
        return Topologies(cid).create_topology()
