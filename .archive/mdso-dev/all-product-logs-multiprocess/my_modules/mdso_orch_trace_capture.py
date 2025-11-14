
import requests
import configparser
import logging
import logging.config
from my_modules import common
import subprocess
import os
import json
from os import path

'''
Work in progress it parses the tosca.resourceTypes.TraceLog product for the circuitID and saves it to a file.

params:

log_dir_path/temp_file/dir/
directory_name
dir
cid
'''

# log gathering script magic
logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))
config = configparser.ConfigParser()

# imported function that adds a little color to text
WHITE, BLACK, RED, GREEN, YELLOW, BLUE, PURPLE, Cyan, RESET = common.text_color()

# function to gather the orch trace per circuitID
def orch_trace_get(log_dir_path, dir, cid, token, directory_name, config, product_name):
    '''
    params:
        log_dir_path = is the beginning path
        dir = name of subdirectory
        cid = circuit id

    it all is used for ........file_path = os.path.join(log_dir_path, 'temp_file', dir)
    '''

    # server url located in setup.cfg
    mdso_server = config['mdso']['url']

    logger.info('#' * 60)
    logger.info(f'    - Calling sm_orch_trace.py to grab orch traces for {product_name}-')
    logger.info('#' * 60)

    resource_type = "tosca.resourceTypes.TraceLog"

    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }

    # token and server info to pass to the delete_token()
    print(f'this is my token {GREEN}{token}{RESET}')

    data_count_response = requests.get(f'{mdso_server}/bpocore/market/api/v1/resources/count?exactTypeId={resource_type}', headers=headers, verify=False)
    offset_difference = 100

    # do to the large amount of logs in mdso i decided to do a count of total logs and parse the bottom two hundred
    data_count = 10
    logger.info(f'Total MDSO log history for {resource_type}: {data_count}')

    # creates circuit id with the .orch_trace at the end to search for label
    orchtrace_name = f'{cid}.orch_trace'
    url = '{}/bpocore/market/api/v1/resources?resourceTypeId={}&p=label%3A%20{}&limit={}'.format(mdso_server, resource_type, orchtrace_name, data_count)

    # response is the variable containing the get request
    response = requests.get(url, headers=headers, verify=False)

    data = response.json()
 
    # check has no use now but may use
    check = bool(data["items"])
    logger.info(f'orch trace available to parse: {check}')

    # file_path = os.path.join(log_dir_path, 'temp_file', dir)
    file_path = os.path.join(log_dir_path, directory_name, dir)
    isExists = os.path.exists(file_path)
    if isExists is not True:
        logger.info("directory doesn't exist")
    else:
        logger.info('directory exists continuing to next step')
        logger.info(f'file path: {file_path}')

        # parses the json from the api response and searches for the orchtrace_name and saves it to a txt file
        for i in range(len(data['items'])):
            if orchtrace_name in data['items'][i]['label']:
                with open(f'{file_path}/{cid}_orch_trace.txt', 'w') as outfile:
                    json.dump(data['items'][i], outfile, indent=4)


if __name__ == '__main__':

    resource_type = 'tosca.resourceTypes.TraceLog'

    cid = '80.L1XX.005054..CHTR'

    log_dir_path = r"C:\Users\P2160442\Desktop"
    dir = '80.L1XX.005054..CHTR'

    orch_trace_get(log_dir_path, dir, cid)
