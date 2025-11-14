from typing import Optional
from pydantic import BaseModel, Field


class RemedyTicketPayloadModel(BaseModel):
    circuit_id: str = Field(examples=["51.L1XX.803170..TWCC"])
    construction_complete: str = Field(examples=["true"])
    address: str = Field(examples=["24219 Railroad Ave Newhall CA 91321"])
    customer_name: str = Field(examples=["LUXEN - NEWHALL"])
    terminating_ftp_port: str = Field(examples=["FL1RK1PANEL01-01 PORT 39/40"])
    wavelength: str = Field(examples=["1549.32"])
    fiber_distance: str = Field(examples=["2km"])
    prism_id: str = Field(examples=["2578603"])
    order_number: str = Field(examples=["ENG-02358598"])
    # Optional
    sheath: Optional[str] = Field(None, examples=["411E to FH #1"])
    fiber_assigned: Optional[str] = Field(None, examples=["BR/SL"])
    priority_class: Optional[str] = Field(None, examples=["rapid_build"])


class RemedyDisconnectTicketPayloadModel(BaseModel):
    circuit_id: str = Field(examples=["51.L1XX.803170..TWCC"])
    address: str = Field(examples=["24219 Railroad Ave Newhall CA 91321"])
    customer_name: str = Field(examples=["LUXEN - NEWHALL"])
    hub_clli: str = Field(examples=["BFLONYKK"])
    equipment_id: str = Field(examples=["BFLONYKKQW"])
    port_access_id: str = Field(examples=["XE-1/0/0"])
    order_number: str = Field(examples=["ENG-02358598"])
    notes: str = Field(
        examples=[
            """LEVEL 3 NEW TWCC :: 2355 COSTCO WAY 54311 :: Single-Customer Disconnect
             :: 92.L1XX.004554..CHTR :: DEPRWI020QW:GE-0/0/22"""
        ]
    )
    summary: str = Field(examples=["{hub} :: Single-Customer Disconnect"])
    # Optional
    additional_details: Optional[str] = Field(None, examples=["Old Remedy ticket: WO00000000001"])


class RemedyChangeTicketPayloadModel(BaseModel):
    epr: str = Field(examples=["ENG-00989755"])
    template: str = Field(examples=["Verizon 1G to 10G", "Routine 1G to 10G"])
    start_time: str = Field(examples=["12:00 AM"])
    end_time: str = Field(examples=["6:00 AM"])
    requestor_pid: str = Field(examples=["P8675309"])
    coordinator_group: str = Field(examples=["SEEI&O", "Coordinated Impact Provisioning"])
    timezone: str = Field(examples=["EST", "CST", "MST", "PCT", "HST"])
    # Optional
    cid: Optional[str] = Field(None, examples=["51.L1XX.803170..TWCC"])
