import requests
import logging
import palantir_app
from flask import abort

logger = logging.getLogger(__name__)


def get_seek(endpoint, params):
    """
    gets the return from VCD API
    :param: endpoint: Desired endpoint,
    :param: params: any params for endpoint.
    EX: endpoint= /diceinfo/, params= 'zip_code=78758&rf_codes=RF120'
    :return: API repsonse in json format
    """
    required_keys = ["channels", "service_group_data"]
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}
    try:
        resp = requests.get(
            f"{palantir_app.url_config.SEEK_BASE_URL}{endpoint}",
            headers=headers,
            params=params,
            verify=False,
            timeout=30,
        )
        logger.info(f"Response from GET_SEEK: {resp}")
        if resp.status_code == 200:
            resp = resp.json()
            for k in resp:
                if k in required_keys:
                    if resp[k]:
                        continue
                    else:
                        return f"Error: Null value returned for key {k}: {resp[k]}"
            return resp
        else:
            return f"{resp.status_code} Error response from SEEK: {resp.json()}"
    except Exception as e:
        abort(500, f"Error from SEEK API: {e}")
