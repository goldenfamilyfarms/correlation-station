from typing import Literal
from pydantic import Field

from .basemodels import ServiceTypeModel


class CreateMTUTransportPayloadModel(ServiceTypeModel):
    mtu_tid: str
    cpe_tid: str
    mtu_handoff: str
    cpe_uplink: str
    side: Literal["a_side", "z_side"]
    build_type: Literal["Home Run", "STU (Single Tenant Unit)", "Strip Mall", "MTU New Build", "Null"]
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
