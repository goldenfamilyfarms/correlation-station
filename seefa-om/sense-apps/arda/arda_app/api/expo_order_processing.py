import logging

from arda_app.api._routers import v1_tools_router
from arda_app.bll.models.payloads.expo_order_processing import ExpoOrderProcessingPayloadModel
from arda_app.bll.expo_order_processing_main import get_expo_order_processing_main, put_expo_order_processing_main

logger = logging.getLogger(__name__)

# References
# https://jira.charter.com/browse/SEEFAEXPO-88
# https://jira.charter.com/browse/SEEFAEXPO-695
# https://jira.charter.com/browse/SENSE_SEDA-1999


@v1_tools_router.get("/expo_orderProcessing", summary="Check the status and queue of EXPO stages and substages")
def get_expo_queue_info(stages: str = "All"):
    """Get EXPO queue status by single stage or multiple comma-separated stages\n
    ALLOWED_STAGES = [
        "CID",
        "ISP",
        "Design",
        "ESP",
        "MS-CD",
        "NA",
        "MS-NA",
        "NC",
        "MS-NC",
        "SOVA",
        "BMS",
        "ARDA",
        "BEORN",
        "PALANTIR"
    ]\n
    Ex. CID,Design,NC\n
    "ARDA" will get CID, ISP, Design, BMS\n
    "BEORN" or "PALANTIR" will get ESP, MS-CD, NA, MS-NA, NC, MS-NC"""

    logger.info("Initializing EXPO orderProcessing GET")
    logger.info(f"v1/expo_orderProcessing param: {stages}")

    return get_expo_order_processing_main(stages)


@v1_tools_router.put("/expo_orderProcessing/pause", summary="Pause the queue or trigger of EXPO stages and substages")
def put_expo_order_processing(payload: ExpoOrderProcessingPayloadModel):
    """Pause EXPO queues or triggers, or update queue processing interval or delay

    Able to pause by stage, substage, microservice, or everything

    ALLOWED_STAGES = [
        "All",
        "CID",
        "ISP",
        "Design",
        "ESP",
        "MS-CD",
        "NA",
        "MS-NA",
        "NC",
        "MS-NC",
        "SOVA",
        "BMS",
        "ARDA",
        "BEORN",
        "PALANTIR"
    ]

    ALLOWED_SUBSTAGES = {
    "Design": [
        "All",
        "Quick Connect",
        "Serviceable",
        "New with CJ",
        "Bandwidth Change",
        "Logical Change",
        "Disconnect",
        "Add"
    ],
    "MS-CD": ["All", "New Install"],
    "NA": ["All", "Enterprise", "Disconnect"],
    "MS-NA": ["All", "New Install", "MNE"],
    "NC": ["All", "Enterprise", "Disconnect", "Wireless Internet Access"],
    "MS-NC": ["All", "New Install", "MNE"]
    }

    Pausing "ARDA" will pause CID, ISP, Design, BMS\n
    Pausing "BEORN" or "PALANTIR" will pause ESP, MS-CD, NA, MS-NA, NC, MS-NC
    """

    logger.info("Initializing EXPO orderProcessing PUT")
    logger.info(f"v1/expo_orderProcessing/pause payload: {payload.model_dump()}")

    body = payload.model_dump()
    return put_expo_order_processing_main(body)
