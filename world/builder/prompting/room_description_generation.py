from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any

from world.builder.schemas.room_tag_schema import normalize_room_tags

from .room_description_prompt import assemble_room_description_prompt


@dataclass(frozen=True)
class RoomDescriptionGenerationResult:
    ok: bool
    text: str | None
    error: str | None
    provenance: dict[str, Any]


def _input_hash(room: dict | None, zone: dict | None) -> str:
    room_payload = dict(room or {})
    zone_payload = dict(zone or {})
    normalized = {
        "room": {
            "id": str(room_payload.get("id") or room_payload.get("name") or "").strip(),
            "name": str(room_payload.get("name") or "").strip(),
            "details": sorted(str(key or "").strip().lower() for key in dict(room_payload.get("details") or {}).keys() if str(key or "").strip()),
            "exits": sorted(str(direction or "").strip().lower() for direction in dict(room_payload.get("exits") or room_payload.get("exitMap") or {}).keys() if str(direction or "").strip()),
            "tags": normalize_room_tags(room_payload.get("tags")),
        },
        "zone": {
            "zone_id": str(zone_payload.get("zone_id") or zone_payload.get("name") or "").strip(),
            "name": str(zone_payload.get("name") or "").strip(),
            "generation_context": zone_payload.get("generation_context") or {},
        },
    }
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def generate_room_description(room: dict | None, zone: dict | None, *, client: Any, llm_config: Any, max_prompt_chars: int = 5000, max_tokens: int = 250) -> RoomDescriptionGenerationResult:
    prompt = assemble_room_description_prompt(room, zone, max_prompt_chars=max_prompt_chars)
    llm_enabled = bool(getattr(llm_config, "llm_enabled", False))
    model = str(getattr(llm_config, "llm_model", "")).strip()
    temperature = float(getattr(llm_config, "llm_temperature", 0.5) or 0.5)
    provenance = {
        "source": "llm",
        "model": model,
        "temperature": temperature,
        "prompt_trimmed": prompt.trimmed,
        "input_hash": _input_hash(room, zone),
    }
    if not llm_enabled or client is None:
        return RoomDescriptionGenerationResult(
            ok=False,
            text=None,
            error="Local LLM generation is unavailable.",
            provenance={**provenance, "source": "disabled"},
        )

    try:
        text = await client.generate(prompt.prompt, max_tokens=max_tokens, temperature=temperature)
    except Exception as exc:  # pragma: no cover - exercised through unit tests with stubs
        return RoomDescriptionGenerationResult(
            ok=False,
            text=None,
            error=str(exc) or "Local LLM generation failed.",
            provenance={**provenance, "source": "unavailable"},
        )

    return RoomDescriptionGenerationResult(
        ok=True,
        text=str(text or "").strip() or None,
        error=None,
        provenance=provenance,
    )