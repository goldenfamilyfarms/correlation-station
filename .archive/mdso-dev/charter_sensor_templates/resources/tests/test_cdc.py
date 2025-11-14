import unittest
import unittest.mock as mock
import json
import requests
from collections import namedtuple
import sys
sys.path.append('model-definitions')
from mockfunctions import MockResponse
from scripts.networkservice.circuitdetailscollector import Activate
from scripts.common_plan import CommonPlan


class test_circuit_data_collector(unittest.TestCase):
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

    @unittest.skip("need to fix ERROR")
    def test_cdc_eline(self):
        """
        test case - circuitdatacollector Activate(Eline)
        test case to unit test activate functionality of the circuit details collector module.
        This test case covers the positive use case where the arda resposne corrosponds to
        and eline service and parent resource is present
        """
        inst = Activate(self.params)

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
        # reading required responses from files
        # for this test modules json files are present under the path tests/json/test_cdc
        with open("resources/tests/jsons/test_cdc/arda_eline.json") as json_data:
            arda_response = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/eline_circuit_details_resource.json") as resource_json:
            my_resource = eval(resource_json.read())
        with open("resources/tests/jsons/test_cdc/eline_circuit_details.json") as details_json:
            my_circuit_details = eval(details_json.read())

        # setting up the resource tuple to returned as would be returned by plansdk function
        ResourceInfo = namedtuple("ResourceInfo", ["resource", "resource_id", "provider_resource_id"])
        return_tuple = ResourceInfo(my_resource, "1234567", None)

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_arda_response = mock.Mock(return_value=arda_response)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_associated_network_service_for_resource = mock.Mock(return_value={"id": "4567"})
        inst.bpo.resources.create = mock.Mock(return_value=return_tuple)
        inst.patch_observed = mock.Mock()

        # calling the run function
        result = inst.run()
        expected_result = {"circuit_details_id": my_resource["id"]}
        self.assertEqual(result, json.dumps(expected_result))

        # making assertions to make sure all calls were made correctly
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])
        inst.get_built_in_product.assert_called_with("charter.resourceTypes.CircuitDetails")
        inst.get_associated_network_service_for_resource.assert_called_with(self.params["resourceId"])
        inst.bpo.resources.create.assert_called_with("4567", my_circuit_details, wait_time=120)

    @unittest.skip("need to fix ERROR")
    def test_cdc_eline_without_parent(self):
        """
        test case - circuitdatacollector Activate(Eline) without parent
        test case to unit test activate functionality of the circuit details collector module.
        This test case covers the positive use case where the arda resposne corrosponds to
        and eline service and parent resource is ABSENT
        """
        inst = Activate(self.params)

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
        # reading required responses from files
        # for this test modules json files are present under the path tests/json/test_cdc
        with open("resources/tests/jsons/test_cdc/arda_eline.json") as json_data:
            arda_response = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/eline_circuit_details_resource.json") as resource_json:
            my_resource = eval(resource_json.read())
        with open("resources/tests/jsons/test_cdc/eline_circuit_details.json") as details_json:
            my_circuit_details = eval(details_json.read())

        # setting up the resource tuple to returned as would be returned by plansdk function
        ResourceInfo = namedtuple("ResourceInfo", ["resource", "resource_id", "provider_resource_id"])
        return_tuple = ResourceInfo(my_resource, "1234567", None)

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_arda_response = mock.Mock(return_value=arda_response)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_associated_network_service_for_resource = mock.Mock(return_value=None)
        inst.bpo.resources.create = mock.Mock(return_value=return_tuple)
        inst.patch_observed = mock.Mock()

        # calling the run function
        result = inst.run()
        expected_result = {"circuit_details_id": my_resource["id"]}
        self.assertEqual(result, json.dumps(expected_result))

        # making assertions to make sure all calls were made correctly
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])
        inst.get_built_in_product.assert_called_with("charter.resourceTypes.CircuitDetails")
        inst.get_associated_network_service_for_resource.assert_called_with(self.params["resourceId"])
        inst.bpo.resources.create.assert_called_with("12345", my_circuit_details, wait_time=120)
        inst.patch_observed.assert_not_called()

    @unittest.skip("errors")
    def test_cdc_fia_only_PE(self):
        """
        test case - circuitdatacollector Activate(FIA-Only PE)
        test case to unit test activate functionality of the circuit details collector module.
        This test case covers the positive use case where the arda resposne corrosponds to
        and fia service and parent resource is present
        """
        inst = Activate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.009158..TWCC",
                               "operation": "NETWORK_SERVICE_ACTIVATION",
                               "use_alternate_circuit_details_server": False,
                               "stage": "TEST",
                               "network_service_resource_id": "4567"},
            }
        }

        # reading required responses from files
        # for this test modules json files are present under the path tests/json/test_cdc
        with open("resources/tests/jsons/test_cdc/bpo_constants.json") as json_data:
            bpo_constants = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/arda_fia_only_pe.json") as json_data:
            arda_response = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/fia_only_pe_resource.json") as resource_json:
            my_resource = eval(resource_json.read())
        with open("resources/tests/jsons/test_cdc/fia_only_pe_circuit_details.json") as details_json:
            my_circuit_details = eval(details_json.read())

        created_cd = my_circuit_details
        created_cd["id"] = "5b4488bc-a621-45ae-8dbb-974047414f37"

        # setting up the resource tuple to returned as would be returned by plansdk function
        ResourceInfo = namedtuple("ResourceInfo", ["resource", "resource_id", "provider_resource_id"])
        return_tuple = ResourceInfo(my_resource, "1234567", None)

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.get_bpo_contants_resource = mock.Mock(return_value=bpo_constants)
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_circuit_details_server_response = mock.Mock(return_value=arda_response)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_associated_network_service_for_resource = mock.Mock(return_value={"id": "4567"})
        inst.bpo.resources.create = mock.Mock(return_value=return_tuple)
        inst.patch_observed = mock.Mock()

        CommonPlan.splunk_logger_setup = mock.Mock()
        # calling the run function
        inst.update_circuit_details_with_neighbor_info = mock.Mock(return_value=my_circuit_details['topology'])
        resp = MockResponse(json_data=my_circuit_details, status_code=200)
        CommonPlan.mget = mock.Mock(return_value=resp)

        result = inst.run()
        expected_result = {"circuit_details_id": my_resource["id"]}
        assert result == expected_result
        # making assertions to make sure all calls were made correctly
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])
        inst.get_built_in_product.assert_called_with("charter.resourceTypes.CircuitDetails")
        inst.get_associated_network_service_for_resource.assert_called_with(self.params["resourceId"])
        inst.bpo.resources.create.assert_called_with("4567", my_circuit_details, wait_active=False)

    @unittest.skip("need to fix ERROR")
    def test_cdc_fia_PE_AGG(self):
        """
        test case - circuitdatacollector Activate(FIA- PE & AGG )
        test case to unit test activate functionality of the circuit details collector module.
        This test case covers the positive use case where the arda resposne corrosponds to
        and fia service and parent resource is present
        """
        inst = Activate(self.params)

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
        # reading required responses from files
        # for this test modules json files are present under the path tests/json/test_cdc
        with open("resources/tests/jsons/test_cdc/bpo_constants.json") as json_data:
            bpo_constants = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/arda_fia_pe_agg.json") as json_data:
            arda_response = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/fia_pe_agg_resource.json") as resource_json:
            my_resource = eval(resource_json.read())
        # with open("resources/tests/jsons/test_cdc/fia_pe_agg_circuit_details.json") as details_json:
            # my_circuit_details = eval(details_json.read())

        # setting up the resource tuple to returned as would be returned by plansdk function
        ResourceInfo = namedtuple("ResourceInfo", ["resource", "resource_id", "provider_resource_id"])
        return_tuple = ResourceInfo(my_resource, "1234567", None)

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.get_bpo_contants_resource = mock.Mock(return_value=bpo_constants)
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_circuit_details_server_response = mock.Mock(return_value=arda_response)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_associated_network_service_for_resource = mock.Mock(return_value={"id": "4567"})
        inst.bpo.resources.create = mock.Mock(return_value=return_tuple)
        inst.patch_observed = mock.Mock()

        # calling the run function
        result = inst.run()
        expected_result = {"circuit_details_id": my_resource["id"]}
        self.assertEqual(result, json.dumps(expected_result))

        # making assertions to make sure all calls were made correctly
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])
        inst.get_built_in_product.assert_called_with("charter.resourceTypes.CircuitDetails")
        inst.get_associated_network_service_for_resource.assert_called_with(self.params["resourceId"])
        inst.bpo.resources.create.assert_called_with("4567", my_resource, wait_time=120)

    @unittest.skip("need to fix ERROR")
    def test_cdc_fia_complete(self):
        """
        test case - circuitdatacollector Activate(FIA- complete circuit)
        test case to unit test activate functionality of the circuit details collector module.
        This test case covers the positive use case where the arda resposne corrosponds to
        and fia service and parent resource is present
        """
        inst = Activate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_cdc",
                "resourceTypeId": "charter.resourceTypes.CircuitDetailsCollector",
                "productId": "5a7b5782-aace-4170-9e5b-c9a3b5f3b718",
                "properties": {"circuit_id": "51.L1XX.008488..TWCC", "stage": "TEST"},
            }
        }
        # reading required responses from files
        # for this test modules json files are present under the path tests/json/test_cdc
        with open("resources/tests/jsons/test_cdc/bpo_constants.json") as json_data:
            bpo_constants = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/arda_fia_complete.json") as json_data:
            arda_response = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/fia_complete_resource.json") as resource_json:
            my_resource = eval(resource_json.read())
        with open("resources/tests/jsons/test_cdc/fia_complete_circuit_details.json") as details_json:
            my_circuit_details = eval(details_json.read())

        # setting up the resource tuple to returned as would be returned by plansdk function
        ResourceInfo = namedtuple("ResourceInfo", ["resource", "resource_id", "provider_resource_id"])
        return_tuple = ResourceInfo(my_resource, "1234567", None)

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.get_bpo_contants_resource = mock.Mock(return_value=bpo_constants)
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.get_circuit_details_server_response = mock.Mock(return_value=arda_response)
        inst.get_built_in_product = mock.Mock(return_value={"id": "12345"})
        inst.enter_exit_log = mock.Mock()
        inst.get_associated_network_service_for_resource = mock.Mock(return_value={"id": "4567"})
        inst.bpo.resources.create = mock.Mock(return_value=return_tuple)
        inst.patch_observed = mock.Mock()

        # calling the run function
        result = inst.run()
        expected_result = {"circuit_details_id": my_resource["id"]}
        self.assertEqual(result, json.dumps(expected_result))

        # making assertions to make sure all calls were made correctly
        inst.bpo.resources.get.assert_called_with(self.params["resourceId"])
        inst.get_built_in_product.assert_called_with("charter.resourceTypes.CircuitDetails")
        inst.get_associated_network_service_for_resource.assert_called_with(self.params["resourceId"])
        inst.bpo.resources.create.assert_called_with("4567", my_circuit_details, wait_time=120)

    def test_get_circuit_details_server_response_negative(self):
        """
        test case - Circuit Data Collector "get_circuit_details_server_response_negative"
        unit test case to verify system exit call when
        bpo constant resource is not present
        """
        # creating an instance of Activate class
        inst = Activate(self.params)

        # mocking the required functions
        inst.get_bpo_contants_resource = mock.Mock(return_value=None)
        inst.logger = mock.Mock()
        inst.enter_exit_log = mock.Mock()

        self._write = mock.patch("sys.stderr")
        self.write = self._write.start()

        # defining dummy variables required for the function to run stand alone
        inst.the_class = "abc"
        inst.log_file = "abcd"

        # result = inst.get_arda_response()

        # verifying system exit is called with correct code
        with self.assertRaises(SystemExit) as cm:
            inst.get_circuit_details_server_response()
            self.write.assert_has_calls(
                ["Error in abc, ERROR: No active BPO Constants available..  Please check file: abcdok"]
            )
        self.assertEqual(cm.exception.code, 1)

    def test_get_circuit_details_server_response_positive(self):
        """
        test case - Circuit Data Collector "get_circuit_details_server_response_positive"
        unit test case to verify the method
        get_circuit_details_server_response
        """
        # creating an instance of Activate class
        inst = Activate(self.params)

        # generating dummy response for requests.get
        Req_res = namedtuple("Req_res", ["status_code", "text", "json"])

        # getting arda response from dummy database
        with open("resources/tests/jsons/test_cdc/bpo_constants.json") as json_data:
            bpo_constants = json.load(json_data)
        with open("resources/tests/jsons/test_cdc/arda_eline.json") as json_data:
            arda_response = json.load(json_data)
            arda_response = json.dumps(arda_response)

        req_return = Req_res(200, arda_response, "abc")

        # mocking the required functions
        inst.get_bpo_contants_resource = mock.Mock(return_value=bpo_constants)
        requests.get = mock.Mock(return_value=req_return)
        inst.logger = mock.Mock()

        # setting up dummy variables required to execute function
        inst.circuit_id = "51.L1XX.009158..TWCC.cd"
        inst.stage = "TEST"
        # calling the test function
        inst.use_alternate_url = False

        res = inst.get_circuit_details_server_response()

        # making assertions
        self.assertEqual(res, json.loads(arda_response))
        requests.get.assert_called_with(
            "https://97.105.228.217/orchestrate/sahil2.json", verify=False, headers={"Accept": "application/json"}
        )


if __name__ == "__main__":
    unittest.main()
