import logging
import requests
import urllib3

import beorn_app

from common_sense.common.errors import abort

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


def create_token():
    """get a token to authenticate calls to MDSO"""
    headers = {"Content-type": "application/json"}
    data = {
        "username": beorn_app.auth_config.MDSO_USER,
        "password": beorn_app.auth_config.MDSO_PASS,
        "tenant": "master",
        "expires_in": 60,
        "grant_type": "password",
    }
    try:
        r = requests.post(
            f"{beorn_app.url_config.MDSO_BASE_URL}/tron/api/v1/oauth2/tokens",
            headers=headers,
            json=data,
            verify=False,
            timeout=30,
        )
        if r.status_code in [200, 201]:
            token = r.json()["accessToken"]
            return token

        if r.status_code == 401:
            logging.debug("Error - Can't authenticate to create a token")
            abort(401, "Not Authenticated")
        elif r.status_code == 500:
            logger.debug("Error - Server error when trying to create a token")
        elif r.status_code == 404:
            logger.debug("Error - Resource not found when trying to create a token")
        else:
            logger.debug("Error - http code {}".format(r.status_code), r.content)
        abort(502, "Bad response from MDSO")
    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        abort(504, "Connection error to MDSO")
    except OSError:
        logger.debug("Attempt to get a token from Blue Planet Failed for Unknown Reasons")
        abort(500)


def delete_token(token):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "token {}".format(token),
    }
    requests.delete(
        f"{beorn_app.url_config.MDSO_BASE_URL}/tron/api/v1/oauth2/tokens/{token}",
        headers=headers,
        verify=False,
        timeout=300,
    )
