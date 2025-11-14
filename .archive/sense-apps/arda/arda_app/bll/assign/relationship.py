import logging

from common_sense.common.errors import abort

from arda_app.dll.granite import get_granite, assign_relationship

logger = logging.getLogger(__name__)


def wiabackup_relationship(data):
    if not data:
        abort(500, "SupportedProdTemplate WIA BACKUP - Data information is unknown")

    if data["product_name"] in ("Wireless Internet Backup", "Wireless Internet Access-Backup"):
        path_inst_id = get_cid_info(data["cid"])
        related_path_inst_id = get_cid_info(data["related_cid"])

        assign_relationship(path_inst_id, related_path_inst_id)


def get_cid_info(cid):
    get_granite_url = f"/circuitSites?CIRCUIT_NAME={cid}&PATH_CLASS=P"
    cid_info = get_granite(get_granite_url)

    try:
        return cid_info[0]["CIRC_PATH_INST_ID"]
    except (TypeError, KeyError, IndexError):
        abort(500, "No CID inst id data found in granite")
