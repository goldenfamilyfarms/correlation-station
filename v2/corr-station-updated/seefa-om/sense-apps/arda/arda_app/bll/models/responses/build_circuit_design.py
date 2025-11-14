from pydantic import Json, RootModel


class BuildCircuitDesignResponseModel(RootModel):
    root: Json
