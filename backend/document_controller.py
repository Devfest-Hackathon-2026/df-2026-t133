
import io
import warnings
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from io import BytesIO
from typing import Annotated, Literal

from fastapi import (
    File,
    Form,
    HTTPException,
    UploadFile,
)
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from .services.document_analysis_service import (
    DocumentAnalysisService,
    DocumentAnalysisError,
    DocumentImage,
)


class DocumentController:
    MAX_IMAGES = 12
    MAX_FILE_SIZE = 5 * 1024 * 1024
    MAX_TOTAL_SIZE = 25 * 1024 * 1024
    MAX_PIXELS = 20_000_000

    ALLOWED_FORMATS = {
        "JPEG": "image/jpeg",
        "PNG": "image/png",
    }

    def __init__(self, analysis_service: DocumentAnalysisService | None = None,):
        self.router = APIRouter(
            prefix="/api/documents",
            tags=["Documents"]
        )
        
        self.analysis_service = analysis_service

        self.router.add_api_route(
            path="/upload",
            endpoint=self.upload_documents,
            methods=["POST"],
            summary="Upload multiple medical document images"
        )
        
        self.router.add_api_route(
            path="/analyze",
            endpoint=self.analyze_documents,
            methods=["POST"],
            summary="Analyze uploaded medical documents",
        )

    def get_router(self) -> APIRouter:
        return self.router

    def _validate_image(self, data: bytes, filename: str) -> dict:
        """
        Validate image content and extract metadata.
        Do not trust filename or content-type alone.
        """
        try:
            with warnings.catch_warnings():
                warnings.simplefilter(
                    "error", Image.DecompressionBombWarning
                )

                # First pass: inspect image and verify structure.
                with Image.open(io.BytesIO(data)) as image:
                    image_format = image.format
                    width, height = image.size

                    if image_format not in self.ALLOWED_FORMATS:
                        raise HTTPException(
                            status_code=415,
                            detail=f"Unsupported image format: {filename}"
                        )

                    if width * height > self.MAX_PIXELS:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Image dimensions too large: {filename}"
                        )

                    image.verify()

                # Second pass: ensure image pixels can be decoded.
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
                detail=f"Invalid or corrupted image: {filename}"
            ) from exc

        return {
            "filename": filename,
            "content_type": self.ALLOWED_FORMATS[image_format],
            "size_bytes": len(data),
            "width": width,
            "height": height,
        }

    async def upload_documents(
        self,
        files: Annotated[
            list[UploadFile],
            File(description="Medical document images in page order")
        ]
    ) -> dict:
        """
        Receive and validate multiple document images.
        No OCR or persistent storage in this phase.
        """
        if not 1 <= len(files) <= self.MAX_IMAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Upload between 1 and {self.MAX_IMAGES} images."
            )

        documents = []
        total_size = 0

        try:
            for page_index, file in enumerate(files):
                filename = file.filename or f"page_{page_index + 1}"

                # Read at most MAX_FILE_SIZE + 1 bytes.
                data = await file.read(self.MAX_FILE_SIZE + 1)

                if len(data) > self.MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large: {filename}"
                    )

                total_size += len(data)

                if total_size > self.MAX_TOTAL_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Total upload size exceeds 25 MB."
                    )

                metadata = self._validate_image(data, filename)

                documents.append({
                    "page_index": page_index,
                    **metadata,
                })

            return {
                "status": "success",
                "total_pages": len(documents),
                "documents": documents,
            }

        finally:
            for file in files:
                await file.close()
                
    async def analyze_documents(
        self,
        files: Annotated[list[UploadFile], File(...)],
        language: Annotated[
            Literal["vi", "en", "ja"],
            Form(),
        ] = "vi",
    ) -> dict:
        """
        Upload images and execute the complete analysis pipeline.
        """

        MAX_IMAGES = 12
        MAX_FILE_SIZE = 5 * 1024 * 1024
        MAX_TOTAL_SIZE = 25 * 1024 * 1024
        MAX_IMAGE_PIXELS = 40_000_000

        allowed_formats = {
            "image/jpeg": "JPEG",
            "image/png": "PNG",
        }

        if self.analysis_service is None:
            raise HTTPException(
                status_code=503,
                detail="Document analysis is not configured.",
            )

        if not 1 <= len(files) <= MAX_IMAGES:
            raise HTTPException(
                status_code=400,
                detail="Upload between 1 and 12 images.",
            )

        images = []
        total_size = 0

        try:
            for page_index, file in enumerate(files):

                # Step 1: Validate MIME type.
                mime_type = file.content_type

                if mime_type not in allowed_formats:
                    raise HTTPException(
                        status_code=415,
                        detail=(
                            "Only JPEG and PNG images are supported."
                        ),
                    )

                # Step 2: Read with a per-file size limit.
                image_data = await file.read(
                    MAX_FILE_SIZE + 1
                )

                if not image_data:
                    raise HTTPException(
                        status_code=400,
                        detail="An uploaded image is empty.",
                    )

                if len(image_data) > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Each image must be 5 MB or smaller.",
                    )

                total_size += len(image_data)

                if total_size > MAX_TOTAL_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Total upload size exceeds 25 MB.",
                    )

                # Step 3: Verify actual image content.
                try:
                    with Image.open(
                        BytesIO(image_data)
                    ) as image:

                        actual_format = image.format

                        if (
                            image.width * image.height
                            > MAX_IMAGE_PIXELS
                        ):
                            raise HTTPException(
                                status_code=413,
                                detail="Image dimensions are too large.",
                            )

                        image.verify()

                except HTTPException:
                    raise

                except (
                    UnidentifiedImageError,
                    OSError,
                    ValueError,
                    Image.DecompressionBombError,
                ) as exc:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid or corrupted image.",
                    ) from exc

                # Step 4: Check content type matches image format.
                if actual_format != allowed_formats[mime_type]:
                    raise HTTPException(
                        status_code=415,
                        detail="Image format does not match MIME type.",
                    )

                # Step 5: Preserve page ordering.
                images.append(
                    DocumentImage(
                        page_index=page_index,
                        filename=(
                            file.filename
                            or f"page_{page_index}"
                        ),
                        mime_type=mime_type,
                        data=image_data,
                    )
                )

        finally:
            for file in files:
                await file.close()

        # Step 6: Execute the existing services.
        try:
            return await run_in_threadpool(
                self.analysis_service.analyze,
                images,
                language,
            )

        except DocumentAnalysisError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Document analysis failed.",
                    "stage": exc.stage,
                },
            ) from exc
