
import io
import logging
import warnings
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from google.api_core.exceptions import GoogleAPICallError
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .services.ocr_service import OCRService


logger = logging.getLogger(__name__)


class OCRController:
    MAX_IMAGES = 12
    MAX_FILE_SIZE = 5 * 1024 * 1024
    MAX_TOTAL_SIZE = 25 * 1024 * 1024
    MAX_PIXELS = 20_000_000

    ALLOWED_FORMATS = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
    }

    def __init__(self, ocr_service: OCRService):
        self.ocr_service = ocr_service

        self.router = APIRouter(
            prefix="/api/ocr",
            tags=["OCR"],
        )

        self.router.add_api_route(
            path="/extract",
            endpoint=self.extract,
            methods=["POST"],
            summary="Extract text from multiple document images",
        )

    def get_router(self) -> APIRouter:
        return self.router

    def _validate_image(
        self,
        data: bytes,
        filename: str,
    ) -> str:
        """Validate image bytes and return actual MIME type."""

        try:
            with warnings.catch_warnings():
                warnings.simplefilter(
                    "error",
                    Image.DecompressionBombWarning,
                )

                with Image.open(io.BytesIO(data)) as image:
                    image_format = image.format
                    width, height = image.size

                    if image_format not in self.ALLOWED_FORMATS:
                        raise HTTPException(
                            status_code=415,
                            detail=f"Unsupported image: {filename}",
                        )

                    if width * height > self.MAX_PIXELS:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Image too large: {filename}",
                        )

                    image.verify()

                with Image.open(io.BytesIO(data)) as image:
                    image.load()

        except HTTPException:
            raise

        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            SyntaxError,
            Image.DecompressionBombWarning,
            Image.DecompressionBombError,
        ) as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image: {filename}",
            ) from exc

        return self.ALLOWED_FORMATS[image_format]

    async def extract(
        self,
        files: Annotated[
            list[UploadFile],
            File(description="Document images in page order"),
        ],
    ) -> dict:
        """Validate and OCR multiple images sequentially."""

        if not 1 <= len(files) <= self.MAX_IMAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Upload between 1 and {self.MAX_IMAGES} images.",
            )

        pages = []
        total_size = 0

        try:
            for page_index, file in enumerate(files):
                filename = (
                    file.filename or f"page_{page_index + 1}"
                ).replace("\\", "/").split("/")[-1]

                data = await file.read(self.MAX_FILE_SIZE + 1)

                if len(data) > self.MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large: {filename}",
                    )

                total_size += len(data)

                if total_size > self.MAX_TOTAL_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Total upload exceeds 25 MB.",
                    )

                mime_type = self._validate_image(
                    data,
                    filename,
                )

                try:
                    # Google SDK is synchronous.
                    # Run in threadpool to avoid blocking FastAPI.
                    result = await run_in_threadpool(
                        self.ocr_service.extract_text,
                        data,
                        mime_type,
                    )
                except GoogleAPICallError as exc:
                    logger.error(
                        "Document AI failed on page %s: %s",
                        page_index + 1,
                        type(exc).__name__,
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            f"OCR processing failed for "
                            f"page {page_index + 1}"
                        ),
                    ) from exc

                pages.append({
                    "page_index": page_index,
                    "filename": filename,
                    "text": result["text"],
                    "lines": result["lines"],
                })

            return {
                "status": "success",
                "total_pages": len(pages),
                "pages": pages,
            }

        finally:
            for file in files:
                await file.close()
