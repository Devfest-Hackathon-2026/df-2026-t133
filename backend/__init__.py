
import os

from fastapi import FastAPI

from .document_controller import DocumentController
from .ocr_controller import OCRController
from .services.ocr_service import OCRService

from .medical_controller import MedicalController
from .services.medical_extraction_service import (
    MedicalExtractionService,
)

from .fhir_controller import FHIRController
from .services.fhir_service import FHIRService

from .patient_explanation_controller import (
    PatientExplanationController,
)

from .services.patient_explanation_service import (
    PatientExplanationService,
)

from .teachback_controller import TeachBackController

from .services.teachback_service import TeachBackService

from .services.document_analysis_service import (
    DocumentAnalysisService,
)

class ControllerRegistry:
    def __init__(self, app: FastAPI):
        self.app = app

        ocr_service = OCRService(
            project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ["DOCUMENT_AI_LOCATION"],
            processor_id=os.environ["DOCUMENT_AI_PROCESSOR_ID"],
        )
        
        medical_service = MedicalExtractionService(
            project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get(
                "GEMINI_LOCATION",
                "global",
            ),
            model=os.environ.get(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            ),
        )
        
        fhir_service = FHIRService()
        
        explanation_service = PatientExplanationService(
            project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get(
                "GEMINI_LOCATION",
                "global",
            ),
            model=os.environ.get(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            ),
        )
        
        teachback_service = TeachBackService(
            project_id=os.environ["GOOGLE_CLOUD_PROJECT"],
            location=os.environ.get(
                "GEMINI_LOCATION",
                "global",
            ),
            model=os.environ.get(
                "GEMINI_MODEL",
                "gemini-3.8-flash",
            ),
        )
        
        analysis_service = DocumentAnalysisService(
            ocr_service=ocr_service,
            medical_service=medical_service,
            fhir_service=fhir_service,
            explanation_service=explanation_service,
        )


        self.controllers = [
            DocumentController(analysis_service=analysis_service,),
            OCRController(ocr_service=ocr_service),
            MedicalController(medical_service=medical_service),
            FHIRController(fhir_service=fhir_service),
            PatientExplanationController(explanation_service=explanation_service),
            TeachBackController(teachback_service=teachback_service),
        ]

    def register(self) -> None:
        for controller in self.controllers:
            self.app.include_router(
                controller.get_router()
            )
