from typing import Optional, Literal
from pydantic import BaseModel, Field

from .basemodels import ServiceTypeModel, TypeIIModel


class SideInfo(ServiceTypeModel, TypeIIModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    product_name: str = Field(examples=["Fiber Internet Access"])
    # Optional
    service_code: Optional[str] = None
    customers_elan_name: Optional[str] = None
    number_of_b_channels: Optional[str] = None
    number_of_analog_lines: Optional[str] = None
    number_of_native_lines: Optional[str] = None
    number_of_ported_lines: Optional[str] = None
    number_of_circuits_in_group: Optional[str] = None
    product_family: Optional[str] = Field(None, examples=["Dedicated Internet Service"])
    engineering_id: Optional[str] = Field(None, examples=["a2gDK0000008BW7YAM"])
    engineering_name: Optional[str] = Field(None, examples=["ENG-03750746"])
    service_location_address: Optional[str] = Field(None, examples=["11921 N. Mopac Expwy, Austin, TX 78759"])
    fiber_building_serviceability_status: Optional[str] = Field(None, examples=["On Net"])
    uni_type: Optional[str] = Field(None, examples=["Access"])
    retain_ip_address: Optional[str] = Field(None, examples=["Y"])
    build_type: Optional[str] = Field(None, examples=["Home Run"])
    bw_speed: Optional[str] = Field(None, examples=["200"])
    bw_unit: Optional[str] = Field(None, examples=["Mbps"])
    agg_bandwidth: Optional[str] = Field(None, examples=["200Mbps"])
    connector_type: Optional[str] = Field(None, examples=["LC"])
    engineering_job_type: Optional[str] = Field(None, examples=["Express BW Upgrade", "Upgrade"])
    service_request_order_type: Optional[str] = Field(None, examples=["new install", "change request"])
    related_cid: Optional[str] = Field(None, examples=["84.L4XX.000058..CHTR"])
    pid: Optional[str] = Field(None, examples=["3029803"])
    ipv4_type: Optional[str] = Field(None, examples=["LAN"])
    block_size: Optional[str] = Field(None, examples=["/29=5"])
    class_of_service_needed: Optional[str] = Field(None, examples=["yes"])
    class_of_service_type: Optional[str] = Field(None, examples=["Gold"])
    a_location: Optional[str] = Field(None, examples=["11921 N. Mopac Expwy, Austin, TX 78759"])
    z_location: Optional[str] = Field(None, examples=["11921 N. Mopac Expwy, Austin, TX 78759"])
    create_new_elan_instance: Optional[str] = Field(None, examples=["yes"])
    billing_account_ordering_customer: Optional[str] = Field(None, examples=["8448200193944351"])
    granite_site_name: Optional[str] = Field(
        None, examples=["ELANCAPX-UNIVERSITY COOPERATIVE HOUSING ASSOCIATION//500 LANDFAIR AVE"]
    )
    change_reason: Optional[str] = Field(None, examples=["Upgrading Service"])
    assigned_cd_team: Optional[str] = Field(None, examples=["Retail"])
    spectrum_primary_enni: Optional[str] = Field(None, examples=["60.KGFD.000001..TWCC"])
    primary_vlan: Optional[str] = Field(None, examples=["VLAN2100"])
    spectrum_secondary_enni: Optional[str] = Field(None, examples=["60.KGFD.000002..TWCC"])
    secondary_vlan: Optional[str] = Field(None, examples=["VLAN2101"])
    related_order: Optional[str] = Field(None, examples=["epr"])
    primary_fia_service_type: Optional[str] = Field(None, examples=["Routed"])
    ip_address: Optional[str] = Field(None, examples=["xxx.xx.xx.xxx/31"])
    usable_ip_addresses_requested: Optional[str] = Field(None, examples=["/30"])
    retain_ip_addresses: Optional[str] = Field(None, examples=["no"])
    network_platform: Optional[str] = Field(None, examples=["Legacy"])
    primary_construction_job_fiber_type: Optional[str] = Field(None, examples=["EPON"])
    protection_notes: Optional[str] = Field(None, examples=["Populated"])
    type_of_protection_needed: Optional[str] = Field(None, examples=["Populated"])
    complex: Optional[str] = Field(None, examples=["yes"])
    physical_diversity_needed: Optional[str] = Field(None, examples=["yes"])
    secondary_fia_service_type: Optional[str] = Field(None, examples=["BGP"])
    cpe_gear: Optional[Literal["RAD-ETX203AX (1G)", "ADVA-GE114PRO-C (1G)", "RAD2i-10G-B (10G)", "ADVA-XG108 (10G)"]] = (
        None
    )
    team_to_install_cpe: Optional[Literal["Field Service", "Construction", "CPE Not Needed"]] = None
    project_manager_email: Optional[str] = Field(None, examples=["someone@charter.com"])
    construction_coordinator_email: Optional[str] = Field(None, examples=["coordinator@charter.com"])
    service_delivery_manager_email: Optional[str] = Field(None, examples=["sd@charter.com"])


class ASideInfo(SideInfo):
    pass


class ZSideInfo(SideInfo):
    pass


class CircuitDesignPayloadModel(BaseModel):
    z_side_info: ZSideInfo
    a_side_info: Optional[ASideInfo] = None
