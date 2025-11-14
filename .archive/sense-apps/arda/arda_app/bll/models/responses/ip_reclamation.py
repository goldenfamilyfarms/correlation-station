from pydantic import BaseModel, Field


class IPReclamationResponseModel(BaseModel):
    message: str = Field(..., examples=["108.25.121.142/29", "2700:5001:F583::/48", "2700:5001:F500::11E/127"])
