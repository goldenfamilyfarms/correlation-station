""" -*- coding: utf-8 -*-

UpdateObservedProperty Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of MurderSuicide plans

"""
import time
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class Activate(CommonPlan):
    """this is the class that is called for the initial activation of the
    ServiceProvisioner.
    """

    def process(self):
        self.bpo.relationships.delete_relationships(self.resource["id"])
        self.bpo.resources.delete(self.resource["id"])

    def enter_exit_log(self, message, state="STARTED"):
        pass


class Terminate(CommonPlan):
    """this is the class that is called for the initial activation of the
    ServiceProvisioner.
    """

    def process(self):
        time.sleep(self.properties["wait_time"])
        try:
            self.bpo.relationships.delete_relationships(self.properties["resource_id"])
            self.bpo.resources.delete(self.properties["resource_id"])
        except Exception as ex:
            self.logger.exception(ex)

    def enter_exit_log(self, message, state="STARTED"):
        pass
