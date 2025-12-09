from pydantic import BaseModel, Field


class QCTransportResponseModel(BaseModel):
    transport_path: str = Field(..., examples=["51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW"])
