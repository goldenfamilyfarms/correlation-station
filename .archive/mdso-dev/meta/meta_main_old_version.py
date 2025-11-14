# Searches for and parses orch traces for a particular day

import configparser
import json
import logging
import logging.config
import pandas as pd
import pendulum
import sys, os
from prettyprinter import pprint
from my_modules import mdso_test, mdso_orch_trace_capture_test, beorn, webexteams_sender, connectivity, commit_error_check, post_deployment_error_watch
from my_modules.common import set_up_logging
from product_data_frame_model import ProductDataModel
from collections import Counter
import re
import time
import matplotlib.pyplot as plt
import itertools
import requests
import openpyxl
import shutil

'''
META_Tool Capabilities
•	Products (ServiceMapper, NetworkService and DisconnectMapper)
•	Checks for Errors at any time interval set (minutes, hours, days, or weeks)
•	Gives a count of each error occurrence.
•	Can runs tests on errors of interest that are added to a list.
•	Sends information of interest to Webex rooms
•	Creates xlsx files containing all errors found.
•	Creates a bar graph displaying error counts
•	Added API ability to the flask web URL.
•	During tests no matter what time interval is set an api request is sent to capture the most up to date logs 
•	Current scheduled checks are.
    o	Testing every 15 minutes for the “unable to connect to device”.
    o	Every morning the previous days errors are gathered.self\.date_time_format
    o	Every Monday morning the previous week  errors are gathered.

'''

# TODO add docstrings to methods and more detailed information in docstrings pertaining to the app launchers params dictionary and what they do 


logger = set_up_logging()


class MetaMain():

    def __init__(self, param_dictionary):
        self.param_dictionary = param_dictionary
        self.product_type = param_dictionary["product_type"]
        self.product_name = param_dictionary["product_name"]
        self.time_interval = param_dictionary["time_interval"]
        self.time_increment = param_dictionary["time_increment"]
        self.search_date_detail = param_dictionary['search_date_detail']
        self.plot_error_history = param_dictionary.get('plot_error_history')
        self.plot_errors_required = param_dictionary.get('plot_errors_required')
        self.categorized_error_data_spreadsheet_required = param_dictionary.get('categorized_error_data_spreadsheet_required')
        self.is_error_test_required = param_dictionary['is_error_test_required']
        self.error_test_list = param_dictionary.get('error_test_list')
        self.get_ip_and_fqdn_from_nf = param_dictionary.get('get_ip_and_fqdn_from_nf')
        self.refresh_logs = param_dictionary.get('refresh_logs')
        self.test_to_perform = param_dictionary.get('test_to_perform')
        self.webex_room_id = param_dictionary.get('webex_room_id')

        # main method defined instance attributes
        self.config = configparser.ConfigParser()
        self.config.read('/home/meta/setup.cfg')
        self.now = pendulum.now('UTC')
        self.files_directory = self.config['files_directory']['log_dir_path']
        self.mdso_server = self.config['mdso']['url']
        self.created_date, self.time_range_value, self.date_time_modified = self.manipulate_date_time_if_needed()


    def main(self):
        '''
        '''
        timer_start = time.perf_counter()
        logger.info('#' * 60)
        logger.info(f' ----> {os.path.basename(__file__)} <--')
        logger.info('#' * 60)
        logger.info('#' * 60)
        logger.info('    - Running Daily SEEFA - Compliance Error report -')
        logger.info('#' * 60)

        self.token = mdso_test.get_token(self.config, self.mdso_server)
        self.response = self.get_all_market_resources_for_product_from_mdso()

        todays_log_list = self.iterate_mdso_market_resourceType_data_by_product_and_date_time()
        raw_mdso_dataframe = pd.json_normalize(todays_log_list, sep="_")
        raw_mdso_dataframe.to_excel(f'{self.files_directory}raw_mdso_dataframe.xlsx')

        # this takes the raw_mdso_dataframe and just shows a specific createdAt date of data that is needed
        daily_df = raw_mdso_dataframe.loc[raw_mdso_dataframe["createdAt"] >= self.date_start]
        logger.info(f"this is the start_date {self.date_start}")

        # this takes the raw daily_df and just shows columns of data that is needed. based on the ProductDataModel class (it may very per product)
        daily_df_modeled = daily_df[ProductDataModel.get_product_data_model(self.product_name)]
        daily_df_modeled.to_excel(f'{self.files_directory}daily_df_modeled.xlsx')
        
        # default model for now
        dataframe = Dataframe(self.param_dictionary).create_new_empty_dataframe_with_columns(ProductDataModel("Default_Model").get_product_custom_dataframe_columns_model())
        self.test_payload = ProductError(self.param_dictionary).get_needed_variables_from_df_and_parse_orch_trace_data(daily_df_modeled, dataframe, self.token, self.config)

        dataframe.to_excel(f'{self.files_directory}{self.product_name}_categorized_error_data.xlsx')
        categorized_error_count = Dataframe(self.param_dictionary).categorize_and_count_errors_found(dataframe)
        categorized_dataframe = Dataframe(self.param_dictionary).create_a_new_dataframe_that_contains_categorized_error_and_count(categorized_error_count)
        # logger.info(f'categorized_dataframe: {categorized_dataframe}')
        defect_number_list =  list(categorized_dataframe["Defect_number"])
        count_list =  list(categorized_dataframe["Count"])
        Plot(self.param_dictionary).plot_the_error_occurrence(defect_number_list, count_list)
        categorized_dataframe.to_excel(f'{self.files_directory}{self.product_name}_categorized_error_count.xlsx')
        logger.info(f"self.test_payload: {self.test_payload}")

        # options of sending the xlsx file and graph
        if self.categorized_error_data_spreadsheet_required:
            self.send_to_webex_room([f'{self.product_name}_categorized_error_data.xlsx'], webex_room_id=self.webex_room_id)
        if self.plot_errors_required:
            self.send_to_webex_room([f'product_errors.png'], webex_room_id=self.webex_room_id)
        if self.plot_error_history:
            Plot(self.param_dictionary).plot_error_occurrence_over_a_specified_number_of_days(dataframe, self.plot_error_history)
            self.send_to_webex_room([f'error_history.png'], webex_room_id=self.webex_room_id)

        ProductErrorTest(self.param_dictionary, self.test_payload, self.token).perform_test_on_error()

        self.copy_categorized_error_dataframe_spreadsheet_to_logs_directory()

        # is used to test the speed at which the script runs
        timer_stop = time.perf_counter()
        logger.info(f'total time = {timer_stop - timer_start:0.4f} seconds')

    def get_all_market_resources_for_product_from_mdso(self):
        response = mdso_test.get_market_resourceType(self.token, self.mdso_server, self.product_name, debug=False)
        if self.product_type == 'service_mapper':
            response = self.flatten_json_response_for_service_mapper(response)
        return response
    
    def flatten_json_response_for_service_mapper(self, response):
        '''takes the nested device tid and management ip and creates flattened key values

        :param json response: json data from the service mapper api call
        :return json: altered json data
        '''        
        for item in response:
            if item.get('properties', dict).get('device_properties'):
                device_properties = item['properties']['device_properties']
                for k, v in device_properties.items():
                    item['properties']['device_tid'] = k
                    if v.get('Management IP'):
                        item['properties']['Management_IP'] = v['Management IP']
                device_properties.clear()
        return response

    def get_ip_and_fqdn_info_from_beorn_and_network_function(self):
        self.check_network_function(self.token)
        for cid, value in self.test_payload.items():
            self.get_fqdn_and_managementIP_from_beorn(cid, value['tid'])

    def check_network_function(self, token):
        '''checks network function'''
        for k, v in self.test_payload.items():
            tid = v['tid']
            response = mdso_test.get_market_resourceType_network_function_by_tid(token, tid, debug=False)
            # print(response)
            if response:
                ip_address = response[0]["properties"].get("ipAddress")
                communication_state = response[0]["properties"].get("communicationState")
                self.test_payload[k]['fqdn']= ip_address
                self.test_payload[k]['communication_state']= communication_state

    def get_device_details(self, cid, tid):
        '''Calls beorn and and uses the Device class to capture info'''
        circuit_details = beorn.get_circuit_details_topology_from_beorn(cid)
        for topology in circuit_details["topology"]:
            for device_data in topology["data"]["node"]:
                device = Device(device_data)
                if device.tid == tid:
                    return device

    def get_fqdn_and_managementIP_from_beorn(self, cid, tid):
        device = self.get_device_details(cid, tid)
        if device.tid == tid:
            self.test_payload[cid]['beorn_fqdn']= device.fqdn

    def get_formatted_folder_name_value_for_dir(self, daily_df_modeled, i):
        '''formats folder name value to use as directory - currently not being used - future use'''
        return daily_df_modeled.at[daily_df_modeled.index[i], "folder_name"].replace(" ", "_").replace(":", "-").replace("/", "-")[:-13]

    def manipulate_date_time_if_needed(self):
        # time_range is every increment is a day subtracted from today
        self.time_range = self.time_increment
        if self.time_interval == "minutes":
            self.date_time_modified = self.now.subtract(minutes=int(self.time_range))
            self.time_range_value = self.date_time_modified.format("dddd MM-DD-YYYY HH:mm:ss")
            self.created_date = self.date_time_modified.format("YYYY-MM-DDTHH:mm")
        if self.time_interval == "hours":
            self.date_time_modified = self.now.subtract(hours=int(self.time_range))
            self.time_range_value = self.date_time_modified.format("dddd MM-DD-YYYY HH:mm:ss")
            self.created_date = self.date_time_modified.format("YYYY-MM-DDTHH")
        if self.time_interval == "days":
            self.date_time_modified = self.now.subtract(days=int(self.time_range))
            self.time_range_value = f'for {self.date_time_modified.format("dddd MM-DD-YYYY")}'
            self.created_date = self.date_time_modified.format("YYYY-MM-DD")
        if self.time_interval == "weeks":
            self.date_time_modified = self.now.subtract(weeks=int(self.time_range))
            self.time_range_value = f'{self.date_time_modified.format("dddd MM-DD-YYYY")} through {self.now.format("dddd MM-DD-YYYY")}'
            self.created_date = self.date_time_modified.format("YYYY-MM-DDTHH")
        day_of_week = self.date_time_modified.format("dddd")
        central_time_zone = self.date_time_modified.in_tz("US/Central").format(
            "ddd MMM Do HH:mm:ss A [CST] YYYY"
        )
        self.date_start = self.date_time_modified.to_datetime_string()
        logger.info("It's " + day_of_week + "! Start Date: " + central_time_zone)
        return self.created_date, self.time_range_value, self.date_time_modified
    
    def iterate_mdso_market_resourceType_data_by_product_and_date_time(self):
        '''this loops through api response (items) and adds todays createdAt items to a list'''
        todays_log_list = []
        for item in self.response:
            for item_key, item_value in item.items():
                if self.search_date_detail == 'exact_date':
                    if item_key == "createdAt" and self.created_date in item_value:
                        todays_log_list.append(item)
                else:
                    if item_key == "createdAt" and self.created_date <= item_value:
                        todays_log_list.append(item)
        if not todays_log_list:
            exit('todays log list is empty,  no errors to gather at this moment')
        return todays_log_list
    
    def get_current_logs_now(self):
        '''Calls API to start the product log gathering if searched for errors discovered.
        By default logs are gathered at the top of each hour
        '''

        headers = {
        # Already added when you pass json= but not when you pass data=
        'Content-Type': 'application/json',
        }
        data = {"service_type": f"{self.product_type}"}
        response = requests.get('http://98.6.16.11/api_logs', headers=headers, json=data)
        response_info = response.json()
        logger.info(f"API call to log server response: {response}")
        logger.info(f"API call to log server response info: {response_info}")
        logger.info(f"API call to log server complete:")
        return response

    def send_to_webex_room(self, product_item_list, webex_room_id):
        '''add list of csv files to list'''

        # webex login
        webex_api = webexteams_sender.webex_login()

        # this is the webex room where the logs will be sent
        room_id = webex_room_id

        # message = "Today's Random Standup List"
        for product_item in product_item_list:
            error_file = [f'{self.files_directory}{product_item}']
            try:
                webexteams_sender.webex_group_send(
                    webex_api, room_id, file=error_file
                    # webex_api, room_id, message=message, file=error_file
                )
            except Exception as e:
                logger.info(f"issue with webex: {e}")
                time.sleep(5)

    def copy_categorized_error_dataframe_spreadsheet_to_logs_directory(self):
        ''' for now this is used for one purpose to copy error codes spreadsheet to the logs directory
        so it can be visible via flask web tool
        '''
        source = "/home/meta/compliance_automation_error_codes.xlsx"
        destination = f'{self.files_directory}compliance_automation_error_codes_copy.xlsx'
        shutil.copy(source, destination)
        logger.info(f"compliance_automation_error_codes copied successfully to: {destination}")


class ProductError(MetaMain):

    def __init__(self, param_dictionary):
        super().__init__(param_dictionary)

    def get_needed_variables_from_df_and_parse_orch_trace_data(self, daily_df_modeled, dataframe, token, config):
        '''gets variables, parses orch trace data and returns the test payload if test cases found'''
        self.the_test_payload = {}
        daily_df_modeled = daily_df_modeled.fillna('None')
        for i in range(len(daily_df_modeled)):
            date_time = self.get_actual_createdAt_date_from_dataframe(daily_df_modeled, i)
            self.cid = self.get_circuit_id_from_dataframe_if_available(daily_df_modeled, i)
            resource_id = self.get_resource_id_from_dataframe(daily_df_modeled, i)
            tid = self.get_tid_from_dataframe_if_available(daily_df_modeled, i)
            management_ip = self.get_management_ip_from_dataframe_if_available(daily_df_modeled, i)
            orch_data = mdso_orch_trace_capture_test.orch_trace_get(self.cid, resource_id, token, config, self.product_name)
            # print(orch_data)
            if not orch_data['items']:
                logger.info(f'looks like no orch data: {orch_data}')
                continue
            if self.product_name == "NetworkService":
                self.iterate_network_service_orch_trace(orch_data, tid, management_ip, date_time, dataframe, self.cid)
            elif self.product_name == "ServiceMapper":
                self.iterate_service_mapper_orch_trace(orch_data, tid, management_ip, date_time, dataframe, self.cid)
            elif self.product_name == "NetworkServiceUpdate":
                self.iterate_service_mapper_orch_trace(orch_data, tid, management_ip, date_time, dataframe, self.cid)
            elif self.product_name == "DisconnectMapper":
                self.a_side_endpoint = self.get_tid_endpoints_and_disco_status_from_dataframe(daily_df_modeled, i, "properties_a_side_endpoint")
                self.a_side_disconnect = self.get_tid_endpoints_and_disco_status_from_dataframe(daily_df_modeled, i, "properties_a_side_disconnect")
                self.z_side_endpoint = self.get_tid_endpoints_and_disco_status_from_dataframe(daily_df_modeled, i, "properties_z_side_endpoint")
                self.z_side_disconnect = self.get_tid_endpoints_and_disco_status_from_dataframe(daily_df_modeled, i, "properties_z_side_disconnect")
                self.iterate_disconnect_mapper_orch_trace(orch_data, tid, management_ip, date_time, dataframe, self.cid)
        # print(f'self.the_test_payload: {self.the_test_payload}')
        return self.the_test_payload

    def get_actual_createdAt_date_from_dataframe(self, daily_df_modeled, i):
        return daily_df_modeled.at[daily_df_modeled.index[i], "createdAt"]
    
    def get_circuit_id_from_dataframe_if_available(self, daily_df_modeled, i):
        cid = ''
        if "properties_circuit_id" in daily_df_modeled:
            cid = daily_df_modeled.at[daily_df_modeled.index[i], "properties_circuit_id"]
        elif "properties_expected_data_cid" in daily_df_modeled:
            cid = daily_df_modeled.at[daily_df_modeled.index[i], "properties_expected_data_cid"]
        return cid
    
    def get_resource_id_from_dataframe(self, daily_df_modeled, i):
        return daily_df_modeled.at[daily_df_modeled.index[i], "id"]
    
    def get_tid_from_dataframe_if_available(self, daily_df_modeled, i):
        if "properties_device_tid" in daily_df_modeled:
            return daily_df_modeled.at[daily_df_modeled.index[i], "properties_device_tid"]
        else:
            return 'None'
        
    def get_management_ip_from_dataframe_if_available(self, daily_df_modeled, i):
        if "properties_Management_IP" in daily_df_modeled:
            return daily_df_modeled.at[daily_df_modeled.index[i], "properties_Management_IP"]
        else:
            return 'None'
        
    def get_tid_endpoints_and_disco_status_from_dataframe(self, daily_df_modeled, i, column_item_name):
        return daily_df_modeled.at[daily_df_modeled.index[i], column_item_name]
    
    def iterate_disconnect_mapper_orch_trace(self, orch_data, tid, management_ip, date_time, df, cid):
        def remove_endpoint_tids_if_full_disco():
            partial_disco_list = []
            endpoint_tids_dict = {self.a_side_endpoint: self.a_side_disconnect, self.z_side_endpoint: self.z_side_disconnect}
            for tid, disco_status in endpoint_tids_dict.items():
                if disco_status == "PARTIAL":
                    partial_disco_list.append(tid)
            return partial_disco_list
        
        partial_disco_list = remove_endpoint_tids_if_full_disco()
        logger.info(f'partial_disco_list : {partial_disco_list}')
        for trace in orch_data["items"][0]["properties"]["orchestration_trace"]:
            if trace.get("categorized_error"):
                if not [item for item in partial_disco_list if(item in trace.get("categorized_error"))]:
                    if trace.get("categorized_error") and trace['resource_type'] != 'tosca.resourceTypes.ConnectivityCheck':
                        Dataframe(self.param_dictionary).perform_error_check_and_add_to_a_dataframe(trace, tid, management_ip, date_time, df, cid, self.the_test_payload)
                else:
                    Dataframe(self.param_dictionary).perform_error_check_and_add_to_a_dataframe(trace, tid, management_ip, date_time, df, cid, self.the_test_payload)
                    break

    def iterate_network_service_orch_trace(self, orch_data, tid, management_ip, date_time, df, cid):
        for trace in orch_data["items"][0]["properties"]["orchestration_trace"]:
            if trace.get("categorized_error") and trace['resource_type'] != 'tosca.resourceTypes.ConnectivityCheck':
                Dataframe(self.param_dictionary).perform_error_check_and_add_to_a_dataframe(trace, tid, management_ip, date_time, df, cid, self.the_test_payload)
                break

    def iterate_service_mapper_orch_trace(self, orch_data, tid, management_ip, date_time, df, cid):
        for trace in orch_data["items"][0]["properties"]["orchestration_trace"]:
            if trace.get("categorized_error"):
                Dataframe(self.param_dictionary).perform_error_check_and_add_to_a_dataframe(trace, tid, management_ip, date_time, df, cid, self.the_test_payload)
                break

    def get_log_link(self, cid, date_time):
        '''creates a log link'''
        formatted_date_time = date_time.replace("T", "_").replace(":", "-")[:-5]
        formatted_six_digit_date = self.now.format('MM_DD_YY')
        return f'http://98.6.16.11/reports/daily_{self.product_type}_logs/{formatted_six_digit_date}-Service_Mapper_Logs/{cid}_{formatted_date_time}'
    
    def get_log_path(self, cid, datetime):
        '''gets the log path'''
        original_datetime = pendulum.parse(datetime)
        log_directory_date = original_datetime.format("MM_DD_YY")
        log_file_date = original_datetime.format("YYYY-MM-DD_")
        return rf"/home/logs/daily_network_service_logs/{log_directory_date}-{self.product_type.title()}_Logs"


class Dataframe(ProductError):

    def __init__(self, param_dictionary):
        super().__init__(param_dictionary)
        self.categorized_error_dataframe = self.get_categorized_error_to_regex_pattern_dataframe()

    def get_categorized_error_to_regex_pattern_dataframe(self):
        categorized_error_dataframe = pd.read_excel ('/home/meta/compliance_automation_error_codes.xlsx')
        return categorized_error_dataframe
    
    def perform_error_check_and_add_to_a_dataframe(self, trace, tid, management_ip, date_time, df, cid, the_test_payload):
        # these are a few characters that needed to be stripped before the regex was performed mainly the ^
        df_character_remove_table = str.maketrans({"\n": "", '"': "'", "^": " "})
        filtered_df_error = trace["categorized_error"][0:500].translate(df_character_remove_table)
        process = self.get_name_of_resource_where_error_occurred(trace["process"])
        filtered_df_error = f'{filtered_df_error} - {process}'
        is_existing_error = self.check_if_error_is_categorized(filtered_df_error)
        if not is_existing_error:
            match = 'New Error Discovered'
        else:
            match = is_existing_error

        if self.is_error_test_required:
            self.check_if_error_needs_test_performed_add_to_dictionary(match, cid, tid, management_ip, date_time, the_test_payload, filtered_df_error)

        self.adding_new_row_of_data_to_dataframe(dataframe=df, dictionary={'Date': date_time,
                                                                            'Circuit ID': cid,
                                                                            'Resource That Failed': trace["process"],
                                                                            'Error': filtered_df_error,
                                                                            'New Error': match,
                                                                            'Device Tid': tid,
                                                                            'Management IP': management_ip,
                                                                            })
        
    def get_name_of_resource_where_error_occurred(self, trace):
        if len(trace.split(".")) == 3:
            description = f'{trace.split(".")[1]}'
        else:
            description = trace.split(".")[2]
        return description
    
    def check_if_error_is_categorized(self, error_item):
        '''checks error for existing pattern match and returns match if found

        :param str error_item: circuit failure error
        :return str: pattern if found
        '''

        for i in range(len(self.categorized_error_dataframe)):
            check = re.search(self.error_to_regex_pattern_dataframe(i, "Regex Pattern"), error_item)
            if check:
                return self.error_to_regex_pattern_dataframe(i, "Error Code")
            
    def error_to_regex_pattern_dataframe(self, index, column):
        return self.categorized_error_dataframe.at[self.categorized_error_dataframe.index[index], column]
    
    def categorize_and_count_errors_found(self, dataframe):
        '''looks at all errors and checks for frequency.
        The categorized error, count and error_number are added

        :param _type_ dataframe: dataframe
        :return dict: error to count
        '''
        categorized_error_count = {}
        for i in range(len(self.categorized_error_dataframe)):
            test = dataframe.loc[dataframe['Error'].str.contains(fr'{self.error_to_regex_pattern_dataframe(i, "Regex Pattern")}'), :]
            categorized_error_count[self.error_to_regex_pattern_dataframe(i, "Regex Pattern")] = [test.shape[0], self.error_to_regex_pattern_dataframe(i, "Error Code")]
        return categorized_error_count
            
    def check_if_error_needs_test_performed_add_to_dictionary(self, error_code, cid, tid, ip, date_time, the_test_payload, filtered_df_error):
        '''Checks for error that requires further testing
        self.error_test_list is a list of DE-#### passed from a launcher script

        :param str error_code: defect error code  Example DE-1000
        :param str cid: circuit_id
        :param str tid: tid of device
        :param str ip: management ip address for device
        '''
        # TODO add more detailed information in docstring pertaining to the app launchers params dictionary
        if error_code in self.error_test_list:
            the_test_payload[cid] = self.gather_items_for_payload_based_on_test_type(self.test_to_perform, tid, ip, cid, date_time, error_code, filtered_df_error)
            logger.info(f"{error_code} detected adding cid to a list")

    def gather_items_for_payload_based_on_test_type(self, test_to_perform, tid, ip, cid, date_time, error_code, filtered_df_error):
        '''gathers the specific information needed per test'''
        if test_to_perform == 'connectivity':
            return {'tid': tid, 'ip': ip, 'log_web_link': self.get_log_link(cid, date_time), "defect": error_code}
        elif test_to_perform == 'ra_commit_error_check':
            return {'full_dir_path': self.get_log_path(cid, date_time), "defect": error_code}
        elif test_to_perform == 'post_deployment_error_watch':
            return {'error': filtered_df_error, "defect": error_code, "product_type": self.product_type}

    def adding_new_row_of_data_to_dataframe(self, dataframe, dictionary):
        '''Example: dictionary = {'Categorized_error': Categorized_error, 'Count': count,}'''
        dataframe.loc[len(dataframe)] = dictionary

    def create_a_new_dataframe_that_contains_categorized_error_and_count(self, categorized_error_count):
        categorized_dataframe = self.create_new_empty_dataframe_with_columns({'Date': [],
                                                                            'Defect_number': [],
                                                                            'Categorized_error': [],
                                                                            'Count': [],
                                                                            })
        for k, v in categorized_error_count.items():
            self.adding_new_row_of_data_to_dataframe(dataframe=categorized_dataframe, dictionary={'Date': f'{self.created_date} - {self.now.to_atom_string()}',
                                                                                                'Defect_number': v[1],
                                                                                                'Categorized_error': k,
                                                                                                'Count': v[0],})

        return categorized_dataframe

    def create_new_empty_dataframe_with_columns(self, dictionary):
        '''creates custom dataframe with column from passing a dictionary
        example: {'Circuit ID': [], 'Resource That Failed': [], 'Error': [],}
        '''
        return pd.DataFrame(dictionary)


class ProductErrorTest(Dataframe):
    param_dictionary: dict
    test_payload: dict
    token: str

    def __init__(self, param_dictionary, test_payload, token):
        self.test_payload = test_payload
        self.token = token
        super().__init__(param_dictionary)

    def choose_test_to_run(self):
        '''returns the test to be performed'''
        test = {
                "connectivity": connectivity.Connectivity,
                "ra_commit_error_check": commit_error_check.RaErrorCapture,
                "post_deployment_error_watch": post_deployment_error_watch.ErrorWatch}
        return vars(test[self.test_to_perform](self.webex_room_id, self.test_payload))

    def perform_test_on_error(self):
        if self.get_ip_and_fqdn_from_nf:
            self.get_ip_and_fqdn_info_from_beorn_and_network_function()
        if self.refresh_logs:
            # gets the web log url updated
            self.get_current_logs_now()
        logger.info(f"self.test_payload before being sent out for testing: {self.test_payload}")
        if self.is_error_test_required:
            self.choose_test_to_run()


class Plot(MetaMain):

    def __init__(self, param_dictionary):
        super().__init__(param_dictionary)

    def plot_the_error_occurrence(self, error_number, count):
        x_cord_modified = []
        y_cord_modified = []
        plt.figure(figsize=(15,15))
        for item1, item2 in zip(error_number, count):
            if item2 != 0:
                x_cord_modified.append(item1)
                y_cord_modified.append(int(item2))

        plt.barh(x_cord_modified, y_cord_modified)
        plt.title(f'{self.product_type} Errors {self.time_range_value} check')
        for index, value in enumerate(y_cord_modified):
            plt.text(value, index,
                    str(value))

        # plt.show()
        plt.savefig(f'{self.files_directory}product_errors.png')

    def plot_error_occurrence_over_a_specified_number_of_days(self, df, error_item):
        '''plots occurrence over a period of time

        :param dataframe df: dataframe containing the weekly report info with errors
        :param int days: the number of day to plot. Example 3
        :param str error_item: the error thats being investigated. Example DE-1041
        :return png image: plotted chart showing daily results
        '''

        # being cute and using a dictionary
        choose_time_interval = {'weeks': self.now.subtract(weeks=self.time_increment),
                                'days': self.now.subtract(days=self.time_increment),
                                'hours': self.now.subtract(hours=self.time_increment),
                                'minutes': self.now.subtract(minutes=self.time_increment)}
        start = choose_time_interval[self.time_interval]

        def days_to_check_errors_for(start):
            date_list = []
            period = pendulum.period(start, pendulum.now())
            for dt in period:
                date_list.append(dt.format("YYYY-MM-DD"))
            return date_list

        date_list = days_to_check_errors_for(start)

        def check_dataframe_for_error(df, error_item):
            list_of_dates_added_per_error = []
            for i in range(len(df)):
                if df.at[df.index[i], "New Error"] == error_item:
                    list_of_dates_added_per_error.append(df.at[df.index[i], "Date"][:-14])
            return list_of_dates_added_per_error

        list_of_dates_added_per_error = check_dataframe_for_error(df, error_item)
        
        def count_occurrence_in_list(list_of_dates, date):
            return list_of_dates.count(date)

        def get_y_point_for_line_graph():
            y = []
            for date in date_list:
                count = count_occurrence_in_list(list_of_dates_added_per_error, date)
                y.append(count)
            return y

        y = get_y_point_for_line_graph()

        def plot_stuff(x_cord, y_cord):

            plt.figure(figsize=(15,15))
            plt.plot(x_cord, y_cord)
            plt.plot(y_cord, marker = 'o', ms = 10)
            plt.title(f'Service Mapper Errors for {error_item}')
            plt.ylabel("Count")
            plt.xlabel("Date")
            plt.xticks(rotation=45, ha='right')
        
            # plt.show()
            plt.savefig(f'{self.files_directory}error_history.png')

        plot_stuff(date_list, y)


class Device:
    def __init__(self, device):
        self.details = device.get("name")
        self.edgepoint_details = device.get("ownedNodeEdgePoint")
        self.tid = self.details[0].get("value")
        self.role = self.details[1].get("value")
        self.vendor = self.details[2].get("value")
        self.model = self.details[3].get("value")
        self.management_ip = self.details[4].get("value")
        self.fqdn = self.details[6].get("value")
        self.equipment_status = self.details[7].get("value")


if __name__ == '__main__':

    # this variable is used for the real time and is used in the main function parameters
    now = pendulum.now('America/Chicago')
    now.set(hour=2, minute=00, second=39).to_datetime_string()
    testnow = pendulum.datetime(2023, 8, 7, 2, 00, 38)
    now = pendulum.now('UTC')
    print(f'this is the now being passed: {now}')

    # print(today)

    # add to the param_dictionary to the MetaMain() params instead of now for future.
    param_dictionary = {
        "product_type": "service_mapper",
        "time_interval": "days",
        "time_increment": 1,
        "search_date_detail": "exact_date",
        "date_time_format": "YYYY-MM-DDTHH:",
        "is_error_test_required": False,
    }

    try:
        # MetaMain(dt).main()
        MetaMain(now).main()
    except Exception:
        logger.error("Looks like something failed...", exc_info=True)
        
    
