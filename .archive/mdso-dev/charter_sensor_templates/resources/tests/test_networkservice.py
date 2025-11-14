""" -*- coding: utf-8 -*-

CommonPlan Plans

Versions:
   0.1 Apr 06, 2018
       Initial check in of test suite for networkservice.py

"""

import unittest
import unittest.mock as mock
import sys
sys.path.append('model-definitions')
from scripts.networkservice.networkservice import Terminate, Update, ActivateSite, Suspend, Resume
from scripts.common_plan import CommonPlan


class test_networkservice(unittest.TestCase):

    """
    test suite containing unit tests for the
    module networkservice.py
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

    def test_terminate(self):
        """
        test case - networkservice terminate
        test case to test Terminate Class
        """

        inst = Terminate(self.params)

        # setting up the database for test case
        resources = {
            "12345": {
                "id": "12345",
                "label": "unit_test_ns",
            }
        }

        with open("resources/tests/jsons/test_ns/dependencies.json") as dep_res:
            dependencies = eval(dep_res.read())

        def resources_get(args):
            """
            function to return values to get calls made during
            the execution of run function
            """
            return resources[args]

        # mocking required functions in the template
        inst.bpo.resources.get = mock.Mock(side_effect=resources_get)
        inst.enter_exit_log = mock.Mock()
        inst.bpo.resources.get_dependencies = mock.Mock(return_value=dependencies)
        inst.bpo.resources.delete_dependencies = mock.Mock()
        inst.logger = mock.Mock()
        inst.get_built_in_product = mock.Mock(return_value={"id": "2018"})
        inst.bpo.resources.create = mock.Mock()
        inst.mget = mock.Mock(return_value=dependencies)
        inst.soft_terminate_process = mock.Mock(return_value=dependencies)

        CommonPlan.splunk_logger_setup = mock.Mock()

        self._sleep = mock.patch("time.sleep")
        self.sleep = self._sleep.start()

        # calling the run function
        resp = inst.run()
        self.assertIsNone(resp)

        # defining expected calls based on database
        cd_res = [
            {
                "resourceTypeId": "charter.resourceTypes.CircuitDetails",
                "id": "1000",
                "properties": {"circuit_id": "1010"},
            }
        ]

        rem_res = [
            {"resourceTypeId": "charter.resourceTypes.abc", "id": "1020"},
            {"resourceTypeId": "mef.resourceTypes.LegatoService", "id": "1030", "orchState": "active"},
            {"resourceTypeId": "charter.resourceTypes.xyz", "id": "1040"},
        ]
        call1 = mock.call("12345", None, rem_res, force_delete_relationship=True)
        call2 = mock.call("12345", None, cd_res, force_delete_relationship=True)
        calls = [call1, call2]
        # making assertions
        inst.bpo.resources.get.assert_called_with("12345")
        inst.bpo.resources.get_dependencies.assert_called_with(resources["12345"]["id"])
        inst.bpo.resources.delete_dependencies.assert_has_calls(calls, any_order=False)

    def test_update(self):
        """
        test case - networkservice Update
        test to test update for network service
        """
        # since the code isnt ready not doing anything
        Update(self.params)

    def test_activatesite(self):
        """
        test case - networkservice ActivateSite
        test to test ActivateSite for network service
        """
        # since the code isnt ready not doing anything
        ActivateSite(self.params)

    def test_suspend(self):
        """
        test case - networkservice Suspend
        test to test suspend for network service
        """
        # since the code isnt ready not doing anything
        Suspend(self.params)

    def test_resume(self):
        """
        test case - networkservice Resume
        test to test resume for network service
        """
        # since the code isnt ready not doing anything
        Resume(self.params)
