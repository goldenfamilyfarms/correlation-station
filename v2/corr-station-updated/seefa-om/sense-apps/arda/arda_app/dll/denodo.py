import logging
import requests

from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from common_sense.common.errors import abort, remove_api_key
from arda_app.common import url_config, auth_config
from arda_app.dll.utils import get_hydra_headers


logger = logging.getLogger(__name__)
API_KEY = auth_config.ARDA_HYDRA_KEY


def denodo_get(endpoint, params=None):
    url = f"{url_config.HYDRA_BASE_URL}{endpoint}"
    for x in range(3):
        if x > 0:
            sleep(5)
        try:
            resp = requests.get(url, headers=get_hydra_headers(), params=params, verify=False, timeout=60)
            if resp.text.startswith("\n<!DOCTYPE"):
                logger.exception(f"Invalid response from Denodo: {url}")
                continue
            elif resp.status_code in [200, 201, 202, 204]:
                return resp.json()
            else:
                abort(
                    500,
                    f"Denodo unexpected status code: {resp.status_code} - "
                    f"URL: {url}{f' - PARAMS: {params}' if params else ''}",
                )
        except Exception:
            logger.info(f"Denodo API responded with status code: {resp.status_code} for URL: {url}")
    logger.exception("Can't connect to Hydra")
    abort(500, f"Hydra timeout - URL: {remove_api_key(url)}")


def get_isp_group(clli):
    endpoint = f"/prod/denodo/ent_design/enid_sense/views/remedy_isp_groups/?clli={clli}"
    resp = denodo_get(endpoint)
    try:
        isp_group = resp["elements"][0]
        logger.debug(f"ISP_GROUP: {isp_group['isp_group']}")
        return isp_group
    except Exception:
        abort(500, f"Could not find ISP group for HUB CLLI: {clli} in ENID")


def get_npa_three_digits(zip_code):
    """Get first two digits of npa value based on zip_code"""
    headers = {"APPLICATION": "SENSE-ARDA"}
    url = (
        f"{url_config.HYDRA_BASE_URL}"
        "/prod/denodo/app_int/dv_zipcode_combined"
        f"/views/dv_zipcode_combined?api_key={API_KEY}&zipcode={zip_code}"
    )

    retry_strategy = Retry(
        total=5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET", "POST"], backoff_factor=3
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)

    try:
        with requests.Session() as session:
            session.mount("https://", adapter)

            resp = session.get(url=url, headers=headers, verify=False)
            resp.raise_for_status()

            if resp.status_code == 200:
                if resp.json()["elements"]:
                    for record in resp.json()["elements"]:
                        if record["zipcode"] == zip_code:
                            areacode = record["areacode"]

                            if len(areacode) > 1:
                                return areacode
                            else:
                                abort(500, f"Not enough digits in area code '{areacode}'")
                        else:
                            abort(500, f"No record found for zip code {zip_code}")
                else:
                    abort(500, f"No record found for zip code {zip_code}")
    except (requests.ConnectTimeout, requests.ConnectionError, requests.exceptions.RequestException):
        logger.exception("Can't connect to Denodo")
        abort(500, f"Timed out getting data from Denodo for URL: {remove_api_key(url)}")
