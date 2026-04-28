"""Story generation service powered by Claude."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Literal

from anthropic import AsyncAnthropic
from loguru import logger
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import get_settings

MAX_RETRIES = 3
REQUEST_TIMEOUT_SECONDS = 60
INPUT_COST_PER_MILLION = 3.0
OUTPUT_COST_PER_MILLION = 15.0


class PanelSchema(BaseModel):
    """Schema for one comic panel."""

    panel_number: int = Field(ge=1, le=4)
    scene_description: str = Field(min_length=1, max_length=200)
    dialogue: str | None = None
    character_present: bool
    panel_type: Literal["action", "dialogue", "establishing", "closeup"]
    camera_angle: Literal["wide", "medium", "close", "aerial"]

    @field_validator("scene_description")
    @classmethod
    def validate_english_text(cls, value: str) -> str:
        if "\n" in value:
            return value.replace("\n", " ").strip()
        return value.strip()


class PageSchema(BaseModel):
    """Schema for one comic page."""

    page_number: int = Field(ge=1)
    panels: list[PanelSchema]

    @field_validator("panels")
    @classmethod
    def validate_panel_count(cls, value: list[PanelSchema]) -> list[PanelSchema]:
        if len(value) != 4:
            raise ValueError("Each page must have exactly 4 panels")
        expected_panel_numbers = [1, 2, 3, 4]
        actual_panel_numbers = [panel.panel_number for panel in value]
        if actual_panel_numbers != expected_panel_numbers:
            raise ValueError("Panel numbers must be 1..4 in order")
        return value


class ScriptSchema(BaseModel):
    """Schema for generated comic script."""

    title: str = Field(min_length=1, max_length=255)
    genre: str = Field(min_length=1, max_length=120)
    pages: list[PageSchema]


@dataclass
class ClaudeUsage:
    """Usage metadata from Claude responses."""

    input_tokens: int
    output_tokens: int

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.input_tokens / 1_000_000) * INPUT_COST_PER_MILLION
        output_cost = (self.output_tokens / 1_000_000) * OUTPUT_COST_PER_MILLION
        return round(input_cost + output_cost, 6)


class StoryService:
    """Generate and validate comic scripts via Claude."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model

    async def generate_script(self, prompt: str, pages: int, style: str) -> dict[str, Any]:
        """Generate a production-ready comic script as valid JSON."""
        operation_started_at = time.perf_counter()
        logger.bind(user_id="system", action="story_generation", duration_ms=0).info(
            "Story generation started pages={pages} style={style}",
            pages=pages,
            style=style,
        )

        system_prompt = self._build_system_prompt(pages=pages, style=style)
        correction_feedback: str | None = None
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            attempt_started_at = time.perf_counter()
            try:
                user_prompt = self._build_user_prompt(prompt=prompt, correction_feedback=correction_feedback)
                raw_response, usage = await self._request_claude(system_prompt=system_prompt, user_prompt=user_prompt)
                script = self._parse_and_validate_script(raw_response=raw_response, expected_pages=pages)
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action="story_generation_attempt", duration_ms=duration_ms).info(
                    "Story generation attempt succeeded attempt={attempt} input_tokens={input_tokens} output_tokens={output_tokens} estimated_cost_usd={estimated_cost_usd}",
                    attempt=attempt,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    estimated_cost_usd=usage.estimated_cost_usd,
                )
                total_duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
                logger.bind(user_id="system", action="story_generation", duration_ms=total_duration_ms).info(
                    "Story generation finished title={title}",
                    title=script["title"],
                )
                return script
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = exc
                correction_feedback = str(exc)
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action="story_generation_attempt", duration_ms=duration_ms).warning(
                    "Invalid script payload attempt={attempt} error={error}",
                    attempt=attempt,
                    error=type(exc).__name__,
                )
            except asyncio.TimeoutError as exc:
                last_error = exc
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action="story_generation_attempt", duration_ms=duration_ms).warning(
                    "Story generation timed out attempt={attempt}",
                    attempt=attempt,
                )
            except Exception as exc:
                last_error = exc
                duration_ms = int((time.perf_counter() - attempt_started_at) * 1000)
                logger.bind(user_id="system", action="story_generation_attempt", duration_ms=duration_ms).error(
                    "Unexpected Claude error attempt={attempt} error={error_type}",
                    attempt=attempt,
                    error_type=type(exc).__name__,
                )

            if attempt < MAX_RETRIES:
                await asyncio.sleep(2 ** (attempt - 1))

        total_duration_ms = int((time.perf_counter() - operation_started_at) * 1000)
        logger.bind(user_id="system", action="story_generation", duration_ms=total_duration_ms).error(
            "Story generation failed after retries"
        )
        if last_error is None:
            raise RuntimeError("Story generation failed without a specific error")
        raise RuntimeError(f"Failed to generate valid script after {MAX_RETRIES} attempts") from last_error

    async def _request_claude(self, *, system_prompt: str, user_prompt: str) -> tuple[str, ClaudeUsage]:
        response = await asyncio.wait_for(
            self.client.messages.create(
                model=self._model,
                max_tokens=4096,
                temperature=0.7,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if not response.content:
            raise ValueError("Claude returned empty content")
        content_block = response.content[0]
        raw_response = getattr(content_block, "text", "").strip()
        if not raw_response:
            raise ValueError("Claude returned blank text")
        usage = ClaudeUsage(
            input_tokens=int(getattr(response.usage, "input_tokens", 0)),
            output_tokens=int(getattr(response.usage, "output_tokens", 0)),
        )
        return raw_response, usage

    def _parse_and_validate_script(self, *, raw_response: str, expected_pages: int) -> dict[str, Any]:
        payload = self._extract_json_payload(raw_response=raw_response)
        parsed = json.loads(payload)
        script_model = ScriptSchema.model_validate(parsed)
        if len(script_model.pages) != expected_pages:
            raise ValueError(f"Expected exactly {expected_pages} pages, received {len(script_model.pages)}")
        expected_page_numbers = list(range(1, expected_pages + 1))
        actual_page_numbers = [page.page_number for page in script_model.pages]
        if actual_page_numbers != expected_page_numbers:
            raise ValueError("Page numbers must be sequential and start at 1")
        return script_model.model_dump()

    def _extract_json_payload(self, *, raw_response: str) -> str:
        cleaned_response = raw_response.strip()
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response.strip("`")
            cleaned_response = cleaned_response.replace("json", "", 1).strip()
        return cleaned_response

    def _build_user_prompt(self, *, prompt: str, correction_feedback: str | None) -> str:
        if not correction_feedback:
            return f"Create a comic script from this idea:\n{prompt}"
        return (
            "Your previous output was not valid according to the required JSON schema.\n"
            f"Validation feedback: {correction_feedback}\n"
            "Regenerate and return only corrected valid JSON.\n"
            f"Original idea:\n{prompt}"
        )

    def _build_system_prompt(self, *, pages: int, style: str) -> str:
        return (
            "You are a professional comic book screenwriter.\n"
            f"Create exactly {pages} pages for a {style} style comic.\n"
            "Each page must contain exactly 4 panels.\n"
            "For each panel include:\n"
            '- scene_description: visual prompt for image generation, in English only, max 200 chars\n'
            "- dialogue: spoken text or null\n"
            '- panel_type: one of "action" | "dialogue" | "establishing" | "closeup"\n'
            '- camera_angle: one of "wide" | "medium" | "close" | "aerial"\n'
            "Return only valid JSON matching this exact structure:\n"
            "{\n"
            '  "title": "string",\n'
            '  "genre": "string",\n'
            '  "pages": [\n'
            "    {\n"
            '      "page_number": 1,\n'
            '      "panels": [\n'
            "        {\n"
            '          "panel_number": 1,\n'
            '          "scene_description": "string en inglés para FLUX",\n'
            '          "dialogue": "string | null",\n'
            '          "character_present": true,\n'
            '          "panel_type": "string",\n'
            '          "camera_angle": "string"\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "Do not include markdown, comments, or extra keys."
        )
