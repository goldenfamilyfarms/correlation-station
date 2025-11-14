from pydantic import Json, RootModel


class SupportedProductResponseModel(RootModel):
    root: str = Json
