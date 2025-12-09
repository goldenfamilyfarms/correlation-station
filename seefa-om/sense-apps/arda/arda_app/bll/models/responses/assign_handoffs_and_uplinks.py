from pydantic import BaseModel, Field


class AssignHandoffsAndUplinksResponseModel(BaseModel):
    message: str = Field(..., examples=["CPE Uplink has been added successfully."])
