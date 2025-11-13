from time import sleep
from .utilities.fortigateAPI import Fortigate


def is_firmware_valid(current, target, logger):
    """
    currently checks if firmware version are equal
    can easily be modified to allow for higher versions than the target
    :param current: current firmware version
    :param target: target firmware version
    :param logger: logging object
    :return: boolean
    """
    try:
        # Remove the "v" prefix if present
        current = current.lstrip('v')
        target = target.lstrip('v')

        parts1 = [int(p) for p in current.split('.')]
        parts2 = [int(p) for p in target.split('.')]

        # Compare each component numerically
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                # target is higher than current
                return False
            elif p1 > p2:
                # target is lower than current
                return False

        # If one version string is shorter but all preceding components are equal
        if len(parts1) < len(parts2):
            # target is higher than current
            return False
        elif len(parts1) > len(parts2):
            # target is lower than current
            return False
        else:
            # versions are equal
            return True
    except Exception:
        msg = "Problem occurred while checking firmware versions. Ensure firmware is up to date"
        logger.log_issue(
            external_message=msg,
            internal_message=msg,
            code=2999,
            category=4
        )
        # stop the firmware upgrade process by saying they are equal after we log the error
        return True


def determine_filename(model, device_type='fortigate', firmware='7.0.5'):
    lookup = {
        'fortigate': {
            '7.0.5': {
                '40F': 'FGT_40F-v7.0.5-build0304-FORTINET.out',
                '60E': 'FGT_60E-v7.0.5-build0304-FORTINET.out',
                '60F': 'FGT_60F-v7.0.5-build0304-FORTINET.out',
                '61E': 'FGT_61E-v7.0.5-build0304-FORTINET.out',
                '61F': 'FGT_61F-v7.0.5-build0304-FORTINET.out',
                '200E': 'FGT_200E-v7.0.5-build0304-FORTINET.out',
                '201E': 'FGT_201E-v7.0.5-build0304-FORTINET.out',
                '100F': 'FGT_100F-v7.0.5-build0304-FORTINET.out',
                '600E': 'FGT_600E-v7.0.5-build0304-FORTINET.out',
                '601E': 'FGT_601E-v7.0.5-build0304-FORTINET.out',
                '2000E': 'FGT_2000E-v7.0.5-build0304-FORTINET.out',
                '2200E': 'FGT_2200E-v7.0.5-build0304-FORTINET.out',
                '3400E': 'FGT_3400E-v7.0.5-build0304-FORTINET.out',
                '3600E': 'FGT_3600E-v7.0.5-build0304-FORTINET.out',
                '4200F': 'FGT_4200F-v7.0.5-build4515-FORTINET.out',
                '6500F': None,
            }
        },
        'fortiswitch': {
            '7.0.4': {
                '108E': 'FSW_108E-v7-build0071-FORTINET.out',
                '108E-POE': 'FSW_108E_POE-v7-build0071-FORTINET.out',
                '124F': 'FSW_124F-v7-build0071-FORTINET.out',
                '124F-POE': 'FSW_124F_POE-v7-build0071-FORTINET.out',
                '148F': 'FSW_148F-v7-build0071-FORTINET.out',
                '148F-POE': 'FSW_148F_POE-v7-build0071-FORTINET.out',
                '424E': 'FSW_424E-v7-build0071-FORTINET.out',
                '424E-POE': 'FSW_424E_POE-v7-build0071-FORTINET.out',
                '448E': 'FSW_448E-v7-build0071-FORTINET.out',
                '448E-POE': 'FSW_448E_POE-v7-build0071-FORTINET.out',
                '1024E': 'FSW_1024E-v7-build0071-FORTINET.out',
            }
        }
    }
    return lookup[device_type][firmware][model]


def upgrade_firmware_fortiguard(target_version, fortigate, logger):
    # Find the ID of the firmware on FortiGuard, fail out if unable to determine
    results = fortigate.get_system_firmware()
    if results is None:
        message = "Failed to get system firmware"
        logger.log_issue(
            external_message=message,
            internal_message=message,
            code=2061,
            category=2
        )
        return False

    # normalize incase 'v' is already supplied in target version
    target_version = target_version.replace('v', '')
    target_version = f"v{target_version}"

    logger.info(f"Current firmware version is {fortigate.firmware}")
    logger.info(f"Target version is {target_version}")

    # check if we need to do anything with firmware
    up_to_date = is_firmware_valid(
        current=fortigate.firmware,
        target=target_version,
        logger=logger
    )
    if up_to_date:
        return True

    versions = results['results']['available']
    if len(versions) == 0:
        logger.info("no versions of available firmware found")
        return False

    target_fw_data = [x for x in versions if x["version"] == target_version]
    if len(target_fw_data) == 0:
        message = f"Failed to find target firmware version {target_version}"
        logger.log_issue(
            external_message=message,
            internal_message=message,
            code=2061,
            category=2
        )
        return False
    target_fw_data = target_fw_data[0]
    logger.info(f"Upgrading firmware from {fortigate.firmware} to {target_fw_data['version']}")

    # Apply the firmware update
    fortigate.update_firmware(target_fw_data["id"])

    # Wait and check that the upgrade was successful
    logger.info('Please stand by while rebooting the system.')
    fortigate.firmware = None
    sleep(120)
    tries = 0
    while (tries < 10):
        tries += 1
        fortigate.get_system_status()
        if fortigate.firmware is None:
            sleep(30)
            continue
        logger.info('Firmware upgrade completed')
        return True
    else:
        logger.error(
            'Timeout while upgrading firmware. Please verify device is '
            'reachable.')
        return False


def upgrade_firmware_ftp(ip, key, ftp_server, ftp_user, ftp_password, firmware, logger):
    '''Execute firmware upgrade'''
    script = """
    exe restore image ftp {} {} {} {}
    """.format(firmware['filename'], ftp_server, ftp_user, ftp_password)

    fortigate = Fortigate(ip, key)
    fortigate.upload_config_script('firmware_via_ftp', script)
    logger.info('Please stand by while rebooting the system.')
    fortigate.firmware = None
    sleep(120)

    tries = 0
    while (tries < 10):
        tries += 1
        fortigate.get_system_status()
        if fortigate.firmware is None:
            sleep(30)
            continue
        logger.info('Firmware upgrade completed')
        break
    else:
        logger.error(
            'Timeout while upgrading firmware. Please verify device is '
            'reachable.')
        return False

    if fortigate.firmware != "v{}.{}.{}".format(firmware['major'], firmware['minor'], firmware['patch']):
        return False

    return True


def handle_firmware(
        ip, key, major, minor, patch, ftp_server, ftp_user, ftp_password,
        logger):
    logger.info('Beginning firmware upgrade script!')
    status = {
        'current': None,
        'target': None,
        'upgrade_path': [],
        'errors': [],
        'completed': False
    }

    fortigate = Fortigate(ip, key)
    fortigate.get_system_status()
    if fortigate.serial is None:
        logger.error('Failed to get system status')
        status['errors'].append('Failed to get system status')
        return status

    status['current'] = {
        'major': fortigate.firmware_major,
        'minor': fortigate.firmware_minor,
        'patch': fortigate.firmware_patch,
        'build': fortigate.firmware_build
    }

    # Determine if firmware upgrade is needed
    target_version = 'v{}.{}.{}'.format(major, minor, patch)
    if fortigate.firmware == target_version:
        logger.info('Device already on target firmware')
        status['completed'] = True
        return status

    # Determine if the target firmware is available for this device
    available = fortigate.get_system_firmware()['results']['available']
    for i in available:
        if i['major'] != major:
            continue
        if i['minor'] != minor:
            continue
        if i['patch'] != patch:
            continue
        status['target'] = {
            'major': i['major'],
            'minor': i['minor'],
            'patch': i['patch'],
            'build': i['build']
        }
        break
    else:
        logger.error('Target firmware unavailable')
        status['errors'].append('Target firmware unavailable')
        return status

    # Determine full upgrade path
    # Haven't figured out full upgrade path yet. Go straight to target for now.
    status['upgrade_path'].append(status['target'])  # TODO: find upgrade path

    # Determine filename for needed firmware.
    for i in status['upgrade_path']:
        i['filename'] = determine_filename(
            fortigate.model, i['major'], i['minor'], i['patch'], i['build'])

    # Push firmware to device
    for i in status['upgrade_path']:
        i['completed'] = upgrade_firmware_ftp(
            ip, key, ftp_server, ftp_user, ftp_password, i, logger)
        if i['completed'] is False:
            break
    else:
        status['completed'] == True

    return status
