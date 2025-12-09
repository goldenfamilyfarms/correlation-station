import datetime
import logging

import requests
from flask_restx import Namespace, Resource, fields

from common_sense.common.errors import abort

api = Namespace(
    "v1/apimetrics",
    description="get api performance for\
    the past day",
)
logger = logging.getLogger(__name__)

api_perf_metric_model = api.model(
    "api_perf_metric_model",
    {
        "uri_path": fields.String,
        "method": fields.String,
        "num_of_requests": fields.Integer(min=0),
        "avg_resp_time": fields.Integer(min=0),
    },
)


@api.route("")
@api.response(200, "OK", api_perf_metric_model)
@api.response(500, "Application Error")
class ApiMetrics(Resource):
    def api_perf_metrics(self, results):
        api_perf_metrics = []
        uri_paths_regex = ["/arda/v", "/beorn/v", "/palantir/v", "/shelob/v"]

        for result in results:
            # Do only uri_paths that got our API
            for uri_path_regex in uri_paths_regex:
                if "uri_path" in result:
                    if uri_path_regex in result["uri_path"]:
                        # Do perm metrics only on 2XX responses
                        if result["response_code"] > 199 and result["response_code"] < 300:
                            # check for adding to current metrics
                            for metric in api_perf_metrics:
                                if metric["uri_path"] == result["uri_path"] and metric["method"] == result["method"]:
                                    # up the count
                                    metric["num_of_requests"] += 1
                                    # calculate the new avg
                                    avg = (metric["avg_resp_time"] + result["total_time"]) / metric["num_of_requests"]
                                    break
                            # Adding a new uri metric
                            else:
                                api_perf_metrics.append(
                                    {
                                        "uri_path": result["uri_path"],
                                        "method": result["method"],
                                        "num_of_requests": 1,
                                        "avg_resp_time": avg,
                                    }
                                )
        return api_perf_metrics

    def get(self):
        # build url
        sw_base_url = (
            "https://avi.chtrse.com/api/analytics/logs?type=1&"
            "virtualservice=virtualservice-73b85ce6-b00e-4119-87e7-d11e8d5b0539"
        )
        mw_base_url = (
            "https://avi.chtrse.com/api/analytics/logs?type=1&"
            "virtualservice=virtualservice-a16a304b-4949-43f4-9ec2-a0225ccc450a"
        )
        static_query_params = "&udf=true&nf=true&timeout=2&orderby=-report_timestamp&page_size=20&page=1&"
        end = "{}{}{}".format("end=", datetime.datetime.utcnow().isoformat(), "&duration=86400")

        r_sw = requests.get(
            "{}{}{}".format(sw_base_url, static_query_params, end), verify=False, auth=("sense", "$en$E123"), timeout=300
        )
        r_mw = requests.get(
            "{}{}{}".format(mw_base_url, static_query_params, end), verify=False, auth=("sense", "$en$E123"), timeout=300
        )
        if r_sw.status_code == 200 and r_mw.status_code == 200:
            resp_data_sw = r_sw.json()
            resp_data_mw = r_mw.json()
        else:
            abort(r_sw.status_code)

        mw_api_metrics = self.api_perf_metrics(resp_data_mw["results"])
        sw_api_metrics = self.api_perf_metrics(resp_data_sw["results"])

        return {"MW": mw_api_metrics, "SW": sw_api_metrics}
