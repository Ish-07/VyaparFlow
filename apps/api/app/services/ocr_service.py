from functools import lru_cache
from io import BytesIO
from pathlib import Path
import tempfile

from fastapi import HTTPException, UploadFile, status
from paddleocr import PaddleOCR
from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings

settings = get_settings()

SUPPORTED_IMAGE_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}


class OCRService:
    def __init__(self):
        if settings.ocr_provider != "paddleocr":
            raise RuntimeError(f"Unsupported OCR provider: {settings.ocr_provider}")

        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang=settings.ocr_language,
            use_gpu=settings.ocr_enable_gpu,
            show_log=False,
        )

    async def extract_text_from_upload(self, file: UploadFile) -> str:
        if file.content_type not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only PNG, JPG, JPEG, and WEBP image uploads are supported for OCR right now.",
            )

        file_bytes = await file.read()
        return self.extract_text_from_image_bytes(file_bytes)

    def extract_text_from_image_bytes(self, file_bytes: bytes) -> str:
        try:
            image = Image.open(BytesIO(file_bytes)).convert("RGB")
        except UnidentifiedImageError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not read this image file.",
            ) from exc

        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                temp_path = tmp.name
                image.save(temp_path)

            result = self.ocr.ocr(temp_path, cls=True)
            lines: list[str] = []

            for page in result or []:
                for item in page or []:
                    text = item[1][0]
                    if text:
                        lines.append(text.strip())

            extracted = "\n".join(line for line in lines if line)
            if not extracted.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="OCR completed, but no readable text was found.",
                )

            return extracted

        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)


@lru_cache
def get_ocr_service() -> OCRService:
    return OCRService()