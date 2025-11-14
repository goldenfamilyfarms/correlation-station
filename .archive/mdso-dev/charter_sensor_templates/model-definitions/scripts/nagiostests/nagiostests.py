import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from update_results import UpdateResults


class RunTest(CommonPlan):
    KAFKA_LAG_TEST = "check_kafka_lag"

    def process(self):
        test_name = self.properties["test_name"]
        return test_name


class UpdateResults(CommonPlan, UpdateResults):
    def process(self):
        operation = self.bpo.resources.get_operation(self.resource["id"], self.params["operationId"])
        results = operation["inputs"]["results"]

        self.update_results(self, self.resource, results)
