import time
import uuid

import structlog
from flask import Request, Response

logging = structlog.getLogger()


class LoggingWSGIMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        request_id = str(uuid.uuid4()).replace("-", "")[:8].upper()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start_time = time.perf_counter_ns()

        # Capture request data before Flask processes it
        request = Request(environ)
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
            if content_length > 1048576:  # 1MB limit
                request_payload = "<payload too large>"
            else:
                request_payload = environ.get("wsgi.input").read(content_length)
                # Create proper BytesIO replacement
                from io import BytesIO

                environ["wsgi.input"] = BytesIO(request_payload)
        except Exception:
            request_payload = "<capture failed>"

        try:
            response: Response = self.app(environ, start_response)
        except Exception:
            structlog.stdlib.get_logger("api_error").exception("Uncaught Exception")
            raise
        finally:
            process_time = str((time.perf_counter_ns() - start_time) / 10**9)
            request_args = request.args
            request_path = request.path

            logging.info(f"Request Path: {request_path}")
            logging.info(f"Request Query Params: {request_args}")
            logging.info(f"Request Payload: {request_payload}")

        structlog.contextvars.bind_contextvars(ProcessTime=process_time)

        return response
