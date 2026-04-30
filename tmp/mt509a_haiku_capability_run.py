from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import anthropic
except ImportError as exc:  # pragma: no cover - runtime integration path
    raise SystemExit("Anthropic SDK not installed. Run: pip install anthropic") from exc

from tmp.mt505_test_rooms import TEST_ROOMS


MODEL_NAME = "claude-haiku-4-5"
DESCRIPTION_SYSTEM_PROMPT_PATH = REPO_ROOT / "world" / "builder" / "templates" / "room_description_system_prompt.txt"
MARKUP_SYSTEM_PROMPT_PATH = REPO_ROOT / "tmp" / "mt505_state_markup_prompt.txt"
OUTPUT_PATH = REPO_ROOT / "exports" / "mt509a_haiku_capability.txt"


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _json_block(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=True, sort_keys=True)


def _room_user_message(room: dict[str, Any]) -> str:
    return (
        "Write one grounded DireMud room description in plain prose.\n"
        "Do not use $state markup in this pass.\n\n"
        f"Room name: {room['name']}\n"
        f"Room ID: {room['room_id']}\n"
        f"Environment: {room['environment']}\n"
        f"Short description: {room['short_desc']}\n"
        f"Tags:\n{_json_block(room['tags'])}\n\n"
        f"Zone context:\n{room['zone_context']}\n"
    )


def _markup_user_message(room: dict[str, Any], description: str) -> str:
    return (
        f"Room name: {room['name']}\n"
        f"Room ID: {room['room_id']}\n"
        f"Environment: {room['environment']}\n"
        f"Description:\n{description}\n\n"
        f"Applicable state groups: {', '.join(room['applicable_state_groups'])}\n"
        f"Applicable states: {', '.join(room['applicable_states'])}\n"
    )


def _extract_text(response: Any) -> str:
    chunks: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            chunks.append(text)
    return "\n".join(chunk.strip() for chunk in chunks if chunk and chunk.strip()).strip()


def _usage_dict(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if not usage:
        return {}
    data: dict[str, int] = {}
    for key in (
        "input_tokens",
        "output_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        value = getattr(usage, key, None)
        if isinstance(value, int):
            data[key] = value
    return data


def _merge_usage(total: dict[str, int], current: dict[str, int]) -> None:
    for key, value in current.items():
        total[key] = total.get(key, 0) + value


def _call_model(client: Any, *, system_prompt: str, user_message: str, max_tokens: int) -> tuple[str, dict[str, int]]:
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=max_tokens,
        temperature=0.3,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return _extract_text(response), _usage_dict(response)


def main() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set in the environment")

    run_started_at = time.perf_counter()
    client = anthropic.Anthropic()
    description_system_prompt = _load_text(DESCRIPTION_SYSTEM_PROMPT_PATH)
    markup_system_prompt = _load_text(MARKUP_SYSTEM_PROMPT_PATH)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    total_usage: dict[str, int] = {}
    total_api_calls = 0
    total_errors = 0

    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        handle.write("MT-509a - Claude Haiku 4.5 capability test for stateful descriptions\n")
        handle.write("=" * 60 + "\n\n")

        for room in TEST_ROOMS:
            room_id = room["room_id"]
            name = room["name"]
            print(f"[{room_id}] Pass 1...")
            pass_1_output = ""

            handle.write(f"## {room_id} — {name}\n\n")
            handle.write(f"Environment: {room['environment']}\n")
            handle.write(f"Applicable groups: {', '.join(room['applicable_state_groups'])}\n")
            handle.write(f"Applicable states: {', '.join(room['applicable_states'])}\n\n")

            try:
                total_api_calls += 1
                pass_1_output, usage = _call_model(
                    client,
                    system_prompt=description_system_prompt,
                    user_message=_room_user_message(room),
                    max_tokens=300,
                )
                _merge_usage(total_usage, usage)
                if not pass_1_output:
                    raise RuntimeError("Model returned empty Pass 1 output")
                handle.write(f"### Pass 1 (plain prose):\n{pass_1_output}\n\n")
            except Exception as exc:  # pragma: no cover - runtime integration path
                total_errors += 1
                error_text = f"[ERROR: {exc}]"
                handle.write(f"### Pass 1 (plain prose):\n{error_text}\n\n")
                handle.write("### Pass 2 (with markup):\n[ERROR: skipped because Pass 1 failed]\n\n")
                handle.write("-" * 60 + "\n\n")
                print(f"[{room_id}] Pass 1 failed: {exc}")
                continue

            print(f"[{room_id}] Pass 2...")
            try:
                total_api_calls += 1
                pass_2_output, usage = _call_model(
                    client,
                    system_prompt=markup_system_prompt,
                    user_message=_markup_user_message(room, pass_1_output),
                    max_tokens=500,
                )
                _merge_usage(total_usage, usage)
                if not pass_2_output:
                    raise RuntimeError("Model returned empty Pass 2 output")
                handle.write(f"### Pass 2 (with markup):\n{pass_2_output}\n\n")
            except Exception as exc:  # pragma: no cover - runtime integration path
                total_errors += 1
                handle.write(f"### Pass 2 (with markup):\n[ERROR: {exc}]\n\n")
                print(f"[{room_id}] Pass 2 failed: {exc}")

            handle.write("-" * 60 + "\n\n")
            print(f"[{room_id}] Done.")

        elapsed_seconds = time.perf_counter() - run_started_at
        handle.write("## Run Summary\n\n")
        handle.write(f"Total API calls: {total_api_calls}\n")
        handle.write(f"Total errors: {total_errors}\n")
        handle.write(f"Elapsed seconds: {elapsed_seconds:.2f}\n")
        if total_usage:
            handle.write("Usage totals:\n")
            for key in sorted(total_usage):
                handle.write(f"- {key}: {total_usage[key]}\n")
        else:
            handle.write("Usage totals: none reported by SDK\n")
        handle.write("SDK cost fields: none exposed by the Anthropic Python SDK response object in this run.\n")

    print(f"Output saved to: {OUTPUT_PATH}")
    print(f"Total API calls: {total_api_calls}")
    print(f"Total errors: {total_errors}")
    print(f"Elapsed seconds: {time.perf_counter() - run_started_at:.2f}")
    if total_usage:
        print(f"Usage totals: {total_usage}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())