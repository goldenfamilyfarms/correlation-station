import logging

from arda_app.bll.net_new.create_cpe import create_cpe_shelf, create_shelf_WIA
from arda_app.bll.net_new.create_vgw import create_vgw_shelf
from arda_app.bll.net_new.create_mne import create_mne_shelf
from arda_app.bll.net_new.create_sbb import create_SBB_shelves
from arda_app.bll.net_new.with_cj.create_mtu import create_mtu_shelf

logger = logging.getLogger(__name__)


def create_shelf_main(payload):
    if "Wireless Internet Access" in payload["product_name"]:
        logger.info("Creating WIA shelf")
        return create_shelf_WIA(payload)
    elif payload["role"] == "mtu":
        logger.info("Creating MTU shelf")
        return create_mtu_shelf(payload)
    elif payload["role"] == "cpe":
        logger.info("Creating CPE shelf")
        return create_cpe_shelf(payload)
    elif payload["role"] == "vgw":
        logger.info("Creating VGW shelf")
        return create_vgw_shelf(payload)
    elif payload["role"] == "mne":
        logger.info("Creating MNE MX shelves")
        return create_mne_shelf(payload)
    elif payload["role"] == "sbb":
        logger.info("Creating SBB shelves")
        return create_SBB_shelves(payload)
