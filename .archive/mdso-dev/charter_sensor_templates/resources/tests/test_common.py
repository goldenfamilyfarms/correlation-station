import unittest
import unittest.mock as mock
import sys
sys.path.append('model-definitions')
from scripts.common_plan import CommonPlan


class test_common(unittest.TestCase):
    """
    test suite to unit test common plan functionality
    """

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
            "logFile": "/home/vagrant/charter/model-definitions/logs/abc.log",
            "resourceId": "12345",
            "traceId": "123456",
            "bpUserId": "8dc1fea2-e3d2-4c80-84ec-a6d874560368",
        }
        self.inst = CommonPlan(params)

    def test_is_string_uuid_positive(self):
        """
        test case - common plan "is_string_uuid_positive"
        test case to unit test positive scenario
        for the function "is_string_uuid"
        """
        str_ok = "8dc1fea2-e3d2-4c80-84ec-a6d874560368"
        result = self.inst.is_string_uuid(str_ok)
        self.assertTrue(result)

    def test_is_string_uuid_negative(self):
        """
        test case - common plan "is_string_uuid_negative"
        test case to unit test negative scenario
        for the function "is_string_uuid"
        """
        str_fail = "abcdefgh"
        result = self.inst.is_string_uuid(str_fail)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
