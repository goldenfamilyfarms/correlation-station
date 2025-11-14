
import requests
import json

from prettyprinter import pprint
import configparser
import json
import logging
import logging.config
import pandas as pd
import pendulum
from my_modules.common import set_up_logging, set_up_config
import sys, os

'''not being used just for testing'''

logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)
config = set_up_config()

class Device:
    def __init__(self, device):
        self.details = device["name"]
        self.edgepoint_details = device["ownedNodeEdgePoint"]
        self.tid = self.details[0]["value"]
        self.role = self.details[1]["value"]
        self.vendor = self.details[2]["value"]
        self.model = self.details[3]["value"]
        self.management_ip = self.details[4]["value"]
        self.fqdn = self.details[6]["value"]
        self.equipment_status = self.details[7]["value"]
        self.network_interface = self.edgepoint_details[0]["name"][0]['value']
        self.handoff_interface = self.edgepoint_details[1]["name"][0]['value']
        self.port_role = self.edgepoint_details[1]["name"][1]["value"]


def get_circuit_details_topology_from_beorn(cid) -> dict:
    """
    this function take the circuit id returns a circuit details topology dictionary.
    """

    logger.info("#" * 60)
    logger.info("    - Parsing beorn json data for  FQDN and Vendor info -")
    logger.info("#" * 60)

    beorn_url = config["mdso"]["beorn_url"]

    # api call to retrieve granite circuit details
    beorn = requests.get(f"{beorn_url}{cid}")
    logger.info(f"url use to search granite data: {beorn_url}")
    data = json.loads(beorn.text)

    # the length of a healthy beorn json result is 8 any thing less is bypassed to the next circuit
    data_validation = len(json.loads(beorn.text))

    # second try api call to retrieve granite circuit details just incase and only if needed
    if data_validation <= 7:
        # secondary api call to retrieve granite circuit details
        logger.info(
            f"Trying again. Beorn data is incomplete and showing {data_validation} out of 8 elements"
        )
        beorn = requests.get(f"{beorn_url}{cid}")
        data = json.loads(beorn.text)

    return data


cid = '90.L1XX.003259..CHTR'

def get_fqdn_and_managementIP_from_beorn(cid):
    circuit_details = get_circuit_details_topology_from_beorn(cid)
    for topology in circuit_details["topology"]:
        for device_data in topology["data"]["node"]:
            device = Device(device_data)
            if device.tid == 'POMOCAAR2ZW':
                print(device.fqdn)
                print(device.management_ip)
                print(device.network_interface)
                print(device.handoff_interface)
                print(device.port_role)
                print(device.model)


get_fqdn_and_managementIP_from_beorn(cid)
