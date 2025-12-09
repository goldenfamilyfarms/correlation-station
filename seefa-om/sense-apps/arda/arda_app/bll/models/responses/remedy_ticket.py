from pydantic import BaseModel


class RemedyTicketResponseModel(BaseModel):
    work_order: str


class RemedyDisconnectTicketResponseModel(BaseModel):
    work_order: str
