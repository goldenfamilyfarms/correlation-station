from pydantic import BaseModel, Field


class SiteResponseModel(BaseModel):
    created_new_site: bool = Field(default=False, alias="created new site")
    siteName: str = Field(None, examples=["Site Name"])
    clli: str = Field(None, examples=["CHRLNCRL"])
    lat: str = Field(None, examples=["-79.12345"])
    lon: str = Field(None, examples=["46.123456"])
