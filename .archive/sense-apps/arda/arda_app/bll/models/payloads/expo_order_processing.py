from pydantic import Field, BaseModel
from typing import Optional


class ExpoOrderProcessingPayloadModel(BaseModel):
    pid: str = Field(examples=["P8675309"])
    stage: str = Field(
        examples=[
            "All",
            "CID",
            "ISP",
            "Design",
            "ESP",
            "MS-CD",
            "NA",
            "MS-NA",
            "NC",
            "MS-NC",
            "SOVA",
            "BMS",
            "ARDA",
            "BEORN",
            "PALANTIR",
        ]
    )
    # Optional
    substage: Optional[str] = Field(None, examples=["Quick Connect", "Serviceable", "Disconnect"])
    queue_status: Optional[str] = Field(None, examples=["ON", "OFF"])
    trigger_status: Optional[str] = Field(None, examples=["ON", "OFF"])
    interval_seconds: Optional[int] = Field(None, examples=[60, 120])
    delay_minutes: Optional[int] = Field(None, examples=[0, 5])
