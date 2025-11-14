import requests
import json
# from prettyprinter import pprint
import configparser
import json
import logging
import logging.config
import pandas as pd
import pendulum
import sys, os


# log gathering script magic
logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))
config = configparser.ConfigParser()

def fqdn_vendor_get(config, cid):
    '''
    this function take the circuit id and gets FQDN and Vendor brand of each device then converts the
    vendor name to the appropriate resourceTypeId and returns a dictionary.
    '''

    logger.info('#' * 60)
    logger.info('    - Calling fqdn_beorn.py to parse beorn json data -')
    logger.info('#' * 60)

    beorn_url = config['mdso']['beorn_url']
    fqdn_dictionary = {}

    # api call to retrieve granite circuit details
    beorn = requests.get(f'{beorn_url}{cid}')
    logger.info(f'url use to search granite data: {beorn_url}')
    data = json.loads(beorn.text)

    # the length of a healthy beorn json result is 8 any thing less is bypassed to the next circuit
    data_validation = len(json.loads(beorn.text))

    # second try api call to retrieve granite circuit details just incase and only if needed
    if data_validation <= 7:
        # secondary api call to retrieve granite circuit details
        logger.info(f'Trying again. Beorn data is incomplete and showing {data_validation} out of 8 elements')
        beorn = requests.get(f'{beorn_url}{cid}')
        data = json.loads(beorn.text)
        data_validation = len(json.loads(beorn.text))

    # verifies the validity of the beorn json before continuing. Was needed due to the filtering and just not giving data when issues were discovered
    if data_validation >= 8:
        logger.info(f'Beorn data checks out good with {data_validation} out of 8 elements')
        service_type = data['serviceType']
        service_type_check = bool(service_type)
        logger.info(f'service type: {service_type}')
        aloc_path = data['topology'][0]['data']['node']

        # loops through beorn to gather FQDN and Vendor of each device in the path
        for i in range(len(aloc_path)):
            beorn_fqdn_name = data['topology'][0]['data']['node'][i]['name'][6]['value']
            beorn_fqdn_value = data['topology'][0]['data']['node'][i]['name'][2]['value']
            logger.info(f'fqdn: {beorn_fqdn_name}')
            logger.info(f'vendor: {beorn_fqdn_value}')
            if beorn_fqdn_name == None or beorn_fqdn_value == None:
                logger.info(f'FQDN or Vendor for a device is missing in beorn.  moving on to next device')
            else:
                fqdn_dictionary[beorn_fqdn_name] = beorn_fqdn_value.lower()
            if service_type != 'FIA':
                zloc_path = data['topology'][1]['data']['node']
                for i in range(len(zloc_path)):
                    beorn_fqdn_name = data['topology'][1]['data']['node'][i]['name'][6]['value']
                    beorn_fqdn_value = data['topology'][1]['data']['node'][i]['name'][2]['value']
                    if beorn_fqdn_name == None or beorn_fqdn_value == None:
                        logger.info(f'FQDN or Vendor for a device is missing in beorn.  moving on to next device')
                    else:
                        fqdn_dictionary[beorn_fqdn_name] = beorn_fqdn_value.lower()
                        logger.info(f'fqdn_dictionary: {fqdn_dictionary}')

        # vender dictionary based of vendor type of device
        vender_log_dir_dictionary = {"bpraadva": "bpraadva.resourceTypes.NetworkFunction",
                                     "rajuniper": "junipereq.resourceTypes.NetworkFunction",
                                     "radra": "radra.resourceTypes.NetworkFunction",
                                     "bpracisco": "bpracisco.resourceTypes.NetworkFunction"}

        fqdn_resourceType_dictionary = {}

        # loops the dictionaries to convert the fqdn_dictionary values to resouceTypeId's
        for key, val in fqdn_dictionary.items():
            for key1, val1 in vender_log_dir_dictionary.items():
                if val in key1:
                    # fqdn_resourceType_dictionary.update({key: val1})
                    fqdn_resourceType_dictionary.update({key: [key1, val1]})

        logger.info(f'fqdn_resourceType_dictionary: {fqdn_resourceType_dictionary}')
        return fqdn_resourceType_dictionary
    else:
        # add empty dictionaries so that the return would not trigger a NoneType error
        logger.info(f'On second try beorn json data is missing needed data. Only showing {data_validation} out of a possible 8 in element length So passing to the next circuit')
        logger.info(f'Captured beorn json data {data}')
        fqdn_resourceType_dictionary = {}
        vender_log_dir_dictionary = {}
        return fqdn_resourceType_dictionary


if __name__ == "__main__":

    cid = "23.L1XX.001022..CHTR"
 
    fqdn_resourceType_dictionary = fqdn_vendor_get(cid)

    print(fqdn_resourceType_dictionary)
