from typing import Literal
from pydantic import BaseModel, Field


class NocAnalysisPayloadModel(BaseModel):
    bandwidth: Literal["Gold", "Silver", "Bronze"]
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
