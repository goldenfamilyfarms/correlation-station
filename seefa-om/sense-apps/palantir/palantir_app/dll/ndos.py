import requests

import palantir_app
from common_sense.common.errors import abort


def ndos_post(endpoint, payload, timeout=30):
    header = {"Content-type": "application/json", "cache-control": "no-cache"}
    try:
        resp = requests.post(
            f"{palantir_app.url_config.NDOS_BASE_URL}{endpoint}", headers=header, json=payload, timeout=timeout
        )
        # error response definitions, pass through to isin_default for proper 200
        if resp.status_code == 200:
            if "<html>" in str(resp.content):
                abort(502, f"Unexpected response from NDOS: {resp.content}")
            else:
                try:
                    return resp.json()
                except Exception:
                    abort(502, f"Unexpected response from NDOS: {resp.content}")
        # Gracefully handle 204 responses for v2/device
        elif resp.status_code == 204:
            return
        else:
            abort(
                502, f"Unexpected status code when attempting post to NDOS: {resp.status_code} | content: {resp.content}"
            )
    except (ConnectionError, requests.ConnectionError):
        abort(504, "Failure connecting to NDOS")
    except requests.ReadTimeout:
        abort(504, "Timed out waiting on data to arrive from NDOS")
