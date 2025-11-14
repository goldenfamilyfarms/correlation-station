from typing import Literal, Optional
from pydantic import Field, BaseModel

from .basemodels import TypeIIModel


class AssignGsipPayloadModel(BaseModel, TypeIIModel):
    cid: str = Field(..., examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(..., examples=["Fiber Internet Access"])
    # Optional
    class_of_service_type: Optional[Literal["Gold", "Silver", "Bronze"]] = None

    # needed for type II payload model
    class Config:
        populate_by_name = True
