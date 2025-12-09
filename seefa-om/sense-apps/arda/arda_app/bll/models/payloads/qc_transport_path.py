from pydantic import Field
from typing import Literal
from .basemodels import ServiceTypeModel


class QCTransportPayloadModel(ServiceTypeModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    agg_bandwidth: str = Field(examples=["1Gbps"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    side: Literal["a_side", "z_side"]
