
import numpy as npfrom 
from my_modules import webexChatBot
from my_modules.common import set_up_logging
# import webexChatBot
from pathlib import Path
import re, os
import configparser
import logging
import logging.config


'''
this is sending error to the post deployment chat

example:
    test_payload = {"32.L1XX.006299..CHTR": {'error': filtered_df_error, "defect": error_code}
'''

logger = set_up_logging()

# META-BOT
BOT_TOKEN = "MDU1ZTJiOWMtMGQ4OC00YTcwLTllOTEtOWVjNTExNjQ3Yzg3M2M1YWE3ZWEtMGMx_PF84_7b835734-9034-479a-8451-1c20629a0ffd"

class ErrorWatch():
    def __init__(self, webex_room_id, payload: dict):
        self.room_id = webex_room_id
        if payload:
            for key, value in payload.items():
                self.circuit_id = key
                self.defect = value['defect']
                self.error = value['error']
                self.product_type = value['product_type']
                self.main()
            print(f'self.room_id being passed: {self.room_id}')
        # else:
        #     message = 'No defects matching the commit error were found'
        #     webexChatBot.send_message(message=message, bot_token=BOT_TOKEN, room_id=self.room_id)

    def markup_message(self):
        message = f"[**{self.product_type} - {self.circuit_id}**]  \
            \nMETA Classified Error: {self.defect} \
            \nError Found: -->  {self.error}"
        return message

    def main(self):

        logger.info('#' * 60)
        logger.info(f' ----> {os.path.basename(__file__)} <--')
        logger.info('#' * 60)

        logger.info('#' * 60)
        logger.info(f' ----> Post Deployment Error Watch for {self.product_type}-')
        logger.info('#' * 60)

        message = self.markup_message()
        webexChatBot.send_message(message=message, bot_token=BOT_TOKEN, room_id=self.room_id)

if __name__ == "__main__":
    from webexChatBot import send_message
    webex_room_id = "Y2lzY29zcGFyazovL3VzL1JPT00vNjFjNzQ3MzAtMjMwMi0xMWVkLTg4YWEtZjkwYTcyYTM0MWE5"
    filtered_df_error = "MDSO | Error: Resource 050a3c30-61f6-11ee-866f-e3871dcf70de failed:Failed task:(1) activate: Failed remote script 'activate'(exit code: 1): Error in scripts.networkservice.circuitdetailscollector.Activate, IP 76.53.123.250/29 is not a network address.  Please check file: plan-script-050a3c30-61f6-11ee-866f-e3871dcf70de-activate-2023-10-03T14:06:19.682Z{'autoClean': False, 'createdAt': '2023-10-03T14:06:19.623Z', 'desiredOrchState': 'active', 'differences': [], 'discovered': False, 'do - serviceMapper"
    error_code = 'New Error Discovered'

    test_payload = {
                    "32.L1XX.006299..CHTR": {'error': filtered_df_error, "defect": error_code}
                    }

    ErrorWatch(webex_room_id, test_payload)
