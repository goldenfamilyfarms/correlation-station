import logging

from flask import request
from flask_restx import Namespace, Resource, fields

from common_sense.common.errors import abort
from palantir_app.bll.resource_status import stand_alone_config_removal
from palantir_app.common.constants import PASS_THROUGH
from palantir_app.common.mdso_operations import resource_status
from palantir_app.dll.mdso import _create_token, _delete_token

api = Namespace("v1/resourcestatus", description="Status of MDSO resources")

logger = logging.getLogger(__name__)


@api.route("")
@api.response(
    200,
    "OK",
    api.model(
        "resource_status_success",
        {
            "id": fields.String(example="5ce47efe-c165-4795-8952-313b5c67d98b"),
            "label": fields.String(example="51.L1XX.009025..TWCC"),
            "description": fields.String(example="CID from sense CLI"),
            "resourceTypeId": fields.String(example="charter.resourceTypes.NetworkService"),
            "productId": fields.String(example="5cd39377-4d4d-4c71-8c17-69cf4d4dec4d"),
            "tenantId": fields.String(example="0dc14019-d59c-4826-89d8-48ca10064d92"),
            "shared": fields.String(example="false"),
            "subDomainId": fields.String(example="7fd5144c-552f-39a3-9464-08d3b9cfb251"),
            "properties": fields.Nested(
                api.model(
                    "properties",
                    {
                        "stage": fields.String(example="PRODUCTION"),
                        "state": fields.String(example="PROVISIONING_PRE_CHECKS"),
                        "circuit_id": fields.String(example="51.L1XX.009025..TWCC"),
                        "site_status": fields.List(
                            fields.Nested(
                                api.model(
                                    "site_status",
                                    {
                                        "host": fields.String(example="AUSDTXIR2ZW"),
                                        "site": fields.String(example="1121"),
                                        "state": fields.String(example="NOT_STARTED"),
                                    },
                                )
                            )
                        ),
                    },
                )
            ),
            "discovered": fields.String(example="false"),
            "differences": fields.List(fields.Raw()),
            "desiredOrchState": fields.String(example="active"),
            "orchState": fields.String(example="activating"),
            "reason": fields.String(example="MDSO failure reason if any"),
            "tags": fields.Nested(api.model("tags", {})),
            "providerData": fields.Nested(
                api.model("provider", {"templateResources": fields.Nested(api.model("templateresource", {}))})
            ),
            "updatedAt": fields.String(example="2019-05-21T22:43:32.880Z"),
            "createdAt": fields.String(example="2019-05-21T22:43:10.460Z"),
            "autoClean": fields.String(example="false"),
        },
    ),
)
@api.response(400, "Bad request", api.model("bad request", {"message": fields.String(example="Missing resource_id.")}))
@api.response(404, "Resource Not Found")
@api.response(
    500,
    "Application Error",
    api.model("app error", {"message": fields.String(example="MDSO failed to process the resource status request")}),
)
class ResourceStatus(Resource):
    @api.doc(params={"resourceId": "resourceId"})
    def get(self):
        """Takes resourceID and returns status."""

        if "resourceId" not in request.args:
            abort(400, "Missing resource_id.")

        if "resourceId" == PASS_THROUGH:
            return {"status": "Completed", PASS_THROUGH: True}

        token = _create_token()
        headers = {"Accept": "application/json", "Authorization": "token {}".format(token)}

        error_msg, data = resource_status(headers, request.args["resourceId"])
        if error_msg:
            _delete_token(token)
            logger.debug(error_msg)
            if error_msg == "Resource not found":
                abort(404, error_msg)
            else:
                abort(500, error_msg)

        _delete_token(token)

        if "standaloneConfigDelivery" in data["resourceTypeId"]:
            data = stand_alone_config_removal(data)

        return data
