from flask_restx import Namespace, Resource

from common_sense.common.errors import abort
from palantir_app.common.oss_checks import are_systems_healthy

api = Namespace("v2/health", description="health of systems check")


@api.route("")
@api.response(504, "One or More Systems Unhealthy")
@api.response(200, "OK")
class HealthCheck(Resource):
    @api.doc("health_check")
    def get(self):
        """Ensures critical servers are up and running and returns status"""
        results = {"tested": [], "untested": [], "passed": [], "failed": []}
        systems_health = are_systems_healthy(results)
        if systems_health is True:
            return "Healthy!"
        else:
            abort(504, f"One or More Systems Are Testing Unhealthy\\n{results}")
