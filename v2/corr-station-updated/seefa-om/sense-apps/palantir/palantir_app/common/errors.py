"""HTTP errors to raise on certain conditions"""

import logging

from palantir_app.common.logging_setup import format_connection_error

logger = logging.getLogger(__name__)


class InvalidUsage(Exception):
    """Create custom HTTP errors

    Note that used alone, these types of
    errors will only result in internal server errors - need a handler
    """

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code:
            self.status_code = status_code
        else:
            self.status_code = 400
        self.payload = payload
        logger.exception(format_connection_error("endpoint", message, status_code))

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        rv["status_code"] = self.status_code
        return rv


class ConnectionIssue(Exception):
    """A custom connection error for issues we encounter connecting
    to routers
    """

    # Connection error 503 - SERVICE_UNAVAILABLE

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code:
            self.status_code = status_code
        else:
            self.status_code = 503
        self.payload = payload
        logger.exception(format_connection_error("endpoint", message, status_code))

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        rv["status_code"] = self.status_code
        return rv
