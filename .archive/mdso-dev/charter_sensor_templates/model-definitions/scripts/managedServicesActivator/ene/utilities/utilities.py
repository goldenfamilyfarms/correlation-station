import logging
import logging.config
from ipaddress import IPv4Address, ip_interface, ip_network
from unittest.mock import Mock
from time import sleep
import requests
import yaml
from requests.exceptions import (
    ConnectionError, ConnectTimeout, HTTPError, ReadTimeout)

JSONDecodeError = Exception


def check_route(ip, destination):
    '''
    Verify that an IP is within a given subnet. Returns True/False.

    ----------------------------------------------------------------------------
    Arguments
    ---------
    ip:  IPv4 address or CIDR
        e.g. 1.1.1.1, 10.0.0.1/32, 172.16.0.0/255.255.255.0

    destination:  IPv4 network CIDR

    ----------------------------------------------------------------------------
    Returns
    -------
    bool

    '''
    ip = str(ip).strip().replace(' ', '/')
    destination = str(destination).strip().replace(' ', '/')
    try:
        ip = ip_interface(ip)
        destination = ip_network(destination)
    except ValueError:
        return False

    if ip in destination:
        return True
    else:
        return False


def get_ip_info(ip):
    '''
    Verify that given IP is valid. Return the IP's host address, subnet mask,
    network CIDR, prefix length, and whether or not its a private IP as a tuple.

    ----------------------------------------------------------------------------
    Arguments
    ---------
    ip:  IPv4 address or CIDR

    ----------------------------------------------------------------------------
    Returns
    -------
    ('10.10.150.2', '255.255.255.0', '10.10.150.0/24', 24, True)

    '''
    try:
        ip = ip_interface(str(ip).strip().replace(' ', '/'))
    except ValueError:
        return None
    return (str(ip.ip), str(ip.netmask), str(ip.network), ip._prefixlen, IPv4Address(ip.ip).is_private)


def get_model(serial):
    '''
    Determine FortiGate model by the device's serial number.

    ----------------------------------------------------------------------------
    Arguments
    ---------
    serial:  FortiGate serial number

    ----------------------------------------------------------------------------
    Returns
    -------
    Device model:  e.g. 60E, 100F, 2000E, etc

    '''
    model_lookup = {
        'FGT60E': '60E',
        'FGT60F': '60F',
        'FGT61E': '61E',
        'FGT61F': '61F',
        'FG200E': '200E',
        'FG201E': '201E',
        'FG5H0E': '500E',
        'FG5H1E': '501E',
        'FG6H0E': '600E',
        'FG6H1E': '601E',
        'FGT2KE': '2000E',
        'FG200D': '200D',
        'FG100D': '100D',
        'FGT80C': '80C',
        'FGT90D': '90D',
        'FGT1KD': '1000D',
        'FGT3HD': '300D',
        'FGT5HD': '500D',
        'FG600C': '600C',
        'FG100F': '100F',
        'FG1K5D': '1500D',
        'FGT1KC': '1000C',
        'FG3K4E': '3400E',
        'FG39E6': '3960E',
        'FGT40F': '40F',
        'FGVM02': 'VM02',
        'FG300C': '300C',
        'FG3K6E': '3600E'
    }
    try:
        return model_lookup[str(serial).strip()[:6]]
    except KeyError:
        return None


def send_request(
        url, action="GET", attempts=3, headers=None, logger=None, params=None,
        payload=None, timeout=(5, 10), verify=False):
    '''
    Wrapper for HTTP requests to include error handling.

    ------------------------------------------------------------------------
    Arguments
    ---------
    url:  URL for the new Request object

    action:  Method for the new Request object: GET, POST, PUT, or DELETE

    attempts:  Number of times the request will be sent before giving up

    headers:  Dictionary of HTTP Headers to send with the Request

    params:  Dictionary of parameters to add to the URL. Any key with a value
        of None will not be added to the URL.

    payload:  A JSON serializable object to send in the body of the Request

    timeout:  How many seconds to wait for the server to send data before
        giving up, as a float, or a (connect timeout, read timeout) tuple

    verify:  Controls whether to verify the server's TLS certificate

    ------------------------------------------------------------------------
    Returns
    -------

    '''
    if headers is None:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "deflate",
            "Content-Type": "application/json"
        }

    if params is None:
        params = {}

    if logger is None:
        logger = Mock()

    tries = 0
    while (tries < attempts):
        tries += 1
        logger.info('> {} | {}'.format(url, action))
        try:
            if action == 'GET':
                response = requests.get(
                    url=url, headers=headers, params=params,
                    timeout=timeout, verify=verify)

            elif action == 'POST':
                attempts = 1
                response = requests.post(
                    url=url, headers=headers, json=payload, params=params,
                    timeout=timeout, verify=verify)

            elif action == 'PUT':
                attempts = 1
                response = requests.put(
                    url=url, headers=headers, json=payload, params=params,
                    timeout=timeout, verify=verify)

            elif action == 'DELETE':
                attempts = 1
                response = requests.delete(
                    url=url, headers=headers, json=payload, params=params,
                    timeout=timeout, verify=verify)

            else:
                print('Method not supported: {}'.format(action))
                return None

        except (ConnectTimeout, ReadTimeout):
            logger.warning('>> Timeout, retry')
            continue

        except (ConnectionError, HTTPError):
            logger.warning('>> Failed to establish a new connection')
            break

        if response.ok:
            logger.info(
                '>> Response: {} {} - '.format(action, response.status_code),
                '{}'.format(response.reason))
            if response.text:
                try:
                    return response.json()
                except JSONDecodeError:
                    return response.text

        # Handle rate limiting
        elif response.status_code == 429:
            logger.warning(
                '>> Response: {} {} - '.format(action, response.status_code),
                '{}'.format(response.reason))
            sleep(1)
            continue

        # Handle expected server error codes
        elif response.status_code in (
                400, 401, 403, 404, 405, 413, 424, 500):
            logger.warning(
                '>> Response: {} {} - '.format(action, response.status_code),
                '{}'.format(response.reason))
            break

        # Catch all
        else:
            logger.warning(
                '>> Response: {} {} - '.format(action, response.status_code),
                '{}'.format(response.reason))
            response.raise_for_status()

    # Return None if unsuccessful after all attempts
    logger.warning('>> Unable to get response after all attempts')
    return None


def setup_logger(config_path=None, log_name='utilities'):
    try:
        with open(config_path) as file:
            config = yaml.safe_load(file.read())
            logging.config.dictConfig(config)
        logger = logging.getLogger(log_name)
    except (FileNotFoundError, TypeError):
        logger = Mock()

    return logger
