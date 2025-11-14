# Call MDSO for all CPE Activation Resources

import argparse
import configparser
import json
import logging
import logging.config
import os
import pandas as pd
import requests
import sys
import urllib3
urllib3.disable_warnings()


logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(__name__)

def get_token(config, server):

    # Establish connection to MDSO
    logger.info('Establishing the authorization to MDSO')

    mdso_user = config['mdso']['user']
    mdso_pass = config['mdso']['pass']

    header = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    body = json.dumps(
        {
            'username': mdso_user,
            'password': mdso_pass,
            'tenant': 'master'
        }
    )

    response = requests.post(
        server + '/tron/api/v1/tokens',
        data=body,
        headers=header,
        verify=False
    )

    if 'token' in response.json():
        token = response.json()['token']
        logger.info('Authentication Successful.')

    else:
        logger.exception('Unable to authenticate. Please check url, username and password.')
        sys.exit(127)

    return token


def delete_token(token, server):

    logger.info('Deleting token authorization to MDSO')

    header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
        }

    del_response = requests.delete('{}/tron/api/v1/tokens/{}'.format(server, token), headers=header, verify=False)

    if del_response.status_code == 204:
        logger.info('Token Deleted Successfully')
    else:
        logger.exception('Issues Deleting Token')
        sys.exit(129)


def get_market_resourceType(token, server, resourceTypeId, debug=False):

    logger.info('Requesting 1200 Resources containing: charter.resourceTypes.' + resourceTypeId)

    header = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + token
        }

    # this has been modified to use the setup.cfg to determine which server to to use in the api call
    data_count_response = requests.get(f'{server}/bpocore/market/api/v1/resources/count?exactTypeId=charter.resourceTypes.{resourceTypeId}', headers=header, verify=False)

    # do to the large amount of logs in mdso i decided to do a count of total logs and parse the bottom two hundred
    data_count = data_count_response.json()['count']
    logger.info(f'Total MDSO log history for {resourceTypeId}: {data_count}')

    url = '{}/bpocore/market/api/v1/resources?resourceTypeId=charter.resourceTypes.' \
      '{}&limit={}'.format(server, resourceTypeId, data_count)

    try:
        response = requests.get(url, headers=header, verify=False)

        response_info = response.json()

        if response.status_code == 200:
            # the :300 at the end represents the last 300 for parsing
            items = response.json()['items']

        else:
            logger.info('No Resources Found for: ' + resourceTypeId)
            sys.exit(126)

    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.exception('Can\'t connect to MDSO')
        sys.exit(127)

    if debug:
        print(json.dumps(items, indent=2))

    return items

