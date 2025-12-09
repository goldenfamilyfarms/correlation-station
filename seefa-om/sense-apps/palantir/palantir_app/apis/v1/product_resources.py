import logging
from flask import request
from flask_restx import Namespace, Resource, fields
from common_sense.common.errors import abort
from palantir_app.dll.mdso import get_all_product_resources, product_query
from palantir_app.bll.product_resources import get_times
import datetime as dt

api = Namespace("v1/product_resources", description="Status of MDSO resources")
logger = logging.getLogger(__name__)


@api.route("")
@api.response(200, "OK", api.model("response", {"items": fields.List(fields.String("{ MDSO resource }"))}))
@api.response(400, "Bad request", api.model("bad request", {"message": fields.String(example="Fail Reason")}))
@api.response(500, "Application Error")
class ResourcesList(Resource):
    @api.doc(
        params={
            "resourceType": "Product Resource-type",
            "sinceDay": "Integer day of the month",
            "sinceMonth": "Integer month",
            "sinceYear": "Integer Year",
            "n_days": "Integer number of days (this takes priority over the date if provided)",
        }
    )
    def get(self):
        try:
            # declare params
            if "resourceType" not in request.args:
                abort(400, "Missing parameter: resourceType")

            if "n_days" not in request.args:
                for arg in ["sinceDay", "sinceMonth", "sinceYear"]:
                    if arg not in request.args:
                        abort(400, "Must provide parameter n_days or provide: 'sinceDay', 'sinceMonth' and 'sinceYear'")

            resource_type = request.args["resourceType"]
            since_day = request.args.get("sinceDay")
            since_month = request.args.get("sinceMonth")
            since_year = request.args.get("sinceYear")
            n_days = request.args.get("n_days")

            # define the date
            if n_days:
                today = dt.datetime.today()
                start_day = today - dt.timedelta(days=int(n_days))
            else:
                start_day = dt.datetime(year=int(since_year), month=int(since_month), day=int(since_day))
        except Exception as e:
            abort(500, f"An issue occurred parsing the provided parameters: {e}")

        try:
            # get the product id
            prod_id = product_query(product_name=resource_type)
            if not prod_id:
                abort(500, f"Issue occurred finding product id for: {resource_type}")

            # get the resources
            status, resource_list = get_all_product_resources(product_id=prod_id)
            if not status:
                abort(500, f"Issue occurred querying resources: {resource_list}")
        except Exception as e:
            abort(500, f"An issue occurred getting data from MDSO: {e}")

        try:
            # separate out new ones
            recent_resources = []
            for resource in resource_list:
                times = get_times(resource)
                if times["start"] > start_day:
                    recent_resources.append(resource)
            return {"items": recent_resources}
        except Exception as e:
            abort(500, f"processing the data from MDSO  {e}")
