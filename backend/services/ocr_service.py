
from google.api_core.client_options import ClientOptions
from google.cloud import documentai


class OCRService:
    def __init__(
        self,
        project_id: str,
        location: str,
        processor_id: str,
    ):
        options = ClientOptions(
            api_endpoint=f"{location}-documentai.googleapis.com"
        )

        self.client = documentai.DocumentProcessorServiceClient(
            client_options=options
        )

        self.processor_name = self.client.processor_path(
            project_id,
            location,
            processor_id,
        )

    @staticmethod
    def _get_text(text: str, text_anchor) -> str:
        """Extract OCR text from Document AI text anchors."""
        parts = []

        for segment in text_anchor.text_segments:
            start = int(segment.start_index)
            end = int(segment.end_index)
            parts.append(text[start:end])

        return "".join(parts).strip()

    def extract_text(
        self,
        image_data: bytes,
        mime_type: str,
    ) -> dict:
        """Run OCR on one image and return structured results."""

        raw_document = documentai.RawDocument(
            content=image_data,
            mime_type=mime_type,
        )

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
        )

        result = self.client.process_document(request=request)
        document = result.document

        lines = []

        for page in document.pages:
            for line in page.lines:
                layout = line.layout

                line_text = self._get_text(
                    document.text,
                    layout.text_anchor,
                )

                bounding_box = [
                    {
                        "x": round(float(vertex.x), 4),
                        "y": round(float(vertex.y), 4),
                    }
                    for vertex in layout.bounding_poly.normalized_vertices
                ]

                lines.append({
                    "text": line_text,
                    "confidence": round(
                        float(layout.confidence), 4
                    ),
                    "bounding_box": bounding_box,
                })

        return {
            "text": document.text,
            "lines": lines,
        }
