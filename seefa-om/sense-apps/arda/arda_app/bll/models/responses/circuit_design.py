from pydantic import BaseModel, Field


class CircuitDesignResponseModel(BaseModel):
    circ_path_inst_id: str = Field(..., examples=["2356781"])
    maintenance_window_needed: str = Field(..., examples=["no"])
    hub_work_required: str = Field(..., examples=["no"])
    cpe_installer_needed: str = Field(..., examples=["no"])
    ip_video_on_cen: str = Field(..., examples=["no"])
    ctbh_on_cen: str = Field(..., examples=["no"])
    cpe_model_number: str = Field(..., examples=["FSP 150-GE114PRO-C"])
    engineering_job_type: str = Field(..., examples=["Partial Disconnect"])
    cosc_blacklist_ticket: str = Field(..., examples=["ticket_ABCD"])
    message: str
