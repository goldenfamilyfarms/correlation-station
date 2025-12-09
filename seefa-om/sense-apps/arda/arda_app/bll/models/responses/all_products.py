from typing import List

from pydantic import BaseModel


class AllProductsResponseModel(BaseModel):
    relatedCircuitStatus: List[str]
