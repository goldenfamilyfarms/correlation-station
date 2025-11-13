""" -*- coding: utf-8 -*-

SEEFA Connectivity Check

Versions:
   0.1 May 27, 2022
       Initial check in of SEEFA Connectivity Check plans

"""
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
from scripts.smartconnect.connection import Connection
from scripts.smartconnect.mdso_internal_utils import MDSOInternalSmartConnect


class Activate(CommonPlan):
    """
    Use Smart Connect to connect to device to determine reachability
    Update resource properties with reachable status bool
    """

    def process(self):
        self.properties = self.resource["properties"]
        self.vendor = self.properties["vendor"]
        self.host_id = self.properties["host_id"]
        mdso_internal = MDSOInternalSmartConnect(self)
        self.connection_type = mdso_internal.get_connection_type(self.vendor)
        try:
            self.logger.info(f"Attempting to log into device: {self.host_id}")
            self.connection = Connection(
                plan=self,
                host_id=self.host_id,
                vendor=self.vendor,
                credentials=mdso_internal.get_credentials(self.vendor, self.connection_type),
            )
            self.logger.info(f"Logged in: {self.connection.is_connected}")
            self.bpo.resources.patch_observed(
                self.resource["id"],
                data={
                    "properties": {
                        "reachable": self.connection.is_connected,
                    }
                },
            )
        finally:
            try:
                self.logger.info("Closing connection")
                self.connection.close()
            except Exception:
                pass


class Terminate(CommonPlan):
    def process(self):
        pass
