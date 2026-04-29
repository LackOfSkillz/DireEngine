from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tmp.mt505_test_rooms import TEST_ROOMS


MODEL_NAME = "qwen2.5-14b-instruct"
BASE_URL = "http://127.0.0.1:1234/v1/chat/completions"
DESCRIPTION_SYSTEM_PROMPT_PATH = REPO_ROOT / "world" / "builder" / "templates" / "room_description_system_prompt.txt"
MARKUP_SYSTEM_PROMPT_PATH = REPO_ROOT / "tmp" / "mt505_state_markup_prompt.txt"
OUTPUT_PATH = REPO_ROOT / "exports" / "mt506_qwen_capability.txt"


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


def _usage_dict(payload: dict[str, Any]) -> dict[str, int]:
    usage = payload.get("usage") or {}
    data: dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        value = usage.get(key)
        if isinstance(value, int):
            data[key] = value
    return data


def _merge_usage(total: dict[str, int], current: dict[str, int]) -> None:
    for key, value in current.items():
        total[key] = total.get(key, 0) + value


def _call_model(*, system_prompt: str, user_message: str, max_tokens: int, timeout_seconds: int) -> tuple[str, dict[str, int]]:
    response = requests.post(
        BASE_URL,
        json={
            "model": MODEL_NAME,
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("Model returned no choices")
    message = choices[0].get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise RuntimeError("Model returned empty content")
    return content, _usage_dict(payload)


def main() -> int:
    description_system_prompt = _load_text(DESCRIPTION_SYSTEM_PROMPT_PATH)
    markup_system_prompt = _load_text(MARKUP_SYSTEM_PROMPT_PATH)
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    total_usage: dict[str, int] = {}
    total_calls = 0
    error_count = 0
    per_call_durations: list[float] = []
    run_started = time.perf_counter()

    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        handle.write("MT-506 - Qwen 2.5 14B Instruct capability test for stateful descriptions\n")
        handle.write("=" * 60 + "\n\n")

        for room in TEST_ROOMS:
            room_id = room["room_id"]
            name = room["name"]
            print(f"[{room_id}] Pass 1...")

            handle.write(f"## {room_id} — {name}\n\n")
            handle.write(f"Environment: {room['environment']}\n")
            handle.write(f"Applicable groups: {', '.join(room['applicable_state_groups'])}\n")
            handle.write(f"Applicable states: {', '.join(room['applicable_states'])}\n\n")

            pass_1_output = ""
            try:
                started = time.perf_counter()
                total_calls += 1
                pass_1_output, usage = _call_model(
                    system_prompt=description_system_prompt,
                    user_message=_room_user_message(room),
                    max_tokens=300,
                    timeout_seconds=180,
                )
                per_call_durations.append(time.perf_counter() - started)
                _merge_usage(total_usage, usage)
                handle.write(f"### Pass 1 (plain prose):\n{pass_1_output}\n\n")
            except Exception as exc:  # pragma: no cover - runtime integration path
                error_count += 1
                handle.write(f"### Pass 1 (plain prose):\n[ERROR: {exc}]\n\n")
                handle.write("### Pass 2 (with markup):\n[ERROR: skipped because Pass 1 failed]\n\n")
                handle.write("-" * 60 + "\n\n")
                print(f"[{room_id}] Pass 1 failed: {exc}")
                continue

            print(f"[{room_id}] Pass 2...")
            try:
                started = time.perf_counter()
                total_calls += 1
                pass_2_output, usage = _call_model(
                    system_prompt=markup_system_prompt,
                    user_message=_markup_user_message(room, pass_1_output),
                    max_tokens=500,
                    timeout_seconds=180,
                )
                per_call_durations.append(time.perf_counter() - started)
                _merge_usage(total_usage, usage)
                handle.write(f"### Pass 2 (with markup):\n{pass_2_output}\n\n")
            except Exception as exc:  # pragma: no cover - runtime integration path
                error_count += 1
                handle.write(f"### Pass 2 (with markup):\n[ERROR: {exc}]\n\n")
                print(f"[{room_id}] Pass 2 failed: {exc}")

            handle.write("-" * 60 + "\n\n")
            print(f"[{room_id}] Done.")

        total_runtime = time.perf_counter() - run_started
        handle.write("## Run Summary\n\n")
        handle.write(f"Total API calls: {total_calls}\n")
        handle.write(f"Total errors: {error_count}\n")
        handle.write(f"Total runtime seconds: {total_runtime:.2f}\n")
        if per_call_durations:
            handle.write(f"Average call seconds: {sum(per_call_durations) / len(per_call_durations):.2f}\n")
            handle.write(f"Fastest call seconds: {min(per_call_durations):.2f}\n")
            handle.write(f"Slowest call seconds: {max(per_call_durations):.2f}\n")
        if total_usage:
            handle.write("Usage totals:\n")
            for key in sorted(total_usage):
                handle.write(f"- {key}: {total_usage[key]}\n")
        else:
            handle.write("Usage totals: none reported by LM Studio response\n")

    print(f"Output saved to: {OUTPUT_PATH}")
    print(f"Total API calls: {total_calls}")
    print(f"Total errors: {error_count}")
    print(f"Total runtime seconds: {total_runtime:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())