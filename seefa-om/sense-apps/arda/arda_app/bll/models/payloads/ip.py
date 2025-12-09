from pydantic import Field, BaseModel


class IPPayloadModel(BaseModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    service: str = Field(examples=["net_new", "quick_connect"])
    ipv4_type: str = Field(examples=["LAN", "ROUTED"])
    block_size: str = Field(examples=["/29=5"])
    acct: str = Field(examples=["53n53123533FA"])
    epr: str = Field(examples=[r"ENG-533FA123"])
