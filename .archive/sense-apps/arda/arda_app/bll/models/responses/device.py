from pydantic import Json, RootModel


class DeviceResponseModel(RootModel):
    root: Json
