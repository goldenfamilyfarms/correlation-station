import logging

from fastapi import Query
from arda_app.bll.scrape_ip import scrape_ip_main
from common_sense.common.errors import abort
from arda_app.api._routers import v1_tools_router


logger = logging.getLogger(__name__)


@v1_tools_router.get("/ip_reservation_gather")
def ip_reservation_gather(epr: str = Query(None, examples=["ENG-04455341"])):
    """Gather information necessary to delegate IP addresses to an EPR."""

    logger.info("Initializing IP Reservation Gather")
    resp = scrape_ip_main(epr)

    # resp should be a valid dict of data
    if not resp or not isinstance(resp, dict):
        abort(500, "Invalid response from scrape_ip")

    # return to front-end
    return resp
    # wait for user confirmation ...
