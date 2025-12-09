from pydantic import BaseModel, Field


class CustomerResponseModel(BaseModel):
    created_new_customer: bool = Field(default=False, alias="created new customer")
    customer: str = Field(None, examples=["Customer ID"])
