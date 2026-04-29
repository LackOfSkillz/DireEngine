from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from tools.generate_sample_descriptions import (  # noqa: E402
    build_llm_client,
    generate_samples_from_runtime,
    load_generation_zone,
    setup_django,
)
from world.builder.prompting.room_description_prompt import (  # noqa: E402
    PROMPT_VERSION,
    determine_applicable_state_groups,
    determine_applicable_states,
)


ROOM_TARGETS = [
    ("crossingV2", "crossingV2_192_132"),
    ("crossingV2", "crossingV2_178_132"),
    ("demo1", "CRO_500_100"),
]
OUTPUT_PATH = REPO_ROOT / "exports" / "mt502_stateful_test.txt"


def build_filtered_zones() -> tuple[list[dict], dict[tuple[str, str], dict], dict[str, dict]]:
    zone_to_room_ids: dict[str, list[str]] = {}
    for zone_id, room_id in ROOM_TARGETS:
        zone_to_room_ids.setdefault(zone_id, []).append(room_id)

    filtered_zones: list[dict] = []
    room_index: dict[tuple[str, str], dict] = {}
    zone_index: dict[str, dict] = {}
    for zone_id, room_ids in zone_to_room_ids.items():
        zone = load_generation_zone(zone_id)
        zone_room_map = {str(room.get("id") or "").strip(): room for room in list(zone.get("rooms") or [])}
        filtered_zone = dict(zone)
        filtered_zone["rooms"] = [zone_room_map[room_id] for room_id in room_ids]
        filtered_zones.append(filtered_zone)
        zone_index[zone_id] = zone
        for room_id in room_ids:
            room_index[(zone_id, room_id)] = zone_room_map[room_id]
    return filtered_zones, room_index, zone_index


def render_export(samples: list, room_index: dict[tuple[str, str], dict], zone_index: dict[str, dict]) -> str:
    sample_map = {sample.room_id: sample for sample in samples}
    lines = [
        "MT-502 Stateful Fragment Test",
        f"Prompt version: {PROMPT_VERSION}",
        f"Model: {os.getenv('LLM_MODEL', 'qwen2.5-14b-instruct')}",
        f"Temperature: {os.getenv('LLM_TEMPERATURE', '0.5')}",
        "",
    ]
    for zone_id, room_id in ROOM_TARGETS:
        zone = zone_index[zone_id]
        room = room_index[(zone_id, room_id)]
        sample = sample_map[room_id]
        lines.extend(
            [
                f"[Room: {room_id}]",
                f"Zone: {zone_id}",
                f"Applicable state groups: {', '.join(determine_applicable_state_groups(room, zone)) or 'none'}",
                f"Applicable states: {', '.join(determine_applicable_states(room, zone)) or 'none'}",
                "Description:",
                sample.text if sample.text else f"[ERROR] {sample.error or 'unknown generation failure'}",
                "---",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    setup_django()
    zones, room_index, zone_index = build_filtered_zones()
    llm_config = SimpleNamespace(
        llm_enabled=True,
        llm_base_url=os.getenv("LLM_BASE_URL", "http://127.0.0.1:1234"),
        llm_model=os.getenv("LLM_MODEL", "qwen2.5-14b-instruct"),
        llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.5")),
        log_llm_calls=True,
    )
    client = build_llm_client(llm_config)
    samples = asyncio.run(
        generate_samples_from_runtime(
            zones,
            llm_config=llm_config,
            client=client,
            limit=len(ROOM_TARGETS),
            max_tokens=220,
        )
    )
    OUTPUT_PATH.write_text(render_export(samples, room_index, zone_index), encoding="utf-8")
    print(f"Export written to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())