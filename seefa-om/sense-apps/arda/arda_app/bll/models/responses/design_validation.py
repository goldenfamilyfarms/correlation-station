from pydantic import BaseModel, Field, RootModel


class DesignValidationResponseModel(BaseModel):
    validation_circuit_design_notes: str = Field(..., examples=["No issues found with the circuit"])
    ODIN_verification: str = Field(..., examples=["Passed", "Failed"])


class DesignValidationOdinResponseModel(RootModel):
    root: list[dict]
