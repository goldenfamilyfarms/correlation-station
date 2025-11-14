from paramiko import SSHClient, AutoAddPolicy
from arda_app.common import auth_config


def can_connect(host: str) -> dict:
    try:
        conn = SSHClient()
        conn.load_system_host_keys()
        conn.set_missing_host_key_policy(AutoAddPolicy())
        conn.connect(
            host,
            22,
            auth_config.TACACS_USER,
            auth_config.TACACS_PASS,
            timeout=30,
            allow_agent=False,
            look_for_keys=False,
        )

        return {"accessible": True, "message": f"Successfully logged into {host}"}
    except Exception as err:
        return {"accessible": False, "message": f"Unable to log into {host}", "error": str(err)}
