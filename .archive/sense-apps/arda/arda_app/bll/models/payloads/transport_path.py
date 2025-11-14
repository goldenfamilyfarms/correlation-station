from pydantic import BaseModel, Field
from typing import Optional


class TransportPathPayloadModel(BaseModel):
    circuit_id: str = Field(examples=["51.L1XX.803170..TWCC"])
    hub_clli_code: str = Field(examples=["AUSBTX50"])
    bandwidth_value: str = Field(examples=["100"])
    bandwidth_type: str = Field(examples=["Mbps"])
    build_type: str = Field(examples=["MTU", "Home Run"])
    product_name_order_info: str = Field(examples=["Ethernet"])
    service_location_address: str = Field(examples=["24219 Railroad Ave Newhall CA 91321"])
    # Optional
    granite_site_name: Optional[str] = Field(
        None, examples=["IGWDCACI-23336 EMPLOYMENT DEVELOPMENT DEPARTMENT//4540 W CENTURY BLVD"]
    )
