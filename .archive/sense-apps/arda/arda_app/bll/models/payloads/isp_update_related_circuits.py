from typing import List, Optional
from pydantic import BaseModel, Field


class CircuitIdFields(BaseModel):
    product_name_order_info: str = Field(examples=["Ethernet"])
    circuit_id: str = Field(examples=["51.L1XX.008342..CHTR", "52.L1XX.008342..CHTR"])


class ISPUpdateRelatedCircuitsPayloadModel(BaseModel):
    related_circuit_ids: List[CircuitIdFields]
    # Optional
    service_location_address: Optional[str] = Field(None, examples=["24219 Railroad Ave Newhall CA 91321"])
    main_circuit_id: Optional[CircuitIdFields] = None
    transport_path: Optional[str] = Field(None, examples=["51001.GE1.AUSDTXIR2QW.AUSZTXOC2ZW"])
