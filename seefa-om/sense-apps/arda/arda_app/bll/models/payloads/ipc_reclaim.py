from pydantic import BaseModel, Field


class IPCPayloadModel(BaseModel):
    ip: str = Field(examples=["123.56.67.89/30"])
