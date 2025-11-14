import logging
import re

from fastapi import Query
from paramiko import SSHClient, AutoAddPolicy

from arda_app.common import auth_config
from common_sense.common.errors import abort
from arda_app.api import atlas_router

logger = logging.getLogger(__name__)


@atlas_router.get("/accessibility", summary="Checks reachability for a specified ip address")
def accessibility(ip_address: str = Query(..., description="IP Address to check reachability")):
    """Checks reachability for a specified ip address"""

    if not _is_valid_ip_address(ip_address):
        abort(500, "Invalid IP Address format")

    return _can_connect(ip_address)


def _can_connect(host):
    try:
        conn = SSHClient()
        conn.load_system_host_keys()
        conn.set_missing_host_key_policy(AutoAddPolicy())
        conn.connect(host, 22, auth_config.TACACS_USER, auth_config.TACACS_PASS, allow_agent=False, look_for_keys=False)

        return {"accessible": True, "message": f"Successfully logged into {host}"}
    except Exception as err:
        return {"accessible": False, "message": f"Unable to log into {host}", "error": str(err)}


def _is_valid_ip_address(ip_address, cidr=32):
    ip_regex = r"((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    if 0 <= int(cidr) <= 32:
        if re.match(ip_regex, ip_address):
            return True
        else:
            return False
    else:
        return False
