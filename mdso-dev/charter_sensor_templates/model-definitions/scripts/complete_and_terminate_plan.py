""" -*- coding: utf-8 -*-

NetworkServiceCheck Plans

Versions:
   0.1 Jan 8, 2017
       Initial check in of NetworkServiceCheck plans

"""
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class CompleteAndTerminatePlan(CommonPlan):
    """this is the class that is called for the initial activation of the
    NetworkServiceCheck.  The only input it requires is the circuit_id associated
    with the service.
    """

    DeletionWaitTimeSeconds = 10

    def run(self):
        return_value = super(CompleteAndTerminatePlan, self).run()

        product = self.bpo.market.get_products_by_resource_type(self.BUILT_IN_RESOURCE_TERMINATOR)[0]

        r = {
            "label": self.resource["label"] + ".term",
            "productId": product["id"],
            "properties": {"resource_id": self.resource["id"], "wait_time": self.DeletionWaitTimeSeconds},
        }

        self.bpo.resources.create(self.resource["id"], r, wait_active=False)

        return return_value
