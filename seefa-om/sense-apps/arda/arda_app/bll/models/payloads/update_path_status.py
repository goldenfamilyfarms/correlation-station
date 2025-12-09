from typing import Optional
from pydantic import Field

from .basemodels import ServiceTypeModel


class UpdatePathStatusPayloadModel(ServiceTypeModel):
    product_name: str = Field(examples=["Fiber Internet Access"])
    status: str = Field(examples=["Designed", "Pending Decommission"])
    # Optional
    due_date: Optional[str] = Field(None, examples=["2023-06-08"])
    engineering_job_type: Optional[str] = Field(None, examples=["Partial Disconnect", "Full Disconnect"])
    engineering_name: Optional[str] = Field(None, examples=["ENG-04178112"])
    service_location_address: Optional[str] = Field(None, examples=["225 BURNS RD"])
