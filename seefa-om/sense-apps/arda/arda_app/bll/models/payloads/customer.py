from typing import Optional
from pydantic import BaseModel, Field


class CustomerPayloadModel(BaseModel):
    name: str = Field(examples=["Name"])
    type: str = Field(examples=["ENTERPRISE"])
    country: str = Field(examples=["USA"])
    sf_id: str = Field(examples=["ACCT-123456"])
    # Optional
    phone: Optional[str] = None
    fax: Optional[str] = None
    bill_contact: Optional[str] = None
    tech_contact: Optional[str] = None
    address: Optional[str] = Field(None, examples=["1 Main St"])
    city: Optional[str] = Field(None, examples=["Wimmington"])
    state: Optional[str] = Field(None, examples=["NC"])
    zip_code: Optional[str] = Field(None, examples=["28405"])
    colo_datacenter: Optional[str] = Field(None, examples=["Yes"])
