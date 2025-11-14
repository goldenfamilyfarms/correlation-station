import logging

from common_sense.common.errors import abort
from arda_app.bll.assign.gsip import assign_gsip_main
from arda_app.dll.granite import get_circuit_uda_info

logger = logging.getLogger(__name__)


def bw_upgrade_assign_gsip(cid, circ_path_inst_id, product_name, class_of_service_type):
    circuit_uda_info = get_circuit_uda_info(cid=circ_path_inst_id)
    vc_class = [circuit for circuit in circuit_uda_info if circuit.get("ATTR_VALUE", "") == "TYPE 2"]
    if vc_class:
        logger.info("Type 2 circuit detected. Skipping assign gsip.")
    else:
        try:
            payload = {
                "cid": cid,
                "product_name": product_name,
                "class_of_service_type": class_of_service_type,
                "path_inst_id": circ_path_inst_id,
            }
            assign_gsip_main(payload)
        except Exception:
            logger.error(f"failed to assign GSIP for {cid}")
            abort(500, f"Failed to assign GSIP for {cid}")
