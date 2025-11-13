# Flake8: noqa: E402
import logging
import os
import traceback

from dotenv import load_dotenv
from flask import Blueprint, Flask, has_request_context, request
from flask_restx import Api
from flask_restx.apidoc import apidoc

from beorn_app.config import AppConfig, AuthConfig, UrlConfig

# quick and dirty check for empty str vs encrypted str of first env var
env_vars_set = os.environ.get("ARIN_API_KEY")
if not env_vars_set:
    load_dotenv(override=True)

app_config = AppConfig()
auth_config = AuthConfig()
url_config = UrlConfig()

os.environ["MS_NAME"] = "BEORN"

from beorn_app.apis.v1.bandwidth import api as bandwidth_api_v1
from beorn_app.apis.v1.cpe import api as cpe_v1
from beorn_app.apis.v1.device import api as device_v1
from beorn_app.apis.v1.eligibility import api as eligibility_v1
from beorn_app.apis.v1.ene import api as ene_v1
from beorn_app.apis.v1.granite_status import api as granite_status_v1
from beorn_app.apis.v1.health import api as health_api_v1
from beorn_app.apis.v1.managed_rphy import api as rphy_v1
from beorn_app.apis.v1.managed_service import api as managed_service_api_v1
from beorn_app.apis.v1.mne import api as mne_v1
from beorn_app.apis.v1.rphy_rfcodes import api as rphy_rfcodes_v1
from beorn_app.apis.v1.service import api as service_v1
from beorn_app.apis.v1.submodule_test import api as submodule_test
from beorn_app.apis.v2.cpe import api as cpe_v2
from beorn_app.apis.v2.eligibility import api as eligibility_v2
from beorn_app.apis.v2.managed_service import api as managed_service_api_v2
from beorn_app.apis.v3.cpe import api as cpe_v3
from beorn_app.apis.v3.service import api as service_v3
from beorn_app.apis.v3.topologies import api as topologies_api_v3
from beorn_app.common.logging_setup import setup_logging

with open("VERSION", "r") as f:
    version = f.read()

__version__ = version


app = Flask(__name__)

app.config["ERROR_404_HELP"] = False
app.config["PROPAGATE_EXCEPTIONS"] = True
setup_logging()
logger = logging.getLogger(__name__)



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
            "TRACE": f"{traceback.format_exc()}",
        }
        logger.error(error_details)
        return {"message": f"BEORN - {error_details}", "summary": "SENSE | SENSE Bug Error"}, 500
    else:
        logger.error(error)
        return {"message": f"BEORN - {error}", "summary": "SENSE | SENSE Bug Error"}, 500


# to server swagger libs from arda
URL_PREFIX = "/beorn"
apidoc.url_prefix = URL_PREFIX
# Prefix URL with 'beorn_app/' here
blueprint = Blueprint("api", __name__, url_prefix=URL_PREFIX)

# All API metadata
api = Api(
    blueprint,
    title="BEORN - SEEFA Provisioning Microservices",
    version=__version__,
    description="Provisioning microservice <style>.models {display: none !important}</style>",
    catch_all_404s=True,
)

app.register_blueprint(blueprint)

api.add_namespace(device_v1)
api.add_namespace(health_api_v1)
api.add_namespace(service_v1)
api.add_namespace(service_v3)
api.add_namespace(cpe_v1)
api.add_namespace(cpe_v2)
api.add_namespace(cpe_v3)
api.add_namespace(bandwidth_api_v1)
api.add_namespace(topologies_api_v3)
api.add_namespace(managed_service_api_v1)
api.add_namespace(granite_status_v1)
api.add_namespace(managed_service_api_v2)
api.add_namespace(rphy_rfcodes_v1)
api.add_namespace(rphy_v1)
api.add_namespace(mne_v1)
api.add_namespace(ene_v1)
api.add_namespace(eligibility_v1)
api.add_namespace(eligibility_v2)
api.add_namespace(submodule_test)
