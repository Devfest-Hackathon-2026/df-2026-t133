from fastapi import APIRouter, HTTPException

from .models.fhir_schemas import FHIRNormalizeRequest
from .services.fhir_service import FHIRService


class FHIRController:

    def __init__(
        self,
        fhir_service: FHIRService,
    ):
        self.fhir_service = fhir_service

        self.router = APIRouter(
            prefix="/api/fhir",
            tags=["FHIR"],
        )

        self.router.add_api_route(
            path="/normalize",
            endpoint=self.normalize,
            methods=["POST"],
            summary="Normalize medical facts to FHIR R4",
        )

    def get_router(self) -> APIRouter:
        return self.router

    async def normalize(
        self,
        request: FHIRNormalizeRequest,
    ) -> dict:
        """
        Normalize medical extraction results
        into FHIR R4 resources.
        """

        # Step 1: Validate unique page indices.
        page_indices = [
            page.page_index
            for page in request.pages
        ]

        if len(page_indices) != len(set(page_indices)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate page_index values.",
            )

        # Step 2: Validate unique context references.
        context_keys = [
            (
                context.page_index,
                context.source_line_index,
            )
            for context in request.contexts
        ]

        if len(context_keys) != len(set(context_keys)):
            raise HTTPException(
                status_code=400,
                detail="Duplicate fact contexts.",
            )

        # Step 3: Validate references to existing facts.
        fact_keys = {
            (
                page.page_index,
                fact.source_line_index,
            )
            for page in request.pages
            for fact in page.facts
        }

        for key in context_keys:
            if key not in fact_keys:
                raise HTTPException(
                    status_code=400,
                    detail="Context references an unknown fact.",
                )

        # Step 4: Call FHIRService.
        result = self.fhir_service.normalize(request)

        return result