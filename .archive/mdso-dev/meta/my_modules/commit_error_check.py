
import numpy as npfrom 
from my_modules import webexChatBot
from pathlib import Path
from my_modules.common import set_up_logging
import re, os



'''
this is for parsing RA logs for errors

example:
    test_payload = {"90.VSXX.000160..CHTR":{'full_dir_path': '/home/logs/daily_network_service_logs/10_21_23-Network_Service_Logs', 'defect': 'DE-1119'},
                    "32.L1XX.006299..CHTR":{'full_dir_path': '/home/logs/daily_network_service_logs/10_13_23-Network_Service_Logs', 'defect': 'DE-1110'},
                    }
'''

logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)

# META-BOT
BOT_TOKEN = "MDU1ZTJiOWMtMGQ4OC00YTcwLTllOTEtOWVjNTExNjQ3Yzg3M2M1YWE3ZWEtMGMx_PF84_7b835734-9034-479a-8451-1c20629a0ffd"

class RaErrorCapture():
    def __init__(self, webex_room_id, payload: dict):
        self.room_id = webex_room_id
        if payload:
            for key, value in payload.items():
                self.circuit_id = key
                self.defect = value['defect']
                self.daily_dir_path = value['full_dir_path']
                # self.file_dir = rf'C:\Users\P2160442\{self.full_dir_path}'
                self.file_dir = self.find_exact_directory()
                self.sub_dir_list = []
                self.main()
            print(f'self.room_id being passed: {self.room_id}')
        else:
            message = 'No defects matching the commit error were found'
            webexChatBot.send_message(message=message, bot_token=BOT_TOKEN, room_id=self.room_id)

    def find_exact_directory(self):
        for item in os.listdir(self.daily_dir_path):
            if self.circuit_id in item:
                return rf'{self.daily_dir_path}/{item}'

    def iterate_log_directory_and_append_ra_directories_to_list(self):
        os.chdir(self.file_dir)
        script_plan_dir_list = os.listdir(self.file_dir)
        for file_item in script_plan_dir_list:
            # print(file_item)
            if os.path.isdir(file_item):
                self.sub_dir_list.append(file_item)
        return self.sub_dir_list
    
    def capture_ra_error_message(self):
        combined_data_list = []
        ra_commit_error_dictionary = {}
        for sub_dir in self.sub_dir_list:
            ra_dir_path = rf'{self.file_dir}/{sub_dir}'
            for ra_log in os.listdir(ra_dir_path):
                # print(ra_log)
                os.chdir(ra_dir_path)
                with open(ra_log) as newfile:
                    data = re.findall('(?:<xnm:error.*>[\s\S]*?</xnm:error>)', newfile.read())
                    combined_data_list.extend(data)
                data_refined = self.remove_none_message_info_from_list(combined_data_list)
                ra_commit_error_dictionary[self.circuit_id] = {self.defect: {sub_dir: []}}
                ra_commit_error_dictionary[self.circuit_id][self.defect][sub_dir] += data_refined

        return ra_commit_error_dictionary

    # TODO in the future will pass variable to search any tag needed
    def remove_none_message_info_from_list(self, data):
        string = ''.join(data)
        data_refined = re.findall('(?:<message>[\s\S]*?</message>)', string)
        return data_refined

    def main(self):

        self.iterate_log_directory_and_append_ra_directories_to_list()
        ra_errors = self.capture_ra_error_message()
        print(ra_errors)
        for key, value in ra_errors.items():
            info = f'{key} - {value}'
            webexChatBot.send_message(message=info, bot_token=BOT_TOKEN, room_id=self.room_id)


if __name__ == "__main__":
    from webexChatBot import send_message

    test_payload = {
                    "90.VSXX.000160..CHTR":{'full_dir_path': '/home/logs/daily_network_service_logs/10_21_23-Network_Service_Logs', 'defect': 'DE-1119'},
                    "32.L1XX.006299..CHTR":{'full_dir_path': '/home/logs/daily_network_service_logs/10_13_23-Network_Service_Logs', 'defect': 'DE-1110'},
                    }

    RaErrorCapture(test_payload)
