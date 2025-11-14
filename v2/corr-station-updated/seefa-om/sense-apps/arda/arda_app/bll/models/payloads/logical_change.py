from typing import Optional, Literal
from pydantic import Field

from .basemodels import ServiceTypeModel


class LogicalChangePayloadModel(ServiceTypeModel):
    cid: str = Field(..., examples=["81.L1XX.006522..TWCC"])
    engineering_name: str = Field(..., examples=["ENG-1234567"])
    product_name: str = Field(..., examples=["Fiber Internet Access"])
    change_reason: Literal[
        "Upgrading Service", "HV - Complex", "Feature Change-No MRC Impact", "Feature Change-MRC Impact"
    ]
    # Optional
    third_party_provided_circuit: Optional[str] = Field(None, examples=["true"], alias="3rd_party_provided_circuit")
    class_of_service_needed: Optional[str] = Field(None, examples=["yes"])
    class_of_service_type: Optional[str] = Field(None, examples=["Silver"])
    engineering_id: Optional[str] = None
    spectrum_primary_enni: Optional[str] = Field(None, examples=["90.KGFD.000072..CHTR"])
    spectrum_secondary_enni: Optional[str] = Field(None, examples=["90.KGFD.000072..CHTR"])
    primary_vlan: Optional[str] = Field(None, examples=["1100"])

    class Config:
        populate_by_name = True
