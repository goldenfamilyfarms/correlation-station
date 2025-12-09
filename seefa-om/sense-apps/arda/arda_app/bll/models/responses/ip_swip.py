from pydantic import BaseModel, Field


class IPSWIPResponseModel(BaseModel):
    message: str = Field(..., examples=["IPs have been SWIP'd: 192.168.0.1/28, 2001:0db8::/48"])


class IPUnSWIPResponseModel(BaseModel):
    message: str = Field(..., examples=["IPs removed from ARIN: 192.168.0.1/28, 2001:0db8::/48"])
