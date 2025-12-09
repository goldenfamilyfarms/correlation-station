from pydantic import Json, RootModel


class LightTestCheckResponseModel(RootModel):
    root: Json
