import os
import pendulum
from datetime import datetime
from my_modules import webexteams_sender
import time
import logging
import logging.config
import configparser
from os import path


logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))
config = configparser.ConfigParser()
config.read('/home/setup.cfg')

# info gathered from setup.cfg
setup_directory_name = config['log_capture_setup_info']['directory_name']
setup_log_dir_path = config['log_capture_setup_info']['log_dir_path']
setup_room_id = config['webex_room_id']['room_id']
setup_product_name = config['mdso']['product_name']

logger.info('#' * 60)
logger.info(f'    - Running webex_logs_sender.py for {setup_product_name}')
logger.info('#' * 60)

# this variable is used for the real time and is used in the main function parameters
now = pendulum.now('America/Chicago')

# un comment the below line if you need to send a previous days log
# now = now.subtract(days=1)

# adjusted the time zone to UTC since sensor hosts are set to UTC (5hrs ahead)
dt = now.set(tz='America/Chicago').set(tz='UTC')

# webex login
webex_api = webexteams_sender.webex_login()

# this is the webex room where the logs will be sent
room_id = setup_room_id

# daily generated directory name like the one bash file creates
directory_name = now.strftime(f"%m_%d_%y-{setup_directory_name}")

# path to the latest daily logs on the new log server
dir_path = f'{setup_log_dir_path}/{directory_name}/'

# verifies that path exists before trying to send out anything via webex
dir_path_check = os.path.exists(dir_path)
if dir_path_check:
    files = os.listdir(dir_path)

    # loops through the Daily Service_Mapper_Logs directory and sends out each zipped log via webex
    for item in files:
        path = f'{dir_path}{item}'
        file = [path]
        try:
            webexteams_sender.webex_group_send(webex_api, room_id, file)
        except Exception:
            logger.info(f'issue with webex: {Exception}')
            time.sleep(5)
else:
    logger.info(f'Nothing to send no new directory created for todays logs')