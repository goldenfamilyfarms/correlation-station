from typing import Optional
from pydantic import BaseModel, Field


class RelatedSiteNamePayloadModel(BaseModel):
    related_circuit_id: str = Field(examples=["27.L1XX.000002.GSO.TWCC"])

    # Optional
    product_family: Optional[str] = Field(None, examples=["Secure Dedicated Internet"])
