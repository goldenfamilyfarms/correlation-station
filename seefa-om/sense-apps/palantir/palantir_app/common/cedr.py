import logging

import requests

import palantir_app
from common_sense.common.errors import abort
from palantir_app.common.utils import get_hydra_headers
from palantir_app.common.endpoints import DENODO_CEDR_DV

logger = logging.getLogger(__name__)


def query_by_tid_or_ip(tid=None, ip=None):
    """Returns info for a device based on ip or tid"""

    if not tid and not ip:
        return None

    alias = "hostname" if tid else "ipaddr"

    url = (
        f"{palantir_app.url_config.HYDRA_BASE_URL}{DENODO_CEDR_DV}{alias}"
        f"/views/bv_cedr_device_by_{alias}?{alias}={tid if tid else ip}"
    )
    logger.debug(url)

    return query_cedr_data(url)


def query_cedr_data(query):
    headers = get_hydra_headers()
    try:
        r = requests.get(query, headers=headers, timeout=300)
        if r.status_code == 200:
            return r.json()["elements"] or None
        if r.status_code == 404:
            return None
        else:
            abort(502, f"Denodo returned an error code - {r.status_code}")

    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, "Connection error with denodo")
