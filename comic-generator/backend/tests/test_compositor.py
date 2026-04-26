from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.compositor_service import CompositorService


def _one_pixel_image_bytes() -> bytes:
    image = Image.new("RGB", (1, 1), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_compose_page_outputs_valid_png_and_expected_size(monkeypatch):
    service = CompositorService()
    image_bytes = _one_pixel_image_bytes()

    async def fake_download(_url: str):
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")

    monkeypatch.setattr(service, "_download_image", fake_download)

    output = await service.compose_page(
        panel_images=["a", "b", "c", "d"],
        dialogues=["hi", "there", "comic", "page"],
        page_number=1,
        style="manga",
    )

    composed = Image.open(io.BytesIO(output))
    assert composed.format == "PNG"
    assert composed.size == (1800, 2400)


@pytest.mark.asyncio
async def test_compose_page_wraps_long_dialogue(monkeypatch):
    service = CompositorService()
    image_bytes = _one_pixel_image_bytes()

    async def fake_download(_url: str):
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")

    recorded_dialogues: list[str] = []
    original_draw_bubble = service._draw_dialogue_bubble

    def wrapped_draw_bubble(**kwargs):
        recorded_dialogues.append(kwargs["dialogue"])
        return original_draw_bubble(**kwargs)

    monkeypatch.setattr(service, "_download_image", fake_download)
    monkeypatch.setattr(service, "_draw_dialogue_bubble", wrapped_draw_bubble)

    long_dialogue = "This is a very long dialogue " * 20
    await service.compose_page(
        panel_images=["a", "b", "c", "d"],
        dialogues=[long_dialogue, "short", "short", "short"],
        page_number=2,
        style="western",
    )

    assert any(len(dialogue) > 100 for dialogue in recorded_dialogues)


@pytest.mark.asyncio
async def test_compose_page_skips_dialogue_bubble_when_null(monkeypatch):
    service = CompositorService()
    image_bytes = _one_pixel_image_bytes()

    async def fake_download(_url: str):
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")

    bubble_calls: list[str] = []

    def fake_draw_bubble(**kwargs):
        bubble_calls.append(kwargs["dialogue"])

    monkeypatch.setattr(service, "_download_image", fake_download)
    monkeypatch.setattr(service, "_draw_dialogue_bubble", fake_draw_bubble)

    await service.compose_page(
        panel_images=["a", "b", "c", "d"],
        dialogues=[None, "line 2", "line 3", "line 4"],
        page_number=3,
        style="noir",
    )

    assert len(bubble_calls) == 3
    assert all(item is not None for item in bubble_calls)
