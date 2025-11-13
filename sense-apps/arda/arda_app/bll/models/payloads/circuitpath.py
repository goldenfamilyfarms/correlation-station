from typing import Optional
from pydantic import BaseModel, Field


class SiteAIdFieldsPayloadModel(BaseModel):
    # Optional
    customer: Optional[str] = Field(None, examples=["Customer ID"])
    site: Optional[str] = Field(None, examples=["Site ID"])
    site_zip_code: Optional[str] = Field(None, examples=["12345"])
    site_enni: Optional[str] = Field(None, examples=["21.L1XX.stuff"])


class SiteZIdFieldsPayloadModel(BaseModel):
    customer: str = Field(examples=["Customer ID"])
    site: str = Field(examples=["Site ID"])
    site_zip_code: str = Field(examples=["12345"])


class CircuitPathPayloadModel(BaseModel):
    z_side_site: SiteZIdFieldsPayloadModel
    service_media: str
    customer_type: str = Field(examples=["CARRIER"])
    product_service: str = Field(examples=["COM-DIA"])
    path_order_num: str = Field(examples=["1234"])
    bw_value: str = Field(examples=["100"])
    # Optional
    a_side_site: Optional[SiteAIdFieldsPayloadModel] = None
    managed_service: Optional[bool] = None
    tsp_auth: Optional[str] = None
    tsp_expiration: Optional[str] = None
    bw_unit: Optional[str] = Field(None, examples=["MBPS"])
    off_net_provider_cid: Optional[str] = Field(
        None, alias="off-net_provider_cid", examples=["required for Finished Internet"]
    )
    off_net_service_provider: Optional[str] = Field(
        None, alias="off-net_service_provider", examples=["required for Finished Internet"]
    )
    assigned_ip_subnet: Optional[str] = Field(None, examples=["required for Finished Internet"])
    ipv4_service_type: Optional[str] = Field(None, examples=["required for Finished Internet"])
    trunk: Optional[int] = Field(None, examples=[1])
