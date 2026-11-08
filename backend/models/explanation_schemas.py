from typing import Literal

from pydantic import BaseModel, Field

from .medical_schemas import MedicalPage


class FHIRSource(BaseModel):
    page_index: int
    source_line_index: int
    source_quote: str


class FHIRStatusEntry(BaseModel):
    source: FHIRSource
    fhir_hint: str
    label: str
    value: str | None = None

    reason: str | None = None
    reasons: list[str] = Field(default_factory=list)


class FHIRNormalizationResult(BaseModel):
    mapped: list[FHIRStatusEntry] = Field(
        default_factory=list
    )
    pending_review: list[FHIRStatusEntry] = Field(
        default_factory=list
    )
    unmapped: list[FHIRStatusEntry] = Field(
        default_factory=list
    )


class ExplanationRequest(BaseModel):
    language: Literal["vi", "en", "ja"] = "vi"

    pages: list[MedicalPage] = Field(
        min_length=1,
        max_length=12,
    )

    fhir_result: FHIRNormalizationResult | None = None


class EvidenceLinkedText(BaseModel):
    text: str
    fact_ids: list[str]


class FactExplanation(BaseModel):
    fact_id: str
    explanation: str


class ExplanationDraft(BaseModel):
    summary: EvidenceLinkedText

    explanations: list[FactExplanation] = Field(
        default_factory=list
    )

    clinician_questions: list[EvidenceLinkedText] = Field(
        default_factory=list
    )