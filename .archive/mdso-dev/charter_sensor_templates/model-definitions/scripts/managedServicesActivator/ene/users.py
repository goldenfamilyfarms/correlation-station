from .utilities.fortigateAPI import Fortigate
from .utilities.utilities import get_ip_info


def config_ldap_servers(ip, key, logger, servers):
    logger.info('Beginning LDAP server script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    for i in servers:
        server_ip = get_ip_info(i['ip'])
        if server_ip is None:
            logger.warning('Invalid LDAP server IP provided, skipping')
            errors.append('Invalid LDAP server IP provided, skipping')
            continue

        server = {
            'name': i['name'],
            'server': server_ip[0],
            'dn': i['dn'],
            'cnid': i.get('cnid', 'sAMAccountName'),
            'port': i.get('port', 389),
            'source_port': i.get('source_port', 0),
            'vdom': i.get('vdom', None)
        }
        if i.get('username', None) is not None:
            server['auth_type'] = 'regular'
            server['username'] = i['username']
            server['password'] = i.get('password', None)

        source_ip = get_ip_info(i.get('source_ip', None))
        if source_ip is not None:
            server['source_ip'] = source_ip[0]

        result = fortigate.config_user_ldap(**server)
        if result is None:
            logger.error(
                'Failed to configure LDAP server "{}"'.format(i['name']))
            errors.append(
                'Failed to configure LDAP server "{}"'.format(i['name']))

    logger.info('Ending LDAP server script!')
    return errors


def config_radius_servers(ip, key, logger, servers):
    '''
    Configure RADIUS server entries

    ----------------------------------------------------------------------------
    Arguments
    ---------
    ip: (str)  FortiGate's management IP

    key: (str)  FortiGate's API key

    logger: (str)  Logger to be used

    servers: (list)  List of dictionaries including servers to be configured
        {
            'name': 'server2',
            'ip': '10.1.1.21',
            'secret': 'awvoiknmwvekm',
            'auth_type': 'ms_chap_v2',  # optional
            'interface': 'internal1',   # optional
            'nas_ip': '10.1.1.1',       # optional
            'radius_port': 1812,        # optional
            'vdom': 'root'              # optional
        }

    ----------------------------------------------------------------------------
    Returns
    -------
    errors: (list)  List of errors encountered
    '''
    logger.info('Beginning RADIUS server script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    for i in servers:
        server_ip = get_ip_info(i['ip'])
        if server_ip is None:
            logger.warning('Invalid RADIUS server IP provided, skipping')
            errors.append('Invalid RADIUS server IP provided, skipping')
            continue

        server = {
            'name': i['name'],
            'server': server_ip[0],
            'secret': i['secret'],
            'auth_type': i.get('auth_type', 'auto'),
            'interface': i.get('interface', None),
            'nas_ip': i.get('nas_ip', '0.0.0.0'),
            'radius_port': i.get('radius_port', 0),
            'vdom': i.get('vdom', None)
        }

        nas_ip = get_ip_info(i.get('nas_ip', '0.0.0.0'))
        if nas_ip is not None:
            server['nas_ip'] = nas_ip[0]

        result = fortigate.config_user_radius(**server)
        if result is None:
            logger.error(
                'Failed to configure RADIUS server "{}"'.format(i['name']))
            errors.append(
                'Failed to configure RADIUS server "{}"'.format(i['name']))

    logger.info('Ending RADIUS server script!')
    return errors


def config_user_groups(ip, key, logger, groups):
    '''
    Configure user groups

    ----------------------------------------------------------------------------
    Arguments
    ---------
    ip: (str)  FortiGate's management IP

    key: (str)  FortiGate's API key

    logger: (str)  Logger to be used

    groups: (list)  List of dictionaries including groups to be configured
        {
            'name': 'enterprise',
            'local': '['alice', 'bob'],     # optional
            'servers': [                    # optional
                {
                    'server_name': 'DC01',
                    'group_name': 'CN=test,CN=Users,DC=fglab,DC=local'  # optional
                }
            ],
            'vdom': 'root'                  # optional
        }

    ----------------------------------------------------------------------------
    Returns
    -------
    errors: (list)  List of errors encountered
    '''
    logger.info('Beginning user group script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)
    fortigate.get_system_status()

    # Create a lookup for users/servers/groups in each vdom
    fortigate.get_system_vdoms()
    vdoms = {i['name']: {} for i in fortigate.system_vdoms}
    for vdom in vdoms:
        fortigate.get_user_local(vdom=vdom)
        fortigate.get_user_ldap(vdom=vdom)
        fortigate.get_user_radius(vdom=vdom)
        fortigate.get_user_groups(vdom=vdom)
        vdoms[vdom]['users'] = [i['name'] for i in fortigate.user_local]
        ldap = [i['name'] for i in fortigate.user_ldap]
        radius = [i['name'] for i in fortigate.user_radius]
        vdoms[vdom]['servers'] = ldap + radius
        vdoms[vdom]['groups'] = [i['name'] for i in fortigate.user_groups]

    for group in groups:
        vdom = group.get('vdom', 'root')
        fortigate.get_user_groups(vdom=vdom)

        new = {
            'name': group['name'],
            'member': [],
            'match': [],
            'vdom': group.get('vdom', 'root')
        }

        for i in group.get('users', []):
            if i in vdoms[vdom]['users']:
                new['member'].append(i)
            else:
                logger.warning('User "{}" does not exist'.format(i))
                errors.append('User "{}" does not exist'.format(i))

        remote = group.get('servers', [])
        for i in remote:
            if i['server_name'] not in vdoms[vdom]['servers']:
                logger.warning('Server "{}" does not exist'.format(i))
                errors.append('Server "{}" does not exist'.format(i))
                continue
            new['member'].append(i['server_name'])
            if i.get('group_name', None) is not None:
                entry = {
                    'id': remote.index(i) + 1,
                    'server-name': i['server_name'],
                    'group-name': i['group_name']
                }
                new['match'].append(entry)

        response = fortigate.config_user_group(**new)
        if response is None:
            logger.warning('Failed to configure user group "{}"'.format(new['name']))
            errors.append('Failed to configure user group "{}"'.format(new['name']))
            response = fortigate.config_user_group(new['name'], [])
            if response is not None:
                logger.warning('Empty user group "{}"created'.format(new['name']))

    logger.info('Ending user group script!')
    return errors
