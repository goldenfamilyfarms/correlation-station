from pydantic import BaseModel, Field


class AssignParentPathsResponseModel(BaseModel):
    message: str = Field(..., examples=["Parent Paths & Cloud has been successfully added."])
