from pydantic import BaseModel, Field


class DisconnectResponseModel(BaseModel):
    BFLONYKK0QW: str = Field(..., examples=["XE-0"])
    BFLONYKK1CW: str = Field(..., examples=["AE17"])
