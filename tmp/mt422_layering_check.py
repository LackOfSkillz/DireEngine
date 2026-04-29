from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from tools.generate_sample_descriptions import load_generation_zone, setup_django  # noqa: E402
from world.builder.prompting.room_description_prompt import assemble_room_description_prompt  # noqa: E402


ZONE_ID = "crossingV2"
ROOM_ID = "crossingV2_178_132"
OUTPUT_CAPTURE = REPO_ROOT / "tmp" / "mt422_layering_check.txt"
OUTPUT_VERDICT = REPO_ROOT / "tmp" / "mt422_layering_verdict.md"
MAX_PROMPT_CHARS = 22000
MAX_TOKENS = 140
TEMPERATURE = 0.5
DEFAULT_BASE_URL = "http://127.0.0.1:1234"
DEFAULT_MODEL = "qwen2.5-14b-instruct"
DEFAULT_TIMEOUT = 60.0
CHAT_COMPLETIONS_PATH = "/v1/chat/completions"

FORBIDDEN_SIGNAL_PATTERNS = {
    "hearth": r"\bhearth\b",
    "beams": r"\bbeams?\b",
    "ale": r"\bale\b",
    "roasting meat": r"\broasting meat\b",
    "barrels": r"\bbarrels?\b",
    "patrons": r"\bpatrons?\b",
    "timber": r"\btimber\b",
    "flickering light": r"\bflickering light\b",
    "a narrow passage": r"\ba narrow passage\b",
}

UI_BANNED_PHRASES = [
    "in the heart of",
    "the air is thick with",
    "whispers secrets",
    "forgotten",
    "ancient",
    "shrouded",
    "mysterious",
    "hidden",
    "long-abandoned",
]


def _get_room_and_zone() -> tuple[dict, dict]:
    zone = load_generation_zone(ZONE_ID)
    room_index = {str(room.get("id") or "").strip(): room for room in list(zone.get("rooms") or [])}
    return room_index[ROOM_ID], zone


def _base_url() -> str:
    return str(os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).strip().rstrip("/")


def _model_name() -> str:
    return str(os.getenv("LLM_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _timeout() -> float:
    raw_timeout = os.getenv("LLM_TIMEOUT")
    try:
        return float(raw_timeout if raw_timeout not in (None, "") else DEFAULT_TIMEOUT)
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def _completions_url() -> str:
    return f"{_base_url()}{CHAT_COMPLETIONS_PATH}"


def _build_payload(prompt_text: str) -> dict:
    return {
        "model": _model_name(),
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }


def _extract_response_text(response_json: dict) -> str:
    choices = list(response_json.get("choices") or [])
    if not choices:
        return ""
    first_choice = choices[0] or {}
    message = first_choice.get("message") or {}
    return str(message.get("content") or "").strip()


def _signal_hits(text: str) -> dict[str, int]:
    lowered = str(text or "")
    hits: dict[str, int] = {}
    for label, pattern in FORBIDDEN_SIGNAL_PATTERNS.items():
        count = len(re.findall(pattern, lowered, flags=re.IGNORECASE))
        if count:
            hits[label] = count
    for phrase in UI_BANNED_PHRASES:
        count = lowered.lower().count(phrase)
        if count:
            hits[f"banned phrase: {phrase}"] = count
    return hits


def _verdict_markdown(prompt, payload: dict, response_json: dict, response_text: str, signal_hits: dict[str, int]) -> str:
    layering_supported = not any(key in signal_hits for key in ["hearth", "beams", "ale", "roasting meat", "barrels", "patrons", "timber", "flickering light"])
    if layering_supported:
        verdict = "UI prompt may be influencing the API path."
    else:
        verdict = "UI prompt is not reliably taking effect on the API path."

    lines = [
        "# MT-422 Layering Verdict",
        "",
        verdict,
        "",
        "## Request Shape",
        "",
        f"- Endpoint: `{_completions_url()}`",
        f"- Message count: {len(payload.get('messages') or [])}",
        f"- System messages sent by API client: {sum(1 for message in payload.get('messages') or [] if message.get('role') == 'system')}",
        f"- Prompt trimmed: {prompt.trimmed}",
        "",
        "## Response Signals",
        "",
    ]

    if signal_hits:
        for label, count in signal_hits.items():
            lines.append(f"- {label}: {count}")
    else:
        lines.append("- No forbidden tavern/example-leakage signals detected.")

    lines.extend(
        [
            "",
            "## Response Text",
            "",
            "```text",
            response_text or "[empty response]",
            "```",
            "",
            "## Interpretation",
            "",
            "If the LM Studio UI system prompt were strongly layering onto this API path, fabricated tavern/interior detail such as hearth, beams, ale, barrels, or roasting meat should have been suppressed for this diagnostic room. Their presence is evidence against reliable UI-prompt layering on the API path.",
            "",
        ]
    )
    return "\n".join(lines)


async def _request(payload: dict) -> tuple[httpx.Response, dict | str]:
    async with httpx.AsyncClient(timeout=_timeout()) as http_client:
        response = await http_client.post(_completions_url(), json=payload)
    try:
        response_json = response.json()
    except ValueError:
        response_json = {"raw_text": response.text}

    return response, response_json


def main() -> int:
    setup_django()
    room, zone = _get_room_and_zone()
    prompt = assemble_room_description_prompt(room, zone, max_prompt_chars=MAX_PROMPT_CHARS)
    payload = _build_payload(prompt.prompt)

    response, response_json = asyncio.run(_request(payload))

    response_text = _extract_response_text(response_json) if isinstance(response_json, dict) else ""
    signal_hits = _signal_hits(response_text)

    capture = {
        "zone_id": ZONE_ID,
        "room_id": ROOM_ID,
        "prompt_trimmed": prompt.trimmed,
        "request_payload": payload,
        "response_status": response.status_code,
        "response_json": response_json,
        "signal_hits": signal_hits,
    }
    OUTPUT_CAPTURE.write_text(json.dumps(capture, indent=2), encoding="utf-8")
    OUTPUT_VERDICT.write_text(_verdict_markdown(prompt, payload, response_json if isinstance(response_json, dict) else {}, response_text, signal_hits), encoding="utf-8")
    print(f"Layering capture written to {OUTPUT_CAPTURE}")
    print(f"Layering verdict written to {OUTPUT_VERDICT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())