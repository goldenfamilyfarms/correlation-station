from pydantic import BaseModel, Field


class AdvaRadResponseModel(BaseModel):
    VENDOR: str = Field(..., examples=["RAD"])
