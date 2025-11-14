from pydantic import Json, RootModel


class BandwidthChangeResponseModel(RootModel):
    root: Json
