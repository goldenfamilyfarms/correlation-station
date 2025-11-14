from .utilities.fortigateAPI import Fortigate
from .utilities.utilities import get_ip_info


def create_lookups(ip, key, logger):
    '''Determine the highest level reference for each interface/route'''
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    fortigate.get_system_vdoms()
    vdoms = {i['name']: {} for i in fortigate.system_vdoms}
    for vdom in vdoms:
        fortigate.get_system_interfaces(vdom=vdom)
        fortigate.get_system_switch_interfaces(vdom=vdom)
        fortigate.get_system_virtual_switches(vdom=vdom)
        fortigate.get_system_zones(vdom=vdom)
        fortigate.get_router_static(vdom=vdom)
        rib = fortigate.get_routing_table(vdom=vdom)
        fortigate.get_firewall_addresses(vdom=vdom)
        fortigate.get_firewall_addrgrps(vdom=vdom)
        fortigate.get_firewall_custom_services(vdom=vdom)
        fortigate.get_firewall_service_groups(vdom=vdom)
        fortigate.get_firewall_ippools(vdom=vdom)
        fortigate.get_firewall_vips(vdom=vdom)
        fortigate.get_firewall_vipgrps(vdom=vdom)
        fortigate.get_user_local(vdom=vdom)
        fortigate.get_user_groups(vdom=vdom)

        interface_lookup = {}
        for intf in fortigate.system_interfaces:
            interface_lookup[intf['name']] = intf['name']
        if fortigate.system_virtual_switches is not None:
            for switch in fortigate.system_virtual_switches:
                for intf in switch['port']:
                    interface_lookup[intf['name']] = switch['name']
                    if intf['name'] in interface_lookup:
                        interface_lookup[intf['name']] = switch['name']
        for switch in fortigate.system_switch_interfaces:
            for intf in switch['member']:
                interface_lookup[intf['interface-name']] = switch['name']
                if intf['interface-name'] in interface_lookup:
                    interface_lookup[intf['interface-name']] = switch['name']
        for zone in fortigate.system_zones:
            for intf in zone['interface']:
                interface_lookup[intf['interface-name']] = zone['name']
                if intf['interface-name'] in interface_lookup:
                    interface_lookup[intf['interface-name']] = zone['name']
        for key, value in interface_lookup.items():
            if value in interface_lookup:
                interface_lookup[key] = interface_lookup[value]

        route_lookup = {}
        for intf in fortigate.system_interfaces:
            route_lookup[get_ip_info(intf['ip'])[2]
                         ] = interface_lookup[intf['name']]
        for route in fortigate.router_static:
            if route['blackhole'] == 'enable':
                continue
            if route.get("device") not in interface_lookup:
                # todo, im not sure if this will cause down stream issues but it is necessary for this script to work
                continue
            route_lookup[get_ip_info(route['dst'])[2]
                         ] = interface_lookup[route['device']]
        for route in rib:
            if route['interface'] == 'Null':
                continue
            route_lookup[get_ip_info(route['ip_mask'])[2]
                         ] = interface_lookup[route['interface']]
        for key, value in route_lookup.items():
            if value in interface_lookup:
                route_lookup[key] = interface_lookup[value]

        address_lookup = []
        for address in fortigate.firewall_addresses:
            address_lookup.append(address['name'])
        for addrgrp in fortigate.firewall_addrgrps:
            address_lookup.append(addrgrp['name'])

        services = []
        for service in fortigate.firewall_custom_services:
            services.append(service['name'])
        for group in fortigate.firewall_service_groups:
            services.append(group['name'])

        ippools = []
        for ippool in fortigate.firewall_ippools:
            ippools.append(ippool['name'])

        vips = []
        for vip in fortigate.firewall_vips:
            vips.append(vip['name'])
        for vipgrp in fortigate.firewall_vipgrps:
            vips.append(vipgrp['name'])

        users = []
        for user in fortigate.user_local:
            users.append(user['name'])

        user_groups = []
        for group in fortigate.user_groups:
            user_groups.append(group['name'])

        vdoms[vdom]['interfaces'] = interface_lookup
        vdoms[vdom]['routes'] = route_lookup
        vdoms[vdom]['addresses'] = address_lookup
        vdoms[vdom]['services'] = services
        vdoms[vdom]['ippools'] = ippools
        vdoms[vdom]['vips'] = vips
        vdoms[vdom]['users'] = users
        vdoms[vdom]['user_groups'] = user_groups
    return vdoms


def find_matching_policy(policies, new):
    for policy in policies:
        if policy["name"] == new["name"]:
            return policy
    else:
        return None


def config_firewall_policy(ip, key, logger, policies):
    logger.info('Beginning firewall policy script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)

    # Determine default management VDOM
    fortigate.get_system_global()
    vdom = "root"
    fortigate.get_firewall_policies(vdom=vdom)

    # Normalize inputs, assign default values as needed
    logger.info("===============================================================================")
    logger.info("CONFIGURING FIREWALL POLICIES")
    logger.info("===============================================================================")
    import json
    for policy in policies:
        logger.info("-------------------------------------------------------------------------------")
        logger.info(f"policy: {json.dumps(policy, indent=4)}")
        logger.info("-------------------------------------------------------------------------------")

        # Check for existing duplicate policies
        existing = find_matching_policy(fortigate.firewall_policies, policy)

        # Apply config
        if existing:
            logger.info('Found existing policy: {}'.format(
                existing['policyid']))
        else:
            policy['logtraffic'] = 'all'
            policy['vdom'] = vdom
            response = fortigate.config_firewall_policy(**policy)
            if response is None:
                logger.warning('Failed to configure firewall policy')
                errors.append('Failed to configure firewall policy')

    logger.info("===============================================================================")
    logger.info("ENDING FIREWALL POLICIES SCRIPT")
    logger.info("===============================================================================")
    return errors
