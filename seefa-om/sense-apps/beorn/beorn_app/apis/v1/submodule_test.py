import logging

from flask_restx import Namespace, Resource

from common_sense.common.test import test

api = Namespace("v1/submodule_test", description="testing shared submodule across the microservices")

logger = logging.getLogger(__name__)


@api.route("")
class Submodule(Resource):
    def get(self):
        resp = test
        return resp
