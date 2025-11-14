from typing import List, Optional, Union
from pydantic import BaseModel, Field


class RelatedCircuitId(BaseModel):
    path: str = Field(None, examples=["51.L4XX.%..SUNW"], description="Created path id")
    circuit_inst_id: str = Field(None, examples=["12345"])


class CircuitPathResponseModel(BaseModel):
    path: str = Field(None, examples=["51.L4XX.%..SUNW"], description="Created path id")
    circuit_inst_id: str = Field(None, examples=["12345"])
    relatedCircuitId: Optional[Union[List[RelatedCircuitId], RelatedCircuitId]] = None
