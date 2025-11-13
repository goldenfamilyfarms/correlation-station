from pydantic import BaseModel, Field


class AssignEnniResponseModel(BaseModel):
    message: str = Field(..., examples=["ENNI has been added successfully."])
