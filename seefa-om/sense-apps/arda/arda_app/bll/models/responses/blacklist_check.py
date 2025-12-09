from pydantic import BaseModel, Field


class BlacklistCheckResponseModel(BaseModel):
    ips_checked: list = Field(alias="ip's_checked")
    blacklist_status: bool
    blacklist_ips: list = Field(alias="blacklist_ip's")
