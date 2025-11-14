from pydantic import Field
from typing import Optional

from .basemodels import ServiceTypeModel


class BandwidthChangePayloadModel(ServiceTypeModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    bw_speed: str = Field(examples=["10"])
    bw_unit: str = Field(examples=["Gbps"])
    change_reason: str = Field(examples=["Change Reason"])
    engineering_job_type: str = Field(examples=["Express BW Upgrade", "Upgrade", "Downgrade"])
    # Optional
    engineering_name: Optional[str] = Field(None, examples=["ENG-12345689"])
    engineering_id: Optional[str] = Field(None, examples=["ENG-12345689"])
    odin_check: Optional[bool] = Field(True, examples=[True])
    primary_fia_service_type: Optional[str] = Field(None, examples=["LAN"])
    uni_type: Optional[str] = Field(None, examples=["Access"])
    connector_type: Optional[str] = Field(None, examples=["RJ45"])
    retain_ip_addresses: Optional[str] = Field(None, examples=["N"])
    usable_ip_addresses_requested: Optional[str] = Field(None, examples=["N"])
    ip_address: Optional[str] = Field(None, examples=["192.168.1.1"])
    spectrum_primary_enni: Optional[str] = Field(None, examples=["21002.GE10.SNACTX901CW.SNACTX90WCW"])
    spectrum_secondary_enni: Optional[str] = Field(None, examples=["21002.GE10.SNACTX901CW.SNACTX90WCW"])
    primary_vlan: Optional[str] = Field(None, examples=["VLAN1200"])
    secondary_vlan: Optional[str] = Field(None, examples=["VLAN1202"])
    type_2: Optional[str] = Field(None, examples=["Y"])
