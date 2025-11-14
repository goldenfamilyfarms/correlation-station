# main_mdso_log_capture.py - gathers plan-script, orch traces and RA logs

import configparser
import concurrent.futures
import json
import logging
import logging.config
from posixpath import dirname
import pandas as pd
import pendulum
import sys, os
from my_modules import mdso, mdso_fqdn_beorn_capture, mdso_orch_trace_capture
from my_modules.mdso_ra_log_capture import RaLogs
from common_plan import Environment_Setup
import subprocess
import shutil
from shutil import make_archive
from os import path
import ast

logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

class Logs_Main(Environment_Setup):

    def main(self):
        # this variable is used for the real time and is used in the main function parameters
        self.now = pendulum.now('America/Chicago')
        weekday = self.now.format('dddd')
        logger.info(f'the day of the week is: {weekday}')

        # adjusted the time zone to UTC since sensor hosts are set to UTC (5hrs ahead)
        dt = self.now.set(tz='America/Chicago').set(tz='UTC')

        logger.info(f'date time: {dt}')
        try:
            # cid_resourceId_dictionary, directory_name, date_start, token = self.mdso_product_log_retriever(dt, weekday)
            cid_resourceId_dictionary, self.directory_name, self.date_start, token = self.mdso_product_log_retriever()
            # loops through the cid_resourceId_dictionary and passes the key and value to the bash script via command line arguements
            for k, v in cid_resourceId_dictionary.items():
                cid = k.split("_")[0]
                self.dir = k.replace(' ', '_').replace(':', '-').replace('/', '-')[:-13]
                self.resource_id = v

                # defining the path to the logs
                self.log_dir_path = f'{self.setup_log_dir_path}'
                # self.directory_name = f'{self.setup_directory_name}'
                cid_zip_dir_path = f'/{self.log_dir_path}/{self.directory_name}/{self.dir}'

                # because we check every hour on the hour for the latest service_mapper logs we check to see if current ra directory exist if false we create directory and download ra log else we move to the next in line
                isExists = os.path.exists(cid_zip_dir_path)
                if isExists is not True:
                    if self.plan_script:
                        logger.info('#############################################')
                        logger.info(f'if available gathering plan-script logs for {self.product_name}')
                        logger.info('#############################################')
                        try:
                            for server in self.mdso_host_list:
                                with concurrent.futures.ProcessPoolExecutor() as executor:
                                    executor.submit(self.plan_script_function, self.resource_id, self.dir, self.directory_name, self.log_dir_path, server, self.date_start)
                        except Exception as e:
                            logger.info(f'there was an issue gathering plan-script logs for circuit id {cid}. exception: {e}')
                        try:
                            subprocess.run([f'cp {cid_zip_dir_path}/* {cid_zip_dir_path}/plan-script-downloads'], shell=True)
                            subprocess.run([f'cd {cid_zip_dir_path}/plan-script-downloads && mmv "*" "#1.log"'], shell=True)
                        except Exception as e:
                            logger.info(f'there was and issue adding the .log extension for {cid}. exception: {e}')
                        try:
                            subprocess.run([f'cd {cid_zip_dir_path} && mmv "*" "#1.txt"'], shell=True)
                        except Exception as e:
                            logger.info(f'there was and issue adding the .txt extension for {cid}. exception: {e}')
                    if self.orch_trace:
                        try:
                            # orch_trace gathering section
                            mdso_orch_trace_capture.orch_trace_get(self.log_dir_path, self.dir, cid, token, self.directory_name, self.config, self.product_name)
                        except Exception as e:
                            logger.info(f'there was and issue gathering orch trace for circuit id {cid}. exception: {e}')
                    if self.ra_logs:
                        try:
                            # RA logs gathering sectionl
                            fqdn_resourceType_dictionary = mdso_fqdn_beorn_capture.fqdn_vendor_get(self.config, cid)
                        except Exception as e:
                            logger.info(f'there was and issue gathering fqdn_resourceType_dictionary for circuit id {cid}. exception: {e}')
                        try:
                            RaLogs(fqdn_resourceType_dictionary, self.dir, self.now, token, self.config, self.product_name, self.directory_name, self.log_dir_path).provider_resource_Id_get()
                            logger.info(f'Passing arguements to scp_ra_log_grabber.sh to gather RA logs {self.date_start}')
                        except Exception as e:
                            logger.info(f'Something went wrong durring the RA log gathering {cid} : {e}')
                else:
                    logger.info(f'file {dir} exists continuing to next circuit')

            my_list = os.listdir(f'{self.setup_log_dir_path}/')
            logger.info(f'List of all the subdirectory names under the daily directory directory: {my_list}')

            mdso.delete_token(token, self.mdso_server)
        except Exception:
            logger.error("Looks like sompthin failed...", exc_info=True)

    def mdso_product_log_retriever(self):
        '''Collects daily MDSO Product Logs

        Logs Gathered:

        plan-script -- shows detail per product

        orch traces -- shows birds eye view of each product as they are called

        RA logs -- shows device configs

        '''

        logger.info('#' * 60)
        logger.info(f'- Calling main_mdso_log_capture.py to check for and gather logs for {self.product_name} -')
        logger.info('#' * 60)
    
        token = mdso.get_token(self.config, self.mdso_server)
        items = mdso.get_market_resourceType(token, self.mdso_server, self.product_name, debug=False)

        df_mdso_data = pd.io.json.json_normalize(items, sep='_')
        # print(df_mdso_data)

        df_mdso_data['createdAt'] = pd.to_datetime(df_mdso_data['createdAt'])
        # print(df_mdso_data)

        cid_resourceId_dictionary = {}

        # date_start is set to -3 hour from current time now
        date_start = self.now.subtract(hours=int(self.time_range))

        # local Central time zone info
        central_dt = pendulum.now()
        day_of_week = central_dt.format('dddd')
        central_time_zone = central_dt.in_tz('US/Central').format('ddd MMM Do HH:mm:ss A [CST] YYYY')

        # converts the date_start to a string for use below
        date_start = date_start.to_datetime_string()
        logger.info('It\'s ' + day_of_week +'! Start Date: ' + central_time_zone)

        # this takes the df_mdso_data dataframe and just shows what i want to see
        hourly_df = df_mdso_data.loc[df_mdso_data['createdAt'] >= date_start]
        logger.info(f'this is the start_date {date_start}')
    
        # this is the current time
        date_end = self.now

        # converts the date_end to a string for use below
        date_end = date_end.to_datetime_string()

        if 'ManagedServicesActivator' in self.product_name or 'PortActivation' in self.product_name:
            # this arranges the columns in the order we want.
            hourly_df = hourly_df[['createdAt', 'id', 'label', 'orchState', 'productId', 'reason', 'resourceTypeId']]
            # adding a column called folder_name to the dataframe that concatenates the circuit id and the date
            # which will be used to name the subdirectory for the logs
            hourly_df['folder_name'] = hourly_df['label'].map(str) + '_' + hourly_df['createdAt'].map(str)
        else:
            hourly_df = hourly_df[['createdAt', 'id', 'properties_circuit_id', 'orchState', 'productId', 'reason', 'resourceTypeId']]
            hourly_df['folder_name'] = hourly_df['properties_circuit_id'].map(str) + '_' + hourly_df['createdAt'].map(str)

        # hourly_df.to_csv('mdso_product_data.csv')
        
        # for every row it adds the Circuit Id concatenated with date/time as key and the resource id as value the the cid_resourceId_dictionary.
        for i in range(len(hourly_df)):
            cid_resourceId_dictionary[hourly_df.iat[i, 7]] = hourly_df.iat[i, 1]
        logger.info(f'cid_resourceId_dictionary: {cid_resourceId_dictionary}')

        # daily generated directory name like the one bash file creates
        self.directory_name = self.now.strftime(f"%m_%d_%y-{self.setup_directory_name}")
        return cid_resourceId_dictionary, self.directory_name, date_start, token

    def plan_script_function(self, resource_id, dir, directory_name, log_dir_path, server_ip, date_start):
        # plan-script logs gathering section
        subprocess.call(['bash', '/home/all-product-logs-multiprocess/mdso_product_log_capture2_test.sh', resource_id, dir, directory_name, log_dir_path, server_ip])
        logger.info(f'Sending {dir} - {resource_id} to bash script to gather {directory_name} - ' + date_start)

if __name__ == '__main__':
    Logs_Main(Environment_Setup).main()


