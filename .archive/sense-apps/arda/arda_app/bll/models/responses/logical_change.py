from pydantic import BaseModel, Field


class LogicalChangeResponseModel(BaseModel):
    circ_path_inst_id: str
    engineering_job_type: str = Field(..., examples=["Logical Change"])
    message: str = Field(..., examples=["class of service type updated successfully"])
