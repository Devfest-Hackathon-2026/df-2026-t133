import logging

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from .models.teachback_schemas import (
    TeachBackGenerateRequest,
    TeachBackEvaluateRequest,
)
from .services.teachback_service import (
    TeachBackService,
    TeachBackInputError,
)


logger = logging.getLogger(__name__)


class TeachBackController:

    def __init__(
        self,
        teachback_service: TeachBackService,
    ):
        self.teachback_service = teachback_service

        self.router = APIRouter(
            prefix="/api/teachback",
            tags=["Teach-Back"],
        )

        self.router.add_api_route(
            path="/generate",
            endpoint=self.generate,
            methods=["POST"],
            summary="Generate teach-back questions",
        )

        self.router.add_api_route(
            path="/evaluate",
            endpoint=self.evaluate,
            methods=["POST"],
            summary="Evaluate a teach-back response",
        )

    def get_router(self) -> APIRouter:
        return self.router

    async def generate(
        self,
        request: TeachBackGenerateRequest,
    ) -> dict:
        """
        Generate patient-friendly teach-back questions.
        """
        try:
            result = await run_in_threadpool(
                self.teachback_service.generate_questions,
                request,
            )

            return result

        except TeachBackInputError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            logger.error(
                "Teach-back generation failed: %s",
                type(exc).__name__,
            )

            raise HTTPException(
                status_code=502,
                detail="Teach-back generation failed.",
            ) from exc

    async def evaluate(
        self,
        request: TeachBackEvaluateRequest,
    ) -> dict:
        """
        Evaluate a user's answer against document facts.
        """
        try:
            result = await run_in_threadpool(
                self.teachback_service.evaluate_answer,
                request,
            )

            return result

        except TeachBackInputError as exc:
            raise HTTPException(
                status_code=400,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            logger.error(
                "Teach-back evaluation failed: %s",
                type(exc).__name__,
            )

            raise HTTPException(
                status_code=502,
                detail="Teach-back evaluation failed.",
            ) from exc