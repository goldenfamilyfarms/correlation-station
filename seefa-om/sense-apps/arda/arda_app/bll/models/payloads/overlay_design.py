from typing import Optional
from pydantic import Field

from .basemodels import MSBasePayloadModel


class OverlayDesignPayloadModel(MSBasePayloadModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    engineering_name: str = Field(examples=["ENG-1234567"])
    # Optional
    service_location_id: Optional[str] = None
    service_location_record_id: Optional[str] = None
    service_location_building_state: Optional[str] = None
    third_party_circuit: Optional[str] = Field(None, alias="3rd_party_provided_circuit", examples=["Y"])
    agg_bandwidth: Optional[str] = Field(None, examples=["200Mbps"])
    assigned_cd_team: Optional[str] = Field(None, examples=["Retail"])
    billing_account_ordering_customer: Optional[str] = Field(None, examples=["8448200193944351"])
    change_reason: Optional[str] = Field(None, examples=["Upgrading Service"])
    pid: Optional[str] = Field(None, examples=["3029803"])
    service_location_street: Optional[str] = Field(None, examples=["123 street ave"])
    service_location_city: Optional[str] = Field(None, examples=["Pflugerville"])
    service_location_state: Optional[str] = Field(None, examples=["TX"])
    service_location_zip_code: Optional[str] = Field(None, examples=["78660"])
