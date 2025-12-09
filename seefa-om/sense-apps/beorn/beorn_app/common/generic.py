import logging
import time
import re

BIT = 1
KILOBIT = 10**3 * BIT
MEGABIT = 10**6 * BIT
GIGABIT = 10**9 * BIT
TERABIT = 10**12 * BIT
PETABIT = 10**15 * BIT
BYTE = 8 * BIT
KILOBYTE = 10**3 * BYTE
MEGABYTE = 10**6 * BYTE
GIGABYTE = 10**9 * BYTE
TERABYTE = 10**12 * BYTE
PETABYTE = 10**15 * BYTE

# Circuit Testing Path Types
FIA = "FIA"
ELAN = "ELAN"
ELINE = "ELINE"
ELINE_SEGMENT = "ELINE SEGMENT"
CTBH = "CTBH"

ADVA = "ADVA"
ALCATEL = "ALCATEL"
CIENA = "CIENA"
CISCO = "CISCO"
JUNIPER = "JUNIPER"
NOKIA = "NOKIA"
RAD = "RAD"
SUMITOMO = "SUMITOMO"

ENG_ID_REGEX = re.compile("ENG-[0-9]{8}")
MAC_ADDR_REGEX = re.compile(".{2}:.{2}:.{2}:.{2}:.{2}:.{2}")

LOGGER = logging.getLogger(__name__)


def wait_for_success(func):
    def wait(*args, **kwargs):
        retries = 5  # 1sec, 4sec, 7sec, 11sec, 18sec
        add_sleep_time = 3
        sleep_time = 1
        result = False
        while retries > 0:
            retries = retries - 1
            result = func(*args, **kwargs)
            if result:
                break
            LOGGER.warning(f"Invalid Result. Retries Left: {retries}")
            time.sleep(sleep_time)
            temp = max(sleep_time, add_sleep_time)
            sleep_time = sleep_time + add_sleep_time
            add_sleep_time = temp
        else:
            LOGGER.warning("Time out waiting for success of {}".format(func.__name__), exc_info=True)
        return result

    return wait
