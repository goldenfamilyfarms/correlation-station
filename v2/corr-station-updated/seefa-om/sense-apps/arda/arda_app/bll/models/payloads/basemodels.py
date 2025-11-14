from pydantic import BaseModel, Field
from typing import Literal, Optional


class RelatedCidModel(BaseModel):
    related_circuit_id: str = Field(examples=["81.L1XX.006522..TWCC"])


class ServiceTypeModel(BaseModel):
    service_type: Literal[
        "change_logical",
        "net_new_cj",
        "net_new_no_cj",
        "net_new_qc",
        "net_new_serviceable",
        "disconnect",
        "z_side",
        "bw_change",
        "net_new",
        "add",
    ]


class MSServiceTypeModel(BaseModel):
    service_type: Literal["managed_services_1_epr", "managed_services", "ms_new_install"]


class MSProductFamilyModel(BaseModel):
    product_family: Literal[
        "Enterprise Network Additional",
        "Enterprise Network Edge",
        "Enterprise Network Switch",
        "Enterprise Network WiFi",
        "Hosted Voice - Trunk (DOCSIS)",
        "Hosted Voice - Trunk (Fiber)",
        "Managed Network Camera",
        "Managed Network Additional",
        "Managed Network Edge",
        "Managed Network Edge Per Room",
        "Managed Network IoT Sensor",
        "Managed Network Switch",
        "Managed Network WiFi",
        "SBB 1-19 Outlets",
        "SBB-Healthcare",
        "SBB-Hospitality",
        "Fiber Connect Plus",
    ]


class MSProductNameModel(BaseModel):
    product_name: Literal[
        "FC + Remote PHY",
        "Hosted Voice - (Fiber)",
        "Hosted Voice - (DOCSIS)",
        "SBB-Fiber (Coax Distribution)",
        "SBB-Fiber (Cat5/6 Distribution)",
        "SBB-Coax",
        "Managed Network Edge",
    ]


class ProductFamilyModel(BaseModel):
    product_family: Literal[
        "Enterprise Network Additional",
        "Enterprise Network Edge",
        "Enterprise Network Switch",
        "Enterprise Network WiFi",
        "Hosted Voice - Trunk (DOCSIS)",
        "Hosted Voice - Trunk (Fiber)",
        "Managed Network Camera",
        "Managed Network Additional",
        "Managed Network Edge",
        "Managed Network Edge Per Room",
        "Managed Network IoT Sensor",
        "Managed Network Switch",
        "Managed Network WiFi",
        "SBB 1-19 Outlets",
        "SBB-Healthcare",
        "SBB-Hospitality",
    ]


class ProductNameModel(BaseModel):
    product_name: Literal[
        "Carrier E-Access (Fiber)",
        "Carrier Fiber Internet Access",
        "Carrier Transport EPL",
        "EP-LAN (Fiber)",
        "EP-LAN (Fiber UHS)",
        "EPL (Fiber)",
        "EVP-LAN",
        "FC + Remote PHY",
        "Fiber Internet Access",
        "Hosted Voice - (Fiber)",
        "Hosted Voice - (DOCSIS)",
        "Hosted Voice - (Overlay)",
        "Managed Network Edge",
        "PRI Trunk (Fiber)",
        "PRI Trunk(Fiber) Analog",
        "PRI Trunk (DOCSIS)",
        "SBB - Hospitality - High Definition",
        "SBB 1-19 Outlets",
        "SIP - Trunk (Fiber)",
        "SIP - Trunk (DOCSIS)",
        "SIP Trunk(Fiber) Analog",
        "Wireless Internet Access-Primary",
        "Wireless Internet Access-Primary-Out of Footprint",
        "Wireless Internet Access",
        "Wireless Internet Access - Off-Net",
    ]


class MSBasePayloadModel(MSServiceTypeModel, MSProductNameModel, MSProductFamilyModel):
    pass


class TypeIIModel:
    third_party_provided_circuit: Optional[str] = Field(None, examples=["Y"], alias="3rd_party_provided_circuit")
    type_II_circuit_accepted_by_spectrum: Optional[bool] = Field(None, examples=[False])
    service_provider: Optional[str] = Field(None, examples=["COMCAST / Comcast"])
    service_provider_uni_cid: Optional[str] = Field(None, examples=["70.KGGS.021142..TESTA99.."])
    service_provider_cid: Optional[str] = Field(None, examples=["70.VLXP.019925.ON.TESTA100.."])
    service_provider_vlan: Optional[str] = Field(None, examples=["2086"])
    spectrum_buy_nni_circuit_id: Optional[str] = Field(None, examples=["40.KGFD.000189..CHTR"])

    # needed for type II payload model
    class Config:
        populate_by_name = True
