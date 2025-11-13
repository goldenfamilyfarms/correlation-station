import argparse
import configparser
import logging
import logging.config
import os
from my_modules import notify2, common
from webexteamssdk import WebexTeamsAPI
import random



# # gives the daily count of Passes | Fallout | Excludes
# fallout_totals = fallout_counter()

message = "Served Fresh!!"

# imported function to add color to things
WHITE, BLACK, RED, GREEN, YELLOW, BLUE, PURPLE, Cyan, RESET = common.text_color()

# these two lines allow for logging
logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

# function logs into webex
def webex_login():
    logger.info('Reading setup.cfg for secrets')
    config = configparser.ConfigParser()
    config.read('/home/setup.cfg')
    token = config['webex']['bot_token']
    logger.info('Creating Webex token')
    webex_api = WebexTeamsAPI(access_token=token)
    return webex_api

# function send messages and attachments to batchers
def webex_send(webex_api, user, message):
    '''This is the magic that allows for sending of a message and
    attachment to a user via webexteams
    '''
    logger.info('Attempting to send zipped log via webex')
    msg = f'''
    {message}
    '''
    filename = ['generated_CPEA_Template.xlsx']
    notify2.direct_message(webex_api, user, msg, filename)
    logger.info(f'Log sent to webex')
    logger.info(f'webex message sent to {GREEN}Webexteams{RESET}')

def webex_group_send(webex_api, room_id, file):
    '''This is the magic that allows for sending of a message and
    attachment to a room id via webexteams
    '''
    logger.info('composing webex message and attaching log')
    msg = f'''

    {message}

    '''
    filename = file

    notify2.group_message(webex_api, room_id, msg, filename)
    logger.info(f'Message sent to webex')
    logger.info(f'webex message sent to {GREEN}Webexteams{RESET}')


if __name__ == '__main__':

    notify2.webex_api = webex_login()
    # user = 'michaelx.smith@charter.com'
    # room_id = "Y2lzY29zcGFyazovL3VzL1JPT00vYzU5NDk2NTAtNTY5NC0xMWViLWFhMGYtZWRjZDk5MTdkMGU2",  #Clan Beef Supreme
    room_id = 'Y2lzY29zcGFyazovL3VzL1JPT00vMjllNTE1NjAtNmJhZi0xMWViLWJkZmEtMzdkNzc0Y2Y0MDA0'   #Bot_test_room
    # room_id = "Y2lzY29zcGFyazovL3VzL1JPT00vZDBlNmRjMTAtNTU2MS0xMWU5LWI3OWQtYjE1ZTM0ZWJjYmM3",  #"OPP & the Funky Bunch"
    # room_id = 'Y2lzY29zcGFyazovL3VzL1JPT00vYjk2MWRmNzAtOTE1Yy0xMWViLTgyYWItY2IxZmYxNDRjYzQ1'    #Fallout Collab W/ Provisioning
    file = [r'C:\Users\P2160442\Desktop\fallout_files\Jokers_defects.xlsx']
    notify2.webex_group_send(webex_api, room_id, file)
