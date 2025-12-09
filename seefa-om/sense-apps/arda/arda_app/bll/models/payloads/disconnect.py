from typing import Optional
from pydantic import Field, field_validator
from .basemodels import ServiceTypeModel
from common_sense.common.errors import abort


class DisconnectPayloadModel(ServiceTypeModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    # Optional
    service_location_address: Optional[str] = Field(None, examples=["11921 N. Mopac Expwy, Austin, TX 78759"])
    product_family: Optional[str] = Field(None, examples=["Dedicated Internet Service"])
    engineering_name: Optional[str] = Field(None, examples=["ENG-05326542"])

    @field_validator("product_name")
    @classmethod
    def _supported_products(cls, value) -> "DisconnectPayloadModel":
        value = "SIP - Trunk (Fiber)" if value == "SIP Trunk (Fiber)" else value

        if value not in (
            "Carrier E-Access (Fiber)",
            "Fiber Internet Access",
            "Carrier Fiber Internet Access",
            "EP-LAN (Fiber)",
            "EPL (Fiber)",
            "EVPL (Fiber)",
            "Hosted Voice - (Fiber)",
            "Hosted Voice - (DOCSIS)",
            "Hosted Voice - (Overlay)",
            "PRI Trunk (DOCSIS)",
            "PRI Trunk (Fiber)",
            "PRI Trunk(Fiber) Analog",
            "SIP - Trunk (Fiber)",
            "SIP Trunk(Fiber) Analog",
            "SIP - Trunk (DOCSIS)",
            "Managed Network Edge - Spectrum Provided",
            "Managed Network Edge - Customer Provided",
            "Managed Network Edge - Off Net",
            "Managed Network Edge - Customer Provided - Off Net",
            "Managed Network Edge – Teleworker",
        ):
            abort(500, f"Unsupported product :: {value}")
        return value
