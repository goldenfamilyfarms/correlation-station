from pydantic import Json, RootModel


class OpticCheckResponseModel(RootModel):
    root: Json
