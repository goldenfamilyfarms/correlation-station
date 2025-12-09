from pydantic import Field, BaseModel


class DesignValidationPayloadModel(BaseModel):
    product_name: str = Field(..., examples=["Fiber Internet Access"])
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    assigned_cd_team: str = Field(default="Retail - NE", examples=["Retail - NE"])
    passthrough: bool = Field(default=False, examples=[True, False])
    pending_circuit: bool = Field(default=False, examples=[True, False])
