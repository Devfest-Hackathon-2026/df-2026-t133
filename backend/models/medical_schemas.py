
from typing import Literal

from pydantic import BaseModel, Field


class OCRLine(BaseModel):
    text: str
    confidence: float | None = None
    bounding_box: list[dict[str, float]] = Field(
        default_factory=list
    )


class OCRPage(BaseModel):
    page_index: int = Field(ge=0)
    filename: str = ""
    text: str = ""
    lines: list[OCRLine] = Field(default_factory=list)


class OCRInput(BaseModel):
    pages: list[OCRPage] = Field(
        min_length=1,
        max_length=12,
    )


class MedicalFact(BaseModel):
    fhir_hint: Literal[
        "Condition",
        "Observation",
        "DiagnosticReport",
        "MedicationRequest",
        "Procedure",
        "Immunization",
        "AllergyIntolerance",
        "Appointment",
        "Encounter",
        "Composition",
        "Other",
    ]

    label: str
    value: str | None = None
    unit: str | None = None

    source_line_index: int
    source_quote: str

    needs_review: bool = False


class MedicalPage(BaseModel):
    page_index: int

    document_type: Literal[
        "clinical_note",
        "laboratory_report",
        "prescription",
        "discharge_summary",
        "vaccination_record",
        "other",
        "unknown",
    ]

    facts: list[MedicalFact] = Field(
        default_factory=list
    )

    review_notes: list[str] = Field(
        default_factory=list
    )


class MedicalExtractionResult(BaseModel):
    pages: list[MedicalPage]
