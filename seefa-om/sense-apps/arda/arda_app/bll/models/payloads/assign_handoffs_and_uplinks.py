from typing import Literal, Optional
from pydantic import Field
from .basemodels import ServiceTypeModel, TypeIIModel


class AssignHandoffsAndUplinksPayloadModel(ServiceTypeModel, TypeIIModel):
    side: Literal["a_side", "z_side"]
    build_type: Literal["Home Run", "STU (Single Tenant Unit)", "Strip Mall", "MTU New Build", "Null", "type2_hub"]
    port_role: Literal["uplink", "handoff"]
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    circ_path_inst_id: str = Field(examples=["1234"])
    number_of_circuits_in_group: int = Field(0, examples=[1])
    # Optional
    mtu_tid: Optional[str] = None
    cpe_tid: Optional[str] = None
    mtu_uplink: Optional[str] = None
    mtu_new_build_transport: Optional[str] = None
    mtu_pe_path: Optional[str] = None
    cpe_uplink: Optional[str] = None
    cpe_handoff: Optional[str] = None
    cpe_handoff_paid: Optional[str] = None
    cpe_trunked_path: Optional[str] = None
    zw_path: Optional[str] = None

    # needed for type II payload model
    class Config:
        populate_by_name = True
