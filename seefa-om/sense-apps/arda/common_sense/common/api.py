import logging
import time

LOGGER = logging.getLogger(__name__)


def wait_for_success(func):
    def wait(self, *args, **kwargs):
        retries = 5  # 1sec, 4sec, 7sec, 11sec, 18sec
        add_sleep_time = 3
        sleep_time = 1
        result = False
        while retries > 0:
            retries = retries - 1
            result = func(self, *args, **kwargs)
            if result or isinstance(result, list) or isinstance(result, dict):
                break
            LOGGER.warning(f"Invalid Result. Retries Left: {retries}")
            time.sleep(sleep_time)
            temp = max(sleep_time, add_sleep_time)
            sleep_time = sleep_time + add_sleep_time
            add_sleep_time = temp
        else:
            LOGGER.error(
                "Time out waiting for success of {}".format(func.__name__),
                exc_info=True,
            )
        return result

    return wait
