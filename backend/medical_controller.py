
import logging

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from .models.medical_schemas import OCRInput
from .services.medical_extraction_service import (
    MedicalExtractionService,
)


logger = logging.getLogger(__name__)


class MedicalController:

    def __init__(
        self,
        medical_service: MedicalExtractionService,
    ):
        self.medical_service = medical_service

        self.router = APIRouter(
            prefix="/api/medical",
            tags=["Medical"],
        )

        self.router.add_api_route(
            path="/extract",
            endpoint=self.extract,
            methods=["POST"],
            summary="Extract medical facts from OCR JSON",
        )

    def get_router(self) -> APIRouter:
        return self.router

    async def extract(
        self,
        request: OCRInput,
    ) -> dict:
        page_indices = [
            page.page_index for page in request.pages
        ]

        if len(page_indices) != len(set(page_indices)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate page_index values.",
            )

        try:
            result = await run_in_threadpool(
                self.medical_service.extract,
                request,
            )

        except Exception as exc:
            # Do not log medical content or raw API responses.
            logger.error(
                "Medical extraction failed: %s",
                type(exc).__name__,
            )

            raise HTTPException(
                status_code=502,
                detail="Medical extraction failed.",
            ) from exc

        return {
            "status": "success",
            "total_pages": len(result.pages),
            "pages": [
                page.model_dump()
                for page in result.pages
            ],
        }
