import unittest
import unittest.mock as mock
import json
import sys
sys.path.append('model-definitions')
from scripts.networkservice.networkservicecheck import Activate


class test_network_service_check(unittest.TestCase):
    """
    test suite containing unit tests for the module
    networkservicecheck.py2
    """

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
            "logFile": "/home/vagrant/charter_bit/charter_sensor_templates/resources/tests/logs/abc.log",
            "resourceId": "12345",
            "traceId": "123456",
            "bpUserId": "8dc1fea2-e3d2-4c80-84ec-a6d874560368",
        }

    def test_nsc_network_service_absent(self):
        """
        test case - NetworkServiceCheck network service Absent
        test case to raise and catch exception when network service
        is absent
        """
        inst = Activate(self.params)

        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_nsc",
                "resourceTypeId": "charter.resourceTypes.NetworkServiceCheck",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b781",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "provisioning_stage": "PRE", "resource_id": "1234567"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_associated_network_service_for_circuit_id = mock.Mock(return_value=None)
        inst.get_associated_network_service = mock.Mock(return_value=None)
        inst.enter_exit_log = mock.Mock()
        inst.logger = mock.Mock()

        self._write = mock.patch("sys.stderr")
        self.write = self._write.start()

        # making assertion that the correct exceotion is raised
        with self.assertRaises(SystemExit) as cm:
            inst.run()
        self.write.assert_has_calls(
            [
                mock.call.write(
                    "Error in scripts.networkservice.networkservicecheck.Activate, Error: Unable to get Network Service for 51.L1XX.009158..TWCC.  Please check file: abc.log"
                )
            ]
        )
        self.assertEqual(cm.exception.code, 1)

    def test_nsc_network_service_active(self):
        """
        test case - NetworkServiceCheck network service Already active
        test case to raise and catch exception when network service
        is absent
        """
        inst = Activate(self.params)

        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_nsc",
                "resourceTypeId": "charter.resourceTypes.NetworkServiceCheck",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b781",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "provisioning_stage": "PRE", "resource_id": "12345"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_associated_network_service_for_circuit_id = mock.Mock(
            return_value=[{"orchState": "active", "desiredOrchState": "active", "id": "6789"}]
        )
        inst.get_associated_network_service = mock.Mock(return_value=None)
        inst.enter_exit_log = mock.Mock()
        inst.logger = mock.Mock()

        self._write = mock.patch("sys.stderr")
        self.write = self._write.start()

        # making assertion that the correct exceotion is raised
        with self.assertRaises(SystemExit) as cm:
            inst.run()
        self.write.assert_has_calls(
            [
                mock.call.write(
                    "Error in scripts.networkservice.networkservicecheck.Activate, Error: Network Service already provision for circuit id: 51.L1XX.009158..TWCC, id: 6789.  Please check file: abc.log"
                )
            ]
        )
        self.assertEqual(cm.exception.code, 1)

    def test_nsc_circuit_id_missing(self):
        """
        test case - NetworkServiceCheck circuit id not present
        test case to raise and catch exception when network service
        is absent
        """
        inst = Activate(self.params)

        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_nsc",
                "resourceTypeId": "charter.resourceTypes.NetworkServiceCheck",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b781",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "provisioning_stage": "PRE", "resource_id": "12345"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_associated_network_service_for_circuit_id = mock.Mock(
            return_value=[
                {
                    "orchState": "activating",
                    "desiredOrchState": "active",
                    "id": "6789",
                    "properties": {"stage": "PRODUCTION"},
                }
            ]
        )
        inst.get_associated_circuit_details = mock.Mock(return_value=None)
        inst.get_associated_network_service = mock.Mock(return_value=None)
        inst.enter_exit_log = mock.Mock()
        # inst.logger = mock.Mock()

        self._logger = mock.patch("logging.getLogger")
        self.logger = self._logger.start()
        self._write = mock.patch("sys.stderr")
        self.write = self._write.start()
        self._sleep = mock.patch("time.sleep")
        self.sleep = self._sleep.start()
        # inst.run()
        # making assertion that the correct exceotion is raised
        with self.assertRaises(SystemExit) as cm:
            # inst.logger = mock.Mock()
            inst.run()
        self.write.assert_has_calls(
            [
                mock.call.write(
                    "Error in scripts.networkservice.networkservicecheck.Activate, Error: No circuit details found for id: 51.L1XX.009158..TWCC.  Please check file: abc.log"
                )
            ]
        )
        self.assertEqual(cm.exception.code, 1)

    @unittest.skip("is stupid")
    def test_nsc_mef_service_already_present(self):
        """
        test case - NetworkServiceCheck mef service already present
        test case to see exit_error is called when mef service
        is already present
        """
        inst = Activate(self.params)

        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_nsc",
                "resourceTypeId": "charter.resourceTypes.NetworkServiceCheck",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b781",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "provisioning_stage": "PRE", "resource_id": "12345"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_associated_network_service_for_circuit_id = mock.Mock(
            return_value=[
                {
                    "orchState": "activating",
                    "desiredOrchState": "active",
                    "id": "6789",
                    "properties": {"stage": "PRODUCTION", "resource_id": "12345"},
                }
            ]
        )

        with open("resources/tests/jsons/test_ns/really_good.json") as dep_res:
            circuitdetailz = eval(dep_res.read())

        # inst.get_dependencies = mock.Mock(return_value=dependencies)

        inst.get_resource_by_type_and_properties = mock.Mock(return_value={"id": "1010"})

        inst.get_associated_circuit_details_for_network_service = mock.Mock(return_value=circuitdetailz)

        inst.enter_exit_log = mock.Mock()
        inst.logger = mock.Mock()

        self._write = mock.patch("sys.stderr")
        self.write = self._write.start()

        # making assertion that the correct exceotion is raised
        with self.assertRaises(SystemExit) as cm:
            inst.run()
        self.write.assert_has_calls(
            [
                mock.call.write(
                    "Error in scripts.networkservice.networkservicecheck.Activate, MEF Service 1010 already exists with Circuit Name 51.L1XX.009158..TWCC.  Please check file: abc.log"
                )
            ]
        )
        self.assertEqual(cm.exception.code, 1)

    def test_nsc_positive_case_pre_stage(self):
        """
        test case - NetworkServiceCheck postive case for pre stage
        test case to run positive case when stage is "PRE"
        """
        inst = Activate(self.params)

        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_nsc",
                "resourceTypeId": "charter.resourceTypes.NetworkServiceCheck",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b781",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "provisioning_stage": "PRE"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_associated_network_service_for_circuit_id = mock.Mock(
            return_value=[
                {
                    "orchState": "activating",
                    "desiredOrchState": "active",
                    "id": "6789",
                    "properties": {"stage": "PRODUCTION"},
                }
            ]
        )
        inst.get_associated_circuit_details = mock.Mock(return_value={"properties": {"vc_id": "1122"}})
        inst.get_resource_by_type_and_properties = mock.Mock(return_value=None)
        inst.enter_exit_log = mock.Mock()
        inst.process = mock.Mock()
        inst.logger = mock.Mock()
        inst.bpo.market.get_products_by_resource_type = mock.Mock(return_value=[{"id": "1234"}])
        inst.bpo.resources.create = mock.Mock()

        # instantiating and making assertions
        inst.run()
        inst.bpo.market.get_products_by_resource_type.assert_called_with("tosca.resourceTypes.ResourceTerminator")

    def test_nsc_positive_case_post_stage(self):
        """
        test case - NetworkServiceCheck postive case for post stage
        test case to run positive case when stage is "PRE"
        """
        inst = Activate(self.params)

        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_nsc",
                "resourceTypeId": "charter.resourceTypes.NetworkServiceCheck",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b781",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "provisioning_stage": "POST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        network_service_res = {
            "label": "ns_unittest",
            "orchState": "activating",
            "desiredOrchState": "active",
            "id": "6789",
            "properties": {"stage": "PRODUCTION", "circuit_id": "51.L1XX.009158..TWCC"},
        }
        with open("resources/tests/jsons/test_networkservice/circuit_details.json") as resource_json:
            my_resource = json.load(resource_json)

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_associated_network_service_for_circuit_id = mock.Mock(return_value=[network_service_res])
        inst.get_associated_circuit_details = mock.Mock(return_value=my_resource)
        inst.get_resource_by_type_and_properties = mock.Mock(return_value=None)
        inst.get_dependencies = mock.Mock(return_value=[])
        inst.enter_exit_log = mock.Mock()
        inst.process = mock.Mock()
        # inst.logger = mock.Mock()
        inst.bpo.market.get_products_by_resource_type = mock.Mock(return_value=[{"id": "1234"}])
        inst.bpo.resources.create = mock.Mock()
        inst.get_associated_network_service = mock.Mock(return_value=[{"id": "1234"}])

        # instantiating and making assertions
        inst.run()
        inst.bpo.market.get_products_by_resource_type.assert_called_with("tosca.resourceTypes.ResourceTerminator")


if __name__ == "__main__":
    unittest.main()
