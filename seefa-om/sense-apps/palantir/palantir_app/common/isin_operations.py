import requests

import palantir_app
from common_sense.common.errors import abort


def isin_update(ip):
    """POST to NDOS isin service with the IP"""

    ndos_api_call = f"{palantir_app.url_config.NDOS_BASE_URL}/ndos-isin-service/api/isin"
    ndos_payload = {"ipaddr": ip}
    header = {"Content-type": "application/json", "cache-control": "no-cache"}

    try:
        isin_req = requests.post(ndos_api_call, headers=header, json=ndos_payload, timeout=60)
        # error response definitions, pass through to isin_default for proper 200
        if isin_req.status_code == 200:
            if "<html>" in str(isin_req.content):
                print("API error - Please engage App Integration to investigate: ")
                return False
            else:
                try:
                    isin_resp = isin_req.json()
                    return isin_resp
                except Exception:
                    abort(502, "Bad response from NDOS")

        elif isin_req.status_code == 204 or 500:
            return False

        else:
            abort(502, "Bad response from NDOS")
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(504, "Problem connecting to NDOS")
