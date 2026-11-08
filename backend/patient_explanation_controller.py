import logging

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from .models.explanation_schemas import ExplanationRequest
from .services.patient_explanation_service import (
    PatientExplanationService,
)


logger = logging.getLogger(__name__)


class PatientExplanationController:

    def __init__(
        self,
        explanation_service: PatientExplanationService,
    ):
        self.explanation_service = explanation_service

        self.router = APIRouter(
            prefix="/api/explanation",
            tags=["Patient Explanation"],
        )

        self.router.add_api_route(
            path="/generate",
            endpoint=self.generate,
            methods=["POST"],
            summary="Generate patient-friendly medical explanations",
        )

    def get_router(self) -> APIRouter:
        return self.router

    async def generate(
        self,
        request: ExplanationRequest,
    ) -> dict:

        page_indices = [
            page.page_index
            for page in request.pages
        ]

        if len(page_indices) != len(set(page_indices)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate page_index values.",
            )

        for page in request.pages:
            for fact in page.facts:
                if (
                    fact.source_line_index < 0
                    or not fact.source_quote.strip()
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid medical fact source.",
                    )

        try:
            result = await run_in_threadpool(
                self.explanation_service.generate,
                request,
            )

            return result

        except Exception as exc:
            # Do not log medical facts or source quotations.
            logger.error(
                "Patient explanation failed: %s",
                type(exc).__name__,
            )

            raise HTTPException(
                status_code=502,
                detail="Patient explanation failed.",
            ) from exc