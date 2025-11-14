import unittest
import unittest.mock as mock
import json
import sys
sys.path.append('model-definitions')
from scripts.networkservice.businesslogic import BusinessLogic
from scripts.common_plan import CommonPlan
import mockfunctions


class test_bussiness_logic(unittest.TestCase):
    def setUp(self):
        self._post = mock.patch("requests.post")
        self.post = self._post.start()
        self.post.return_value = mock.Mock(
            status_code=201, headers={"X-Subject-Token": "t1"}, json=mock.Mock(return_value={})
        )
        params = {
            "domain": "master",
            "uri": "http://x.y.z",
            "username": "user1",
            "password": "pass1",
            "logFile": "/home/vagrant/charter_bit/charter_sensor_templates/resources/tests/logs/abc.log",
            "resourceId": "12345",
            "traceId": "123456",
            "bpUserId": "8dc1fea2-e3d2-4c80-84ec-a6d874560368",
        }
        self.common_plan_inst = CommonPlan(params)

    def test_convert_variable_names(self):
        """
        test case - Businesslogic convert_variable_names
        test case to test the convert_variable_names function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_convert_variable_names.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_convert_variable_names.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        self.common_plan_inst = mock.Mock()

        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)

        result = self.business_logic_inst.convert_variable_names(mulesoft_response)
        self.assertEqual(expected_output, result)

    def test_handle_fia_section(self):
        """
        test case - Businesslogic handle_fia_section
        test case to test the test_handle_fia_section function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_handle_fia_section.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_handle_fia_section.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        self.common_plan_inst.logger = mock.Mock()
        self.common_plan_inst.enter_exit_log = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()
        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)

        result = self.business_logic_inst.handle_fia_section(mulesoft_response)
        assert expected_output == result

    def test_remove_empty_lag_members(self):
        """
        test case - Businesslogic remove_empty_lag_members
        test case to test the remove_empty_lag_members function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_remove_empty_lag_members.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_remove_empty_lag_members.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        self.common_plan_inst.logger = mock.Mock()
        self.common_plan_inst.enter_exit_log = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()
        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)

        result = self.business_logic_inst.remove_empty_lag_members(mulesoft_response)
        self.assertEqual(expected_output, result)

    def test_apply_descriptions_to_interfaces(self):
        """
        test case - Businesslogic apply_descriptions_to_interfaces
        test case to test the apply_descriptions_to_interfaces function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_apply_desc_to_interfaces.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_apply_desc_to_interfaces.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)

        self.common_plan_inst.logger = mock.Mock()
        self.common_plan_inst.enter_exit_log = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()
        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)
        resp = mockfunctions.MockResponse(json_data={}, status_code=301)
        CommonPlan.mget = mock.Mock(return_value=resp)
        result = self.business_logic_inst.apply_descriptions_to_interfaces(mulesoft_response)
        assert expected_output == result

    def test_apply_descriptions_to_service_endpoints(self):
        """
        test case - Businesslogic apply_descriptions_to_service_endpoints
        test case to test the apply_descriptions_to_service_endpoints function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_apply_desc_to_service_endpoints.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_apply_desc_to_service_endpoints.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)

        self.common_plan_inst.logger = mock.Mock()
        self.common_plan_inst.enter_exit_log = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()
        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)
        values = ["CNI2TXR26AW.DEV.CHTRSE.COM"]
        CommonPlan.get_pe_nodes_from_circuit_details = mock.Mock(return_value=values)
        result = self.business_logic_inst.apply_descriptions_to_service_endpoints(mulesoft_response)
        assert expected_output == result

    def test_convert_rad_port_name(self):
        """
        test case - Businesslogic convert_rad_port_name
        test case to test the convert_rad_port_name function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_convert_rad_port_name.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_convert_rad_port_name.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)

        self.common_plan_inst.logger = mock.Mock()
        self.common_plan_inst.enter_exit_log = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()
        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)

        result = self.business_logic_inst.convert_rad_port_name(mulesoft_response)
        self.assertEqual(expected_output, result)

    def test_replace_ports_with_lags_service_endpoints(self):
        """
        test case - Businesslogic replace_ports_with_lags_service_endpoints
        test case to test the replace_ports_with_lags_service_endpoints function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_convert_rad_port_name.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_convert_rad_port_name.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)

        self.common_plan_inst.logger = mock.Mock()
        self.common_plan_inst.enter_exit_log = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()
        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)

        result = self.business_logic_inst.convert_rad_port_name(mulesoft_response)
        self.assertEqual(expected_output, result)

    def test_add_connection_type_to_name(self):
        """
        test case - Businesslogic add_connection_type_to_name
        test case to test the add_connection_type_to_name function/functionality of bussinesslogic.py
        """
        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC", "stage": "TEST"},
            }
        }

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # reading required input from files
        # for this test modules json files are present under the path tests/json/test_cdc

        with open("resources/tests/jsons/test_business_logic/input_add_connection_type_to_name.json") as json_data:
            mulesoft_response = json.load(json_data)
        with open("resources/tests/jsons/test_business_logic/output_add_connection_type_to_name.json") as json_data:
            expected_output = json.load(json_data)

        # Mocking the required data
        self.common_plan_inst.bpo.resources.get = mock.Mock(side_effect=resources_get)

        self.common_plan_inst.logger = mock.Mock()
        self.common_plan_inst.enter_exit_log = mock.Mock()
        CommonPlan.splunk_logger_setup = mock.Mock()
        self.common_plan_inst.run()
        self.business_logic_inst = BusinessLogic(self.common_plan_inst)

        result = self.business_logic_inst.add_connection_type_to_name(mulesoft_response)
        self.assertEqual(expected_output, result)


if __name__ == "__main__":
    unittest.main()
