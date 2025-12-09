from pydantic import BaseModel, Field


class CpeSwapResponseModel(BaseModel):
    status: str = Field(..., examples=["successful"])
    new_equip_inst_id: str = Field(..., examples=["1444625"])
    new_handoff_port_inst_id: str = Field(..., examples=["110251852"])
