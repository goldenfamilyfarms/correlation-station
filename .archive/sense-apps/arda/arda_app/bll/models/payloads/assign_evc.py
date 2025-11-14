from pydantic import Field, BaseModel
from typing import Literal


class AssignEvcPayloadModel(BaseModel):
    side: Literal["a_side", "z_side"]
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
