from pydantic import Field, BaseModel


class CpeSwapPayloadModel(BaseModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    device_tid: str = Field(examples=["GNBTNC391ZW"])
    new_model: str = Field(examples=["FSP 150-GE114PRO-C"])
    new_vendor: str = Field(examples=["ADVA"])
