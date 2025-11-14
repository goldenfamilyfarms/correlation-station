from typing import Optional
from pydantic import Field, BaseModel


class ServiceableShelfPayloadModel(BaseModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    connector_type: str = Field(examples=["LC"])
    uni_type: str = Field(examples=["Access"])
    side: str = Field(examples=["z_side"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    # Optional
    agg_bandwidth: Optional[str] = Field(None, examples=["1Gbps"])
