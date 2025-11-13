from typing import Optional
from pydantic import BaseModel, Field


class SitePayloadModel(BaseModel):
    name: str = Field(examples=["Site Name"])
    parent: str = Field(examples=["Syracuse"])
    type: str = Field(examples=["LOCAL"])
    address: str = Field(examples=["1 Main St"])
    city: str = Field(examples=["Austin"])
    state: str = Field(examples=["TX"])
    zip_code: str = Field(examples=["12345"])
    product_name_order_info: str = Field(examples=["Carrier"])
    product_family: str = Field(examples=["CTBH Wave Services"])
    sf_id: str = Field(examples=["ACCT-123456"])
    # Optional
    zip_code_2: Optional[str] = None
    site_contacts: Optional[str] = None
    construction_job_number: Optional[bool] = None
    customer: Optional[str] = Field(None, examples=["Customer ID"])
    room: Optional[str] = Field(None, examples=["# 2A"])
    floor: Optional[str] = Field(None, examples=["Basement"])
    gems_key: Optional[str] = Field(None, examples=["12345"])
    lata_code: Optional[str] = Field(None, examples=["134"])
    fixed_access_code: Optional[str] = Field(None, examples=["14607494"])
    enni: Optional[str] = Field(None, examples=["21.KGFD.000362..CHTR"])
    third_party_provided_circuit: Optional[str] = Field(None, examples=["true"], alias="3rd_party_provided_circuit")

    class Config:
        populate_by_name = True
