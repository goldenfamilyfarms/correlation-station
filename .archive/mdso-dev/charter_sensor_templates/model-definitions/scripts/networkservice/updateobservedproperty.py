""" -*- coding: utf-8 -*-

UpdateObservedProperty Plans

Versions:
   0.1 Jan 03, 2018
       Initial check in of UpdateObservedProperty plans

"""
import sys
sys.path.append('model-definitions')
from scripts.complete_and_terminate_plan import CompleteAndTerminatePlan


class Activate(CompleteAndTerminatePlan):
    """this is the class that is called for the initial activation of the
    ServiceProvisioner.
    """

    def process(self):
        resource_id = self.properties["resource_id"]
        properties = self.properties["properties"]

        self.patch_observed(resource_id, {"properties": properties})

    def enter_exit_log(self, message, state="STARTED"):
        """OVERWRITING THE TRACELOGS SO THEY DO NOT GET CREATED
        FOR THIS RESOURCE.
        """
        pass
