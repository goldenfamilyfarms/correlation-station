from pydantic import BaseModel, Field


class CreateShelfResponseModel(BaseModel):
    cpe_shelf: str = Field(..., examples=["CTPKFLFH3ZW/999.9999.999.99/NIU"])
    cpe_tid: str = Field(..., examples=["CTPKFLFH3ZW"])
    cpe_uplink: str = Field(..., examples=["110250555"])
    cpe_handoff: str = Field(..., examples=["110250558"])
    cpe_handoff_paid: str = Field(..., examples=["ETH PORT 3"])
    zw_path: str = Field(..., examples=["1426487"])
    circ_path_inst_id: str = Field(..., examples=["1377100"])
