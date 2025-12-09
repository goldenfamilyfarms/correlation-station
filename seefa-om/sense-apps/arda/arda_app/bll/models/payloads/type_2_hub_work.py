from pydantic import BaseModel, Field


class Type2HubWorkPayloadModel(BaseModel):
    cid: str = Field(examples=["95.L1XX.004370..CHTR"])
    third_party_provided_circuit: str = Field(examples=["Y"])
    service_provider: str = Field(examples=["COMCAST / Comcast"])
    service_provider_uni_cid: str = Field(examples=["70.KGGS.021142..CPBL.."])
    service_provider_cid: str = Field(examples=["70.VLXP.019925.ON.CPBL.."])
    service_provider_vlan: str = Field(examples=["3991"])
    spectrum_buy_nni_circuit_id: str = Field(examples=["60.KGFD.000001..TWCC"])
