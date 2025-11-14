import logging
import re
import time
import requests

from typing import Tuple

from arda_app.common import url_config, auth_config
from common_sense.common.errors import abort
from arda_app.dll.granite import get_device_fqdn, get_device_model, get_device_vendor
from arda_app.dll.ipc import get_device_by_hostname
from arda_app.dll.sense import get_sense
from common_sense.common.device import verify_device_connectivity

logger = logging.getLogger(__name__)


def _generate_header(token=None):
    header = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        header["Authorization"] = f"token {token}"
    return header


def _create_token():
    """get a token to authenticate calls to MDSO"""

    headers = _generate_header()
    data = {
        # Use MDSO_PASS with dev.env if dev MDSO is needed
        "username": auth_config.MDSO_USER_PROD,
        "password": auth_config.MDSO_PASS_PROD,
        "tenant": "master",
        "expires_in": 60,
        "grant_type": "password",
    }
    try:
        r = requests.post(
            f"{url_config.MDSO_PROD_URL}/tron/api/v1/oauth2/tokens", headers=headers, json=data, verify=False, timeout=30
        )
        if r.status_code in [200, 201]:
            token = r.json()["accessToken"]
            return token
        else:
            abort(500, "Error Code: M001 - Unexpected status code: {r.status_code} at authentication with MDSO.")
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(500, "Error Code: M002 - Connection Timeout at authentication with MDSO.")


def _delete_token(token):
    if token:
        headers = _generate_header(token)
        try:
            requests.delete(
                f"{url_config.MDSO_PROD_URL}/tron/api/v1/oauth2/tokens/{token}",
                headers=headers,
                verify=False,
                timeout=300,
            )
        except Exception:
            logger.info("Unable to delete token")


def mdso_get(endpoint, params=None, timeout=30):
    token = _create_token()
    headers = _generate_header(token)
    try:
        r = requests.get(
            f"{url_config.MDSO_PROD_URL}{endpoint}", headers=headers, params=params, timeout=timeout, verify=False
        )
        if r.status_code == 200:
            logger.info(f"GET response from MDSO: \n{r.json()}")
            return r.json()
        else:
            abort(
                500,
                "Error Code: M003 - Unexpected status code: "
                f"{r.status_code} returned from MDSO endpoint: {endpoint} | Error: {r.text}",
            )
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(500, f"Timeout - Error Code: M004 - Timeout at MDSO for request: {endpoint}.")

    finally:
        _delete_token(token)


def mdso_post(endpoint, payload, timeout=60):
    token = _create_token()
    headers = _generate_header(token)
    try:
        r = requests.post(
            f"{url_config.MDSO_PROD_URL}{endpoint}",
            headers=headers,
            json=payload if payload else None,
            timeout=timeout,
            verify=False,
        )
        if r.status_code in {201, 202}:
            logger.info(f"MDSO POST response: \n{r.json()}")
            return r.json()
        else:
            abort(
                500,
                f"Error Code: M005 - Unexpected status code: {r.status_code} "
                f"returned from MDSO endpoint: {endpoint} | payload: {payload} | Error: {r.text}",
            )
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(500, f"Timeout - Error Code: M006 - Timeout at MDSO for request: {endpoint} | payload: {payload}")

    finally:
        _delete_token(token)


def mdso_delete(endpoint, params=None, timeout=30):
    token = _create_token()
    headers = _generate_header(token)
    try:
        r = requests.delete(
            f"{url_config.MDSO_PROD}{endpoint}", headers=headers, params=params, timeout=timeout, verify=False
        )
        if r.status_code == 204:
            return
        logger.debug(f"URL: {endpoint} \nUnknown delete error. Status code: {r.status_code}")
    except (ConnectionError, requests.Timeout, requests.ConnectionError):
        abort(500, f"Timeout - Error Code: M006 - Timeout at MDSO for request: {endpoint} | params: {params}")

    except Exception as e:
        logger.debug(f"URL: {endpoint}\nDelete error: {e}")
    finally:
        _delete_token(token)


def _get_network_device(hostname, timeout=30, retry=2, quick_return=False):
    """
    get network device obj if no active network device,
    the function must return None.
    If an active one is found we must rsync the device
    """

    if len(hostname) != 11:
        abort(500, f"Hostname must be exactly 11 chars HOSTNAME: {hostname}")

    params = {
        "resourceTypeId": "tosca.resourceTypes.NetworkFunction",
        "p": f"label:{hostname}*",
        "offset": "0",
        "limit": 5,
    }
    endpoint = "/bpocore/market/api/v1/resources"
    logger.info(f"Running Network Device Lookup for {hostname}")

    # removing resync to prevent large delay when gathering info
    # for device in devices:
    # resync device to make sure all data is up to date (only once per device)
    # resync_mdso_device(device["id"])

    try:
        # check for active devices at least twice by defualt
        for _ in range(retry):
            # could be a list of 0, 1, or many
            devices = mdso_get(endpoint, params, timeout)["items"]
            for device in devices:
                # check active device
                if _is_available(device):
                    return device
            # wait 10 seconds before we try checking the devices again
            time.sleep(10)
        # return None if after looping twice a device was not sent back
        if quick_return:
            return devices[0]
        return None
    except IndexError:
        # return None if no items came back
        return None


def _is_available(device):
    if (
        device.get("orchState")
        and device["orchState"] == "active"
        and device.get("properties")
        and device["properties"].get("communicationState")
        and device["properties"]["communicationState"] == "AVAILABLE"
    ):
        return True
    return False


def get_mx_asn(hostname, timeout=60):
    """From the provided TID/hostname, return the ASN of an MX as a string"""
    params = {
        "resourceTypeId": "tosca.resourceTypes.NetworkConstruct",
        "p": f"label:/*{hostname}*",
        "offset": "0",
        "limit": 1000,
    }
    endpoint = "/bpocore/market/api/v1/resources"
    try:
        return mdso_get(endpoint, params, timeout)["items"][0]["properties"]["data"]["attributes"]["routingData"][
            "asNumber"
        ][0]
    except IndexError:
        return None


def _show_interface_config(device_id, port, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "seefa-cd-show-interface-config.json", "parameters": {"interface": port}}
    return mdso_post(endpoint, payload, timeout)


def _get_mx_edna_status(device_id, timeout):
    """Query a Juniper MX to see if it has been EDNA migrated"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "is_edna.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _get_routing_instances(device_id, timeout):
    """Query a Juniper MX for its routing instances"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-routinginstances-full.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_l2_circuits_full(device_id, param, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-l2-circuits-full.json", "parameters": {"name": param}}
    return mdso_post(endpoint, payload, timeout)


def _get_interface_config(device_id, port, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-interface-config.json", "parameters": {"name": port}}
    return mdso_post(endpoint, payload, timeout)


def _get_all_interfaces_config(device_id, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-interfaces-config.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_10g_adva_ports(device_id, timeout):
    """Pull interface info from a 10G ADVA"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "seefa-cd-list_eth_ports.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_10g_adva_flows(device_id, timeout):
    """Pull flow info from a 10G ADVA"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "fre_list.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_1g_adva_ports(device_id, timeout):
    """Pull interface info from a 1G ADVA"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "list_access_ports.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_1g_adva_flows(device_id, timeout):
    """Pull interface flows from a 1G ADVA"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "list_flows.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_rad_ports(device_id, timeout):
    """Pull interface info from a RAD"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "seefa-cd-list-ports.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_rad_port_details(device_id, parameter, timeout):
    """Pull interface info from a RAD"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-port-info-details.json", "parameters": {"type": "ETHERNET", "id": parameter}}
    return mdso_post(endpoint, payload, timeout)


def _show_rad_flows(device_id, timeout):
    """Pull flow info from a RAD"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "list-flows.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_rad_classifiers(device_id, timeout):
    """Pull classifier profiles from a RAD"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "list-classifiers.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_cisco_ports(device_id, parameter, timeout):
    """Pull interface info from a Cisco"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-interface-used-vlan-ids.json", "parameters": {"interface": parameter}}
    return mdso_post(endpoint, payload, timeout)


def _show_cisco_router_evc(device_id, parameter, timeout):
    """Pull EVC info from a Cisco router"""
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "seefa-l2vpn-xconnect.json", "parameters": {"interface": parameter}}
    return mdso_post(endpoint, payload, timeout)


def _show_route(device_id, ip, timeout):
    payload = {"command": "seefa-cd-show-route.json", "parameters": {"ip_add": ip}}
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    return mdso_post(endpoint, payload, timeout)


def _agg_vlans(device_id, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-vlanidentifier-full.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_routing_options(device_id, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get-routingoptions.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


# TODO: Button up with proper command/endpoint from final release
def _show_isis(device_id, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "seefa-cd-show-isis.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def _show_chassis(device_id, port, timeout):
    parameters = port.split("/")
    if len(parameters) < 3:
        abort(500, f"Parameter: {port} is not correct")

    fpc, pic = parameters[0][-1], parameters[1]
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "seefa-cd-show-chassis-fpc-pic.json", "parameters": {"fpc": fpc, "pic": pic}}
    return mdso_post(endpoint, payload, timeout)


def _show_l2circuit_status(device_id, port, timeout):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {
        "command": "show-l2circuit-connection-status.json",
        "parameters": {"interface": port.split(".")[0], "vlan": port.split(".")[1]},
    }
    return mdso_post(endpoint, payload, timeout)


def _show_arp_irb(device_id, timeout, parameter):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {
        "command": "get-arp-query.json",
        "parameters": {"uniqueid": "|irb.99" if not parameter else f"|irb.{parameter}"},
    }
    return mdso_post(endpoint, payload, timeout)


def _get_mdso_parameter(command, parameter):
    parameter_names = {"show_route": "ip_add", "show_interfaces": "port"}
    result = parameter_names.get(command, {})
    if result:
        if not parameter:
            abort(500, f"Parameter: {result} not found for command: {command}")
        result = {result: parameter}
    return result


def get_resource_result(resource_id, device, tries=20, tries_timeout=5):
    endpoint = f"/market/api/v1/resources/{resource_id}"
    try:
        for _ in range(tries):
            data = mdso_get(endpoint, params=None, timeout=30)
            if data.get("orchState") in ("requested", "activating"):
                time.sleep(tries_timeout)
                continue
            elif data.get("orchState") == "active":
                if data.get("properties", {}).get("result", {}).get("Error"):
                    mdso_reason = data["properties"]["result"]["Error"]
                    logger.debug(f"Unable to obtain device data for {device}, MDSO reason: {mdso_reason}")
                    abort(500, f"Unable to obtain device data for {device}, MDSO reason: {mdso_reason}")
                else:
                    return data
            else:
                mdso_reason = ""
                if "reason" in data:
                    mdso_reason = str(data["reason"]).upper()
                logger.debug(f"Unable to obtain device data for {device}, MDSO reason: {mdso_reason}")
                abort(500, f"Unable to obtain device data for {device}, MDSO reason: {mdso_reason}")
    except Exception as e:
        logger.debug(f"Unable to obtain device data for {device}\nError: {e}")
        abort(500, f"Unable to obtain device data for {device}")
    # finally:
    #     mdso_delete(endpoint)


def _get_seefa_device_information(device, command, timeout, parameters):
    label_and_host = get_device_fqdn(device.split(".")[0])
    payload = {
        "productId": _get_mdso_product_id("seefaDeviceInformation"),
        "label": label_and_host,
        "desiredOrchState": "active",
        "properties": {
            "host_id": label_and_host,
            "command": _get_mdso_command_name(command),
            "parameters": _get_mdso_parameter(command, parameters),
            "vendor": get_device_vendor(device),
            "model": get_device_model(device),
        },
    }
    # create seefa device information resource
    resource = mdso_post("/market/api/v1/resources?validate=false&obfuscate=true", payload, timeout)

    # get info from seefa device information resource.
    return get_resource_result(resource.get("id"), device)["properties"]


def _check_device(hostname, timeout=70):
    payload = {
        "label": f"design-{hostname}-ConnectivityCheck",
        "resourceTypeId": "tosca.resourceTypes.ConnectivityCheck",
        "productId": _get_mdso_product_id("ConnectivityCheck", prefix="tosca"),
        "properties": {"device_ip": hostname},
    }
    resource = mdso_post("/market/api/v1/resources?validate=false&obfuscate=true", payload, timeout)

    # get info from seefa device information resource
    return get_resource_result(resource.get("id"), "device", tries=14)


def get_resource_id_from_tid(tid):
    endpoint = (
        "/market/api/v1/resources?resourceTypeId=tosca.resourceTypes.NetworkFunction"
        f"&q=label%3A{tid}&obfuscate=true&offset=0&limit=1000"
    )
    resp = mdso_get(endpoint, timeout=60)
    return resp["items"]


def _get_mdso_command_name(command):
    translated_command_name = {
        "show_route": "seefa-cd-show-route",
        "show_interfaces": "seefa-cd-show-interface-config",
        "seefa-cd-list_eth_ports.json": "seefa-cd-list-ports",
        "seefa-cd-list-ports.json": "seefa-cd-list-ports",
        "agg_vlans": "seefa-cd-get-vlan-identifier-full",
        "show_version": "seefa-cd-show-version",  # TODO add this command to seefa/commands dir in mdso
        "show_isis": "seefa-cd-show-isis",
        "show_routing_options": "seefa-cd-get-routing-options",
        "show_l2circuit_status": "show-l2circuit-connection-status",
    }
    try:
        return translated_command_name[command]
    except KeyError:
        abort(500, "An unsupported command or parameter was issued. Error Code: M012")


def _get_mdso_product_id(product, timeout=30, prefix="charter"):
    """get mdso product id"""
    endpoint = (
        "/bpocore/market/api/v1/products?includeInactive=false&q=resourceTypeId%3A"
        f"{prefix}.resourceTypes.{product}&offset=0&limit=1000"
    )
    return mdso_get(endpoint, {}, timeout)["items"][0].get("id")


def _poll_resource_id(resource_id, hostname):
    palantir_endpoint = f"/palantir/v3/resourcestatus?resourceId={resource_id}"

    for i in range(11):
        if i > 0:
            time.sleep(60)
        resource_resp = get_sense(palantir_endpoint)
        orch_state = resource_resp.get("status")
        logger.info(f"ORCH STATE! {orch_state}")
        if orch_state == "Failed":
            abort(500, f"Error Code: M007 - Device {hostname} failed MDSO onboarding process.")

        if orch_state == "Completed":
            return
        else:
            if i >= 10:
                abort(500, f"Error Code: M008 - Device {hostname} failed MDSO onboarding process.")
            else:
                continue


def get_active_device(hostname, timeout=30, polling=True, model="", device_vendor="") -> Tuple[int, str]:
    """Executes a lookup for the networkfunction MDSO record for the device.
    If a record already exists, verifies active orchState, otherwise fallout.
    If a record does not exist, trigger onboard and return the MDSO Onboarding Resource ID.

    :param hostname: The hostname(TID) of the device to be used for onboarding"""
    logger.info(f"MDSO Onboard initiating for {hostname}")

    # hostname must be uppercase to search MDSO
    hostname = hostname.upper()
    # make call to MDSO to find existing device(network function)
    # return is either an active device or None
    device = _get_network_device(hostname, timeout)
    # return active device if found
    if device:
        if not polling:
            return 202, device["id"]
        return None, device
    # onboard device if there is none existing or not active
    return onboard_device(hostname, timeout, polling, model, device_vendor)


def _exe_cmd(device, command, timeout, parameter=None, smart_connect=True):
    if smart_connect:
        # use seefa device information resource + smart connect to obtain device response
        return _get_seefa_device_information(device, command, timeout, parameter)
    else:
        # use network function resource (device onboarding) + MDSO RA to obtain device response
        # get device id from mdso resource
        device_id = device.get("providerResourceId")
        if command == "show_route" and parameter is not None:
            return _show_route(device_id, parameter, timeout)
        elif command == "show_routing_instances":
            return _get_routing_instances(device_id, timeout)
        elif command == "show_interfaces" and parameter is not None:
            return _show_interface_config(device_id, parameter, timeout)
        elif command == "get_interfaces" and parameter is not None:
            return _get_interface_config(device_id, parameter, timeout)
        elif command == "get_all_interfaces":
            return _get_all_interfaces_config(device_id, timeout)
        elif command == "seefa-cd-list_eth_ports.json":
            return _show_10g_adva_ports(device_id, timeout)
        elif command == "list_access_ports.json":
            return _show_1g_adva_ports(device_id, timeout)
        elif command == "seefa-cd-list-ports.json":
            return _show_rad_ports(device_id, timeout)
        elif command == "get-port-info-details.json" and parameter is not None:
            return _show_rad_port_details(device_id, parameter, timeout)
        elif command == "get-interface-used-vlan-ids.json":
            return _show_cisco_ports(device_id, parameter, timeout)
        elif command == "show_cisco_router_evc" and parameter is not None:
            return _show_cisco_router_evc(device_id, parameter, timeout)
        elif command == "agg_vlans":
            return _agg_vlans(device_id, timeout)
        elif command == "show_version":
            deviceVersion = device.get("properties")["deviceVersion"]
            resourceType = device.get("properties")["resourceType"]
            swVersion = device.get("properties")["swVersion"]
            return {"deviceVersion": deviceVersion, "resourceType": resourceType, "swVersion": swVersion}
        elif command == "show_isis":
            return _show_isis(device_id, timeout)
        elif command == "show_routing_options":
            return _show_routing_options(device_id, timeout)
        elif command == "show_chassis" and parameter is not None:
            # for Juniper devices
            return _show_chassis(device_id, parameter, timeout)
        elif command == "1g_adva_flows":
            return _show_1g_adva_flows(device_id, timeout)
        elif command == "10g_adva_flows":
            return _show_10g_adva_flows(device_id, timeout)
        elif command == "rad_flows":
            return _show_rad_flows(device_id, timeout)
        elif command == "rad_classifiers":
            return _show_rad_classifiers(device_id, timeout)
        elif command == "get-l2-circuits-full.json":
            return _show_l2_circuits_full(device_id, parameter, timeout)
        elif command == "is_edna":
            return _get_mx_edna_status(device_id, timeout)
        elif command == "show_l2circuit_status":
            return _show_l2circuit_status(device_id, parameter, timeout)
        elif command == "show_arp_irb":
            return _show_arp_irb(device_id, timeout, parameter)
        elif command == "show_vlan_brief":
            return show_vlan_brief(device_id, timeout)
        elif command == "show_interface_description":
            return show_interface_description(device_id, timeout)
        elif command == "show_running_config_interface":
            return show_running_config_interface(device_id, parameter, timeout)
        elif command == "get_service_instances":
            return get_service_instances(device_id, parameter, timeout)
        else:
            abort(500, "An unsupported command or parameter was issued. Error Code: M012")
            return False


def onboard_and_exe_cmd(hostname, command, parameter=None, attempt_onboarding=False, timeout=120):
    """
    This method will attempt to run the given mdso command. if the hostname provided needs to be onboarded
    it will do so.

    :param hostname: device name
    :param command: supported commands are show_route and show_interfaces
    :param parameter: paramaters required to run command, i.e. device ip or port
    :param timeout: timeout value to be passed to MDSO GET and PUT methods. Default to 30s
    :return: command result from mdso
    """
    # only EX4200 will use the new seefa device path
    if "EX4200" in get_device_model(hostname):
        mdso_result = _exe_cmd(hostname, command, timeout, parameter=parameter, smart_connect=True)
    else:
        _, device = get_active_device(hostname, timeout)
        mdso_result = _exe_cmd(device, command, timeout, parameter=parameter, smart_connect=False)
    # if attempt_onboarding:
    #     _, device = get_active_device(hostname, timeout)
    #     mdso_result = _exe_cmd(device, command, timeout, parameter=parameter, smart_connect=False)
    # else:
    #     mdso_result = _exe_cmd(hostname, command, timeout, parameter=parameter, smart_connect=True)

    if isinstance(mdso_result, dict) and "result" in mdso_result:
        return mdso_result

    abort(500, f"Error when retrieving data from MDSO for device {hostname} command {command}")


def port_available_on_network(uplink_port, optic, hub_clli_code, timeout=180, attempt_onboarding=False):
    try:
        tid = uplink_port["EQUIP_NAME"].split("/")[0]
    except IndexError:
        abort(500, f"Equipment was not found for port at {hub_clli_code} - Error Code: G009")
    port = f"{optic.lower()}-{uplink_port['PORT_ACCESS_ID']}"
    configuration = network_config(tid, port, timeout, attempt_onboarding)

    if not configuration:
        if tid.endswith("QW"):
            return _check_alternate_qfx_port(tid, port, timeout, attempt_onboarding)
        return True
    else:
        if _validate_config(configuration["interfaces"]["interface"]):
            if tid.endswith("QW"):
                return _check_alternate_qfx_port(tid, port, timeout, attempt_onboarding)
            return True
        # if any config is found beyond DISABLEIF apply-group, port is not available
        return False


def network_config(tid, port, timeout, attempt_onboarding):
    """Get config from the network for a given port. Return None if no config."""
    net_call = onboard_and_exe_cmd(
        command="show_interfaces", hostname=tid, parameter=port, timeout=timeout, attempt_onboarding=attempt_onboarding
    )
    return net_call["result"]["data"]["configuration"]


def _check_alternate_qfx_port(tid, port, timeout, attempt_onboarding):
    """Check alternate BW role (GE / XE). Return True if port is usable"""
    if "ge" in port.lower():
        port = re.sub("ge", "xe", port)
        configuration = network_config(tid, port, timeout, attempt_onboarding)
        if configuration:
            return _validate_config(configuration["interfaces"]["interface"])
        return True
    elif "xe" in port.lower():
        port = re.sub("xe", "ge", port)
        configuration = network_config(tid, port, timeout, attempt_onboarding)
        if configuration:
            return _validate_config(configuration["interfaces"]["interface"])
        return True


def _validate_config(config):
    """Return True if port is available based on config values"""
    try:
        # disable key always has value of None if it exists, so .get() won't work in this situation
        disable_key = config["disable"]
        logger.info(f"disable_key exists, port has 'disable' instead of DISABLEIF apply-group {disable_key}")
        if not config.get("description"):
            return True
    except KeyError:
        if (
            config
            and config.get("apply-groups")
            and "DISABLEIF" in config["apply-groups"]
            and not config.get("description")
        ):
            return True
    return False


def check_onboard(hostname):
    """Onboard status check"""

    data = _get_network_device(hostname, timeout=60)

    if data:
        response = {"id": "", "status": "", "message": ""}
        response["id"] = data.get("id")
        if "orchState" in data:
            if data["orchState"] == "requested" or data["orchState"] == "activating":
                response["status"] = "Processing"
            elif data["orchState"] == "active":
                response["status"] = "Completed"
            else:
                response["status"] = "Failed"
                if "reason" in data:
                    mdso_reason = str(data["reason"]).upper()
                    response["message"] = f"Onboard failed for {hostname}, MDSO reason: {mdso_reason}"
        return response


def qc_port_available_on_network(uplink_port, z_clli_code, timeout=180, attempt_onboarding=False):
    try:
        equip_name = uplink_port["EQUIP_NAME"].split("/")[0]
    except IndexError:
        abort(500, f"Equipment was not found for port at {z_clli_code} - Error Code: G009")
    port = f"{uplink_port['EXPECTED_PAID'].lower()}"
    if uplink_port["VENDOR"] == "ADVA":
        command_name = "seefa-cd-list_eth_ports.json"
    elif uplink_port["VENDOR"] == "RAD":
        command_name = "seefa-cd-list-ports.json"
    elif uplink_port["VENDOR"] == "JUNIPER":
        command_name = "show_interfaces"

    net_call = onboard_and_exe_cmd(
        command=command_name, hostname=equip_name, parameter=port, timeout=timeout, attempt_onboarding=attempt_onboarding
    )

    return net_call


def serviceable_shelf_port_available_on_network(equip_name, vendor, timeout=180, attempt_onboarding=False):
    try:
        equip_name = equip_name.split("/")[0]
    except IndexError:
        abort(500, "Equipment was not found Error Code: G009")
    port = f"{equip_name.lower()}"
    if vendor == "ADVA":
        command_name = "seefa-cd-list_eth_ports.json"
    elif vendor == "RAD":
        command_name = "seefa-cd-list-ports.json"

    return onboard_and_exe_cmd(
        command=command_name, hostname=equip_name, parameter=port, timeout=timeout, attempt_onboarding=attempt_onboarding
    )


def resync_mdso_device(id):
    endpoint = "/bpocore/market/api/v1/resources/{}/resync?full=false"
    mdso_post(endpoint.format(id), None)


def onboard_device(hostname, timeout=30, polling=True, model="", device_vendor=""):
    if "sense.chtrse" in url_config.SENSE_BASE_URL:
        device = verify_device_connectivity(hostname=hostname)["message"]
        # reachable holds FQDN if it resolves to usable IP else usable IP
        # if no usable IP found, verify device connectivity will trigger abort
        device_ip_fqdn = device[hostname.upper()]["reachable"]
    else:
        device_ip_fqdn = get_device_fqdn(hostname)

    endpoint = "/bpocore/market/api/v1/resources?validate=false"
    payload = create_onboard_payload(hostname, device_ip_fqdn, timeout, model, device_vendor)
    logger.info(f"Executing POST to MDSO Onboard API using Payload: \n{payload}")
    mdso_post(endpoint, payload, timeout)
    # returning Network Function ID with less retries
    if not polling:
        device = _get_network_device(hostname, timeout, retry=2, quick_return=True)
        if device:
            device = device.get("id")
        return 202, device

    device = _get_network_device(hostname, timeout, retry=7)
    if device:
        return None, device

    abort(500, f"Error Code: M011 - Device {hostname} failed onboarding in MDSO.")


def create_onboard_payload(hostname, device_ip_fqdn, timeout=30, model="", device_vendor=""):
    # gather data from granite
    # If model is not provided defualt to granite
    if not model:
        model = get_device_model(hostname)

    # If vendor is not provided defualt to granite
    if not device_vendor:
        device_vendor = get_device_vendor(hostname).upper()

    onboarding_id = _get_mdso_product_id("DeviceOnboarder", timeout)

    if device_ip_fqdn == "DHCP":
        device_ip_fqdn = get_device_by_hostname(hostname)
        device_ip_fqdn = device_ip_fqdn.get("ipAddress")
        if not device_ip_fqdn:
            abort(
                500, f"MDSO onboarding error - DHCP is not a valid IP Address. Unable to get IP from IPC for {hostname}"
            )

    session_profile = {
        "JUNIPER": "sensor_jnpr",
        "CISCO": "sensor_cisco_domain_1",
        "RAD": "sensor_rad",
        "ADVA": "sensor_adva" if model and "114" in model else "sensor_adva_netconf",
    }
    payload = {
        "productId": f"{onboarding_id}",
        "label": f"{hostname}.circuit_design",
        "properties": {
            "device_name": f"{hostname}",
            "device_ip": f"{device_ip_fqdn}",
            "device_vendor": f"{device_vendor}",
            "session_profile": f"{session_profile[device_vendor]}",
        },
    }

    # ADVAs require an additional payload value to onboard successfully
    if model and device_vendor == "ADVA":
        payload["properties"]["device_model"] = model

    return payload


def show_vlan_brief(device_id, timeout=180):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "show-vlan-brief.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def show_interface_description(device_id, timeout=180):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "show-interface-description.json", "parameters": {}}
    return mdso_post(endpoint, payload, timeout)


def show_running_config_interface(device_id, interface, timeout=180):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "me3400/show-running-config-interface.json", "parameters": {"interface": interface}}
    return mdso_post(endpoint, payload, timeout)


def get_service_instances(device_id, interface, timeout=180):
    endpoint = f"/ractrl/api/v1/devices/{device_id}/execute"
    payload = {"command": "get_service_instances.json", "parameters": {"interface": interface}}
    return mdso_post(endpoint, payload, timeout)
