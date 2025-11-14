import configparser
import concurrent.futures
import requests
import configparser
import logging
import pendulum
import logging.config
from my_modules.mdso import get_token, delete_token
import subprocess
import os
from my_modules import common
import ast
from common_plan import Environment_Setup


# log gathering script magic
logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class RaLogs(Environment_Setup):
    def __init__(self, fqdn_resourceType_dictionary, cid, now, token, config, product_name, setup_directory_name, setup_log_dir_path):
        self.fqdn_resourceType_dictionary = fqdn_resourceType_dictionary
        self.cid = cid
        self.now = now
        self.token = token
        self.config = config
        self.product_name = product_name
        self.setup_directory_name = setup_directory_name
        self.setup_log_dir_path = setup_log_dir_path

    def ra_log_function(ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server_ip):
        subprocess.call(['bash', '/home/all-product-logs-multiprocess/mdso_ra_log_capture_test.sh', ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server_ip])
        logger.info(f'Sending {cid} - {ra_resource_id} to bash script to gather RA Logs for {directory_name} - ')

    def provider_resource_Id_get(self):
        '''Gathers the provider resource Id and greps MDSO for the RA logs for each device:

        Keyword arguements:

        fqdn_resourceType_dictionary: {'JFVLINBJ2CW.CHTRSE.COM': ['rajuniper', 'junipereq.resourceTypes.NetworkFunction'],
                                        'JFVLINBJ0QW.CHTRSE.COM': ['rajuniper', 'junipereq.resourceTypes.NetworkFunction']}
        cid: circuit id
        now: time
        token: mdso token
        example Id format:
            bpo_5c043a11-b7be-4979-b53a-df8995709a5a_5c37c84c-8637-448c-b68d-a4627ad40a6b
        '''

        # mdso specific info
        mdso_server = self.config['mdso']['url']
        mdso_host_list = ast.literal_eval(self.config['mdso']['mdso_servers'])

        logger.info('#' * 60)
        logger.info(f'    - Calling ra_mdso_grab.py to grab RA logs for {self.product_name} -')
        logger.info('#' * 60)

        # logging the arguements passed to this function
        logger.info(f'fqdn_resourceType_dictionary - {self.fqdn_resourceType_dictionary}')
        logger.info(f'cid - {self.cid}')
        logger.info(f'now - {self.now}')
        logger.info(f'token - {self.token}')

        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {self.token}',
        }

        # token and server info to pass to the delete_token()
        logger.info(f'this is my token {self.token}')
        provider_resource_dictionary = {}
        for k, v in self.fqdn_resourceType_dictionary.items():
            params = (
                ('resourceTypeId', v[1]),
                ('q', f'properties.ipAddress:{k}'),
                ('obfuscate', 'true'),
                ('offset', '0'),
                ('limit', '100000'),
            )

            # API call to MDSO
            response = requests.get(f'{mdso_server}/bpocore/market/api/v1/resources', headers=headers, params=params, verify=False)

            data = response.json()
            logger.info(f'FQDN: {k}')
            # logger.info(f'response json: {data}')
            check = bool(data['items'])
            logger.info(f'Is there providerResourceID available for {k} in the api response: {check}')
            if check is True:
                # this variable equals the coordinates to the providerResourceID
                provider_resource_id = data['items'][0].get('providerResourceId')
                logger.info(f'providerResourceID: {provider_resource_id}')
                provider_resource_dictionary[k] = provider_resource_id
                logger.info(f'provider_resource_dictionary: {provider_resource_dictionary}')
            else:
                pass

        # this for loop determines the value of the fqdn and dir_name variables as well as captures the RA logs based on condition
        for key, val in self.fqdn_resourceType_dictionary.items():
            fqdn = key
            dir_name = val[0]
            logger.info(f'Circuit ID: {self.cid}')
            logger.info(f'FQDN: {fqdn}')
            logger.info(f'ra directory: {dir_name}')

            # daily generated directory name like the one bash file creates example 10_11_22-Network_Service_Logs 
            directory_name = f"{self.setup_directory_name}"

            for key2, val2 in provider_resource_dictionary.items():
                server1 = "50.84.225.156"
                server2 = "50.84.225.157"
                server3 = "50.84.225.158"
                if fqdn in key2:
                    ra_resource_id = val2
                    logger.info(f'ra source ID: {ra_resource_id}')
                    logger.info('sending to bash script loop')
                    logger.info(f'Passing arguements ra resource id = {ra_resource_id}, circuit id = {self.cid}, fqdn = {fqdn}, directory name = {dir_name} to scp_ra_log_grabber.sh to Gather RA log')
                    try:
                        for server in mdso_host_list:
                            with concurrent.futures.ProcessPoolExecutor() as executor:
                                executor.submit(RaLogs.ra_log_function, ra_resource_id, self.cid, fqdn, dir_name, directory_name, self.setup_log_dir_path, server)
                        try:
                            subprocess.run([f'cp {self.setup_log_dir_path}/{directory_name}/{self.cid}/{fqdn}/* {self.setup_log_dir_path}/{directory_name}/{self.cid}/{fqdn}/ra-log-download'], shell=True)
                            subprocess.run([f'cd {self.setup_log_dir_path}/{directory_name}/{self.cid}/{fqdn} && mmv "*" "#1.txt"'], shell=True)
                        except Exception as e:
                            logger.info(f'there was and issue adding the .txt extension for {self.cid}. exception: {e}')                 
                    except:
                        logger.info('issue with gathering RA log')
