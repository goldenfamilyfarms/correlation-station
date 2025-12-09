from typing import Optional
from pydantic import Field, BaseModel


class ElanAddVplsPayloadModel(BaseModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    create_new_elan_instance: str = Field(examples=["Yes", "No", "N/A"])
    product_name: str = Field(examples=["EP-LAN (Fiber)"])
    # Optional
    customers_elan_name: Optional[str] = Field(None, examples=["CHTRSE.VRFID.123456.VIA CARE COMMUNITY HEALTH CENT"])
    granite_site_name: Optional[str] = Field(
        None, examples=["ELANCAPX-UNIVERSITY COOPERATIVE HOUSING ASSOCIATION//500 LANDFAIR AVE"]
    )
