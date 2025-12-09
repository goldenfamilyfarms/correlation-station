from pydantic import BaseModel, Field
from typing import Optional


class CreateBOMPayloadModel(BaseModel):
    cid: str = Field(examples=["61.L4XX.000182..CHTR"])
    engineering_name: str = Field(examples=["ENG-03767758"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    granite_site_name: str = Field(examples=["FNTCCAJS-SPECTRUM FIBER DELIVERY MDU//14817 FOOTHILL BLVD"])
    # Optional
    agg_bandwidth: Optional[str] = Field(None, examples=["20 Mbps", "1 Gbps"])
    expedite: Optional[str] = Field(None, examples=["No", "Yes"])
    voltage: Optional[str] = Field(None, examples=["AC 120", "AC 240", "DC 24", "DC 48"])
    type_of_protection_needed: Optional[str] = Field(None, examples=["Optional UDA - Redundant Power"])
    service_code: Optional[str] = Field(None, examples=["RW700", "RW702", "RW703"])
