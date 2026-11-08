from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from .medical_schemas import MedicalPage


class FactContext(BaseModel):
    """
    Additional externally verified information
    for a specific extracted medical fact.
    """

    page_index: int = Field(ge=0)
    source_line_index: int = Field(ge=0)

    patient_reference: str | None = None

    # Immunization
    occurrence_date: date | None = None
    immunization_status: Literal[
        "completed",
        "not-done",
        "entered-in-error",
    ] | None = None

    # DiagnosticReport
    report_status: Literal[
        "registered",
        "partial",
        "preliminary",
        "final",
        "amended",
        "corrected",
        "appended",
        "cancelled",
        "entered-in-error",
        "unknown",
    ] | None = None


class FHIRNormalizeRequest(BaseModel):
    pages: list[MedicalPage] = Field(
        min_length=1,
        max_length=12,
    )

    contexts: list[FactContext] = Field(
        default_factory=list
    )