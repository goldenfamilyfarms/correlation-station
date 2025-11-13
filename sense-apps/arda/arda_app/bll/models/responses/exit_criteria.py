from pydantic import BaseModel, Field


class ExitCriteriaResponseModel(BaseModel):
    cid: str = Field(..., examples=["51.L1XX.008342..CHTR"])
    circ_path_inst_id: str = Field(..., examples=["2356781"])
    granite_link: str = Field(..., examples=["granite link"])
    maintenance_window_needed: str = Field(..., examples=["no"])
    ip_video_on_cen: str = Field(..., examples=["no"])
    ctbh_on_cen: str = Field(..., examples=["no"])
    cpe_model_number: str = Field(..., examples=["FSP 150-GE114PRO-C"])
    hub_work_required: str = Field(..., examples=["no"])
    cpe_installer_needed: str = Field(..., examples=["no"])
    message: str = Field(..., examples=["Granite, Network, and IP check successful: no IPs blacklisted"])
