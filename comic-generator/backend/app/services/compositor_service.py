"""Comic page compositor and PDF generator service."""

from __future__ import annotations

import asyncio
import io
import tempfile
import textwrap
import time
from datetime import datetime, timezone

import httpx
from fpdf import FPDF
from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from app.services.storage_service import StorageService

PAGE_WIDTH = 1800
PAGE_HEIGHT = 2400
GUTTER = 20
PANEL_WIDTH = 850
PANEL_HEIGHT = 1150
PANEL_BORDER = 3


class CompositorService:
    """Compose comic pages and generate final PDF."""

    def __init__(self, storage_service: StorageService | None = None) -> None:
        self.storage_service = storage_service or StorageService()

    async def compose_page(
        self,
        panel_images: list[str],
        dialogues: list[str | None],
        page_number: int,
        style: str,
        camera_angles: list[str] | None = None,
    ) -> bytes:
        """Compose 4 panels into a comic page PNG."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="compose_page", duration_ms=0).info(
            "Page composition started page_number={page_number} style={style}",
            page_number=page_number,
            style=style,
        )
        if len(panel_images) != 4:
            raise ValueError("compose_page expects exactly 4 panel image URLs")
        if len(dialogues) != 4:
            raise ValueError("compose_page expects exactly 4 dialogue entries")

        downloaded_images = await asyncio.gather(*(self._download_image(url) for url in panel_images))
        page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "black")
        draw = ImageDraw.Draw(page)
        panel_font = self._load_font(size=36)
        footer_font = self._load_font(size=30)

        positions = [
            (40, 40),
            (40 + PANEL_WIDTH + GUTTER, 40),
            (40, 40 + PANEL_HEIGHT + GUTTER),
            (40 + PANEL_WIDTH + GUTTER, 40 + PANEL_HEIGHT + GUTTER),
        ]

        for index, image in enumerate(downloaded_images):
            panel = image.resize((PANEL_WIDTH, PANEL_HEIGHT), Image.Resampling.LANCZOS)
            x_pos, y_pos = positions[index]
            page.paste(panel, (x_pos, y_pos))
            draw.rectangle(
                [x_pos, y_pos, x_pos + PANEL_WIDTH, y_pos + PANEL_HEIGHT],
                outline="black",
                width=PANEL_BORDER,
            )
            dialogue = dialogues[index]
            if dialogue:
                camera_angle = camera_angles[index] if camera_angles and len(camera_angles) > index else "medium"
                self._draw_dialogue_bubble(
                    canvas=page,
                    panel_x=x_pos,
                    panel_y=y_pos,
                    dialogue=dialogue,
                    font=panel_font,
                    camera_angle=camera_angle,
                )

        footer_text = f"Page {page_number}"
        footer_bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
        footer_width = footer_bbox[2] - footer_bbox[0]
        footer_x = (PAGE_WIDTH - footer_width) // 2
        draw.text((footer_x, PAGE_HEIGHT - 55), footer_text, fill="white", font=footer_font)

        output = io.BytesIO()
        page.save(output, format="PNG", optimize=True)
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="compose_page", duration_ms=duration_ms).info(
            "Page composition finished page_number={page_number}",
            page_number=page_number,
        )
        return output.getvalue()

    async def generate_pdf(
        self,
        pages_bytes: list[bytes],
        cover_bytes: bytes,
        title: str,
        comic_id: str,
    ) -> str:
        """Generate final PDF, upload to R2, and return stable storage URL."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="generate_pdf", duration_ms=0).info(
            "PDF generation started comic_id={comic_id}",
            comic_id=comic_id,
        )
        pdf = FPDF(unit="mm", format=(210, 280))
        pdf.set_auto_page_break(auto=False, margin=0)
        pdf.set_compression(True)
        pdf.set_title(title)
        pdf.set_author("Comic Generator AI")
        pdf.set_creator("Comic Generator AI")
        pdf.set_subject(f"Generated on {datetime.now(timezone.utc).isoformat()}")

        cover_temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        try:
            cover_temp.write(cover_bytes)
            cover_temp.close()
            pdf.add_page()
            pdf.image(cover_temp.name, x=0, y=0, w=210, h=280)
        finally:
            pass

        page_temp_paths: list[str] = []
        try:
            for page_data in pages_bytes:
                page_temp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                page_temp.write(page_data)
                page_temp.close()
                page_temp_paths.append(page_temp.name)
                pdf.add_page()
                pdf.image(page_temp.name, x=0, y=0, w=210, h=280)

            pdf_bytes = bytes(pdf.output(dest="S"))
        finally:
            for temp_path in [cover_temp.name, *page_temp_paths]:
                try:
                    import os

                    os.unlink(temp_path)
                except OSError:
                    continue

        pdf_path = f"comics/{comic_id}/final.pdf"
        uploaded_url = await asyncio.to_thread(self.storage_service.upload_file, pdf_bytes, pdf_path, "application/pdf")
        duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="generate_pdf", duration_ms=duration_ms).info(
            "PDF generation finished comic_id={comic_id}",
            comic_id=comic_id,
        )
        return uploaded_url

    async def _download_image(self, url: str) -> Image.Image:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")

    def _load_font(self, *, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = [
            "Comic Sans MS.ttf",
            "comic.ttf",
            "Bangers-Regular.ttf",
            "arial.ttf",
        ]
        for font_name in candidates:
            try:
                return ImageFont.truetype(font_name, size=size)
            except OSError:
                continue
        return ImageFont.load_default()

    def _draw_dialogue_bubble(
        self,
        *,
        canvas: Image.Image,
        panel_x: int,
        panel_y: int,
        dialogue: str,
        font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
        camera_angle: str,
    ) -> None:
        draw = ImageDraw.Draw(canvas)
        max_text_width = PANEL_WIDTH - 80
        wrapped_text = textwrap.fill(dialogue, width=28)
        text_bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, spacing=8)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        bubble_width = min(max_text_width, text_width + 40)
        bubble_height = text_height + 36
        bubble_x = panel_x + (PANEL_WIDTH - bubble_width) // 2

        if camera_angle == "wide":
            bubble_y = panel_y + 30
        elif camera_angle == "close":
            bubble_y = panel_y + PANEL_HEIGHT - bubble_height - 30
        else:
            bubble_y = panel_y + 60

        bubble_rect = [bubble_x, bubble_y, bubble_x + bubble_width, bubble_y + bubble_height]
        draw.rounded_rectangle(bubble_rect, radius=24, fill="white", outline="black", width=3)
        text_x = bubble_x + (bubble_width - text_width) / 2
        text_y = bubble_y + (bubble_height - text_height) / 2
        draw.multiline_text((text_x, text_y), wrapped_text, fill="black", font=font, align="center", spacing=8)
