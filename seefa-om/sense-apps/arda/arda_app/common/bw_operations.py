from common_sense.common.errors import abort
import logging

logger = logging.getLogger(__name__)


def normalize_bandwidth_values(bw_val, bw_unit):
    """Returns bandwidth value in MBPS"""

    # First, make sure we have a proper int here
    try:
        bw_val = int(bw_val)

    except ValueError:
        logger.exception(f"Exception while parsing bandwidth value {bw_val} as an int")
        abort(500, message="Bandwidth value is not an integer")

    # Convert gigabits to megabits to make things a little easier in the logic
    if "G" in bw_unit[0]:
        bw_val = bw_val * 1000
    elif bw_unit[0] not in ["M", "G"]:
        logger.error(f"Unsupported bandwidth value {bw_unit[0]}, must be either Mbps or Gbps")
        abort(500, message="Bandwidth values must be either Mbps or Gbps")

    return bw_val
