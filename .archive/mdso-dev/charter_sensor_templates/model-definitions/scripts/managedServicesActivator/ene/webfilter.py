from .utilities.fortigateAPI import Fortigate
from .utilities.webfilter import WEBFILTER_CATEGORIES


def config_default_webfilter(ip, key, logger, vdom=None):
    logger.info('Beginning default webfilter script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)

    # Default action is monitor
    # Default log is enable
    filters = [
        {'category': 0},  # Unrated
        {'action': 'block', 'category': 1},   # Drug Abuse
        {'action': 'block', 'category': 3},   # Hacking
        {'action': 'block', 'category': 4},   # Illegal or Unethical
        {'action': 'block', 'category': 5},   # Discrimination
        {'action': 'block', 'category': 6},   # Explicit Violence
        {'action': 'block', 'category': 8},   # Other Adult Materials
        {'action': 'block', 'category': 12},  # Extremist Groups
        {'action': 'block', 'category': 13},  # Nudity and Risque
        {'action': 'block', 'category': 14},  # Pornography
        {'action': 'block', 'category': 26},  # Malicious Websites
        {'action': 'block', 'category': 57},  # Marijuana
        {'action': 'block', 'category': 59},  # Proxy Avoidance
        {'action': 'block', 'category': 61},  # Phishing
        {'action': 'block', 'category': 62},  # Plagiarism
        {'action': 'block', 'category': 83},  # Child Sexual Abuse
        {'action': 'block', 'category': 86},  # Spam URLs
        {'category': 90},                     # Newly Observed Domain
        {'category': 91},                     # Newly Registered Domain
        {'category': 140, 'log': 'disable'},  # custom1
        {'action': 'block', 'category': 141}  # custom2
    ]
    for i in filters:
        i['id'] = i['category'] if i['category'] != 0 else 142

    response = fortigate.config_webfilter_profile(
        'CHARTER_DEFAULT', filters=filters, error_allow=True,
        rate_server_ip=True, vdom=vdom)
    if response is None:
        logger.warning('Failed to configure webfilter profile')
        errors.append('Failed to configure webfilter profile')

    logger.info('Ending default webfilter script!')
    return errors


def config_custom_webfilter(
        ip, key, logger, name, filters, comment='', error_allow='enable',
        feature_set='flow', options=None, rate_server_ip='enable', vdom=None):
    logger.info('Beginning custom webfilter script!')
    errors = []
    fortigate = Fortigate(ip, key, logger)

    error_allow = True if error_allow == 'enable' else False
    rate_server_ip = True if rate_server_ip == 'enable' else False
    for i in filters:
        i['category'] = i.get('category', None)
        if type(i['category']) is not int:
            filters.remove(i)
        i['id'] = i['category'] if i['category'] != 0 else 142
        if str(i['category']) not in WEBFILTER_CATEGORIES:
            logger.warning(
                'Invalid webfilter category - {}'.format(i['category']))
            errors.append(
                'Invalid webfilter category - {}'.format(i['category']))
            filters.remove(i)

    response = fortigate.config_webfilter_profile(
        name, filters=filters, comment=comment, error_allow=True,
        feature_set=feature_set, options=options, rate_server_ip=True,
        vdom=vdom)
    if response is None:
        logger.warning('Failed to configure webfilter profile')
        errors.append('Failed to configure webfilter profile')

    logger.info('Ending custom webfilter script!')
    return errors
