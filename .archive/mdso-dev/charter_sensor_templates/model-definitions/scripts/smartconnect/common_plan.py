import os

import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class SmartConnectCommon(CommonPlan):
    """Data, variables, methods needed for Smart Connect modules"""

    def get_file_path(self, dir, vendor):
        return os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "smartconnect/{}/{}".format(dir, vendor.lower()),
            )
        )
