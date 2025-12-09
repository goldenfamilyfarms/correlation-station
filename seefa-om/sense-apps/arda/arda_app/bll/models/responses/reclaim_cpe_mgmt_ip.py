from pydantic import Json, RootModel


class ReclaimCpeMgmtIPResponseModel(RootModel):
    root: Json
