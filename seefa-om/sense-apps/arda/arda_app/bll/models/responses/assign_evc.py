from pydantic import BaseModel, Field


class AssignEVCResponseModel(BaseModel):
    message: str = Field(..., examples=["EVC ID has been added successfully"])
