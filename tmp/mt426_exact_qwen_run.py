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
    build_evaluation_counts,
    build_llm_client,
    collect_repeated_phrases,
    format_export,
    generate_samples_from_runtime,
    load_generation_zone,
    setup_django,
)


ROOM_TARGETS = {
    "demo1": ["CRO_500_100", "CRO_500_150"],
    "crossingV2": ["crossingV2_192_132", "crossingV2_178_132"],
    "new_landing": ["amberwick-lane-western-run-4213-4213-4213", "saltward-street-and-amberwick-lane-4217-4217"],
}
OUTPUT_PATH = REPO_ROOT / "exports" / "sample_descriptions_mt426_qwen14b.txt"


def build_filtered_zones() -> list[dict]:
    zones: list[dict] = []
    for zone_id, room_ids in ROOM_TARGETS.items():
        zone = load_generation_zone(zone_id)
        room_map = {str(room.get("id") or "").strip(): room for room in list(zone.get("rooms") or [])}
        filtered_zone = dict(zone)
        filtered_zone["rooms"] = [room_map[room_id] for room_id in room_ids]
        zones.append(filtered_zone)
    return zones


def main() -> int:
    setup_django()
    zones = build_filtered_zones()
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
            limit=6,
            max_tokens=140,
        )
    )
    repeated_phrases = collect_repeated_phrases([sample.text for sample in samples if sample.text])
    evaluation_counts = build_evaluation_counts(samples)
    OUTPUT_PATH.write_text(format_export(samples, repeated_phrases, evaluation_counts), encoding="utf-8")
    print(f"Export written to {OUTPUT_PATH}")
    print([sample.room_id for sample in samples])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())