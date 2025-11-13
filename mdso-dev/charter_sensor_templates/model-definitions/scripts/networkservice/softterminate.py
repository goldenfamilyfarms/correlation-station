""" -*- coding: utf-8 -*-

SoftTerminate Plans

Versions:
   0.1 Dec 8, 2018
       Initial check in of SoftTerminate plans

"""
import random
from datetime import timedelta, datetime, date
import sys
sys.path.append('model-definitions')
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the the batch processing of existing
    NetworkFunctions to perform a soft termination.
    """

    def process(self):
        app_properties = self.get_bpo_contants_resource()["properties"].get("application_properties", {})
        days_to_keep_active = app_properties.get("days_to_keep_active_network_service", 0)
        days_to_keep_failed = app_properties.get("days_to_keep_failed_network_service", 0)

        if days_to_keep_active <= 0 and days_to_keep_failed <= 0:
            self.logger.info("Configuration not set to soft terminate network resources, so completed.")
        else:
            for ns in self.bpo.resources.get_by_domain_and_type(
                self.BUILT_IN_DOMAIN_ID, self.BUILT_IN_NETWORK_SERVICE_TYPE
            ):
                ns_state = ns["orchState"]
                days_since_last_update = self.get_days_since_last_update(ns)
                if ns_state == "active" and days_since_last_update > days_to_keep_active and days_to_keep_active > 0:
                    self.soft_term_ns(ns)
                elif ns_state == "failed" and days_since_last_update > days_to_keep_failed and days_to_keep_failed > 0:
                    self.soft_term_ns(ns)
                else:
                    self.logger.debug(
                        "NetworkService %s has not reached an archiving age yet (%s)."
                        % (ns["label"], days_since_last_update)
                    )

        self.schedule_next_sync()
        return

    def soft_term_ns(self, ns):
        """performs the soft terminate on the network service"""
        self.logger.info("Performing software terminate on NS " + ns["label"])
        self.bpo.resources.exec_operation(ns["label"], "softTerminate", {})

    def get_days_since_last_update(self, ns):
        """returns the number of days since the last update to a resource"""
        last_update_time = datetime.strptime(ns["updatedAt"].split(".")[0], "%Y-%m-%dT%H:%M:%S")
        return (datetime.now() - last_update_time).days

    def schedule_next_sync(self):
        """schedules the next sync if a schedule does not already exist..."""
        base_label = "batch_soft_terminate_"
        tomorrow = date.today() + timedelta(days=1)
        batch_product = self.bpo.products.get_by_domain_and_type("built-in", self.resource["resourceTypeId"])[0]
        label = base_label + tomorrow.strftime("%b_%d")

        scheduler_prod = self.bpo.products.get_by_domain_and_type("built-in", self.BUILT_IN_RESOURCE_SCHEDULER_TYPE)[0]
        for resource in self.bpo.market.get(
            "/resources?resourceTypeId=%s&p=label:%s*&limit=1000" % (self.BUILT_IN_RESOURCE_SCHEDULER_TYPE, base_label)
        )["items"]:
            if resource["properties"]["schedule_state"] == "SCHEDULED":
                self.logger.info("Scheduler with ID %s already exists, so no need to create a new one" % resource["id"])
                return

        res = {
            "label": label + ".sched",
            "productId": scheduler_prod["id"],
            "properties": {
                "activation_time": {
                    "year": int(tomorrow.strftime("%Y")),
                    "month": tomorrow.strftime("%b"),
                    "day": int(tomorrow.strftime("%d")),
                    "hour": random.randint(1, 3),
                    "minute": random.randint(1, 59),
                },
                "scheduled_resource": {
                    "productId": batch_product["id"],
                    "label": label,
                    "autoClean": False,
                    "properties": {},
                },
            },
        }

        return self.bpo.resources.create(None, res).resource
