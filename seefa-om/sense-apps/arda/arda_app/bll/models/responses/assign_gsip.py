from pydantic import BaseModel, Field


class AssignGSIPResponseModel(BaseModel):
    message: str = Field(..., examples=["GSIP Attributes have been added successfully."])
