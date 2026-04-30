from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from anthropic import Anthropic

from world.builder.prompting.room_description_prompt import (
    build_room_description_markup_user_message,
    build_room_description_user_message,
    load_room_description_state_markup_prompt,
    load_room_description_system_prompt,
)


_PROMPT_DIR = Path(__file__).parent.parent / "templates"


class RoomDescriptionGenerator:
    """Two-pass room description generation via Claude Sonnet 4.5."""

    MODEL = "claude-sonnet-4-5"
    PASS_1_MAX_TOKENS = 400
    PASS_2_MAX_TOKENS = 800
    INPUT_COST_PER_MILLION = 3.0
    OUTPUT_COST_PER_MILLION = 15.0

    def __init__(self):
        self._client = Anthropic()

    def generate(self, room_context: dict, applicable_groups: list[str], applicable_states: list[str]) -> dict:
        room_payload = dict(room_context or {})
        zone_payload = dict(room_payload.get("zone") or {})
        room_data = dict(room_payload.get("room") or {})
        generation_context = dict(room_payload.get("generation_context") or zone_payload.get("generation_context") or {})

        room_id = str(room_data.get("id") or "").strip()
        room_name = str(room_data.get("name") or "").strip()
        if not room_id or not room_name:
            raise ValueError("Room context must include room.id and room.name.")
        if not isinstance(zone_payload, dict) or not zone_payload:
            raise ValueError("Room context must include zone context.")

        start = time.perf_counter()
        pass_1_prompt = load_room_description_system_prompt()
        pass_1_message = build_room_description_user_message(room_data, generation_context)
        pass_1_text, pass_1_usage = self._call_model(
            system_prompt=pass_1_prompt,
            user_message=pass_1_message,
            max_tokens=self.PASS_1_MAX_TOKENS,
        )

        pass_2_prompt = load_room_description_state_markup_prompt()
        pass_2_message = build_room_description_markup_user_message(pass_1_text, applicable_groups, applicable_states)
        pass_2_text, pass_2_usage = self._call_model(
            system_prompt=pass_2_prompt,
            user_message=pass_2_message,
            max_tokens=self.PASS_2_MAX_TOKENS,
        )

        input_tokens = int(pass_1_usage.get("input_tokens", 0)) + int(pass_2_usage.get("input_tokens", 0))
        output_tokens = int(pass_1_usage.get("output_tokens", 0)) + int(pass_2_usage.get("output_tokens", 0))
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return {
            "pass_1": pass_1_text,
            "pass_2": pass_2_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "elapsed_ms": elapsed_ms,
            "approximate_cost_usd": self._approximate_cost_usd(input_tokens, output_tokens),
        }

    def _call_model(self, *, system_prompt: str, user_message: str, max_tokens: int) -> tuple[str, dict[str, int]]:
        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=max_tokens,
            temperature=0.3,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return self._extract_text(response), self._usage_dict(response)

    def _extract_text(self, response: Any) -> str:
        chunks: list[str] = []
        for block in getattr(response, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                chunks.append(str(text).strip())
        return "\n".join(chunk for chunk in chunks if chunk).strip()

    def _usage_dict(self, response: Any) -> dict[str, int]:
        usage = getattr(response, "usage", None)
        if not usage:
            return {}
        data: dict[str, int] = {}
        for key in ("input_tokens", "output_tokens"):
            value = getattr(usage, key, None)
            if isinstance(value, int):
                data[key] = value
        return data

    def _approximate_cost_usd(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (max(0, input_tokens) / 1_000_000) * self.INPUT_COST_PER_MILLION
        output_cost = (max(0, output_tokens) / 1_000_000) * self.OUTPUT_COST_PER_MILLION
        return round(input_cost + output_cost, 6)