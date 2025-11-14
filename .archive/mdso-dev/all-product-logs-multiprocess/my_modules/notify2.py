import os
import logging
import logging.config
from webexteamssdk import WebexTeamsAPI

logging.config.fileConfig(fname='/home/all-product-logs-multiprocess/logging.cfg', disable_existing_loggers=False)
logger = logging.getLogger(os.path.basename(__file__))

def direct_message(api, email, msg=None, filename=None):
    logger.info('Sending notification to: ' + email)
    if filename:
        api.messages.create(toPersonEmail=email, markdown=msg, files=filename)
    else:
        api.messages.create(toPersonEmail=email, markdown=msg)


def get_room_id(api, room_name, debug=False):
    rooms = api.rooms.list()
    logger.info('Searching for room: ' + room_name)
    room = [room for room in rooms if room.title == room_name][0]
    if debug:
        print(room.id)

    return room.id


def group_message(api, room_id, msg=None, filename=None, debug=False):
    logger.info('Sending message to room')
    if filename:
        api.messages.create(roomId=room_id, markdown=msg, files=filename)
    else:
        api.messages.create(roomId=room_id, markdown=msg)
    if debug:
        logger.info(f'group message: {msg}')
