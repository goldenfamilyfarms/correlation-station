
import requests
import configparser
import logging
import logging.config
import subprocess
import os
import json
from os import path
from my_modules.common import set_up_logging, set_up_config

'''
Work in progress it parses the tosca.resourceTypes.TraceLog product for the circuitID and saves it to a file.

params:

log_dir_path/temp_file/dir/
directory_name
dir
cid
'''

logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)
config = set_up_config()


def orch_trace_get(cid, resource_id, token, config, product_name):
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
    logger.info(f'    - for Circuit Id: {cid}')
    logger.info('#' * 60)

    resource_type = "tosca.resourceTypes.TraceLog"
    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }
    # do to the large amount of logs in mdso i decided to do a count of total logs and parse the bottom two hundred
    data_count = 10


    def get_trace_log_via_api_call(origination_id):
        url = '{}/bpocore/market/api/v1/resources?resourceTypeId={}&q=properties.origination_id%3A{}&limit={}'.format(mdso_server, resource_type, origination_id, data_count)
        return requests.get(url, headers=headers, verify=False)


    response = get_trace_log_via_api_call(resource_id)

    return response.json()

if __name__ == '__main__':
    
    # log gathering script magic
    logging.config.fileConfig(fname=r'C:\\Users\\P2160442\Desktop\\Git_Projects\\All-Product-Logs-Multiprocess\\all-product-logs-multiprocess\\logging.cfg', disable_existing_loggers=False)
    logger = logging.getLogger(os.path.basename(__file__))
    config = configparser.ConfigParser()
    # config.read('setup_test.cfg')
    config.read(r'C:\\Users\\P2160442\Desktop\\Git_Projects\\All-Product-Logs-Multiprocess\\all-product-logs-multiprocess\\setup_test.cfg')
    directory_name = 'orch_test'
    token = '7410f029805920562718'
    product_name = 'ServiceMapper'
    resource_type = 'tosca.resourceTypes.TraceLog'

    cid = '70.L1XX.009657..CHTR'

    log_dir_path = r"C:\\Users\\P2160442\Desktop\\Git_Projects\\All-Product-Logs-Multiprocess\\all-product-logs-multiprocess\\my_modules"
    dir = 'test'
    resource_id = 'd88f3990-3233-11ee-b60a-4b26a4c0dbea'
    # orch_trace_get(dir, cid, token, directory_name, config, product_name)
    orch_trace_get(dir, cid, resource_id, token, directory_name, config, product_name)
    # orch_trace_get(log_dir_path, dir, cid)
    # orch_trace_get(dir, cid)
