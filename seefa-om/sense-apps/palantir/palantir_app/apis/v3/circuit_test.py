import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from palantir_app.bll.circuit_test_v3 import circuit_test_model_v3
from palantir_app.bll.circuit_test import check_valid_circuit_id
from common_sense.common.errors import abort

api = Namespace("v3/circuit_test", description="Pull VTA information and status from Granite/MDSO")

logger = logging.getLogger(__name__)

# swagger examples
ok_request = api.model(
    "Successful query and retrieval",
    {
        "mast_seq_key": fields.String(example="3455610027782439000"),
        "sequence": fields.String(example="1.1.0.0.0.0.0.0.0"),
        "topology": fields.String(example="Point to Point"),
        "vendor": fields.String(example="ADVA"),
        "model": fields.String(example="FSP 150CC-GE114/114S"),
        "hostname": fields.String(example="CHRANCIO1ZW"),
        "ipaddress": fields.String(example="10.20.2.209"),
        "interface": fields.String(example="ACCESS-1-1-1-4"),
        "vlanoperation": fields.String(example="PUSH"),
        "servicevlanid": fields.String(example="1200"),
        "customervlanid": fields.String(example="null"),
        "evctype": fields.String(example="null"),
        "split_id": fields.String(example="null"),
        "role": fields.String(example="cpe"),
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
        if not cid or not check_valid_circuit_id(cid):
            abort(400, "please submit a valid circuit id")
        return circuit_test_model_v3(cid)
