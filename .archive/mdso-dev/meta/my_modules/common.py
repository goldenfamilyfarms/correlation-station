import pandas as pd
import io
import configparser
import logging
import logging.config

'''
This module contains code to be shared as needed

'''

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

def set_up_logging():
    '''single location for adding logging ability for scripts'''
    logging.config.fileConfig(fname="/home/meta/logging.cfg",disable_existing_loggers=False,)
    logger = logging.getLogger(__name__)
    return logger

def set_up_config():
    config = configparser.ConfigParser()
    config.read('/home/meta/setup.cfg')
    return config