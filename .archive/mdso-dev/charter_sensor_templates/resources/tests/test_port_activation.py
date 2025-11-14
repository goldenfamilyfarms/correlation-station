import unittest
import unittest.mock as mock
import json
import sys
import pytest
import datetime
sys.path.append('model-definitions')
from scripts.portactivation.portactivation import Activate, GetPortStatus, SetPortStatus, Terminate
from mockfunctions import MockResponse
from scripts.common_plan import CommonPlan


class test_port_activation(unittest.TestCase):
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
            "operationId": "123",
        }

        current_time = datetime.datetime.now()
        delta_time = current_time + datetime.timedelta(minutes=-45)
        self.ttime = delta_time.isoformat()[:19]

    def test_activate(self):
        """
        test case - portActivation Activate
        test case to test the Activate function/functionality of portActivation.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "terminationTime": 30,
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe.json") as json_data:
            tpe_data = json.load(json_data)

        inst = Activate(self.params)
        # Mocking the required data
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_and_check_tpe = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.bpo.resources.create = mock.Mock()
        inst.logger = mock.Mock()
        inst.check_port_activation_resources = mock.Mock(return_value={"status": "Resource not exists"})

        inst.resync_network_function = mock.Mock()

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Ready to configure"}
        assert result == expected_result
        inst.get_built_in_product.assert_called_with("scheduler.resourceTypes.ResourceScheduler")

    def test_activate_resource_already_exists(self):
        """
        test case - portActivation Activate- test Activation resource already exists
        test case to test the Activate function/functionality of portActivation.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "terminationTime": 30,
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # with open("resources/tests/jsons/test_port_activation/tpe.json") as json_data:
            # tpe_data = json.load(json_data)

        inst = Activate(self.params)
        # Mocking the required data
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_and_check_tpe = mock.Mock()
        inst.logger = mock.Mock()
        inst.check_port_activation_resources = mock.Mock(
            return_value={
                "status": "Port Activation resource with resourceId 1234 is already available with device: AUSDTXIR2CW.one.twcbiz.com and port: ge-0/0/5"
            }
        )
        inst.bpo.resources.create = mock.Mock()

        resp = MockResponse(json_data=resources, status_code=200)
        resp = mock.MagicMock(name="resp.text", id="12345s")
        CommonPlan.mget = mock.Mock(return_value=resp)
        inst.execute_ra_command_file = mock.Mock(return_value=resp)

        # calling the run function
        result = inst.process()
        expected_result = {
            "status": "Port Activation resource with resourceId 1234 is already available with device: AUSDTXIR2CW.one.twcbiz.com and port: ge-0/0/5"}
        assert result == expected_result

    def test_activate_port_not_present(self):
        """
        test case - portActivation Activate- Port not present on the device
        test case to test the Activate function/functionality of portActivation.py
        """
        inst = Activate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "terminationTime": 30,
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # Mocking the required data
        tpe = {"status": "Port not present on the device"}
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe)
        inst.bpo.resources.create = mock.Mock()
        inst.logger = mock.Mock()
        inst.check_port_activation_resources = mock.Mock(return_value={"status": "Resource not exists"})

        inst.resync_network_function = mock.Mock()

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Port not present on the device"}
        assert result == expected_result

    def test_activate_device_not_present(self):
        """
        test case - portActivation Activate- Device not present
        test case to test the Activate function/functionality of portActivation.py
        """
        inst = Activate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "terminationTime": 30,
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe.json") as json_data:
            tpe_data = json.load(json_data)

        # Mocking the required data
        tpe = {"status": "Device not present"}
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe)
        inst.add = mock.Mock(
            return_value={"id": "5b7aa437-0302-4e61-accc-ce0d4c894aa9", "properties": {"device_ip": True}}
        )
        inst.await_resource_states = mock.Mock()
        inst.delete_resource = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.bpo.resources.create = mock.Mock()
        inst.logger = mock.Mock()
        inst.check_port_activation_resources = mock.Mock(return_value={"status": "Resource not exists"})
        inst.resync_network_function = mock.Mock()

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Ready to configure"}
        assert result == expected_result

    def test_get_port_status_negative(self):
        """
        test case - portActivation getPortStatus- negative senario
        test case to test the getPortStatus function/functionality of portActivation.py
        """
        inst = GetPortStatus(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "status": "Port not present",
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe.json") as json_data:
            tpe_data = json.load(json_data)

        # Mocking the required data
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.logger = mock.Mock()

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Resource not in Ready to configure state, hence operation can not be executed"}
        assert result == expected_result

    def test_set_port_status(self):
        """
        test case - portActivation setPortStatus
        test case to test the setPortStatus function/functionality of portActivation.py
        """
        inst = SetPortStatus(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "status": "Ready to configure",
                    "terminationTime": 0,
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe.json") as json_data:
            tpe_data = json.load(json_data)

        # Mocking the required data
        operation = {"inputs": {"reqdstate": "up"}}
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.logger = mock.Mock()
        inst.check_port_state = mock.Mock()
        inst.bpo.resources.get_operation = mock.Mock(return_value=operation)
        inst.bpo.resources.patch = mock.Mock()

        inst.description_standard_decision = mock.Mock()
        inst.get_network_function_by_host_or_ip = mock.Mock()

        resp = MockResponse(json_data=resources, status_code=200)
        resp = mock.MagicMock(name="resp.text", id="12345")
        CommonPlan.mget = mock.Mock(return_value=resp)
        inst.execute_ra_command_file = mock.Mock(return_value=resp)

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Successfully triggered patch operation for adminstate change"}
        assert result == expected_result

        # making assertions to make sure all calls were made correctly
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])

    def test_set_port_status_already_enabled(self):
        """
        test case - portActivation setPortStatus- Port state already enabled
        test to check if the port is already enabled or not.
        """
        inst = SetPortStatus(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "status": "Ready to configure",
                    "terminationTime": 0,
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe_up.json") as json_data:
            tpe_data = json.load(json_data)

        # with open("resources/tests/jsons/test_port_activation/get-interface.json") as json_data:
        #    interface = json.load(json_data)

        adstate = {"result": {"interface-information": {"physical-interface": {"admin-status": {"#text": "up"}}}}}

        # Mocking the required data
        operation = {"inputs": {"reqdstate": "up"}}
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.logger = mock.Mock()
        inst.bpo.resources.get_operation = mock.Mock(return_value=operation)
        inst.bpo.resources.patch = mock.Mock()

        # we do not care ab this rn
        inst.description_standard_decision = mock.Mock()
        inst.get_network_function_by_host_or_ip = mock.Mock()

        inst.get_admin_state = mock.Mock(return_value=adstate)
        inst.check_port_state = mock.Mock()

        resp = MockResponse(json_data=adstate, status_code=200)
        # adstate += mock.MagicMock(name="adminstate.text", id="12345")
        CommonPlan.mget = mock.Mock(return_value=resp)
        inst.execute_ra_command_file = mock.Mock(return_value=resp)

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Port already in enabled state"}
        assert result == expected_result
        # making assertions to make sure all calls were made correctly
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])

    def test_set_port_status_not_supported(self):
        """
        test case - portActivation setPortStatus- Operation not supported
        test case to check if the port was activated earlier through Port Activation resource
        """
        inst = SetPortStatus(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "status": "Ready to configure",
                    "terminationTime": 0,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe_up.json") as json_data:
            tpe_data = json.load(json_data)

        # Mocking the required data
        operation = {"inputs": {"reqdstate": "down"}}
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.logger = mock.Mock()
        inst.bpo.resources.get_operation = mock.Mock(return_value=operation)
        inst.bpo.resources.patch = mock.Mock()
        inst.check_port_state = mock.Mock()
        inst.bpo.resources.create = mock.Mock()

        inst.description_standard_decision = mock.Mock()

        resp = MockResponse(json_data=tpe_data, status_code=200)
        resp = mock.MagicMock(name="resp.text", id="12345s")
        CommonPlan.mget = mock.Mock(return_value=resp)
        inst.execute_ra_command_file = mock.Mock(return_value=resp)

        inst.get_network_function_by_host_or_ip = mock.Mock()

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Operation not supported, port was not activated through Port Activation resource"}
        assert result == (expected_result)

    @pytest.mark.skip
    def test_terminate(self):
        """
        test case - portActivation terminate
        test case to check if the port was activated earlier through Port Activation resource and adminSteta is up,
        then disable the port
        """
        inst = Terminate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "status": "Ready to configure",
                    "terminationTime": 30,
                    "wasPortActivated": True,
                    "deactivate_eligible": True,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe_up.json") as json_data:
            tpe_data = json.load(json_data)

        # Mocking the required data
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.logger = mock.Mock()
        inst.bpo.resources.patch = mock.Mock()
        inst.check_port_state = mock.Mock()

        # calling the run function
        inst.resync_network_function = mock.Mock()
        inst.get_network_function_by_host_or_ip = mock.Mock()

        result = inst.process()
        expected_result = {"status": "Successfully triggered patch operation for port status"}
        assert result == expected_result

    def test_terminate_negative(self):
        """
        test case - portActivation terminate - wasPortActivated False
        test case to check if the port was activated earlier through Port Activation resource and adminSteta is up,
        then disable the port
        """
        inst = Terminate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "status": "Ready to configure",
                    "terminationTime": 30,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        with open("resources/tests/jsons/test_port_activation/tpe_up.json") as json_data:
            tpe_data = json.load(json_data)

        # Mocking the required data
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.logger = mock.Mock()
        inst.check_port_state = mock.Mock()
        inst.resync_network_function = mock.Mock()
        inst.get_network_function_by_host_or_ip = mock.Mock()

        # calling the run function
        result = inst.process()
        assert result is None

    def test_terminate_port_not_present(self):
        """
        test case - portActivation terminate- port not present
        test case to check if the port was activated earlier through Port Activation resource and adminSteta is up,
        then disable the port
        """
        inst = Terminate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "properties": {
                    "portname": "ge-0/0/5",
                    "deviceName": "AUSDTXIR2CW.one.twcbiz.com",
                    "vendor": "juniper",
                    "status": "Ready to configure",
                    "terminationTime": 30,
                },
                "resourceTypeId": "charter.resourceTypes.PortActivation",
                "tenantId": "568de260-1a59-4107-adcf-6f4f9f78c240",
                "label": "demo",
                "id": "5b7e5dc4-d23a-4985-a5f7-6de496bae1ef",
                "productId": "5b7aa961-d539-4a23-b1ca-29bfc81d2549",
                "createdAt": self.ttime,
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # Mocking the required data
        tpe_data = {"status": "Port not present"}
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_tpe_by_name_and_host_return_errors = mock.Mock(return_value=tpe_data)
        inst.logger = mock.Mock()
        inst.check_port_state = mock.Mock()
        inst.resync_network_function = mock.Mock()
        inst.get_network_function_by_host_or_ip = mock.Mock()

        # calling the run function
        result = inst.process()
        expected_result = {"status": "Port not present on the device - PA Terminate"}
        assert result == expected_result


if __name__ == "__main__":
    unittest.main()
