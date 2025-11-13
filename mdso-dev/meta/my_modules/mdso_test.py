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
from my_modules.common import set_up_logging, set_up_config
import os


"""
this is for testing with log_capture_test2.py.  the fname on line 26 is pointing to the laptop windows type path


"""

urllib3.disable_warnings()
logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)
config = set_up_config()

def get_token(config, server):

    # Establish connection to MDSO
    logger.info("Establishing the authorization to MDSO")

    mdso_user = config["mdso"]["user"]
    mdso_pass = config["mdso"]["pass"]

    header = {"Content-Type": "application/json", "Accept": "application/json"}

    body = json.dumps(
        {"username": mdso_user, "password": mdso_pass, "tenant": "master"}
    )

    response = requests.post(
        server + "/tron/api/v1/tokens", data=body, headers=header, verify=False
    )

    if "token" in response.json():
        token = response.json()["token"]
        logger.info("Authentication Successful.")

    else:
        logger.exception(
            "Unable to authenticate. Please check url, username and password."
        )
        sys.exit(127)

    return token


def delete_token(token, server):

    logger.info("Deleting token authorization to MDSO")

    header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
    }

    del_response = requests.delete(
        "{}/tron/api/v1/tokens/{}".format(server, token), headers=header, verify=False
    )

    if del_response.status_code == 204:
        logger.info("Token Deleted Successfully")
    else:
        logger.exception("Issues Deleting Token")
        sys.exit(129)

def get_resource_by_type_and_properties(server, token, resource_type, properties):
    header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
    }

    endpoint = f"{server}/bpocore/market/api/v1/resources?resourceTypeId={resource_type}"

    for key, value in properties.items():
        endpoint += "&q=properties.{}:{},".format(str(key), str(value))

    response = requests.get(endpoint, headers=header, verify=False)

    return response["items"]

def get_market_resourceType(token, server, resourceTypeId, debug=False):

    logger.info(f'Requesting Resources containing: charter.resourceTypes.{resourceTypeId}')

    header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
    }

    # this has been modified to use the setup.cfg to determine which server to to use in the api call
    data_count_response = requests.get(
        f"{server}/bpocore/market/api/v1/resources/count?exactTypeId=charter.resourceTypes.{resourceTypeId}",
        headers=header,
        verify=False,
    )

    # do to the large amount of logs in mdso i decided to do a count of total logs and parse the bottom two hundred
    data_count = data_count_response.json()["count"]

    url = (
        "{}/bpocore/market/api/v1/resources?resourceTypeId=charter.resourceTypes."
        "{}&limit={}".format(server, resourceTypeId, data_count)
    )

    try:
        response = requests.get(url, headers=header, verify=False)

        response_info = response.json()

        if response.status_code == 200:
            # the :300 at the end represents the last 300 for parsing
            items = response.json()["items"]

        else:
            logger.info("No Resources Found for: " + resourceTypeId)
            sys.exit(126)

    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        sys.exit(127)

    if debug:
        print(json.dumps(items, indent=2))

    return items

def get_market_resourceType_network_function_by_tid(token, tid, debug=False):
    server = "https://austx-mdso-vip.chtrse.com"
    # hostname = '10.12.152.139'
    # tid = 'CLEWOHKZ4ZW'
    resourceTypeId = "NetworkFunction"

    logger.info(f'Requesting Resources containing: charter.resourceTypes.{resourceTypeId}')

    header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bearer " + token,
    }

    # this has been modified to use the setup.cfg to determine which server to to use in the api call
    data_count_response = requests.get(
        f"{server}/bpocore/market/api/v1/resources/count?exactTypeId=tosca.resourceTypes.{resourceTypeId}",
        headers=header,
        verify=False,
    )

    # do to the large amount of logs in mdso i decided to do a count of total logs and parse the bottom two hundred
    data_count = data_count_response.json()["count"]

    url = f'{server}/bpocore/market/api/v1/resources?resourceTypeId=tosca.resourceTypes.{resourceTypeId}&q=label%3A{tid}&obfuscate=true&offset=0&limit=50'


    try:
        response = requests.get(url, headers=header, verify=False)

        response_info = response.json()

        if response.status_code == 200:
            # the :300 at the end represents the last 300 for parsing
            items = response.json()["items"]

        else:
            logger.info("No Resources Found for: " + resourceTypeId)
            sys.exit(126)

    except (ConnectionError, requests.ConnectTimeout, requests.ConnectionError):
        logger.exception("Can't connect to MDSO")
        sys.exit(127)

    if debug:
        print(json.dumps(items, indent=2))

    return items
