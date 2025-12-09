from arda_app.bll.circuit_design.bandwidth_change.bw_downgrade import bw_downgrade_main
from arda_app.bll.circuit_design.bandwidth_change.express_bw_upgrade import express_bw_upgrade_main
from arda_app.bll.circuit_design.bandwidth_change.normal_bw_upgrade import bw_upgrade_main
from arda_app.bll.models.payloads import BandwidthChangePayloadModel


def bandwidth_change_main(payload: BandwidthChangePayloadModel):
    """Upgrade or Downgrade Bandwidth"""
    if payload.engineering_job_type.lower() == "upgrade":
        return bw_upgrade_main(payload.model_dump())
    if payload.engineering_job_type.lower() == "downgrade":
        return bw_downgrade_main(payload.model_dump())

    return express_bw_upgrade_main(payload.model_dump())
