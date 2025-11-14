from .utilities.fortigateAPI import Fortigate


def config_services(ip, key, logger, services):
    logger.info('Beginning service object script!')
    logger.info('Beginning service object script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    for i in services:
        name = i['name'].strip()
        comment = i.get('comment', '')
        vdom = "root"
        protocol = i['protocol']
        icmptype = i.get('icmptype', None)
        icmpcode = i.get('icmpcode', None)
        protocol_number = i.get('protocol_number', None)
        port_range = i.get('port_range', {'tcp': [], 'udp': []})

        if "TCP/UDP" in protocol.upper():
            if port_range == {'tcp': [], 'udp': []}:
                logger.warning(
                    'No ports provided for "{}" - skipping'.format(name))
                errors.append(
                    'No ports provided for "{}" - skipping'.format(name))
                continue
            if 'tcp' not in port_range:
                port_range['tcp'] = []
            if 'udp' not in port_range:
                port_range['udp'] = []

            for protocol_type in ["tcp", "udp"]:
                port_range[protocol_type] = [f"{x}" for x in port_range[protocol_type]]

            invalid_port = False
            for port in port_range['tcp']:
                if '-' in port:
                    ranges = port.split('-')
                    try:
                        lower = int(ranges[0])
                        upper = int(ranges[1])
                        if 0 > lower > 65535:
                            logger.warning('Invalid TCP port {}'.format(port))
                            errors.append('Invalid TCP port {}'.format(port))
                            invalid_port = True
                            break
                        if 0 > upper > 65535:
                            logger.warning('Invalid TCP port {}'.format(port))
                            errors.append('Invalid TCP port {}'.format(port))
                            invalid_port = True
                            break
                    except (ValueError, IndexError):
                        logger.warning('Invalid TCP port {}'.format(port))
                        errors.append('Invalid TCP port {}'.format(port))
                        invalid_port = True
                        break
                    continue
                else:
                    try:
                        port_number = int(port)
                        if 0 > port_number > 65535:
                            logger.warning(
                                'Invalid TCP port {}'.format(port_number))
                            errors.append(
                                'Invalid TCP port {}'.format(port_number))
                            invalid_port = True
                            break
                    except ValueError:
                        logger.warning('Invalid TCP port {}'.format(port))
                        errors.append('Invalid TCP port {}'.format(port))
                        invalid_port = True
                        break

            for port in port_range['udp']:
                if '-' in port:
                    ranges = port.split('-')
                    try:
                        lower = int(ranges[0])
                        upper = int(ranges[1])
                        if 0 > lower > 65535:
                            logger.warning('Invalid UDP port {}'.format(port))
                            errors.append('Invalid UDP port {}'.format(port))
                            invalid_port = True
                            break
                        if 0 > upper > 65535:
                            logger.warning('Invalid UDP port {}'.format(port))
                            errors.append('Invalid UDP port {}'.format(port))
                            invalid_port = True
                            break
                    except (ValueError, IndexError):
                        logger.warning('Invalid UDP port {}'.format(port))
                        errors.append('Invalid UDP port {}'.format(port))
                        invalid_port = True
                        break
                    continue
                else:
                    try:
                        port_number = int(port)
                        if 0 > port_number > 65535:
                            logger.warning(
                                'Invalid UDP port {}'.format(port_number))
                            errors.append(
                                'Invalid UDP port {}'.format(port_number))
                            invalid_port = True
                            break
                    except ValueError:
                        logger.warning('Invalid UDP port {}'.format(port))
                        errors.append('Invalid UDP port {}'.format(port))
                        invalid_port = True
                        break

            if invalid_port:
                logger.warning(
                    'Invalid port provided for "{}" - skipping'.format(name))
                errors.append(
                    'Invalid port provided for "{}" - skipping'.format(name))
                continue

            if len(port_range['tcp']) == 2:
                if len(set(port_range['tcp'])) == 1:
                    port_range['tcp'] = f"{port_range['tcp'][0]}"
                else:
                    port_range['tcp'] = f"{port_range['tcp'][0]}-{port_range['tcp'][1]}"

            if len(port_range['udp']) == 2:
                if len(set(port_range['udp'])) == 1:
                    port_range['udp'] = f"{port_range['udp'][0]}"
                else:
                    port_range['udp'] = f"{port_range['udp'][0]}-{port_range['udp'][1]}"

            # port_range['tcp'] = ' '.join(port_range['tcp'])
            # port_range['udp'] = ' '.join(port_range['udp'])
            response = fortigate.config_firewall_custom_service(
                name, comment=comment, protocol=protocol, vdom=vdom,
                tcp_portrange=port_range['tcp'], udp_portrange=port_range['udp'])
        elif protocol == 'ICMP':
            if icmptype is None:
                logger.warning('No ICMP type provided - skipping')
                errors.append('No ICMP type provided - skipping')
                continue

            if 0 > icmptype > 255:
                logger.warning(
                    'Invalid ICMP type "{}" provided'.format(icmptype))
                errors.append(
                    'Invalid ICMP type "{}" provided'.format(icmptype))
                continue

            if icmpcode is None:
                logger.warning('No ICMP code provided - skipping')
                errors.append('No ICMP code provided - skipping')
                continue

            if 0 > icmpcode > 255:
                logger.warning(
                    'Invalid ICMP code "{}" provided'.format(icmpcode))
                errors.append(
                    'Invalid ICMP code "{}" provided'.format(icmpcode))
                continue

            response = fortigate.config_firewall_custom_service(
                name, comment=comment, protocol=protocol, vdom=vdom,
                icmptype=icmptype, icmpcode=icmpcode)
        elif protocol == 'IP':
            if protocol_number is None:
                logger.warning('No protocol number provided - skipping')
                errors.append('No protocol number provided - skipping')
                continue

            if 0 > protocol_number > 254:
                logger.warning(
                    'Invalid protocol number "{}" provided'.format(protocol_number))
                errors.append(
                    'Invalid protocol number "{}" provided'.format(protocol_number))
                continue

            response = fortigate.config_firewall_custom_service(
                name, comment=comment, protocol=protocol, vdom=vdom,
                protocol_number=protocol_number)

        else:
            logger.warning(f'Invalid service type requested {protocol} -- skipping')
            errors.append(f'Invalid service type requested  {protocol} -- skipping')

        if response is None:
            logger.warning(f'Failed to create service object "{name}"')
            errors.append(f'Failed to create service object "{name}"')

    logger.info('Ending service object script!')
    return errors


def config_service_groups(ip, key, logger, groups):
    logger.info('Beginning service group script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    for group in groups:
        name = group['name'].strip()
        members = group['members']
        members = [x["name"] for x in members]

        comment = group.get('comment', '')
        vdom = "root"
        fortigate.get_firewall_custom_services(vdom=vdom)
        fortigate.get_firewall_service_groups(vdom=vdom)
        services = [i['name'] for i in fortigate.firewall_custom_services]

        existing_services = []
        for member in members:
            if member in services:
                existing_services.append(member)
            else:
                logger.warning(
                    '"{}" does not exist - removing from "{}" service group'.format(member, name))
                errors.append(
                    '"{}" does not exist - removing from "{}" service group'.format(member, name))
                continue

        response = fortigate.config_firewall_service_group(
            name, existing_services, comment=comment, vdom=vdom)
        if response is None:
            logger.warning(
                'Failed to configure service group "{}"'.format(name))
            errors.append(
                'Failed to configure service group "{}"'.format(name))
            response = fortigate.config_firewall_service_group(
                name, [], comment=comment, vdom=vdom)
            if response is not None:
                logger.warning('Empty service group "{}"created'.format(name))

    logger.info('Ending service group script!')
    return errors
