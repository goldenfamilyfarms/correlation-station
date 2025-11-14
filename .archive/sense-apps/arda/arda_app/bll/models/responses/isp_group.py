from pydantic import RootModel


class ISPGroupResponseModel(RootModel):
    root: str
