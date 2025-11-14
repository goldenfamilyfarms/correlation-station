import logging

from arda_app.common.cd_utils import granite_paths_url
from common_sense.common.errors import abort
from arda_app.dll.granite import get_granite, put_granite

logger = logging.getLogger(__name__)


def assign_evc_main(payload: dict):
    """
    Input:
    payload = {"cid": "91.L1XX.009706..CHTR"}

    Output:
    {"message": "EVC ID has been added successfully."}
    or
    Abort
    """
    cid = payload.get("cid")

    # Get the next available EVC from Granite
    get_granite_url = "/firstPathEVC"
    first_EVC_Path = get_granite(get_granite_url)

    # checking if granite call returned valid response
    if isinstance(first_EVC_Path, list):
        evc_id = first_EVC_Path[0].get("NUMBER")
        range_name = first_EVC_Path[0].get("RANGE_NAME")
    else:
        msg = "No EVCs available from /firstPathEVC response"
        logger.error(msg)
        abort(500, msg)

    if not all((evc_id, range_name)):
        abort(500, "Get granite firstPathEVC error data")

    # Assign EVC
    logger.info(f"Creating Granite circuit revision for {cid}")
    put_granite_url = "/pathAssociation"
    payload = {
        "PATH_NAME": cid,
        "PATH_REV": "1",
        "RANGE_NAME": range_name,
        "ASSOCIATION_NAME": "EVC ID NUMBER/PATH",
        "NUMBER_TYPE": "EVC ID",
        "NUMBER": evc_id,
        "STATUS": "Reserved",
    }
    put_granite(put_granite_url, payload)

    # Update CID Path with EVC ID
    logger.info(f"Updating {cid} with EVC ID")
    put_granite_url = granite_paths_url()
    payload = {"PATH_NAME": cid, "PATH_REVISION": "1", "UDA": {"ADDITIONAL ETHERNET INFO": {"EVC ID": evc_id}}}
    put_granite(put_granite_url, payload)

    return {"message": "EVC ID has been added successfully."}


def assign_evc_2(cid):
    """
    Gets next available EVC from Granite. Assigns it to the CID in granite.

    Input:
    cid = 91.L1XX.009706..CHTR

    Output:
    None
    or
    Abort
    """
    # Get the next available EVC from Granite
    get_granite_url = "/firstPathEVC"
    first_evc_path = get_granite(get_granite_url)

    evc_id = first_evc_path[0].get("NUMBER")
    range_name = first_evc_path[0].get("RANGE_NAME")
    if not all((evc_id, range_name)):
        abort(500, "Get granite firstPathEVC error data")

    # Assign EVC
    logger.info(f"Creating Granite circuit revision for {cid}")
    put_granite_url = "/pathAssociation"
    payload = {
        "PATH_NAME": cid,
        "PATH_REV": "1",
        "RANGE_NAME": range_name,
        "ASSOCIATION_NAME": "EVC ID NUMBER/PATH",
        "NUMBER_TYPE": "EVC ID",
        "NUMBER": evc_id,
        "STATUS": "Reserved",
    }
    put_granite(put_granite_url, payload)

    # Update CID Path with EVC ID
    logger.info(f"Updating {cid} with EVC ID")
    put_granite_url = granite_paths_url()
    payload = {"PATH_NAME": cid, "PATH_REVISION": "1", "UDA": {"ADDITIONAL ETHERNET INFO": {"EVC ID": evc_id}}}
    put_granite(put_granite_url, payload)

    return range_name
