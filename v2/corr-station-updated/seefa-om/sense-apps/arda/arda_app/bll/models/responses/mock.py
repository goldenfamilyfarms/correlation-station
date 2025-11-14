from pydantic import Json, RootModel


class MockResponseModel(RootModel):
    root: Json
