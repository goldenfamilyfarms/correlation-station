from typing import Optional, Literal
from pydantic import Field, model_validator

from .basemodels import ServiceTypeModel, TypeIIModel


class CreateShelfPayloadModel(ServiceTypeModel, TypeIIModel):
    side: Literal["a_side", "z_side"]
    build_type: Literal["Home Run", "STU (Single Tenant Unit)", "Strip Mall", "MTU New Build", "Null", "type2_hub"]
    role: Literal["mtu", "cpe", "vgw", "mne", "sbb"]
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    # Optional
    coax: Optional[bool] = None
    model: Optional[str] = None
    nw_ip: Optional[str] = None
    service_code: Optional[str] = None
    related_cid: Optional[bool] = None
    connector_type: Optional[Literal["RJ45", "RJ48", "SC", "LC", "RF", "N/A", ""]] = None
    uni_type: Optional[Literal["Access", "Trunked", "N/A", ""]] = None
    number_of_circuits_in_group: Optional[str] = Field(None, examples=["1"])
    number_of_b_channels: Optional[str] = None
    cpe_gear: Optional[Literal["RAD-ETX203AX (1G)", "ADVA-GE114PRO-C (1G)", "RAD2i-10G-B (10G)", "ADVA-XG108 (10G)"]] = (
        None
    )

    # needed for type II payload model
    class Config:
        populate_by_name = True

    @model_validator(mode="after")
    def _set_conector_type(cls, values) -> "CreateShelfPayloadModel":
        # Set connector type SIP and PRI products
        # to RJ45 if N/A or RJ48
        if values.product_name in {
            "Hosted Voice - (Fiber)",
            "PRI Trunk (Fiber)",
            "PRI Trunk(Fiber) Analog",
            "PRI Trunk (DOCSIS)",
            "SIP - Trunk (Fiber)",
            "SIP - Trunk (DOCSIS)",
            "SIP Trunk(Fiber) Analog",
        } and values.connector_type in {"N/A", "RJ48"}:
            values.connector_type = "RJ45"
        return values
