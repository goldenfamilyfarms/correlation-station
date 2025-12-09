import os
import json
import logging.config

from arda_app.common import app_config


def setup_logging(path="debug_logging_settings.json", default_level=logging.DEBUG) -> logging.Logger:
    """Setup logging configuration"""

    if app_config.LOGGING_SETTINGS:
        path = app_config.LOGGING_SETTINGS

    if os.path.exists(path):
        with open(path, "r") as f:
            config = json.load(f)
        logging.config.dictConfig(config)

    else:
        logging.basicConfig(level=default_level)
        logging.info("debug_logging_settings.json not found - using basic configuration instead.")

    return logging.getLogger(__name__)


def format_connection_error(endpoint, error, status_code=""):
    return "Connection to {} failed - {}{}".format(endpoint, "{}: ".format(status_code) if status_code else "", error)


def format_api_call(endpoint, call_type, message=""):
    """param call_type is GET, POST, etc."""
    return "{} to {}{}{}".format(call_type.upper(), endpoint, " - " if message else "", message)
