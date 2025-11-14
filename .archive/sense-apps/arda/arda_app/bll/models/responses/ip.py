from pydantic import BaseModel, Field


class IPResponseModel(BaseModel):
    ipv4_service_type: str = Field(None, examples=["Routed"])
    ipv4_glue_subnet: str
    ipv4_assigned_subnets: str
    ipv4_assigned_gateway: str
    ipv6_service_type: str
    ipv6_glue_subnet: str
    ipv6_assigned_subnet: str
    v4_block: str
    v4_net: str
    v4_gateway: str
