from pydantic import BaseModel, Field


class IPReservationResponseModel(BaseModel):
    message: str = Field(..., examples=["IP address has been successfully reserved."])
