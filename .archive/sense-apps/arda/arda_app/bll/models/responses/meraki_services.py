from pydantic import BaseModel, Field


class MerakiServicesResponseModel(BaseModel):
    message: str = Field(..., examples=["Meraki Services process Success"])
