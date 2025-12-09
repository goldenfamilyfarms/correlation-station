from typing import Optional

from pydantic import BaseModel, Field


class MPSCloudModel(BaseModel):
    """MPS Cloud  model from Path Elements."""

    customer_id: Optional[str] = Field(alias="CUSTOMER_ID")
    customer_name: Optional[str] = Field(alias="CUSTOMER_NAME")
    element_name: str = Field(alias="ELEMENT_NAME")
    leg_name: str = Field(alias="LEG_NAME")
    path_a_site: Optional[str] = Field(alias="PATH_A_SITE")
    path_name: str = Field(alias="PATH_NAME")
    path_rev: str = Field(alias="PATH_REV")
    z_clli: Optional[str] = Field(alias="Z_CLLI")
