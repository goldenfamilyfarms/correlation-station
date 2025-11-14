# Flake8: noqa: E402
import os
import sys
import traceback

import structlog

from dotenv import load_dotenv
from flask import Blueprint, Flask, has_request_context, request
from flask_restx import Api
from flask_restx.apidoc import apidoc

from palantir_app.config import AppConfig, AuthConfig, UrlConfig

# Add common directory to path for shared utilities
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'common'))

# Import comprehensive OTEL observability (replaces resource-intensive middleware)
try:
    from observability import setup_observability
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("Warning: OTEL instrumentation not available. Install opentelemetry-*")

# quick and dirty check for empty str vs encrypted str of first env var
env_vars_set = os.environ.get("ARIN_API_KEY")
if not env_vars_set:
    load_dotenv(override=True)


app_config = AppConfig()
auth_config = AuthConfig()
url_config = UrlConfig()

os.environ["MS_NAME"] = "PALANTIR"

from common_sense.common.errors import remove_api_key
from palantir_app.apis.v1.apimetrics import api as apimetrics_api_v1
from palantir_app.apis.v1.compliance_disconnect import api as compliance_disconnect_api_v1
from palantir_app.apis.v1.compliance_provisioning import api as compliance_api_v1
from palantir_app.apis.v1.device_validator import api as device_validator_v1
from palantir_app.apis.v1.health import api as health_api_v1
from palantir_app.apis.v1.mdso_url import api as mdso_url
from palantir_app.apis.v1.operation_status import api as op_status_v1
from palantir_app.apis.v1.overlay_acceptance import api as overlay_acceptance
from palantir_app.apis.v1.overlay_compliance import api as overlay_compliance
from palantir_app.apis.v1.port import api as port_v1
from palantir_app.apis.v1.product_resources import api as product_resources_v1
from palantir_app.apis.v1.resource_status import api as res_status_v1
from palantir_app.apis.v1.rphyipcmac import api as rphyipcmac_v1
from palantir_app.apis.v1.submodule_test import api as submodule_test
from palantir_app.apis.v2.device import api as device_v2
from palantir_app.apis.v2.device_validator import api as device_validator_v2
from palantir_app.apis.v2.health import api as health_api_v2
from palantir_app.apis.v2.port import api as port_v2
from palantir_app.apis.v3.circuit_test import api as circuit_test_v3
from palantir_app.apis.v3.ise import api as ise_api_v3
from palantir_app.apis.v4.circuit_test import api as circuit_test_v4
from palantir_app.apis.v4.resource_status import api as res_status_v4
from palantir_app.common.logging_setup import setup_logging


with open("VERSION", "r") as f:
    version = f.read()

__version__ = version

setup_logging(json_logs=True)
logger = structlog.get_logger()


app = Flask(__name__)
app.config["ERROR_INCLUDE_MESSAGE"] = False
app.config["PROPAGATE_EXCEPTIONS"] = True
app.config["ERROR_404_HELP"] = False

# Initialize comprehensive OTEL observability (traces + metrics)
if OTEL_AVAILABLE:
    try:
        setup_observability(
            app,
            service_name="palantir",
            service_version=version.strip(),
            environment=os.getenv("DEPLOYMENT_ENV", "prod")
        )
        logger.info("Palantir OTEL observability initialized (traces + metrics)")
    except Exception as e:
        logger.warning(f"Failed to initialize OTEL: {e}")
else:
    logger.warning("OTEL not available - running without instrumentation")


@app.errorhandler(Exception)
def handle_internal_server_error(error):
    """Return a custom message and 500 status code"""
    if has_request_context():
        error_details = {
            "SEnSE Bug!!": "Sending Report to SEnSE team for investigation",
            "URL": f"{request.url}",
            "URL PARAMS": f"{request.args}",
            "PAYLOAD": f"{request.data}",
            "REMOTE ADDR": f"{request.remote_addr}",
            "TRACE": remove_api_key(f"{traceback.format_exc()}"),
        }
        logger.error(error_details)
        return {"message": f"PALANTIR - {error_details}", "summary": "SENSE | SENSE Bug Error"}, 500
    else:
        logger.error(error)
        return {"message": f"PALANTIR - {error}", "summary": "SENSE | SENSE Bug Error"}, 500


authorizations = {"Basic Auth": {"type": "basic", "in": "header", "name": "Authorization"}}


# to server swagger libs from palantir.
URL_PREFIX = "/palantir"
apidoc.url_prefix = URL_PREFIX
# Prefix URL with 'palantir_app/' here
blueprint = Blueprint("api", __name__, url_prefix=URL_PREFIX)

# All API metadata
api = Api(
    blueprint,
    title="PALANTIR - SEEFA Acceptance and Network Compliance Microservices",
    version=__version__,
    description="",
    security="Basic Auth",
    authorizations=authorizations,
    catch_all_404s=True,
)

app.register_blueprint(blueprint)

api.namespaces.clear()
api.add_namespace(health_api_v1)
api.add_namespace(health_api_v2)
api.add_namespace(apimetrics_api_v1)
api.add_namespace(compliance_api_v1)
api.add_namespace(compliance_disconnect_api_v1)
api.add_namespace(circuit_test_v3)
api.add_namespace(circuit_test_v4)
api.add_namespace(device_v2)
api.add_namespace(device_validator_v1)
api.add_namespace(device_validator_v2)
api.add_namespace(ise_api_v3)
api.add_namespace(mdso_url)
api.add_namespace(op_status_v1)
api.add_namespace(overlay_acceptance)
api.add_namespace(overlay_compliance)
api.add_namespace(port_v1)
api.add_namespace(port_v2)
api.add_namespace(product_resources_v1)
api.add_namespace(res_status_v1)
api.add_namespace(res_status_v4)
api.add_namespace(rphyipcmac_v1)
api.add_namespace(submodule_test)
