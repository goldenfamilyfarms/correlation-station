from typing import Optional, Literal
from pydantic import BaseModel, Field

from .basemodels import TypeIIModel


class SideInfo(BaseModel, TypeIIModel):
    product_name: str = Field(examples=["Fiber Internet Access"])
    product_family: str = Field(examples=["Dedicated Internet Service"])
    engineering_id: str = Field(examples=["a2g8Z000009NGhIQAW"])
    cid: str = Field(examples=["84.L4XX.000058..CHTR"])
    z_location: str = Field(examples=["11921 N. Mopac Expwy, Austin, TX 78759"])
    service_location_address: str = Field(examples=["11921 N. Mopac Expwy, Austin, TX 78759"])
    # Optional
    customers_elan_name: Optional[str] = None
    number_of_b_channels: Optional[str] = None
    number_of_analog_lines: Optional[str] = None
    number_of_native_lines: Optional[str] = None
    number_of_ported_lines: Optional[str] = None
    number_of_circuits_in_group: Optional[str] = None
    granite_site_name: Optional[str] = None
    fiber_building_serviceability_status: Optional[str] = Field(None, examples=["On Net"])
    connector_type: Optional[str] = Field(None, examples=["LC"])
    uni_type: Optional[str] = Field(None, examples=["Access"])
    engineering_name: Optional[str] = Field(None, examples=["ENG-04155810"])
    a_location: Optional[str] = Field(None, examples=["11921 N. Mopac Expwy, Austin, TX 78759"])
    service_type: Optional[
        Literal["net_new_cj", "net_new_no_cj", "net_new_qc", "net_new_serviceable", "disconnect", "z_side"]
    ] = None
    build_type: Optional[str] = Field(None, examples=["Home Run"])
    related_cid: Optional[str] = Field(None, examples=["84.L4XX.000058..CHTR"])
    pid: Optional[str] = Field(None, examples=["3029803"])
    bw_speed: Optional[str] = Field(None, examples=["200"])
    bw_unit: Optional[str] = Field(None, examples=["Mbps"])
    agg_bandwidth: Optional[str] = Field(None, examples=["200Mbps"])
    primary_fia_service_type: Optional[str] = Field(None, examples=["Routed"])
    usable_ip_addresses_requested: Optional[str] = Field(None, examples=["/30"])
    retain_ip_addresses: Optional[str] = Field(None, examples=["no"])
    spectrum_primary_enni: Optional[str] = Field(None, examples=["cid"])
    primary_vlan: Optional[str] = Field(None, examples=["cid"])
    class_of_service_type: Optional[str] = Field(None, examples=["Gold"])
    class_of_service_needed: Optional[str] = Field(None, examples=["yes"])
    related_order: Optional[str] = Field(None, examples=["epr"])
    create_new_elan_instance: Optional[str] = Field(None, examples=["yes"])
    network_platform: Optional[str] = Field(None, examples=["Legacy"])
    service_code: Optional[str] = Field(None, examples=["12345"])
    cpe_gear: Optional[Literal["RAD-ETX203AX (1G)", "ADVA-GE114PRO-C (1G)", "RAD2i-10G-B (10G)", "ADVA-XG108 (10G)"]] = (
        None
    )
    team_to_install_cpe: Optional[Literal["Field Service", "Construction", "CPE Not Needed"]] = None
    project_manager_email: Optional[str] = Field(None, examples=["someone@charter.com"])
    construction_coordinator_email: Optional[str] = Field(None, examples=["coordinator@charter.com"])
    service_delivery_manager_email: Optional[str] = Field(None, examples=["sd@charter.com"])

    # needed for type II payload model
    class Config:
        populate_by_name = True


class ASideInfo(SideInfo):
    pass


class ZSideInfo(SideInfo):
    billing_account_ordering_customer: str


class BuildCircuitDesignPayloadModel(BaseModel):
    z_side_info: Optional[ZSideInfo] = None
    a_side_info: Optional[ASideInfo] = None
