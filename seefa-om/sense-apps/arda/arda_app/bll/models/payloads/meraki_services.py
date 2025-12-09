from typing import Optional
from pydantic import Field, BaseModel


class MerakiServicesPayloadModel(BaseModel):
    product_name: str = Field(
        alias="Product Name",
        examples=[
            "Managed Network Edge",
            "Managed Network WiFi",
            "Managed Network Switch",
            "Managed Network Camera",
            "Secure Dedicated Internet",
        ],
    )
    cid: str = Field(alias="CID", examples=["51.L1XX.814879..TWCC"])
    account_number: str = Field(alias="Account Number", examples=["ACCT-123456"])
    customer_name: str = Field(alias="Customer Name", examples=["New Life Gospel Ministries"])
    customer_address: str = Field(alias="Customer Address", examples=["123 Wallaby way"])
    # Optional
    high_availability: Optional[bool] = Field(None, alias="High Availability", examples=[True])
    NWID: Optional[str] = Field(None, examples=["615304299089537775"])
