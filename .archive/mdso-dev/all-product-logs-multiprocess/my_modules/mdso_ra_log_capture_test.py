import requests
import concurrent.futures
import configparser
import logging
import pendulum
import logging.config
from my_modules.mdso import get_token, delete_token
import subprocess
import os
from my_modules import common


# log gathering script magic
logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))
config = configparser.ConfigParser()
config.read('/home/network_service/setup.cfg')

# mdso specific info
mdso_server = config['mdso']['url']
mdso_host_list = config['mdso']['mdso_servers']
product_name = config['mdso']['product_name']

# info pulled from the setup.cfg to fill in the directory information
setup_directory_name = config['log_capture_setup_info']['directory_name']
setup_log_dir_path = config['log_capture_setup_info']['log_dir_path']

# imported function that adds a little color to text
WHITE, BLACK, RED, GREEN, YELLOW, BLUE, PURPLE, Cyan, RESET = common.text_color()

def ra_log_function(ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server_ip):
    subprocess.call(['bash', '/home/all-product-logs-multiprocess/mdso_ra_log_capture_test.sh', ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server_ip])


def provider_resource_Id_get(fqdn_resourceType_dictionary, cid, now, token):
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
    logger.info('#' * 60)
    logger.info(f'    - Calling ra_mdso_grab.py to grab RA logs for {product_name} -')
    logger.info('#' * 60)

    # logging the arguements passed to this function
    logger.info(f'fqdn_resourceType_dictionary - {fqdn_resourceType_dictionary}')
    logger.info(f'cid - {cid}')
    logger.info(f'now - {now}')
    logger.info(f'token - {token}')

    headers = {
        'accept': 'application/json',
        'Authorization': f'Bearer {token}',
    }

    # token and server info to pass to the delete_token()
    logger.info(f'this is my token {GREEN}{token}{RESET}')
    provider_resource_dictionary = {}
    for k, v in fqdn_resourceType_dictionary.items():
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
        logger.info(f'response json: {data}')
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
    for key, val in fqdn_resourceType_dictionary.items():
        fqdn = key
        dir_name = val[0]
        logger.info(f'Circuit ID: {cid}')
        logger.info(f'FQDN: {fqdn}')
        logger.info(f'ra directory: {dir_name}')

        # daily generated directory name like the one bash file creates
        directory_name = now.strftime(f"%m_%d_%y-{setup_directory_name}")

        for key2, val2 in provider_resource_dictionary.items():
            server1 = "50.84.225.156"
            server2 = "50.84.225.157"
            server3 = "50.84.225.158"
            if fqdn in key2:
                ra_resource_id = val2
                logger.info(f'ra source ID: {ra_resource_id}')
                logger.info('sending to bash script loop')
                logger.info(f'Passing arguements ra resource id = {ra_resource_id}, circuit id = {cid}, fqdn = {fqdn}, directory name = {dir_name} to scp_ra_log_grabber.sh to Gather RA log')
                # try:
                #     subprocess.call(['bash', '/home/automation-utils-universal-logger/mdso_ra_log_capture.sh', ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, mdso_host_list])
                # except:
                #     logger.info('issue with gathering RA log')
                try:
                    with concurrent.futures.ProcessPoolExecutor() as executor:
                        executor.submit(ra_log_function, ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server1)
                        executor.submit(ra_log_function, ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server2)
                        executor.submit(ra_log_function, ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server3)
                except:
                    logger.info('issue with gathering RA log')
    # return ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server1, server2, server3



if __name__ == '__main__':
    
    fqdn_resourceType_dictionary = ''
    cid = ''
    now = ''
    token = ''

    ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server1, server2, server3 = provider_resource_Id_get(fqdn_resourceType_dictionary, cid, now, token)


    try:
        with concurrent.futures.ProcessPoolExecutor() as executor:
            executor.submit(ra_log_function, ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server1)
            executor.submit(ra_log_function, ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server2)
            executor.submit(ra_log_function, ra_resource_id, cid, fqdn, dir_name, directory_name, setup_log_dir_path, server3)
    except:
        logger.info('issue with gathering RA log')
    # token = get_token(config=config, server=mdso_server)

    # # this is the new dictionary that will be passed from fqdn_beorn.py
    # fqdn_resourceType_dictionary = {'JFVLINBJ2CW.CHTRSE.COM': ['rajuniper', 'junipereq.resourceTypes.NetworkFunction'], 'JFVLINBJ0QW.CHTRSE.COM': ['rajuniper', 'junipereq.resourceTypes.NetworkFunction'], 'JFVLINBX1ZW.CML.CHTRSE.COM': ['radra', 'radra.resourceTypes.NetworkFunction']}

    # now = pendulum.now('America/Chicago')

    # cid = "51.L1XX.008480..TWCC"

    # provider_resource_dictionary = provider_resource_Id_get(fqdn_resourceType_dictionary, cid, now, token)
    # print(provider_resource_dictionary)

    # # like the name implies to delete the mdso token
    # delete_token(token, mdso_server)

