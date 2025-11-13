import json
import logging.config
import os

import beorn_app


def setup_logging(path="debug_logging_settings.json", default_level=logging.DEBUG):
    """Setup logging configuration"""

    if beorn_app.app_config.LOGGING_SETTINGS:
        path = beorn_app.app_config.LOGGING_SETTINGS

    if os.path.exists(path):
        with open(path, "r") as f:
            config = json.load(f)
        logging.config.dictConfig(config)

    else:
        logging.basicConfig(level=default_level)
        print("debug_logging_settings.json not found - using basic configuration instead.")


def format_connection_error(endpoint, error, status_code=""):
    return "Connection to {} failed - {}{}".format(endpoint, "{}: ".format(status_code) if status_code else "", error)


def format_api_call(endpoint, call_type, message=""):
    """param call_type is GET, POST, etc."""
    return "{} to {}{}{}".format(call_type.upper(), endpoint, " - " if message else "", message)