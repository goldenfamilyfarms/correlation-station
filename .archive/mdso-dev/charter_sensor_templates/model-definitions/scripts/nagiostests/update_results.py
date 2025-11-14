"""

"""
import time


class UpdateResults:
    def update_results(self, plan, resource, results):
        self.resource = resource
        self.properties = resource["properties"]

        results_patch = {
            "timestamp": str(time.strftime("%Y/%m/%d %H:%M:%S")),
            "status": results["status"],
            "results_message": results["results_message"],
            "results": results.get("results", {}),
        }

        patch = {"properties": {"test_results": results_patch}}

        plan.bpo.resources.patch_observed(self.resource["id"], patch)

        max_history = self.properties["retained_history"]
        history = self.properties.get("test_result_history", [])
        history.insert(0, results_patch)
        history = history[:max_history]

        patch = {"properties": {"test_result_history": history}}

        plan.bpo.resources.patch_observed(self.resource["id"], patch)
