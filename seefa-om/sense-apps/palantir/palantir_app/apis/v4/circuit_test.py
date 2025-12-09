import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from palantir_app.bll.circuit_test_v4 import ServiceTopology
from common_sense.common.errors import abort

api = Namespace("v4/circuit_test", description="Pull VTA information and status from Granite/MDSO")

logger = logging.getLogger(__name__)

# swagger examples
ok_request = api.model(
    "Successful query and retrieval",
    {
        "CustomerName": fields.String(example="3455610027782439000"),
        "CircuitID": fields.String(example="99.L9XX..999999..CHTR"),
        "Bandwidth": fields.String(example="1 Gbps"),
        "ServiceLevel": fields.String(example="null"),
        "CustomerType": fields.String(example="COM"),
        "ServiceType": fields.String(example="DIA"),
        "Status": fields.String(example="Auto-Designed"),
        "VCID": fields.String(example="null"),
        "ASide": fields.String(example="{}"),
        "ZSide": fields.String(example="{}"),
        "UnitType": fields.String(example="null"),
    },
)

bad_request = api.model(
    "Incorrect URI Parameter",
    {
        "message": fields.String(
            example="please submit a valid circuit id", description="A URI parameter other than 'name' was specified"
        )
    },
)

not_found_request = api.model(
    "The circuit was not found",
    {"message": fields.String(example="no record found", description="no record found for '<cid>'")},
)
not_implemented_error = api.model(
    "not_implemented_error",
    {
        "message": fields.String(
            example="Use case <> not supported in this release",
            description="A use case is not supported in this release",
        )
    },
)

gateway_error = api.model(
    "gateway_error",
    {
        "message": fields.String(
            example="Unexpected data from downstream server",
            description="Unexpected data received from downstream server",
        )
    },
)

connection_error = api.model(
    "connection_error",
    {
        "error": fields.String(
            example="Issue with server connection", description="Connection issue with upstream data source"
        )
    },
)


@api.route("")
@api.response(200, "OK", ok_request)
@api.response(400, "Bad Request", bad_request)
@api.response(404, "Resource Not Found", not_found_request)
@api.response(500, "Internal Server Error")
@api.response(501, "Not Implemented", not_implemented_error)
@api.response(502, "Gateway Error", gateway_error)
@api.response(503, "Service Unavailable")
@api.response(504, "Gateway Timeout", connection_error)
@api.doc(params={"name": "The circuit ID for the service"})
class CircuitTest(Resource):
    def get(self):
        """get details on spirent test circuits"""
        # Check CID
        cid = request.args.get("name")
        logger.debug("== cid {} ==".format(cid))
        if "name" not in request.args:
            abort(400, "invalid uri parameter specified, please use 'name'")
        if cid is None:
            abort(400, "please submit a valid circuit id")
        if len(cid) < 20:
            abort(400, "please submit a valid circuit id")
        if len(request.args) > 1:
            abort(400, "too many uri parameters provided, please only use 'name' parameter")
        return ServiceTopology().circuit_test_model(cid)
