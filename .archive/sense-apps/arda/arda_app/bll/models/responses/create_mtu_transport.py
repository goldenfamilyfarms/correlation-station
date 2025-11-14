from pydantic import BaseModel, Field


class CreateMTUTransportResponseModel(BaseModel):
    mtu_new_build_transport_name: str = Field(..., examples=["transport_name"])
    mtu_new_build_transport: str = Field(..., examples=["transport"])
    message: str = Field(..., examples=["path_name has been successfully created and added to cid"])
