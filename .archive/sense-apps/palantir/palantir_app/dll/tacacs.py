import logging
import paramiko

import palantir_app
from palantir_app.bll.resource_status import get_resource_status
from palantir_app.dll.mdso import mdso_get, mdso_post, product_query
from palantir_app.common.constants import ISE_STATES_EAST, ISE_STATES_SOUTH, ISE_STATES_WEST


logger = logging.getLogger(__name__)

tacacs_usr = palantir_app.auth_config.TACACS_USER
tacacs_pass = palantir_app.auth_config.TACACS_PASS


def get_tacacs_status(ip: str) -> str:
    """
    Connects to device with TACACS creds and returns the status of the connection

    :param ip: IP address of the device
    :type ip: str
    :return: Status of the connection
            "Success" if the connection was successful
            "Auth not successful remediation required" if the connection failed due to auth
            "Failed: <error>" if the connection failed for any other reason
    :rtype: str
    """

    connection_response = "Failed: Unknown Error"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            ip, port=22, username=tacacs_usr, password=tacacs_pass, allow_agent=False, look_for_keys=False, timeout=10
        )
        logger.debug("Connection successful")
        connection_response = "Success"
    except paramiko.AuthenticationException:
        logger.debug("Auth not successful remediation required")
        connection_response = "Auth not successful remediation required"
    except Exception as e:
        logger.debug(f"Failed: {e}")
        connection_response = f"Failed: {e}"
    finally:
        ssh.close()

    return connection_response


def remediate_tacacs_connection(ip: str, tid: str, vendor: str, use_local_creds: bool = False) -> dict:
    """
    Send device to info to MDSO to remediate TACACS connection
    :param ip: IP address of the device
    :type ip: str
    :param tid: TID of the device
    :type tid: str
    :return: Status of the remediation
            {"Success": <Device Response>} if the connection was successful
            {"Error": <error>} if the connection failed for any other reason
    :rtype: dict
    """
    remediation_status = {"properties": {"status": {"Error": "Default State"}}}
    region, state = region_and_state_search(tid)

    endpoint = "/bpocore/market/api/v1/resources?validate=false"
    tacacs_product_id = product_query("seefaTACACSRemediation")
    payload = {
        "desiredOrchState": "active",
        "label": f"{tid}.{ip}",
        "autoClean": False,
        "reason": "string",
        "discovered": False,
        "properties": {"fqdn": ip, "region": region, "vendor": vendor, "state": state, "local_creds": use_local_creds},
        "productId": tacacs_product_id,
    }

    created_resource_id = mdso_post(endpoint, payload, calling_function="remediate_tacacs_connection")["id"]

    resource_status = get_resource_status(
        created_resource_id, map_responses=False, poll=True, poll_counter=10, poll_sleep=30
    )
    if not resource_status["status"]:  # the resource was still processing after poll time expired
        logger.error(
            f"MDSO resource failed to reach a completion state in allotted time: Resource:{created_resource_id}"
        )
        failure = "Poll expired completed MDSO resource status unavailable"
        remediation_status["properties"]["status"]["Error"] = f"Failed: {failure}"
    elif resource_status["status"] != "Completed":
        logger.error(f"MDSO resource failed to complete: Resource:{created_resource_id}:{resource_status['status']}")
        remediation_status["properties"]["status"]["Error"] = "Failed: MDSO resource in error state"
    else:
        logger.debug(f"MDSO resource completed: Resource:{created_resource_id}:{resource_status['status']}")
        remediation_status = mdso_get(
            f"/bpocore/market/api/v1/resources/{created_resource_id}?full=false&obfuscate=true"
        )

    return remediation_status["properties"]["status"]


def region_and_state_search(tid: dict) -> str:
    """
    Returns a region based on the state of the device
    Based on the TID, the state is extracted and compared to a list of states

    :param tid: TID of the device
    :type tid: dict
    :return: Region of the device
    :rtype: str
    """
    # Define state from TID
    state = tid[4:6]

    if any(match in state for match in ISE_STATES_WEST):
        region = "west"
    elif any(match in state for match in ISE_STATES_SOUTH):
        region = "south"
    elif any(match in state for match in ISE_STATES_EAST):
        region = "east"

    return region, state
