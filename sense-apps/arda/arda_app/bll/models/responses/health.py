from pydantic import BaseModel, Field


class HealthResponseModel(BaseModel):
    status: str = Field(..., examples=["Healthy!"])
