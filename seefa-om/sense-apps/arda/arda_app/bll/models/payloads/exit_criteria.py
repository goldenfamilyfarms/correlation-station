from pydantic import Field, BaseModel


class ExitCriteriaPayloadModel(BaseModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    circ_path_inst_id: str = Field(examples=["2356781"])
    engineering_job_type: str = Field(examples=["Partial Disconnect"])
    cpe_model_number: str = Field(examples=["FSP 150-GE114PRO-C"])
    product_name: str = Field(examples=["Fiber Internet Access"])
