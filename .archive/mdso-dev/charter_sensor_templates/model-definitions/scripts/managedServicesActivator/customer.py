import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan
import requests


class Activate(CommonPlan):
    def process(self):
        datastore = self.bpo.market.get(
            "/resources?resourceTypeId={}&p=label:{}&obfuscate=false&limit=1000".format(
                "charter.resourceTypes.datastore", "Datastore"
            )
        )
        url = datastore["items"][0]["properties"]["url"] + self.resource["properties"]["circuitId"] + ".json"
        default_properties = requests.get(url, verify=False).json()

        data = {"properties": {"customerProps": default_properties}}
        self.bpo.resources.patch_observed(self.resource["id"], data=data)


class Terminate(CommonPlan):
    def process(self):
        pass
