from pydantic import BaseModel, Field


class VLANReservationResponseModel(BaseModel):
    message: str = Field(..., examples=["Successful VLAN Reservation"])
