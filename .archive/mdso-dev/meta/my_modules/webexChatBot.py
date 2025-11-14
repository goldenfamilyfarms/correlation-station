from webexteamssdk import WebexTeamsAPI
from my_modules.common import set_up_logging
import os


logger = set_up_logging()
logger.info('#' * 60)
logger.info(f' ----> {os.path.basename(__file__)} <--')
logger.info('#' * 60)

# Use the generated token from the Webex Teams Bot
def get_token():
    # CORE Remediator
    bot_token = (
        "M2MyNjk5MWEtMzYxMy00NDdiLTk3ZmItOTRhYTlhY2NlMGYwNjY0ZGVmZDgtNzlj_PF84_7b835734-9034-479a-8451-1c20629a0ffd"
    )
    # Connectivity Tester
    # bot_token = (
    #     "YWZmZDBiYWYtZWEwMC00M2NlLTllYjMtMTc4NDY1YTUzNmVmNTcyMThjNzctNWY0_PF84_7b835734-9034-479a-8451-1c20629a0ffd"
    # )
    # NF Remediator
    # bot_token = (
    #     "NzdiNDZiZmYtNzY1NS00ODU4LTgxOWYtYTlkNTc1ZTliZTlmMjc3YjBjMWQtMmQw_PF84_7b835734-9034-479a-8451-1c20629a0ffd"
    # )
    return bot_token


# This is used to gather all the rooms the bot is connected to
# Can be filtered to specific rooms
def get_rooms(token):
    webex_api = WebexTeamsAPI(access_token=token)
    rooms = webex_api.rooms.list()
    return rooms


# This will send a message to the room in markdown format with optional file
def execute(token, roomid, msg=None, file=None):
    webex_api = WebexTeamsAPI(token)
    if file:
        webex_api.messages.create(roomId=roomid, markdown=msg, files=file)
    else:
        webex_api.messages.create(roomId=roomid, markdown=msg)


# Main function to send a message to all rooms the bot is connected to
def send_message(message, file=None, room_id=None, bot_token=None):
    if bot_token is None:
        webex_api = get_token()
    else:
        webex_api = bot_token

    rooms = get_rooms(webex_api)
    if room_id:
        room_id = room_id
        execute(webex_api, room_id, msg=message, file=file)
    else:
        for room in rooms:
            room_id = room.id
            md_msg = message
            execute(webex_api, room_id, msg=md_msg, file=file)


if __name__ == "__main__":
    rooms = get_rooms(get_token())
    print(list(rooms))
