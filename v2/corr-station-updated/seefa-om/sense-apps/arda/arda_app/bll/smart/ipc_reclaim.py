import logging

from arda_app.bll.net_new.ip_reclamation import get_subnet_block_by_ip, delete_block
from common_sense.common.errors import abort

logger = logging.getLogger(__name__)


def ipc_reclaim(params):
    ip = params.ip.split("/")[0]
    ipc_resp = get_subnet_block_by_ip(ip)
    if isinstance(ipc_resp, dict):
        block_name = ipc_resp.get("blockName", "")
        user_fields = ipc_resp.get("userDefinedFields", [""])

        # checking IP block size matches in Granite and IPC
        if params.ip.upper().strip() != block_name.upper():
            msg = f"Requested IP: {params.ip} does not match IPC block: {block_name}. Please investigate"
            logger.error(msg)
            abort(500, msg)

        if user_fields:
            for notes in user_fields:
                if "SEEFA_SENSE" in notes:
                    container = ipc_resp.get("container", [""])
                    delete_block(block_name, container[0], "test_cid")
                    return "IP Reset Successful"

        # return fallout message if notes are blank or SEEFA_SENSE is missing from notes
        msg = f"Unable to delete {params.ip} from IPC as the phrase 'SEEFA_SENSE' is not in the notes section."
        logger.error(msg)
        abort(500, msg)
