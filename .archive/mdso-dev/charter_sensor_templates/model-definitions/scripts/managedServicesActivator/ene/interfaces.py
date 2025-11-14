import json


def handle_interface(interface_payload, fortigate, logger):
    # Get system status to ensure device is reachable
    resp = fortigate.raw_config_interface(interface_payload)
    if not resp:
        logger.log_issue(
            external_message=f"Failed to configure {interface_payload.get('type')} interface {interface_payload.get('name', '')}",
            internal_message="Failed to configure interface",
            api_response=None,
            details=f"payload = {interface_payload}",
            code=2050,
            category=0
        )


def get_physical_interfaces(fortigate):
    intfs = fortigate.get_system_interfaces()
    intfs = intfs["results"]
    intfs = [x["name"] for x in intfs if x["type"] == "physical"]
    return intfs


def disable_unused_interfaces(used_interfaces, fortigate, logger):
    physical_interfaces = get_physical_interfaces(fortigate)
    unused_physical = list(set(physical_interfaces) - set(used_interfaces))
    logger.info(f"unused physical interfaces: {json.dumps(unused_physical, indent=4)}")
    errors = []
    for interface in unused_physical:
        disable_pl = {
            "name": interface,
            "status": "down",
            "alias": "not in use",
            "ip": "0.0.0.0 0.0.0.0",
            "allowaccess": "",
            "type": "physical",
        }
        resp = fortigate.raw_config_interface(payload=disable_pl)
        if not resp:
            errors.append(interface)
    return errors
