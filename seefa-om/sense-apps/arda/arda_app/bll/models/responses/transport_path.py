from pydantic import BaseModel, Field


class TransportPathResponseModel(BaseModel):
    transport_path: str = Field(None, examples=["51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW"])


class TransportPathAssignResponseModel(BaseModel):
    message: str = Field(..., examples=["Successful Transport Assignment"])
    port_inst_id: str = Field(..., examples=["98349921"])
    port_access_id: str = Field(..., examples=["GE-0/0/2"])
    slot: str = Field(..., examples=["02"])
    customer_id: str = Field(..., examples=["PARADIGM TAX GROUP - MICROCORP INC"])
    z_address: str = Field(..., examples=["11921 N MO PAC EXPY"])
    z_city: str = Field(..., examples=["AUSTIN"])
    z_state: str = Field(..., examples=["TX"])
    z_zip: str = Field(..., examples=["78759"])
