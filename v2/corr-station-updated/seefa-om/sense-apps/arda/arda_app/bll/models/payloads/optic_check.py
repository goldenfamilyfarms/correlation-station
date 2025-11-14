from typing import Optional
from pydantic import BaseModel, Field


class RemedyFields(BaseModel):
    cid: str = Field(examples=["81.L1XX.006522..TWCC"])
    work_order_id: str = Field(examples=["WO0000000864603"])
    pe_device: str = Field(examples=["AUSGTXLG0QW/001.0003.012.43/SWT#1"])
    pe_port_number: str = Field(examples=["GE-0/0/2"])
    optic_format: str = Field(examples=["< 80km SFP"])
    target_wavelength: str = Field(examples=["1530nm"])
    completed_date: str = Field(examples=["2022-08-12T11:32:45-05:00"])
    # Optional
    status_reason: Optional[str] = Field(None, examples=["Completed"])
    fiber_distance: Optional[str] = Field(None, examples=["11"])
    closure_reason: Optional[str] = Field(None, examples=["With Wavelength Change"])
    dwdm_overlay: Optional[str] = Field(None, examples=["dwdm_overlay"])
    work_detail_notes: Optional[str] = Field(None, examples=["Notes"])
    actual_wavelength_used: Optional[str] = Field(None, examples=["1550nm"])
    order_number: Optional[str] = Field(None, examples=["ENG-03205825"])
    mux_change_required: Optional[str] = Field(None, examples=["no"])
    construction_complete: Optional[str] = Field(None, examples=["no"])
    prism_id: Optional[str] = Field(None, examples=["3122126"])


class SalesForceFields(BaseModel):
    prism_construction_coord_email: str = Field(examples=["email@domain.com"])
    # Optional
    construction_complete_date: Optional[str] = Field(None, examples=["not completed"])
    email: Optional[str] = Field(None, examples=["manager@domain.com"])


class PrismFields(BaseModel):
    wavelength: str = Field(examples=["1549.32"])
    # Optional
    construction_coordinator: Optional[str] = Field(None, examples=["coordinator"])
    process_state: Optional[str] = Field(None, examples=["state"])
    project_status: Optional[str] = Field(None, examples=["status"])


class OpticCheckPayloadModel(BaseModel):
    remedy_fields: RemedyFields
    sales_force_fields: SalesForceFields
    prism_fields: PrismFields
