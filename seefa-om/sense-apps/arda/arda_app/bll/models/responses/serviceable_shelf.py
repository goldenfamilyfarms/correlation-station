from pydantic import BaseModel, Field


class ServiceableShelfResponseModel(BaseModel):
    cpe_shelf: str = Field(..., examples=["HRCYCAPA1ZW/999.9999.999.99/NIU"])
    cpe_tid: str = Field(..., examples=["HRCYCAPA1ZW"])
    cpe_handoff: str = Field(..., examples=["107143956"])
    cpe_handoff_paid: str = Field(..., examples=["ETH_PORT-1-1-1-5"])
    zw_transport_path: str = Field(None, examples=["31001.GE10.LSAICAEV0QW.CLCZCAKC1ZW"])
    zw_transport_path_inst_id: str = Field(None, examples=["1677014"])
    zw_path: str = Field(None, examples=["71001.GE1.WSVLNYWF1QW.AMHRNYPA1ZW"])
    circ_path_inst_id: str = Field(..., examples=["1554134"])
