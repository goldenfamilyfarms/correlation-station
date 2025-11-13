from flask_restx import Namespace, Resource

api = Namespace("v1/health", description="service health check")


@api.route("")
@api.response(404, "Page Not Found")
@api.response(200, "OK")
class HealthCheck(Resource):
    @api.doc("health_check")
    def get(self):
        """Ensures the server is up and running and returns True"""
        if 1 + 1 == 2:
            return "Healthy!"
