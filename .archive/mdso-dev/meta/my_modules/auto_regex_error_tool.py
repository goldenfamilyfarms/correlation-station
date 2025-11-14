import pandas as pd
import openpyxl
import xlsxwriter
import os
import re
import configparser
import shutil
from prettyprinter import pprint
# from my_modules.common import set_up_logging, set_up_config
from common import set_up_logging, set_up_config


'''do not erase this is a work of art.  lol

This will automatically create regex for most errors

regex pattern [^\s]+ 
    will match all items to the next space.  will keep this around
regex pattern (.*?)
    matches all between to word strings... example the weather is (.*?) today.  answer mild or hot or hot as hell
'''

logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)


class AutoRegex():

    def __init__(self, error_codes_dataframe):
        '''this will be where all the params come from and shared'''
        self.error_codes_dataframe = error_codes_dataframe

    def main(self):
        '''this will be where all the methods will be called'''
        self.config = set_up_config()
        self.files_directory = self.config['files_directory']['log_dir_path']

        merged_errors_df = self.merge_all_product_error_data()
        error_list = self.get_all_new_errors_discovered(merged_errors_df)
        self.error_and_pattern_dict = self.the_regex_tool(error_list)
        for k, v in self.error_and_pattern_dict.items():
            print(k)
            print(v)
            print("----------------------------------------------------------------")

        # ? comment out these lines if you just want to print results only for testing
        self.verify_create_and_append_new_errors()
        self.copy_categorized_error_dataframe_spreadsheet_to_logs_directory()
    
    def merge_all_product_error_data(self):
        # TODO add path to xlsx files
        path = rf"{self.files_directory}"
        product_error_data_list = ['ServiceMapper_categorized_error_data.xlsx',
                                'NetworkService_categorized_error_data.xlsx',
                                'NetworkServiceUpdate_categorized_error_data.xlsx',
                                'DisconnectMapper_categorized_error_data.xlsx']
        # Initialize an empty data frame
        merged_errors_df = pd.DataFrame()

        for file in product_error_data_list:
            data = pd.read_excel(os.path.join(path, file))
            merged_errors_df = pd.concat([merged_errors_df, data], ignore_index=True)

        # Writing the merged data frame to a new Excel file
        # TODO add path to xlsx files
        myoutput_path = rf'{self.files_directory}all_product_error_data_combined.xlsx'
        merged_errors_df.to_excel(myoutput_path, index=False)
        return merged_errors_df

    def get_all_new_errors_discovered(self, merged_errors_df):
        '''adds all new error discovered to a list'''
        error_list = []
        # did this to make it easier to regex this is a pre special character remover
        df_character_remove_table = str.maketrans({'"': "'", "^": "\^"})

        for i in range(len(merged_errors_df)):
            if merged_errors_df.at[merged_errors_df.index[i], "New Error"] == "New Error Discovered":
                df_error = merged_errors_df.at[merged_errors_df.index[i], "Error"]
                filtered_df_error = df_error.translate(df_character_remove_table)
                # print(filtered_df_error)
                error_list.append(filtered_df_error)
        return error_list

    def the_regex_tool(self, error_list):
        '''creates regex patterns for mdso errors and lumps all granite issues 
        together
        '''
        self.error_and_pattern_dict = {}
        for error in error_list:
            if 'GRANITE DESIGN' in error:
                self.error_and_pattern_dict[error] = f'(?:GRANITE DESIGN \|.*)'
            else:
                self.error_and_pattern_dict[error] = f'(?:{self.regex_pattern_maker(error)})'
        return self.error_and_pattern_dict

    # def regex_pattern_maker(self, test_string):
    #     '''creates regex pattern for defined string values'''
    #     to_remove = {"[|]": "\|",
    #                 # GOOD Pattern for lists
    #                 "\[(.*?)\]": ".*",
    #                 # GOOD Pattern for dictionary
    #                 "\{(.*?)\}": ".*",
    #                 # GOOD Failed task number remove
    #                 "(?:(?<=Failed task:)\(\d{1,2}\))": ".*",
    #                 "[[]": "\[",
    #                 "[]]": "\]",
    #                 "[(]": "\(",
    #                 "[)]": "\)",
    #                 "[{]": "\{",
    #                 "[}]": "\}",
    #                 "[\n]": "\\n",
    #                 # GOOD ALL PORT Port Patterns LETTER 
    #                 "(?i:ET-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,4})?)": ".*",
    #                 "(?i:GE-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,4})?)": ".*",
    #                 "(?i:XE-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,4})?)": ".*",
    #                 "(?i:ETH-PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
    #                 "(?i:ETH PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
    #                 "(?i:ETH PORT \d\/\d)": ".*",
    #                 "(?i:ETH PORT \d)": ".*",
    #                 "(?i:LAG\d)": ".*",
    #                 "(?:AE\d{1,2})": ".*",
    #                 "(?i:\'AE(\d{1,2})?\')": ".*",
    #                 "(?i:TPE_FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_CTP)": ".*",
    #                 "(?i:TPE_ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_PTP)": ".*",
    #                 "(?i:ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
    #                 "(?i:FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
    #                 "(?i:FP SHAPER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})": ".*",
    #                 "(?i:FP POLICER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})": ".*",
    #                 "(?i:FRE_flow-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
    #                 "(?i:ETHERNET-\d(\/\d{1,2})?)": ".*",
    #                 "(?i:ETHERNET-)": ".*",
    #                 # GOOD Fixes the not IPv4 or IPv6 address error
    #                 "(?P<Not_IPv4_IPv6>([^\s]+)(?= does not appear to be an IPv4 or IPv6 address))": ".*",
    #                 # GOOD Fixes the not network address error
    #                 "(?P<Not_IP>(?<=IP )[^\s]+(?= is not a network address.))": ".*",
    #                 # GOOD Fixes the already exists on device error
    #                 "(?P<IP_Exists>(?<=IP )[^\s]+(?= already exists on device))": ".*",
    #                 # GOOD Fixes the id key value if cut short
    #                 "(?P<id_Key>(?<='id': )[^\s]+)": "\'.*\',",
    #                 # GOOD Fixes the createdAt key value date if cut short
    #                 "(?P<createdAt_Key>(?<='createdAt': )[^\s]+)": "\'.*\',",
    #                 # GOOD Fixes the label key value if cut short
    #                 "(?P<label_Key>(?<='label': ')[^\s]+)": "\'.*\',",
    #                 # GOOD Fixes the productId key value if cut short
    #                 "(?P<productId_Key>(?<='productId': ')[^\s]+)": "\'.*\',",
    #                 # GOOD Fixes the message-id key value if cut short
    #                 "(?P<message_id>(?<=junos' message-id=)[^\>]+)": "\'.*\'",
    #                 # GOOD Fixes the unable to get port resource for port key value if cut short
    #                 "(?P<resource_for_port>(?<=unable to get port resource for port)[^\,]+)": ".*",
    #                 # GOOD Fixes the CPE invalid device role
    #                 "(?P<device_CPE_role_invalid>(?<=DEVICE ROLE CPE is INVALID for )[^\.]+)": ".*",
    #                 # GOOD Fixes the PE invalid device role
    #                 "(?P<device_PE_role_invalid>(?<=DEVICE ROLE PE is INVALID for )[^\.]+)": ".*",
    #                 # GOOD resource id
    #                 "(?:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})": ".*",
    #                 # GOOD date time
    #                 "(?P<DateTime_Search>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,6}Z))": ".*",
    #                 # GOOD IPV4 Pattern
    #                 "(?:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d){1,3}(\/\d{2})?)": ".*",
    #                 # GOOD TID Patterns
    #                 "(?:[A-Z0-9]{10}W(-)?(:)?)": ".*",
    #                 # GOOD EVCID Pattern
    #                 "(?<=evcId )\d{0,6}\s": ".*",
    #                 # GOOD IPV6 test
    #                 "(?:[a-fA-F0-9]{4}[:][^\s]+[:][a-fA-F0-9]{1,4})": ".*",
    #                 # GOOD REMOVING COLONS
    #                 "::": ":",
    #                 # GOOD SERVICE VLANS
    #                 "(?:(VOICE|FIA|ELAN|ELINE)\d{1,4})": ".*",
    #                 # GOOD FQDN Patterns
    #                 "[^\s]+COM": ".*",
    #                 # GOOD CIRCUIT ID Pattern
    #                 "(?:(FRE_)?[0-9]{2}\.[A-Z0-9]{4}\.[0-9]{6}\.\.[A-Z]{0,4})": ".*",
    #                 "Node name: (.*?) is not valid": "Node name: .* is not valid",
    #                 # GOOD REVISION 14 DIGITS
    #                 "[0-9]{14}": ".*",
    #                 "(?:(?<=MANAGEMENT TUNNEL-)\d{1,2})": ".*",
    #                 # GOOD bps DIGITS
    #                 "(?P<bps>(\d+)(?= bps))": ".*",
    #                 # GOOD Repo SHA key number
    #                 "(?P<SHA>(?<=SHA )[a-f0-9]{40})": ".*",
    #                 "(?:(FIA|DIA|ELINE|ELAN|VOICE|VIDEO)\d{3,4})": ".*",
    #                 }
    #     for char in to_remove.keys():
    #         test_string = re.sub(char, to_remove[char], test_string)
    #     return test_string

    def regex_pattern_maker(self, test_string):
        '''creates regex pattern for defined string values'''

        ET = "(?i:ET-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,4})?)"
        GE = "(?i:GE-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,4})?)"
        XE = "(?i:XE-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,4})?)"
        ETH_PORT1 = "(?i:ETH-PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
        ETH_PORT2 = "(?i:ETH PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
        ETH_PORT3 = "(?i:ETH PORT \d\/\d)"
        ETH_PORT4 = "(?i:ETH PORT \d)"
        LAG1 = "(?i:LAG\d)"
        AE = "(?i:(?<=\W)AE(\d{1,2})?(\.\d{2,4})?)"
        TPE_FP = "(?i:TPE_FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_CTP)"
        TPE_ACCESS = "(?i:TPE_ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_PTP)"
        ACCESS = "(?i:ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
        FP = "(?i:FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
        FP_SHAPER = "(?i:FP SHAPER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})"
        FP_POLICER = "(?i:FP POLICER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})"
        FRE_FLOW = "(?i:FRE_flow-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})"
        ETHERNET1 = "(?i:ETHERNET-\d(\/\d{1,2})?)"
        ETHERNET2 = "(?i:ETHERNET-)"

        RESOURCE_ID = "(?:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})"
        DATE_TIME = "(?P<DateTime_Search>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,6}Z))"
        IPV4 = "(?:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d){1,3}(\/\d{2})?)"
        IPV6 = "(?:[a-fA-F0-9]{4}[:][^\s]+[:][a-fA-F0-9]{1,4})"
        TID = "(?:[A-Z0-9]{10}W(-)?(:)?)"
        EVCID = "(?<=evcId )\d{0,6}\s"
        VRFID = "(?:(?<=\s)[A-Z]+\.[A-Z]+\.[0-9]+.[A-Z0-9_]+\.[A-Z]+)"
        VRFID_ELAN = "(?:(?<=\s)[A-Z0-9_]+\.ELAN)"
        SERVICE_VLANS = "(?:(FIA|DIA|ELINE|ELAN|VOICE|VIDEO)\d{3,4})"
        FQDN = "[^\s]+COM"
        CIRCUIT_ID = "(?:(FRE_)?[0-9]{2}\.[A-Z0-9]{4}\.[0-9]{6}\.\.[A-Z]{0,4})"
        REVISION_NUM = "[0-9]{14}"
        MANAGEMENT_TUNNEL = "(?:(?<=MANAGEMENT TUNNEL-)\d{1,2})"
        BPS_DIGITS = "(?P<bps>(\d+)(?= bps))"
        SHA_KEY = "(?P<SHA>(?<=SHA )[a-f0-9]{40})"

        to_remove = {
                    # GOOD Pattern for lists
                    "\[(.*?)\]": ".*",
                    # GOOD Pattern for dictionary
                    "\{(.*?)\}": ".*",
                    # GOOD Failed task number remove
                    "(?:(?<=Failed task:)\(\d{1,2}\))": ".*",
                    # GOOD All Special Characters
                    "[+]": "\+",
                    "[|]": "\|",
                    "[[]": "\[",
                    "[]]": "\]",
                    "[(]": "\(",
                    "[)]": "\)",
                    "[{]": "\{",
                    "[}]": "\}",
                    "[\n]": "\\n",
                    # GOOD ALL PORT Port Patterns LETTER 
                    ET: ".*",
                    GE: ".*",
                    XE: ".*",
                    ETH_PORT1: ".*",
                    ETH_PORT2: ".*",
                    ETH_PORT3: ".*",
                    ETH_PORT4: ".*",
                    LAG1: ".*",
                    AE: ".*",
                    TPE_FP: ".*",
                    TPE_ACCESS: ".*",
                    ACCESS: ".*",
                    FP: ".*",
                    FP_SHAPER: ".*",
                    FP_POLICER: ".*",
                    FRE_FLOW: ".*",
                    ETHERNET1: ".*",
                    ETHERNET2: ".*",
                    RESOURCE_ID: ".*",
                    DATE_TIME: ".*",
                    IPV4: ".*",
                    TID: ".*",
                    EVCID: ".*",
                    VRFID_ELAN: ".*",
                    VRFID: ".*",
                    IPV6: ".*",
                    SERVICE_VLANS: ".*",
                    FQDN: ".*",
                    CIRCUIT_ID: ".*",
                    REVISION_NUM: ".*",
                    MANAGEMENT_TUNNEL: ".*",
                    BPS_DIGITS: ".*",
                    SHA_KEY: ".*",
                    # GOOD Fixes the not IPv4 or IPv6 address error
                    "(?P<Not_IPv4_IPv6>([^\s]+)(?= does not appear to be an IPv4 or IPv6 address))": ".*",
                    # GOOD Fixes the not network address error
                    "(?P<Not_IP>(?<=IP )[^\s]+(?= is not a network address.))": ".*",
                    # GOOD Fixes the already exists on device error
                    "(?P<IP_Exists>(?<=IP )[^\s]+(?= already exists on device))": ".*",
                    # GOOD Fixes the id key value if cut short
                    "(?P<id_Key>(?<='id': )[^\s]+)": "\'.*\',",
                    # GOOD Fixes the createdAt key value date if cut short
                    "(?P<createdAt_Key>(?<='createdAt': )[^\s]+)": "\'.*\',",
                    # GOOD Fixes the label key value if cut short
                    "(?P<label_Key>(?<='label': ')[^\s]+)": ".*',",
                    # GOOD Fixes the productId key value if cut short
                    "(?P<productId_Key>(?<='productId': ')[^\s]+)": "\'.*\',",
                    # GOOD Fixes the message-id key value if cut short
                    "(?P<message_id>(?<=junos' message-id=)[^\>]+)": "\'.*\'",
                    # GOOD Fixes the unable to get port resource for port key value if cut short
                    "(?P<resource_for_port>(?<=unable to get port resource for port)[^\,]+)": ".*",
                    # GOOD Fixes the CPE invalid device role
                    "(?P<device_CPE_role_invalid>(?<=DEVICE ROLE CPE is INVALID for )[^\.]+)": ".*",
                    # GOOD Fixes the PE invalid device role
                    "(?P<device_PE_role_invalid>(?<=DEVICE ROLE PE is INVALID for )[^\.]+)": ".*",
                    "Node name: (.*?) is not valid": "Node name: .* is not valid",
                    "::": ":",
                    }

        for char in to_remove.keys():
            test_string = re.sub(char, to_remove[char], test_string)
        return test_string

    def assign_new_error_code(self):
        '''error code generator'''
        if not self.error_codes_dataframe.empty:
            error_code = self.error_codes_dataframe['Error Code'].values[-1]
            if error_code:
                increment = int(error_code[3:]) + 1
                error_code = f'DE-{increment}'
        else:
            error_code = "DE-1000"
        return error_code

    def save_excel_sheet(self, df, excel_path, sheet_name):
        '''saves new error only to excel sheet'''
        if not os.path.exists(excel_path):
            df.to_excel(excel_path, sheet_name=sheet_name, index=False)
        else:
            with pd.ExcelWriter(excel_path, engine='openpyxl', if_sheet_exists='overlay', mode='a') as writer:
                df.to_excel(writer, sheet_name=sheet_name, startrow=writer.sheets[sheet_name].max_row, header=None, index=False)

    def verify_create_and_append_new_errors(self):
        '''Updates temp list with all current known regex patterns to temp list.
        for loop to add values to self.error_codes_dataframe and excel sheet.
        Only appends none matching regex patterns to self.error_codes_dataframe to reduce duplicates.
        '''

        temp = []
        temp.extend(self.error_codes_dataframe['Regex Pattern'].tolist())

        for raw_error, regex_pattern in self.error_and_pattern_dict.items():
            if regex_pattern not in temp:
                temp.append(regex_pattern)
                self.error_codes_dataframe = pd.DataFrame({'Error Code': [self.assign_new_error_code()], 'Raw Error': [raw_error],'Categorized Error': ["none"], 'Regex Pattern': [regex_pattern],})
                # TODO add path to compliance_automation_error_codes
                self.save_excel_sheet(self.error_codes_dataframe, '/home/meta/compliance_automation_error_codes.xlsx', sheet_name='categorized')

    def copy_categorized_error_dataframe_spreadsheet_to_logs_directory(self):
        ''' for now this is used for one purpose to copy error codes spreadsheet to the logs directory
        so it can be visible via flask web tool
        '''
        source = "/home/meta/compliance_automation_error_codes.xlsx"
        destination = f'{self.files_directory}compliance_automation_error_codes_current.xlsx'
        shutil.copy(source, destination)
        print(f"compliance_automation_error_codes copied successfully to: {destination}")

if __name__== "__main__":

    try:
        error_codes_dataframe = pd.read_excel ('/home/meta/compliance_automation_error_codes.xlsx')
    except:
        error_codes_dataframe = pd.DataFrame()

    AutoRegex(error_codes_dataframe).main()
import pandas as pd
import openpyxl
import xlsxwriter
import os
import re
import configparser
import shutil
from prettyprinter import pprint


'''do not erase this is a work of art.  lol

This will automatically create regex for most errors

regex pattern [^\s]+ 
    will match all items to the next space.  will keep this around
regex pattern (.*?)
    matches all between to word strings... example the weather is (.*?) today.  answer mild or hot or hot as hell
'''


class AutoRegex():

    def __init__(self, error_codes_dataframe):
        '''this will be where all the params come from and shared'''
        self.error_codes_dataframe = error_codes_dataframe

    def main(self):
        '''this will be where all the methods will be called'''
        self.config = configparser.ConfigParser()
        self.config.read('/home/meta/setup.cfg')
        self.files_directory = self.config['files_directory']['log_dir_path']

        merged_errors_df = self.merge_all_product_error_data()
        error_list = self.get_all_new_errors_discovered(merged_errors_df)
        self.error_and_pattern_dict = self.the_regex_tool(error_list)
        for k, v in self.error_and_pattern_dict.items():
            print(k)
            print(v)
            print("----------------------------------------------------------------")

        # ? comment out these lines if you just want to print results only for testing
        self.verify_create_and_append_new_errors()
        self.copy_categorized_error_dataframe_spreadsheet_to_logs_directory()
    
    def merge_all_product_error_data(self):
        # TODO add path to xlsx files
        path = rf"{self.files_directory}"
        product_error_data_list = ['ServiceMapper_categorized_error_data.xlsx',
                                'NetworkService_categorized_error_data.xlsx',
                                'NetworkServiceUpdate_categorized_error_data.xlsx',
                                'DisconnectMapper_categorized_error_data.xlsx']
        # Initialize an empty data frame
        merged_errors_df = pd.DataFrame()

        for file in product_error_data_list:
            data = pd.read_excel(os.path.join(path, file))
            merged_errors_df = pd.concat([merged_errors_df, data], ignore_index=True)

        # Writing the merged data frame to a new Excel file
        # TODO add path to xlsx files
        myoutput_path = rf'{self.files_directory}all_product_error_data_combined.xlsx'
        merged_errors_df.to_excel(myoutput_path, index=False)
        return merged_errors_df

    def get_all_new_errors_discovered(self, merged_errors_df):
        '''adds all new error discovered to a list'''
        error_list = []
        # did this to make it easier to regex this is a pre special character remover
        df_character_remove_table = str.maketrans({'"': "'", "^": "\^"})

        for i in range(len(merged_errors_df)):
            if merged_errors_df.at[merged_errors_df.index[i], "New Error"] == "New Error Discovered":
                df_error = merged_errors_df.at[merged_errors_df.index[i], "Error"]
                filtered_df_error = df_error.translate(df_character_remove_table)
                # print(filtered_df_error)
                error_list.append(filtered_df_error)
        return error_list

    def the_regex_tool(self, error_list):
        '''creates regex patterns for mdso errors and lumps all granite issues 
        together
        '''
        self.error_and_pattern_dict = {}
        for error in error_list:
            if 'GRANITE DESIGN' in error:
                self.error_and_pattern_dict[error] = f'(?:GRANITE DESIGN \|.*)'
            else:
                self.error_and_pattern_dict[error] = f'(?:{self.regex_pattern_maker(error)})'
        return self.error_and_pattern_dict

    def regex_pattern_maker(self, test_string):
        '''creates regex pattern for defined string values'''
        to_remove = {"[|]": "\|",
                    # GOOD Pattern for lists
                    "\[(.*?)\]": ".*",
                    # GOOD Pattern for dictionary
                    "\{(.*?)\}": ".*",
                    # GOOD Failed task number remove
                    "(?:(?<=Failed task:)\(\d{1,2}\))": ".*",
                    "[[]": "\[",
                    "[]]": "\]",
                    "[(]": "\(",
                    "[)]": "\)",
                    "[{]": "\{",
                    "[}]": "\}",
                    "[\n]": "\\n",
                    # GOOD ALL PORT Port Patterns LETTER 
                    "(?i:ET-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,3})?)": ".*",
                    "(?i:GE-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,3})?)": ".*",
                    "(?i:XE-\d{1,2}\/\d{1,2}\/\d{1,2}(\.\d{1,3})?)": ".*",
                    "(?i:ETH-PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
                    "(?i:ETH PORT-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
                    "(?i:ETH PORT \d\/\d)": ".*",
                    "(?i:ETH PORT \d)": ".*",
                    "(?i:LAG\d)": ".*",
                    "(?:AE\d{1,2})": ".*",
                    "(?i:\'AE(\d{1,2})?\')": ".*",
                    "(?i:TPE_FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_CTP)": ".*",
                    "(?i:TPE_ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}_PTP)": ".*",
                    "(?i:ACCESS-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
                    "(?i:FP-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
                    "(?i:FP SHAPER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})": ".*",
                    "(?i:FP POLICER-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,3}-\d{1,3}-\d{1,3})": ".*",
                    "(?i:FRE_flow-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2}-\d{1,2})": ".*",
                    "(?i:ETHERNET-\d(\/\d{1,2})?)": ".*",
                    "(?i:ETHERNET-)": ".*",
                    # GOOD Fixes the not IPv4 or IPv6 address error
                    "(?P<Not_IPv4_IPv6>([^\s]+)(?= does not appear to be an IPv4 or IPv6 address))": ".*",
                    # GOOD Fixes the not network address error
                    "(?P<Not_IP>(?<=IP )[^\s]+(?= is not a network address.))": ".*",
                    # GOOD Fixes the already exists on device error
                    "(?P<IP_Exists>(?<=IP )[^\s]+(?= already exists on device))": ".*",
                    # GOOD Fixes the id key value if cut short
                    "(?P<id_Key>(?<='id': )[^\s]+)": "\'.*\',",
                    # GOOD Fixes the createdAt key value date if cut short
                    "(?P<createdAt_Key>(?<='createdAt': )[^\s]+)": "\'.*\',",
                    # GOOD Fixes the label key value if cut short
                    "(?P<label_Key>(?<='label': ')[^\s]+)": "\'.*\',",
                    # GOOD Fixes the productId key value if cut short
                    "(?P<productId_Key>(?<='productId': ')[^\s]+)": "\'.*\',",
                    # GOOD Fixes the message-id key value if cut short
                    "(?P<message_id>(?<=junos' message-id=)[^\>]+)": "\'.*\'",
                    # GOOD Fixes the unable to get port resource for port key value if cut short
                    "(?P<resource_for_port>(?<=unable to get port resource for port)[^\,]+)": ".*",
                    # GOOD Fixes the CPE invalid device role
                    "(?P<device_CPE_role_invalid>(?<=DEVICE ROLE CPE is INVALID for )[^\.]+)": ".*",
                    # GOOD Fixes the PE invalid device role
                    "(?P<device_PE_role_invalid>(?<=DEVICE ROLE PE is INVALID for )[^\.]+)": ".*",
                    # GOOD resource id
                    "(?:[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})": ".*",
                    # GOOD date time
                    "(?P<DateTime_Search>(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3,6}Z))": ".*",
                    # GOOD IPV4 Pattern
                    "(?:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d){1,3}(\/\d{2})?)": ".*",
                    # GOOD TID Patterns
                    "(?:[A-Z0-9]{10}W(-)?(:)?)": ".*",
                    # GOOD EVCID Pattern
                    "(?<=evcId )\d{0,6}\s": ".*",
                    # GOOD IPV6 test
                    "(?:[a-fA-F0-9]{4}[:][^\s]+[:][a-fA-F0-9]{1,4})": ".*",
                    # GOOD REMOVING COLONS
                    "::": ":",
                    # GOOD SERVICE VLANS
                    "(?:(VOICE|FIA|ELAN|ELINE)\d{1,4})": ".*",
                    # GOOD FQDN Patterns
                    "[^\s]+COM": ".*",
                    # GOOD CIRCUIT ID Pattern
                    "(?:(FRE_)?[0-9]{2}\.[A-Z0-9]{4}\.[0-9]{6}\.\.[A-Z]{0,4})": ".*",
                    "Node name: (.*?) is not valid": "Node name: .* is not valid",
                    # GOOD REVISION 14 DIGITS
                    "[0-9]{14}": ".*",
                    "(?:(?<=MANAGEMENT TUNNEL-)\d{1,2})": ".*",
                    # GOOD bps DIGITS
                    "(?P<bps>(\d+)(?= bps))": ".*",
                    # GOOD Repo SHA key number
                    "(?P<SHA>(?<=SHA )[a-f0-9]{40})": ".*",
                    "(?:(FIA|DIA|ELINE|ELAN|VOICE|VIDEO)\d{3,4})": ".*",
                    }
        for char in to_remove.keys():
            test_string = re.sub(char, to_remove[char], test_string)
        return test_string

    def assign_new_error_code(self):
        '''error code generator'''
        if not self.error_codes_dataframe.empty:
            error_code = self.error_codes_dataframe['Error Code'].values[-1]
            if error_code:
                increment = int(error_code[3:]) + 1
                error_code = f'DE-{increment}'
        else:
            error_code = "DE-1000"
        return error_code

    def save_excel_sheet(self, df, excel_path, sheet_name):
        '''saves new error only to excel sheet'''
        if not os.path.exists(excel_path):
            df.to_excel(excel_path, sheet_name=sheet_name, index=False)
        else:
            with pd.ExcelWriter(excel_path, engine='openpyxl', if_sheet_exists='overlay', mode='a') as writer:
                df.to_excel(writer, sheet_name=sheet_name, startrow=writer.sheets[sheet_name].max_row, header=None, index=False)

    def verify_create_and_append_new_errors(self):
        '''Updates temp list with all current known regex patterns to temp list.
        for loop to add values to self.error_codes_dataframe and excel sheet.
        Only appends none matching regex patterns to self.error_codes_dataframe to reduce duplicates.
        '''

        temp = []
        temp.extend(self.error_codes_dataframe['Regex Pattern'].tolist())

        for raw_error, regex_pattern in self.error_and_pattern_dict.items():
            if regex_pattern not in temp:
                temp.append(regex_pattern)
                self.error_codes_dataframe = pd.DataFrame({'Error Code': [self.assign_new_error_code()], 'Raw Error': [raw_error],'Categorized Error': ["none"], 'Regex Pattern': [regex_pattern],})
                # TODO add path to compliance_automation_error_codes
                self.save_excel_sheet(self.error_codes_dataframe, '/home/meta/compliance_automation_error_codes.xlsx', sheet_name='categorized')

    def copy_categorized_error_dataframe_spreadsheet_to_logs_directory(self):
        ''' for now this is used for one purpose to copy error codes spreadsheet to the logs directory
        so it can be visible via flask web tool
        '''
        source = "/home/meta/compliance_automation_error_codes.xlsx"
        destination = f'{self.files_directory}compliance_automation_error_codes_current.xlsx'
        shutil.copy(source, destination)
        print(f"compliance_automation_error_codes copied successfully to: {destination}")

if __name__== "__main__":

    try:
        error_codes_dataframe = pd.read_excel ('/home/meta/compliance_automation_error_codes.xlsx')
    except:
        error_codes_dataframe = pd.DataFrame()

    AutoRegex(error_codes_dataframe).main()
