from dataclasses import dataclass
from typing import Literal

import logging

logger = logging.getLogger(__name__)

from ..models.medical_schemas import (
    OCRInput,
    OCRPage,
)
from ..models.fhir_schemas import FHIRNormalizeRequest
from ..models.explanation_schemas import (
    ExplanationRequest,
    FHIRNormalizationResult,
)

from .ocr_service import OCRService
from .medical_extraction_service import MedicalExtractionService
from .fhir_service import FHIRService
from .patient_explanation_service import (
    PatientExplanationService,
)


@dataclass(frozen=True)
class DocumentImage:
    page_index: int
    filename: str
    mime_type: str
    data: bytes


class DocumentAnalysisError(Exception):

    def __init__(self, stage: str):
        self.stage = stage
        super().__init__(
            f"Document analysis failed at stage: {stage}"
        )


class DocumentAnalysisService:

    def __init__(
        self,
        ocr_service: OCRService,
        medical_service: MedicalExtractionService,
        fhir_service: FHIRService,
        explanation_service: PatientExplanationService,
    ):
        self.ocr_service = ocr_service
        self.medical_service = medical_service
        self.fhir_service = fhir_service
        self.explanation_service = explanation_service

    def _extract_ocr(
        self,
        images: list[DocumentImage],
    ) -> OCRInput:
        """
        Run Document AI OCR sequentially for all images.
        """
        pages = []

        for image in images:

            ocr_result = self.ocr_service.extract_text(
                image_data=image.data,
                mime_type=image.mime_type,
            )

            page = OCRPage(
                page_index=image.page_index,
                filename=image.filename,
                text=ocr_result["text"],
                lines=ocr_result["lines"],
            )

            pages.append(page)

        return OCRInput(pages=pages)

    def analyze(
        self,
        images: list[DocumentImage],
        language: Literal["vi", "en", "ja"] = "vi",
    ) -> dict:
        """
        Execute the complete ClinPlain analysis pipeline.

        1. OCR
        2. Medical extraction
        3. FHIR normalization
        4. Patient-friendly explanation
        """

        # Step 1: OCR.
        try:
            ocr_input = self._extract_ocr(images)

        except Exception as exc:
            raise DocumentAnalysisError(
                "ocr"
            ) from exc

        # Step 2: Medical extraction.
        try:
            medical_result = self.medical_service.extract(
                ocr_input
            )

        except Exception as exc:
            logger.error(
                "Medical Extraction failed: %s",
                type(exc).__name__,
            )

            logger.error(
                "Error details: %s",
                str(exc),
            )

            raise DocumentAnalysisError(
                "medical_extraction"
            ) from exc

        # Step 3: FHIR normalization.
        try:
            fhir_request = FHIRNormalizeRequest(
                pages=medical_result.pages,
                contexts=[],
            )

            fhir_result = self.fhir_service.normalize(
                fhir_request
            )

        except Exception as exc:
            raise DocumentAnalysisError(
                "fhir_normalization"
            ) from exc

        # Step 4: Patient-friendly explanation.
        try:
            explanation_request = ExplanationRequest(
                language=language,
                pages=medical_result.pages,
                fhir_result=(
                    FHIRNormalizationResult.model_validate(
                        fhir_result
                    )
                ),
            )

            explanation_result = (
                self.explanation_service.generate(
                    explanation_request
                )
            )

        except Exception as exc:
            raise DocumentAnalysisError(
                "patient_explanation"
            ) from exc

        # Step 5: Return unified results.
        return {
            "status": "success",
            "language": language,
            "total_pages": len(images),
            "ocr": {
                "status": "success",
                "total_pages": len(ocr_input.pages),
                "pages": [
                    page.model_dump(mode="json")
                    for page in ocr_input.pages
                ],
            },
            "medical": {
                "status": "success",
                "total_pages": len(medical_result.pages),
                "pages": [
                    page.model_dump(mode="json")
                    for page in medical_result.pages
                ],
            },
            "fhir": fhir_result,
            "explanation": explanation_result,
        }