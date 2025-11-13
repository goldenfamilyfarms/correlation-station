"""Templates for device models."""

import logging

from common_sense.common.errors import abort
from pydantic.dataclasses import dataclass
from typing import Optional
from typing import Literal
from typing import Union


from arda_app.dll.granite import get_selected_vendor
from arda_app.bll.models.device_topology import (
    MODEL_NAMES,
    TEMPLATE_NAMES,
    AVAILABLE_HANDOFF_PORTS,
    PRIMARY_SLOT_PAID_TEMPLATE,
    SECONDARY_SLOT_PAID_TEMPLATE,
    ADVA_114PRO_1G,
    ADVA_FSP_XG108,
    ADVA_120PRO_10G,
    RAD_203AX_1G,
    RAD_2I_10G_FULL,
    RAD_2I_10G_B_HALF,
    CRADLEPOINT_ARC,
)
from arda_app.bll.models.utils import BaseModel
from arda_app.bll.net_new.utils.shelf_utils import get_device_bw

logger = logging.getLogger(__name__)


@dataclass
class PortModel:
    slot: str
    template: str
    connector: str
    port_access_id: str


@dataclass
class SecondaryPortModel:
    slot: str
    template: str
    connector: str
    port_access_id: Union[dict, str]


@dataclass
class UnderlayDeviceTopologyModel(BaseModel):
    """Topology for MTU & CPE devices."""

    role: Literal["mtu", "cpe"]
    device_bw: Literal["1 Gbps", "10 Gbps", "RF", ""] = ""
    connector_type: Literal["RJ-45", "LC", "SC", "N/A", ""] = ""
    vendor: Literal["RAD", "ADVA", "JUNIPER", "CRADLEPOINT", ""] = ""
    model: str = ""
    device_template: str = ""
    uplink: Optional[PortModel] = None
    handoff: Optional[PortModel] = None
    secondary: Optional[SecondaryPortModel] = None

    def __post_init__(self):
        # set vendor if the field is not set
        if not self.vendor:
            self.vendor = get_selected_vendor()["VENDOR"]

        # Set connector type to RJ-45 if N/A
        if self.connector_type in ["N/A", "RJ48"]:
            self.connector_type = "RJ-45"

        try:
            # set device template if the field is not set
            if not self.device_template and not self.model:
                self.device_template = self.get_device_template()
                self.model = MODEL_NAMES[self.device_template]

            # set model if the field is not set
            if not self.model:
                self.model = MODEL_NAMES[self.device_template]

            # set device template if the field is not set
            if not self.device_template:
                self.device_template = TEMPLATE_NAMES[self.model]
        except KeyError:
            logger.error("Device template or model not found in underlay device topology.")
            abort(500, "Device template or model not found in underlay device topology.")

        # set uplink
        self._set_uplink()

        # set secondary uplink
        self._set_secondary_uplink()

    def get_device_template(self):
        if self.device_bw not in {"1 Gbps", "10 Gbps", "RF"}:
            logger.error("Device bandwidth must be set to 1 or 10 Gbps.")
            abort(500, "Device bandwidth must be set to 1 or 10 Gbps.")

        vals = {
            "ADVA": {
                "mtu": {"10 Gbps": ADVA_120PRO_10G, "1 Gbps": None},
                "cpe": {"10 Gbps": ADVA_FSP_XG108, "1 Gbps": ADVA_114PRO_1G},
            },
            "RAD": {
                "mtu": {"10 Gbps": RAD_2I_10G_FULL, "1 Gbps": None},
                "cpe": {"10 Gbps": RAD_2I_10G_B_HALF, "1 Gbps": RAD_203AX_1G},
            },
            "CRADLEPOINT": {
                "mtu": {"10 Gbps": None, "1 Gbps": CRADLEPOINT_ARC},
                "cpe": {"10 Gbps": None, "1 Gbps": None},
            },
        }
        device_template = vals[self.vendor][self.role][self.device_bw] if self.vendor else ""

        if not device_template:
            logger.error(f"{self.role} device template with bandwidth {self.device_bw} not available.")
            abort(500, f"{self.role} device template with bandwidth {self.device_bw} not available.")

        return device_template

    def _set_uplink(self):
        """generate uplink port data"""
        connector_type = "RF" if self.vendor == "CRADLEPOINT" else "LC"
        try:
            slot, paid, card_template = PRIMARY_SLOT_PAID_TEMPLATE[self.device_template]["uplink"][connector_type]
        except TypeError:
            logger.error(f"uplink for {self.device_template} device does not exist.")
            abort(500, f"uplink for {self.device_template} device does not exist.")
        self.uplink = PortModel(slot=slot, template=card_template, connector=connector_type, port_access_id=paid)

    def _set_secondary_uplink(self):
        """generate secondary uplink port data"""
        connector_type = "RF" if self.vendor == "CRADLEPOINT" else "LC"
        try:
            slot, paid, card_template = SECONDARY_SLOT_PAID_TEMPLATE[self.device_template]["secondary"][connector_type]
        except TypeError:
            logger.error(f"secondary uplink for {self.device_template} device does not exist.")
            abort(500, f"secondary uplink for {self.device_template} device does not exist.")
        self.secondary = SecondaryPortModel(
            slot=slot, template=card_template, connector=connector_type, port_access_id=paid
        )

    def set_handoff(self, circuit_bandwidth: str, equipment_data: list = None, existing_cpe: bool = False):
        """set initial handoff ports for new builds"""
        (element_bandwidth_speed, element_bandwidth_unit) = circuit_bandwidth.split()

        port_device_bw = get_device_bw(element_bandwidth_speed, element_bandwidth_unit)
        slot = ""

        # get slot and port access id info
        if existing_cpe:
            port_list = AVAILABLE_HANDOFF_PORTS[self.device_template][port_device_bw][self.connector_type]

            if self.connector_type == "LC" or any(
                model in equipment_data[0]["MODEL"] for model in ("ETX-2", "116PRO", "XG108")
            ):
                slot, paid, card_template = check_paid(port_list, equipment_data, use_slot=True)
            elif equipment_data[0]["MODEL"] == "ETX203AX/2SFP/2UTP2SFP":  # RAD203AX / RJ-45
                slot, paid, card_template = check_paid(port_list[:2], equipment_data)
                if not slot:
                    slot, paid, card_template = check_paid(port_list[2:], equipment_data, use_slot=True)
            else:  # ADVA114PRO / RJ-45
                slot, paid, card_template = check_paid(port_list, equipment_data)

            if not slot:
                abort(500, f"There are no available handoff ports for the requested {self.connector_type} connector.")
        else:
            slot, paid, card_template = PRIMARY_SLOT_PAID_TEMPLATE[self.device_template]["handoff"][port_device_bw][
                self.connector_type
            ]

            if not slot:
                abort(
                    500,
                    f"Handoff: The requested {self.connector_type} connector "
                    f"with bandwidth {port_device_bw} is not supported.",
                )

        self.handoff = PortModel(slot=slot, template=card_template, connector=self.connector_type, port_access_id=paid)

    def get_available_handoff_ports(self, circuit_bandwidth: str):
        """get all available handoff ports"""
        return AVAILABLE_HANDOFF_PORTS[self.device_template][circuit_bandwidth][self.connector_type]

    def set_known_slot(self, circuit_bandwidth: str, slot: str = "", port_access_id: str = ""):
        """set handoff to specific slot"""
        possible_slots = AVAILABLE_HANDOFF_PORTS[self.device_template][circuit_bandwidth][self.connector_type]

        for port in possible_slots:
            if slot and slot in port:
                slot, paid, card_template = port
                self.handoff = PortModel(
                    slot=slot, template=card_template, connector=self.connector_type, port_access_id=paid
                )
                return
            elif port_access_id in port:
                slot, paid, card_template = port
                self.handoff = PortModel(
                    slot=slot, template=card_template, connector=self.connector_type, port_access_id=paid
                )
                return


def check_paid(port_list, equipment_data, use_slot=False):
    v = 1
    check = "PORT_ACCESS_ID"

    if use_slot:
        v = 0
        check = "SLOT"

    for port in port_list:
        for equip in equipment_data:
            if port[v] == equip.get(check):
                return port

    return None, None, None
