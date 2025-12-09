from pydantic import Field, BaseModel
from typing import Literal


class AssignEnniPayloadModel(BaseModel):
    side: Literal["a_side", "z_side"]
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    spectrum_primary_enni: str = Field(examples=["94.KGFD.000010..TWCC"])
    product_name: str = Field(examples=["Carrier E-Access (Fiber)"])
