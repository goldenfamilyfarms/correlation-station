from pydantic import Json, RootModel


class ServiceProductEligibilityResponseModel(RootModel):
    root: Json
