from pydantic import BaseModel, Field


class UpdatePathStatusResponseModel(BaseModel):
    cid: str = Field(..., examples=["32.L1XX.990440..CHTR"])
    ethernet_transport: str = Field(..., examples=["51001.GE10.SMRCTX510QW.SMRCTXFI1ZW"])
    status: str = Field(..., examples=["Designed"])
