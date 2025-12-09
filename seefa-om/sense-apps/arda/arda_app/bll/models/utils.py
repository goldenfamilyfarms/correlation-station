import json
from dataclasses import asdict
from pydantic.dataclasses import dataclass


@dataclass
class BaseModel:
    def dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(asdict(self))
