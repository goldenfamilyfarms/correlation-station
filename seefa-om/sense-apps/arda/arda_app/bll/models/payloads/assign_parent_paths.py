from pydantic import Field
from typing import Literal

from .basemodels import ServiceTypeModel, TypeIIModel


class AssignParentPathsPayloadModel(ServiceTypeModel, TypeIIModel):
    side: Literal["a_side", "z_side"]
    number_of_circuits_in_group: int = 0
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])

    # needed for type II payload model
    class Config:
        populate_by_name = True
