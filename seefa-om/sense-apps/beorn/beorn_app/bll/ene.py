import logging
from flask_restx import fields


logger = logging.getLogger(__name__)


def expected_payloads(api):
    models = {"ene_claim_device": claim_device_expected_payload(api)}
    return models


def claim_device_expected_payload(api):
    """
    Creates the expected payload template for MNE claim device endpoint
    :param api: api
    :return: api.model
    """
    payload = api.model(
        "pl",
        {
            "label": fields.String(example="LABEL"),
            "properties": fields.Nested(
                api.model(
                    "properties",
                    {
                        "customerName": fields.String(example="CUSTOMER_NAME"),
                        "circuitId": fields.String(example="CID"),
                        "address": fields.String(example="11921 N MoPac Expy, Austin, TX, 78759"),
                        "configurations": fields.Nested(api.model("configurations", {})),
                    },
                )
            ),
        },
    )
    return payload


def response_models(api):
    models = {}
    models["bad_request"] = api.model("bad_request", {"message": fields.String(example="Brief failure description")})
    models["ene_post_ok"] = api.model(
        "Successfully retrieved data", {"resource_id": fields.String(example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")}
    )
    return models
