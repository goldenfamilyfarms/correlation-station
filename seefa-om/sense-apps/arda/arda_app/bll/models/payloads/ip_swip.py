from pydantic import Field

from .basemodels import ServiceTypeModel


class IPSWIPPayloadModel(ServiceTypeModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    ipv4_lan: str = Field(examples=["192.168.0.1/28"])
    ipv6_route: str = Field(examples=["2001:0db8:85a3:0000:0000:8a2e:0370:7334/48"])
    customer_id: str = Field(examples=["HELENA AGRI ENTERPRISES, LLC"])
    z_address: str = Field(examples=["8756 TEEL PKWY"])
    z_city: str = Field(examples=["FRISCO"])
    z_state: str = Field(examples=["TX"])
    z_zip: str = Field(examples=["75034"])
