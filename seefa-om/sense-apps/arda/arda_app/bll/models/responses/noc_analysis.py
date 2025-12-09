from pydantic import BaseModel, Field


class NocAnalysisResponseModel(BaseModel):
    prm_tid: str = Field(..., examples=["AMDAOH031ZW"])
    circuit_id: str = Field(..., examples=["74001.GE1.PTTPOH011CW.AMDAOH031ZW"])
    revision: str
    circuit_status: str = Field(..., examples=["Live"])
    bandwidth: str = Field(..., examples=["1 Gbps"])
    category: str = Field(..., examples=["COM-DIA"])
    a_side_site: str = Field(..., examples=["PTTPOH01_TWC/HUB 22-LANCASTER"])
    z_side_site: str = Field(..., examples=["AMDAOH03_MID WEST FABRICATION//313 N JOHNS ST"])
