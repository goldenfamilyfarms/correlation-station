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
import os


logger = set_up_logging()

config = set_up_config()


def get_circuit_details_topology_from_beorn(cid) -> dict:
    """
    this function take the circuit id returns a circuit details topology dictionary.
    """

    
    logger.info('#' * 60)
    logger.info(f' ----> {os.path.basename(__file__)} <--')
    logger.info('#' * 60)

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
