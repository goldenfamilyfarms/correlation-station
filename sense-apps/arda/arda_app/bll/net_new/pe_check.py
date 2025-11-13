from common_sense.common.errors import abort
import logging
from arda_app.dll.granite import get_granite
from arda_app.common.cd_utils import get_l1_url

logger = logging.getLogger(__name__)


def pe_check_main(cid):
    """Input a CID and retrieve assigned elements including transport paths in order"""
    # Get circuit information
    l1_url = get_l1_url(cid)
    l1_res = get_granite(l1_url)
    # Confirm no empty response
    try:
        l1_res[0]
    except IndexError:
        logger.exception(f"No data in response from Granite for Path ID: {cid}")
        abort(500, message=f"No data in response from Granite for Path ID: {cid}.", url=l1_url, response=l1_res)
    elements = [i.get("ELEMENT_NAME") for i in l1_res if i.get("ELEMENT_NAME")]
    return elements, 200
