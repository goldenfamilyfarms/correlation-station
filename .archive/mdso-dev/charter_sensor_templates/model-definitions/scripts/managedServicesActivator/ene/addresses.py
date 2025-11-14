from .utilities.fortigateAPI import Fortigate
from .utilities.geography import GEOGRAPHY_CODES
from .utilities.utilities import get_ip_info


def verify_mac(mac):
    valid = [
        'a', 'b', 'c', 'd', 'e', 'f',
        '1', '2', '3', '4', '5', '6',
        '7', '8', '9', '0', ':'
    ]
    addr = [i for i in mac]

    if len(addr) != 17:
        return False

    if addr[2::3] != [':', ':', ':', ':', ':']:
        return False

    for i in addr:
        if i not in valid:
            return False

    return True


def config_addresses(ip, key, logger, addresses):
    logger.info('Beginning address object script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    for i in addresses:
        allow_routing = i.get('allow_routing', 'disable')
        associated_interface = i.get('associated_interface', '')
        comment = i.get('comment', '')
        country = i.get('country', None)
        fqdn = i.get('fqdn', None)
        macaddr = i.get('macaddr', None)
        name = i['name'].strip()
        subnet = i.get('subnet', None)
        start_ip = i.get('start_ip', None)
        end_ip = i.get('end_ip', None)

        if i['addr_type'] == 'ipmask':
            if subnet is None:
                logger.warning(
                    'No subnet provided for "{}" - skipping'.format(name))
                errors.append(
                    'No subnet provided for "{}" - skipping'.format(name))
                continue

            subnet = get_ip_info(subnet)
            if subnet is None:
                logger.warning('Invalid IP "{}" - skipping'.format(i['subnet']))
                errors.append('Invalid IP "{}" - skipping'.format(i['subnet']))
                continue

            response = fortigate.config_firewall_address(
                name, allow_routing=allow_routing, comment=comment,
                associated_interface=associated_interface, subnet=subnet[2])

        elif i['addr_type'] == 'iprange':
            if start_ip is None or end_ip is None:
                logger.warning(
                    'No start IP provided for "{}" - skipping'.format(name))
                errors.append(
                    'No start IP provided for "{}" - skipping'.format(name))
                continue

            start_ip = get_ip_info(start_ip)
            end_ip = get_ip_info(end_ip)
            if start_ip is None:
                logger.warning(
                    'Invalid start IP "{}" - skipping'.format(i['start_ip']))
                errors.append(
                    'Invalid start IP "{}" - skipping'.format(i['start_ip']))
                continue
            if end_ip is None:
                logger.warning(
                    'Invalid end IP "{}" - skipping'.format(i['end_ip']))
                errors.append(
                    'Invalid end IP "{}" - skipping'.format(i['end_ip']))
                continue

            response = fortigate.config_firewall_address(
                name, addr_type='iprange', start_ip=start_ip[0], comment=comment,
                end_ip=end_ip[0], associated_interface=associated_interface)

        elif i['addr_type'] == 'fqdn':
            if fqdn is None:
                logger.warning(
                    'No FQDN provided for "{}" - skipping'.format(name))
                errors.append(
                    'No FQDN provided for "{}" - skipping'.format(name))
                continue

            response = fortigate.config_firewall_address(
                name, addr_type='fqdn', allow_routing=allow_routing, fqdn=fqdn,
                associated_interface=associated_interface, comment=comment)

        elif i['addr_type'] == 'geography':
            if country is None:
                logger.warning(
                    'No country provided for "{}" - skipping'.format(name))
                errors.append(
                    'No country provided for "{}" - skipping'.format(name))
                continue

            if country not in GEOGRAPHY_CODES:
                logger.warning(
                    'Invalid country code "{}" - skipping'.format(country))
                errors.append(
                    'Invalid country code "{}" - skipping'.format(country))
                continue

            response = fortigate.config_firewall_address(
                name, addr_type='geography', country=country,
                associated_interface=associated_interface, comment=comment)

        elif i['addr_type'] == 'mac':
            if macaddr is None:
                logger.warning(
                    'No MAC provided for "{}" - skipping'.format(name))
                errors.append(
                    'No MAC provided for "{}" - skipping'.format(name))
                continue

            if not verify_mac(macaddr):
                logger.warning('Invalid MAC "{}" - skipping'.format(macaddr))
                errors.append('Invalid MAC "{}" - skipping'.format(macaddr))
                continue

            response = fortigate.config_firewall_address(
                name, addr_type='mac', macaddr=[macaddr], comment=comment,
                associated_interface=associated_interface)

        else:
            logger.warning('Invalid address type requested - skipping')
            errors.append('Invalid address type requested - skipping')
            continue

        if response is None:
            logger.warning(
                'Failed to create address object "{}"'.format(name))
            errors.append(
                'Failed to create address object "{}"'.format(name))

    logger.info('Ending address object script!')
    return errors


def config_address_groups(ip, key, logger, groups):
    logger.info('Beginning address group script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    fortigate.get_firewall_addresses()
    addresses = {i['name']: i for i in fortigate.firewall_addresses}

    for group in groups:
        name = group['name'].strip()
        members = group['members']
        comment = group.get('comment', '')
        allow_routing = group.get('allow_routing', 'disable')

        for member in members:
            try:
                address = addresses[member]
                if address.get('allow-routing', 'disable') == 'disable':
                    allow_routing = 'disable'
            except KeyError:
                members.remove(member)
                logger.warning(
                    '"{}" does not exist - removing from "{}" address group'.format(member, name))
                errors.append(
                    '"{}" does not exist - removing from "{}" address group'.format(member, name))
                continue

        response = fortigate.config_firewall_addrgrp(
            name, members, allow_routing=allow_routing, comment=comment)
        if response is None:
            logger.warning(
                'Failed to create address group "{}"'.format(name))
            errors.append(
                'Failed to create address group "{}"'.format(name))

    logger.info('Ending address group script!')
    return errors
