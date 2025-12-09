from typing import List, Optional
from pydantic import Field, BaseModel


class RelatedEprsPayloadModel(BaseModel):
    engineering_name: str = Field(examples=["ENG-03806752"])
    # Optional
    complete_date: Optional[str] = None
    WO: Optional[str] = Field(examples=["WO0000000000001"])
    submitted_date: Optional[str] = Field(examples=["2023-10-01"])
    submitted_by: Optional[str] = Field(examples=["0051W000004cV9LQAU"])
    status: Optional[str] = Field(examples=["Open"])


class PickSovaWoPayloadModel(BaseModel):
    related_eprs: List[RelatedEprsPayloadModel]
    prism_id: str = Field(examples=["4453191"])
