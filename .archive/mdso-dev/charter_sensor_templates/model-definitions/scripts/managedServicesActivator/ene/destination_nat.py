from .utilities.fortigateAPI import Fortigate
from .utilities.utilities import check_route, get_ip_info


def create_lookups(ip, key, logger):
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()
    fortigate.get_system_interfaces()
    fortigate.get_system_switch_interfaces()
    fortigate.get_system_virtual_switches()
    fortigate.get_system_zones()
    fortigate.get_router_static()
    rib = fortigate.get_routing_table()
    interface_lookup = {}
    for intf in fortigate.system_interfaces:
        interface_lookup[intf['name']] = intf['name']
    if fortigate.system_virtual_switches is not None:
        for switch in fortigate.system_virtual_switches:
            for intf in switch['port']:
                interface_lookup[intf['name']] = switch['name']
    for switch in fortigate.system_switch_interfaces:
        for intf in switch['member']:
            interface_lookup[intf['interface-name']] = switch['name']
            if intf['interface-name'] in interface_lookup:
                interface_lookup[intf['interface-name']] = switch['name']
    for zone in fortigate.system_zones:
        for intf in zone['interface']:
            interface_lookup[intf['interface-name']] = zone['name']
    for key, value in interface_lookup.items():
        if value in interface_lookup:
            interface_lookup[key] = interface_lookup[value]

    route_lookup = {}
    for intf in fortigate.system_interfaces:
        route_lookup[get_ip_info(intf['ip'])[2]
                     ] = interface_lookup[intf['name']]
    for route in fortigate.router_static:
        if route.get("device") not in interface_lookup:
            continue
        if route['blackhole'] == 'enable':
            continue
        route_lookup[get_ip_info(route['dst'])[2]] = interface_lookup[route['device']]
    for route in rib:
        if route['interface'] == 'Null':
            continue
        route_lookup[get_ip_info(route['ip_mask'])[2]
                     ] = interface_lookup[route['interface']]
    for key, value in route_lookup.items():
        if value in interface_lookup:
            route_lookup[key] = interface_lookup[value]
    lookup = {}
    lookup['interfaces'] = interface_lookup
    lookup['routes'] = route_lookup
    return lookup


def configure_vip(
        ip, key, extip, mappedip, logger, extport=None, mappedport=None,
        protocol=None, srcaddr=None):
    logger.info('Beginning port forwarding script!')
    errors = []
    extintf = None
    services = None
    if srcaddr is None:
        srcaddr = []

    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()
    lookup = create_lookups(ip, key, logger)

    # Use default route interface as placeholder for external interface
    default_route_intf = lookup['routes'].get('0.0.0.0/0', None)
    if default_route_intf:
        extintf = default_route_intf

    # Update the external interface to the port that owns the external IP
    for route in lookup['routes']:
        if route == '0.0.0.0/0':
            continue
        if check_route(extip, route):
            extintf = lookup['routes'][route]
            break

    if extintf is None:
        logger.warning('Unable to determine WAN port -- Exiting')
        errors.append('Unable to determine WAN port -- Exiting')
        return errors

    # Use the same process to determine the internal interface
    for route in lookup['routes']:
        if route == '0.0.0.0/0':
            continue
        if check_route(mappedip, route):
            dstintf = lookup['routes'][route]
            break
    else:
        logger.warning('No route to destination IP -- Exiting')
        errors.append('No route to destination IP -- Exiting')
        return errors

    # Create VIP if it doesn't already exist
    response = fortigate.config_firewall_vip(
        extintf, extip, mappedip, extport=extport, mappedport=mappedport,
        protocol=protocol, nat_source_vip='enable')

    # Fail fast if unable to create VIP
    if response is None:
        logger.warning('Unable to create VIP -- Exiting')
        errors.append('Unable to create VIP -- Exiting')
        return errors

    name = [response['mkey']]

    # Create address objects for desired source IPs
    fortigate.get_firewall_addresses()
    for address in srcaddr:
        for i in fortigate.firewall_addresses:
            if address == i['name']:
                break
        else:
            ipmask = get_ip_info(address)
            if ipmask is not None:
                fortigate.config_firewall_address(
                    address, addr_type='ipmask', subnet=ipmask[2])

    if extport == mappedport:
        if protocol == 'tcp':
            fortigate.config_firewall_custom_service(
                name='TCP_{}'.format(extport), tcp_portrange=extport)
            services = ['TCP_{}'.format(extport)]
        elif protocol == 'udp':
            fortigate.config_firewall_custom_service(
                name='UDP_{}'.format(extport), udp_portrange=extport)
            services = ['UDP_{}'.format(extport)]
    else:
        if protocol == 'tcp':
            fortigate.config_firewall_custom_service(
                name='TCP_{}'.format(extport), tcp_portrange=extport)
            fortigate.config_firewall_custom_service(
                name='TCP_{}'.format(mappedport), tcp_portrange=mappedport)
            services = ['TCP_{}'.format(extport), 'TCP_{}'.format(mappedport)]
        elif protocol == 'udp':
            fortigate.config_firewall_custom_service(
                name='UDP_{}'.format(extport), udp_portrange=extport)
            fortigate.config_firewall_custom_service(
                name='UDP_{}'.format(mappedport), udp_portrange=mappedport)
            services = ['UDP_{}'.format(extport), 'UDP_{}'.format(mappedport)]

    result = fortigate.config_firewall_policy(
        extintf, dstintf, srcaddr, name, action='accept', nat='disable',
        service=services, logtraffic='all')
    if result is None:
        logger.warning('Failed to configure firewall policy')
        errors.append('Failed to configure firewall policy')

    logger.info('Ending port forwarding script!')
    return errors
