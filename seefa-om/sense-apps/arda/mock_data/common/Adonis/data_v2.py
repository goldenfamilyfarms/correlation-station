class MockResponseText:
    def __init__(self, text, status_code=200):
        self.status_code = status_code
        self.text = text


class MockResponseJson:
    def __init__(self, response_data, status_code=200):
        self.status_code = status_code
        self.response_data = response_data

    def json(self):
        return self.response_data


def mock_execute_task_good(*args, **kwargs):
    res_data = {"data": "data"}

    return MockResponseJson(res_data, 200)


def mock_execute_task_bad_status(*args, **kwargs):
    res_data = {"data": "data"}

    return MockResponseJson(res_data, 500)


def mock_execute_task_bad(*args, **kwargs):
    raise ConnectionError


def mock_auth_token_good(*args, **kwargs):
    data = {"message": None, "status": "OK", "code": 200, "userToken": "TOKEN"}
    return MockResponseJson(data, 200)


def mock_auth_token_bad_status(*args, **kwargs):
    data = {"userToken": "TOKEN"}
    return MockResponseJson(data, 500)


def mock_execute_rule_check_200(*args, **kwargs):
    data = {"message": None, "status": "OK", "code": 200, "path": [{"name": "item", "id": "1234"}]}
    return MockResponseJson(data, 200)


def mock_execute_rule_check_500(*args, **kwargs):
    data = "test error"
    return MockResponseText(data, 500)


def mock_execute_rule_check_502(*args, **kwargs):
    raise Exception("testing")
