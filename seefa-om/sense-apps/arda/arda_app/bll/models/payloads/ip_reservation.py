from typing import Optional, Literal
from pydantic import BaseModel, Field, model_validator

from .basemodels import ServiceTypeModel
from common_sense.common.errors import abort


class SideInfo(ServiceTypeModel):
    product_name: str = Field(examples=["Fiber Internet Access"])
    engineering_id: str = Field(examples=["ENG-12345689"])
    cid: str = Field(examples=["21.L1XX.025905..CHTR"])
    # Optional
    build_type: Optional[Literal["Home Run", "STU (Single Tenant Unit)", "Strip Mall", "MTU New Build", "Null", ""]] = (
        None
    )
    ipv4_type: Optional[Literal["Routed", "LAN", ""]] = None
    block_size: Optional[Literal["/30=1", "/29=5", "/28=13", "/27=29", ""]] = None

    retain_ip_addresses: Optional[Literal["Yes", "No"]] = None
    ip_address: Optional[str] = Field(examples=["107.144.153.168/29"], default=None)

    @model_validator(mode="after")
    def validate_product_name(cls, values) -> "SideInfo":
        """Validate product_name field."""
        if values.product_name in {"Carrier Fiber Internet Access", "Fiber Internet Access"} and (
            not values.ipv4_type or not values.block_size
        ):
            abort(500, "ipv4_type and block_size fields are required for FIA and Carrier FIA Products.")
        return values

    @model_validator(mode="before")
    def validate_block_size(cls, values) -> "SideInfo":
        """Validate block_size field."""
        if values.get("block_size", "") not in ["/30=1", "/29=5", "/28=13", "/27=29", ""]:
            abort(500, f"Unsupported IPv4 block_size: {values['block_size']}")
        return values


class IPReservationPayloadModel(BaseModel):
    z_side_info: SideInfo
    # Optional
    a_side_info: Optional[SideInfo] = None
