"""Image generation helper service for Replicate integrations."""

from __future__ import annotations

import asyncio
import io
import time
import uuid
from typing import Any

import replicate
from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from loguru import logger

from app.core.config import get_settings
from app.services.storage_service import StorageService

STYLE_PREFIXES: dict[str, str] = {
    "manga": "manga style, black and white, detailed linework, screentone shading, shounen manga aesthetic",
    "western": "american comic book style, bold outlines, vibrant colors, dynamic poses, marvel comics aesthetic",
    "superhero": "superhero comic style, dramatic lighting, bold colors, action-focused, dc comics aesthetic",
    "cartoon": "cartoon style, bright colors, simple outlines, fun and playful, pixar-inspired",
    "noir": "noir comic style, high contrast black and white, dramatic shadows, vintage aesthetic, sin city style",
}
NEGATIVE_PROMPT = "blurry, deformed, ugly, inconsistent, text, watermark, signature"
FLUX_MODEL = "black-forest-labs/flux-1.1-pro"
MAX_RETRIES = 3
IMAGE_TIMEOUT_SECONDS = 120


class ImageService:
    """Generate panel and cover images with Replicate."""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = replicate.Client(api_token=settings.replicate_api_token)
        self.storage_service = storage_service or StorageService()

    async def generate_panel_image(
        self,
        scene_description: str,
        style: str,
        reference_image_url: str | None,
        character_description: str,
    ) -> str:
        """Generate one panel image and return its public URL."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="image_panel_generate", duration_ms=0).info(
            "Panel image generation started style={style}",
            style=style,
        )
        prompt = self._build_prompt(
            scene_description=scene_description,
            style=style,
            character_description=character_description,
        )
        input_payload: dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "width": 768,
            "height": 768,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "output_format": "webp",
        }
        if reference_image_url:
            input_payload["ip_adapter_image"] = reference_image_url

        output_url = await self._run_replicate_with_retries(input_payload=input_payload, action="image_panel_generate")
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="image_panel_generate", duration_ms=duration_ms).info(
            "Panel image generation finished"
        )
        return output_url

    async def generate_cover(self, title: str, style: str, reference_image_url: str | None) -> str:
        """Generate comic cover image URL."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="image_cover_generate", duration_ms=0).info(
            "Cover generation started style={style}",
            style=style,
        )
        style_prefix = self._get_style_prefix(style=style)
        prompt = (
            f"{style_prefix}. comic book cover artwork. "
            f"Title text visible in composition: '{title}'. "
            "Cinematic composition, compelling character pose, high detail."
        )
        input_payload: dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "width": 768,
            "height": 1024,
            "num_inference_steps": 28,
            "guidance_scale": 3.5,
            "output_format": "webp",
        }
        if reference_image_url:
            input_payload["ip_adapter_image"] = reference_image_url

        output_url = await self._run_replicate_with_retries(input_payload=input_payload, action="image_cover_generate")
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="image_cover_generate", duration_ms=duration_ms).info(
            "Cover generation finished"
        )
        return output_url

    async def process_reference_image(self, file: UploadFile) -> str:
        """Validate, optimize, and upload reference image to R2."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="reference_image_process", duration_ms=0).info(
            "Reference image processing started"
        )
        allowed_content_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
        if file.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only JPG, PNG, and WEBP are allowed.",
            )

        file_bytes = await file.read()
        max_bytes = self.settings.max_file_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum allowed size is {self.settings.max_file_size_mb}MB.",
            )

        try:
            optimized_jpeg = self._resize_and_convert_to_jpeg(file_bytes=file_bytes)
        except UnidentifiedImageError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not a valid image") from exc

        path = f"references/{uuid.uuid4()}.jpg"
        uploaded_url = await asyncio.to_thread(
            self.storage_service.upload_file,
            optimized_jpeg,
            path,
            "image/jpeg",
        )
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="reference_image_process", duration_ms=duration_ms).info(
            "Reference image processing finished"
        )
        return uploaded_url

    async def _run_replicate_with_retries(self, *, input_payload: dict[str, Any], action: str) -> str:
        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 1):
            attempt_started_at = time.perf_counter()
            try:
                output = await asyncio.wait_for(
                    asyncio.to_thread(self.client.run, FLUX_MODEL, input=input_payload),
                    timeout=IMAGE_TIMEOUT_SECONDS,
                )
                output_url = self._extract_output_url(output=output)
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action=action, duration_ms=duration_ms).info(
                    "Replicate generation succeeded attempt={attempt}",
                    attempt=attempt,
                )
                return output_url
            except asyncio.TimeoutError as exc:
                last_error = exc
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action=action, duration_ms=duration_ms).warning(
                    "Replicate generation timed out attempt={attempt}",
                    attempt=attempt,
                )
            except Exception as exc:
                last_error = exc
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action=action, duration_ms=duration_ms).warning(
                    "Replicate generation failed attempt={attempt} error={error_type}",
                    attempt=attempt,
                    error_type=type(exc).__name__,
                )

            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** (attempt - 1))

        if last_error is None:
            raise RuntimeError("Image generation failed without a specific error")
        raise RuntimeError(f"Image generation failed after {MAX_RETRIES} attempts") from last_error

    def _extract_output_url(self, *, output: Any) -> str:
        if isinstance(output, str):
            return output
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, str):
                return first
            return str(first)
        raise ValueError("Replicate returned an unsupported output payload")

    def _build_prompt(self, *, scene_description: str, style: str, character_description: str) -> str:
        style_prefix = self._get_style_prefix(style=style)
        return (
            f"{style_prefix}. "
            f"Scene: {scene_description}. "
            f"Main character consistency details: {character_description}. "
            "High quality comic panel composition."
        )

    def _get_style_prefix(self, *, style: str) -> str:
        normalized_style = style.lower().strip()
        if normalized_style not in STYLE_PREFIXES:
            available = ", ".join(sorted(STYLE_PREFIXES.keys()))
            raise ValueError(f"Unsupported style '{style}'. Supported styles: {available}")
        return STYLE_PREFIXES[normalized_style]

    def _resize_and_convert_to_jpeg(self, *, file_bytes: bytes) -> bytes:
        with Image.open(io.BytesIO(file_bytes)) as image:
            rgb_image = image.convert("RGB")
            rgb_image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            rgb_image.save(buffer, format="JPEG", quality=90, optimize=True)
            return buffer.getvalue()
