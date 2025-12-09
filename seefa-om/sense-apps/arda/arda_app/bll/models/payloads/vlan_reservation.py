from typing import List, Optional
from pydantic import Field

from .basemodels import BaseModel, ServiceTypeModel, TypeIIModel


class VLANReservationPayloadModel(ServiceTypeModel, TypeIIModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    # Optional
    primary_vlan: Optional[str] = Field(None, examples=["1100"])
    vlan_requested: Optional[str] = Field(None, examples=["1201"])
    path_instid: Optional[str] = Field(None, examples=["123456"])

    # needed for type II payload model
    class Config:
        populate_by_name = True


class Type2OuterVLANRequestPayloadModel(BaseModel):
    nni: str = Field(examples=["60.KGFD.000001..TWCC"])
    exclusion_list: List[int] = Field(examples=[[1100, 1101, 1103]])
    product_name: str = Field(examples=["Fiber Internet Access"])

    class Config:
        populate_by_name = True
