from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

from tools.generate_sample_descriptions import load_generation_zone, setup_django  # noqa: E402
from world.builder.prompting.room_description_prompt import assemble_room_description_prompt  # noqa: E402


PROMPT_TARGETS = [
    ("new_landing", "amberwick-lane-western-run-4213-4213-4213"),
    ("new_landing", "saltward-street-and-amberwick-lane-4217-4217"),
    ("crossingV2", "crossingV2_178_132"),
]


def _output_path() -> Path:
    custom_path = os.getenv("MT421_PROMPT_AUDIT_PATH", "").strip()
    if custom_path:
        return Path(custom_path)
    return REPO_ROOT / "exports" / "mt421_assembled_prompts.md"


def _max_prompt_chars() -> int:
    raw_value = os.getenv("MT421_PROMPT_AUDIT_MAX_PROMPT_CHARS", "22000").strip()
    return int(raw_value or "22000")


def _room_index(zone_id: str) -> dict[str, dict]:
    zone = load_generation_zone(zone_id)
    return {str(room.get("id") or "").strip(): room for room in list(zone.get("rooms") or [])}


def main() -> int:
    setup_django()
    max_prompt_chars = _max_prompt_chars()
    output_path = _output_path()

    zone_cache: dict[str, dict] = {}
    zone_room_indexes: dict[str, dict[str, dict]] = {}
    for zone_id, _room_id in PROMPT_TARGETS:
        if zone_id in zone_cache:
            continue
        zone_cache[zone_id] = load_generation_zone(zone_id)
        zone_room_indexes[zone_id] = _room_index(zone_id)

    lines = [
        "# MT-421 Assembled Prompts",
        "",
        f"Captured after raising the live prompt budget to {max_prompt_chars} characters.",
        "",
    ]

    for index, (zone_id, room_id) in enumerate(PROMPT_TARGETS, start=1):
        zone = zone_cache[zone_id]
        room = zone_room_indexes[zone_id][room_id]
        prompt = assemble_room_description_prompt(room, zone, max_prompt_chars=max_prompt_chars)
        room_name = str(room.get("name") or room_id).strip() or room_id

        lines.extend(
            [
                f"## {index}. {zone_id} / {room_id}",
                "",
                f"Room name field: `{room_name}`",
                "",
                f"Trimmed: `{prompt.trimmed}`",
                "",
                "```text",
                prompt.prompt,
                "```",
                "",
            ]
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Prompt audit written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())