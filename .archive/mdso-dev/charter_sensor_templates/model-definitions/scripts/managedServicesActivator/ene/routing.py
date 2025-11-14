from .utilities.fortigateAPI import Fortigate
from .utilities.utilities import check_route, get_ip_info


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
        fortigate.get_router_static(vdom=vdom)
        rib = fortigate.get_routing_table(vdom=vdom)
        fortigate.get_firewall_addresses(vdom=vdom)
        fortigate.get_firewall_addrgrps(vdom=vdom)

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

        address_lookup = {}
        for address in fortigate.firewall_addresses:
            if address['type'] != 'ipmask':
                continue
            addr = {
                'allow-routing': address['allow-routing'],
                'associated-interface': address['associated-interface'],
                'color': address['color'],
                'comment': address['comment'],
                'subnet': address['subnet'],
            }
            address_lookup[address['name']] = addr

        vdoms[vdom]['interfaces'] = interface_lookup
        vdoms[vdom]['routes'] = route_lookup
        vdoms[vdom]['addresses'] = address_lookup
    return vdoms


def config_static_routes(ip, key, logger, routes):
    logger.info('Beginning static route script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)

    # Get all existing VDOMs and determine management vdom
    fortigate.get_system_vdoms()
    vdoms = {i['name']: {} for i in fortigate.system_vdoms}
    fortigate.get_system_global()
    mgmt_vdom = fortigate.system_global['management-vdom']

    # Create lookups for each VDOM
    for vdom in vdoms:
        vdoms[vdom]['addresses'] = {}
        vdoms[vdom]['connected'] = {}
        vdoms[vdom]['static'] = {}

        # Get existing firewall addresses and address groups
        fortigate.get_firewall_addresses(vdom=vdom)
        for address in fortigate.firewall_addresses:
            if address['type'] != 'ipmask':
                continue
            if address['allow-routing'] != 'enable':
                continue
            vdoms[vdom]['addresses'][address['name']] = {
                'subnet': get_ip_info(address['subnet'])[2],
                'member': None
            }

        fortigate.get_firewall_addrgrps(vdom=vdom)
        for group in fortigate.firewall_addrgrps:
            if group['allow-routing'] != 'enable':
                continue
            vdoms[vdom]['addresses'][group['name']] = {
                'subnet': None,
                'member': [i['name'] for i in group['member']]
            }

        # Get directly connected routes
        fortigate.get_system_interfaces(vdom=vdom)
        for interface in fortigate.system_interfaces:
            if interface['ip'] == '0.0.0.0 0.0.0.0':
                continue
            if interface['vdom'] != vdom:
                continue
            cidr = get_ip_info(interface['ip'])[2]
            vdoms[vdom]['connected'][cidr] = interface['name']

        # Get existing static routes. Ignore default and blackhole routes.
        fortigate.get_router_static(vdom=vdom)
        for route in fortigate.router_static:
            if route['blackhole'] == 'enable':
                continue
            device = route['device']
            gateway = route['gateway']
            vrf = route['vrf']
            seq = route['seq-num']
            status = route['status']
            # Record routes with address objects
            if route['dstaddr'] != '':
                cidr = vdoms[vdom]['addresses'][route['dstaddr']]['subnet']
                members = vdoms[vdom]['addresses'][route['dstaddr']]['member']
                if members is None:
                    vdoms[vdom]['static'][cidr] = {
                        'device': device,
                        'gateway': gateway,
                        'vrf': vrf,
                        'seq': seq,
                        'status': status
                    }
                else:
                    for member in members:
                        member_cidr = vdoms[vdom]['addresses'][member]['subnet']
                        if member_cidr is None:
                            logger.warning('Nested addrgrp {}'.format(member))
                            continue
                        vdoms[vdom]['static'][member_cidr] = {
                            'device': device,
                            'gateway': gateway,
                            'vrf': vrf,
                            'seq': seq,
                            'status': status
                        }
            # Record for routes without address objects
            else:
                if route['dst'] == '0.0.0.0 0.0.0.0':
                    continue
                cidr = get_ip_info(route['dst'])[2]
                vdoms[vdom]['static'][cidr] = {
                    'device': device,
                    'gateway': gateway,
                    'vrf': vrf,
                    'seq': seq,
                    'status': status
                }

    for route in routes:
        dst = route.get('dst', None)
        dstaddr = route.get('dstaddr', None)
        gateway = route.get('gateway', None)
        blackhole = route.get('blackhole', 'disable')
        distance = route.get('distance', 10)
        vdom = route.get('vdom', mgmt_vdom)
        comment = route.get('comment', '')
        device = None

        # Determine which interface to use to reach the gateway
        for i in vdoms[vdom]['connected']:
            if check_route(gateway, i):
                device = vdoms[vdom]['connected'][i]
                break
        if device is None:
            for i in vdoms[vdom]['static']:
                if check_route(gateway, i):
                    device = vdoms[vdom]['static'][i]['device']
                    break
        if device is None:
            logger.warning(
                'Unable to determine interface to reach gateway: {}'.format(gateway))
            errors.append(
                'Unable to determine interface to reach gateway: {}'.format(gateway))
            continue

        result = fortigate.config_router_static(
            device, blackhole=blackhole, comment=comment, distance=distance,
            dst=dst, dstaddr=dstaddr, gateway=gateway, status=status, vdom=vdom)
        if result is None:
            logger.warning('Failed to configure static route')
            errors.append('Failed to configure static route')
            continue


def config_ospf(
        ip, key, logger, areas=None, networks=None, interfaces=None,
        router_id=None, default_info_originate='disable', vdom='root'):
    logger.info('Beginning OSPF script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    response = fortigate.config_router_ospf(
        router_id=router_id, areas=areas, networks=networks,
        interfaces=interfaces, vdom=vdom,
        default_information_originate=default_info_originate)
    if response is None:
        logger.warning('Failed to configure OSPF')
        errors.append('Failed to configure OSPF')

    logger.info('Ending OSPF script!')
    return errors


def determine_router_id(ip, key, logger, rid, route_lookup, vdom):
    fortigate = Fortigate(ip, key, logger)

    if rid is not None:
        rid_info = get_ip_info(rid)
        rid = '' if rid_info is None else rid_info[0]
    else:
        try:
            wan_intf = route_lookup[vdom]['routes']['0.0.0.0/0']
            fortigate.get_system_interfaces(vdom=vdom)
            for i in fortigate.system_interfaces:
                if i['name'] != wan_intf:
                    continue
                ip = fortigate.get_system_interface_statistics(wan_intf)['ip']
                rid = ip if ip != '0.0.0.0' else ''
        except KeyError:
            rid = ''
    return rid


def merge_config(current, payload, key):
    merged = []
    for old in current:
        if 'q_origin_key' in old:
            del old['q_origin_key']
        for new in payload:
            if old[key] == new[key]:
                merged.append(new)
                break
        else:
            pass
            # merged.append(new)
    return merged


def config_bgp(
        ip, key, logger, asn, neighbors=None, neighbor_ranges=None,
        neighbor_groups=None, networks=None, router_id=None, vdom='root'):
    errors = []
    fortigate = Fortigate(ip, key, logger)
    lookup = create_lookups(ip, key, logger)
    router_id = determine_router_id(ip, key, logger, router_id, lookup, vdom)
    neighbors = [] if neighbors is None else neighbors
    neighbor_ranges = [] if neighbor_ranges is None else neighbor_ranges
    neighbor_groups = [] if neighbor_groups is None else neighbor_groups
    networks = [] if networks is None else networks

    # Pull and merge existing bgp config
    fortigate.get_router_bgp(vdom=vdom)
    asn = fortigate.router_bgp['as']
    router_id_fort = fortigate.router_bgp['router-id']

    if not router_id:
        if not router_id_fort:
            errors.append('IPv4 router IP not provided. Failed to configure BGP')
            return errors
        else:
            router_id = router_id_fort

    merged_neighbors = merge_config(
        fortigate.router_bgp['neighbor'], neighbors, 'ip')

    merged_neighbor_groups = merge_config(
        fortigate.router_bgp['neighbor-group'], neighbor_groups, 'name')

    merged_neighbor_ranges = merge_config(
        fortigate.router_bgp['neighbor-range'], neighbor_ranges, 'prefix')

    merged_networks = merge_config(
        fortigate.router_bgp['network'], networks, 'prefix')

    response = fortigate.config_router_bgp(
        asn, router_id, neighbors=merged_neighbors, networks=merged_networks,
        neighbor_groups=merged_neighbor_groups,
        neighbor_ranges=merged_neighbor_ranges)

    if response is None:
        logger.warning('Failed to configure BGP')
        errors.append('Failed to configure BGP')

    logger.info('Ending BGP script!')
    return errors
