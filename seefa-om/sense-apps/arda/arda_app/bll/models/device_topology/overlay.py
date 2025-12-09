"""Templates for device models."""

import logging

from common_sense.common.errors import abort
from pydantic.dataclasses import dataclass
from typing import Optional
from typing import Literal

from arda_app.bll.models.utils import BaseModel
from arda_app.bll.models.device_topology import (
    AUDIOCODES_M500B,
    OVERLAY_AVAILABLE_HANDOFF_PORTS,
    OVERLAY_PRIMARY_SLOT_PAID_TEMPLATE,
    MODEL_NAMES,
    TEMPLATE_NAMES,
)

logger = logging.getLogger(__name__)


@dataclass
class PortModel:
    slot: str
    template: str
    port_access_id: str


@dataclass
class OverlayDeviceTopologyModel(BaseModel):
    """Topology for voice gateways and overlay devices."""

    role: Literal["vgw", "mne"] = "vgw"
    vendor: Literal["AUDIOCODES", "CISCO"] = "AUDIOCODES"
    model: str = ""
    device_template: str = ""
    uplink: Optional[PortModel] = None
    handoff: Optional[PortModel] = None

    def __post_init__(self):
        # set device template if the field is not set
        try:
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
            logger.error("Device template or model not found in overlay device topology.")
            abort(500, "Device template or model not found in overlay device topology.")

        # set uplink
        self._set_uplink()

        # set handoff
        self._set_handoff()

    def get_device_template(self):
        vals = {"AUDIOCODES": {"vgw": AUDIOCODES_M500B}}
        device_template = vals[self.vendor][self.role] if self.vendor else ""

        if not device_template:
            logger.error(f"{self.role} device template {self.device_template} not available.")
            abort(500, f"{self.role} device template {self.device_template} not available.")

        return device_template

    def _set_uplink(self):
        """generate uplink port data"""
        try:
            slot, paid, card_template = OVERLAY_PRIMARY_SLOT_PAID_TEMPLATE[self.device_template]["uplink"]
        except TypeError:
            logger.error(f"uplink for {self.device_template} device does not exist.")
            abort(500, f"uplink for {self.device_template} device does not exist.")
        self.uplink = PortModel(slot=slot, template=card_template, port_access_id=paid)

    def _set_handoff(self):
        """set initial handoff ports for new builds"""
        # get slot and port access id info
        try:
            slot, paid, card_template = OVERLAY_PRIMARY_SLOT_PAID_TEMPLATE[self.device_template]["handoff"]
        except TypeError:
            logger.error("Device Topology: The requested overlay handoff is not supported.")
            abort(500, "Device Topology: The requested overlay handoff is not supported.")
        self.handoff = PortModel(slot=slot, template=card_template, port_access_id=paid)

    def get_available_handoff_ports(self):
        """get all available handoff ports"""
        return OVERLAY_AVAILABLE_HANDOFF_PORTS[self.device_template]
