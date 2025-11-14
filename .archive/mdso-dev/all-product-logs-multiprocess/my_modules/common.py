import pandas as pd
import io

'''
This module contains code to be shared as needed

'''
# Testing area set active to true to test test dictionary or false to run for real
class Dbg(object):
    active = False


DEBUGGER = Dbg()

# adds Colors to text, e.g., RED + 'Hello' + RESET
def text_color():
    WHITE = '\033[37m'
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    PURPLE = '\033[35m'
    Cyan = '\033[36m'
    RESET = '\033[m'
    return WHITE, BLACK, RED, GREEN, YELLOW, BLUE, PURPLE, Cyan, RESET

WHITE, BLACK, RED, GREEN, YELLOW, BLUE, PURPLE, Cyan, RESET = text_color()


batcher_dict = {
    'Mickey': {'email': 'michaelx.smith@charter.com'},
    'Alex': {'email': 'michaelx.smith@charter.com' },
    'Tina': {'email': 'michaelx.smith@charter.com'},
    'Ashley': {'email': 'michaelx.smith@charter.com'},
    'Chris': {'email': 'michaelx.smith@charter.com'},
    'Richard': {'email': 'michaelx.smith@charter.com'},
    'Tom': {'email': 'michaelx.smith@charter.com'},
    'Dave': {'email': 'michaelx.smith@charter.com'}
}

# if DEBUGGER.active:
#     print(YELLOW + 'TESTING TESTING NO ANIMALS nor EPRs WERE HARMED DURRING THIS TEST' + RESET)
#     # the batcher_dict contains infomation for each batcher the values are passed
#     # to multiple functions to gather data
#     # batcher_dict = {
#     #     'Mickey': {'email': 'michaelx.smith@charter.com'},
#     #     'Alex': {'email': 'michaelx.smith@charter.com' },
#     #     'Tina': {'email': 'michaelx.smith@charter.com'},
#     #     'Ashley': {'email': 'michaelx.smith@charter.com'},
#     #     'Chris': {'email': 'michaelx.smith@charter.com'},
#     #     'Richard': {'email': 'michaelx.smith@charter.com'},
#     #     'Tom': {'email': 'michaelx.smith@charter.com'},
#     #     'Dave': {'email': 'michaelx.smith@charter.com'}
#     # }
# else:
#     # the is the real dictionary.... preferred_defect_delivery leave value empty if would like both email and webex
#     batcher_dict = {
#         'Mickey': {'email': 'michaelx.smith@charter.com', 'preferred_defect_delivery': 'webex'
#                    },
#         'Alex': {'email': 'alex.arandia@charter.com', 'preferred_defect_delivery': 'webex'
#                  },
#         'Tina': {'email': 'tina.yang@charter.com', 'preferred_defect_delivery': 'webex'
#                  },
#         'Ashley': {'email': 'ashley.robles@charter.com', 'preferred_defect_delivery': 'webex'
#                    },
#         'Chris': {'email': 'christopher.schafer@charter.com', 'preferred_defect_delivery': 'webex'
#                   },
#         'Tom': {'email': 'thomas.hauser@charter.com', 'preferred_defect_delivery': 'webex'
#                 },
#         'Dave': {'email': 'david.edelson@charter.com', 'preferred_defect_delivery': 'webex'
#                 }
#     }



# by way of the batcher_dict which stores each batchers report information
# this function determines value for reportID. 'cid_column' and 'defect_column'
# are used locate the circuit id and the defect placement on the spreadsheet
# and is passed to defect_cid_compare()
def report_person_option(batcher_name, batcher_dict):
    email = batcher_dict[batcher_name]['email']
    preferred_defect_delivery = batcher_dict[batcher_name]['preferred_defect_delivery']

    return email, preferred_defect_delivery


if __name__ == '__main__':
    print(batcher_dict)
