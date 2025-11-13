import unittest
import unittest.mock as mock
import sys
sys.path.append('model-definitions')
from scripts.networkservice.updateobservedproperty import Activate
from scripts.common_plan import CommonPlan


class test_update_observed_property(unittest.TestCase):
    def setUp(self):
        self._post = mock.patch("requests.post")
        self.post = self._post.start()
        self.post.return_value = mock.Mock(
            status_code=201, headers={"X-Subject-Token": "t1"}, json=mock.Mock(return_value={})
        )
        self.params = {
            "domain": "master",
            "uri": "http://x.y.z",
            "username": "user1",
            "password": "pass1",
            "logFile": "/home/vagrant/charter/model-definitions/logs/abc.log",
            "resourceId": "12345",
            "traceId": "123456",
            "bpUserId": "8dc1fea2-e3d2-4c80-84ec-a6d874560368",
        }

    def test_update_observed(self):
        """
        test case - updateobservedproperty Activate
         unit test for the template updateobserved property
        """
        inst = Activate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "id": "5aaf5acb-a2a0-4afc-9ff0-bbf52f8a7686",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"resource_id": "5a7b5782-aace-4170-9e5b-c9a3b5f3b720", "properties": "TEST"},
            }
        }
        r = {
            "label": resources[self.params["resourceId"]]["label"] + ".term",
            "productId": "1234",
            "properties": {"wait_time": 10, "resource_id": resources[self.params["resourceId"]]["id"]},
        }

        # function to return values to bpo.resources.get
        def set_effect(args):
            return resources[args]

        # mocking the functions called in template
        inst.bpo.resources.get = mock.Mock(side_effect=set_effect)
        inst.enter_exit_log = mock.Mock()
        inst.patch_observed = mock.Mock()
        inst.bpo.market.get_products_by_resource_type = mock.MagicMock(return_value=[{"id": "1234"}])
        inst.bpo.resources.create = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()

        # calling the run function
        resp = inst.run()

        # making assertions and verifying all calls were made correctly
        self.assertIsNone(resp)
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])
        inst.patch_observed.assert_called_with(
            resources[self.params["resourceId"]]["properties"]["resource_id"],
            {"properties": resources[self.params["resourceId"]]["properties"]["properties"]},
        )
        inst.bpo.market.get_products_by_resource_type.assert_called_with("tosca.resourceTypes.ResourceTerminator")
        inst.bpo.resources.create.assert_called_with(resources[self.params["resourceId"]]["id"], r, wait_active=False)


if __name__ == "__main__":
    unittest.main()
