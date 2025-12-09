from typing import List
from pydantic import BaseModel, Field


class ChildBlockModel(BaseModel):
    container: str
    ipv6: bool = False
    nonBroadcast: bool = False
    primarySubnet: bool = False
    userDefinedFields: List[str]
    blockName: str = Field(examples=["108.25.121.142/29"])
    blockType: str = Field(examples=["RIP-DIA"])
    blockAddr: str = Field(examples=["108.25.121.142"])
    blockStatus: str = Field(examples=["Deployed"])
    blockSize: int = Field(examples=[29])
    discoveryAgent: str = Field(examples=["InheritFromContainer"])
    excludeFromDiscovery: str = Field(examples=["false"])


class BlockPolicyModel(BaseModel):
    cascadePrimaryDhcpServer: bool = False


class IPReclamationPayloadModel(BaseModel):
    inpChildBlock: ChildBlockModel
    inpBlockPolicy: BlockPolicyModel
