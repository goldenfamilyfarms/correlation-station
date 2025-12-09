from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class PathElementsModel:
    """
    Path Elements model.

    TODO: add remaining fields.
    """

    circ_path_inst_id: str = Field(alias="CIRC_PATH_INST_ID")
    path_name: str = Field(alias="PATH_NAME")
    slot: str = Field(alias="SLOT")
    port_inst_id: str = Field(alias="PORT_INST_ID")
    port_access_id: str = Field(alias="PORT_ACCESS_ID")
    path_name: str = Field(alias="PATH_NAME")
