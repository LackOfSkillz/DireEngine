from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.generate_sample_descriptions import (
    build_evaluation_counts,
    build_llm_client,
    collect_repeated_phrases,
    format_export,
    generate_samples_from_runtime,
    load_generation_zone,
    setup_django,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
setup_django()

from world.builder.services.llm_client import BuilderLLMConfig

ROOM_IDS = [
    "crossingV2_686_294", "crossingV2_204_360", "crossingV2_350_362", "crossingV2_456_402", "crossingV2_640_546",
    "crossingV2_228_706", "crossingV2_552_238", "crossingV2_318_564", "crossingV2_120_702", "crossingV2_96_918",
    "crossingV2_352_326", "crossingV2_456_430", "crossingV2_606_546", "crossingV2_650_576", "crossingV2_472_564",
    "crossingV2_556_616", "crossingV2_520_642", "crossingV2_64_698", "crossingV2_66_734", "crossingV2_252_536",
]


def main() -> int:
    zone = load_generation_zone("crossingV2")
    room_index = {room["id"]: room for room in zone["rooms"]}
    filtered_zone = dict(zone)
    filtered_zone["rooms"] = [room_index[room_id] for room_id in ROOM_IDS]

    config = BuilderLLMConfig(
        llm_enabled=True,
        llm_base_url="http://127.0.0.1:1234",
        llm_model="mistral-nemo-12b-instruct",
        llm_temperature=0.5,
        log_llm_calls=True,
    )

    for run_number in range(1, 5):
        client = build_llm_client(config)
        samples = asyncio.run(
            generate_samples_from_runtime(
                [filtered_zone],
                llm_config=config,
                client=client,
                limit=len(ROOM_IDS),
                max_tokens=140,
            )
        )
        repeated_phrases = collect_repeated_phrases([sample.text for sample in samples if sample.text])
        evaluation_counts = build_evaluation_counts(samples)
        content = format_export(samples, repeated_phrases, evaluation_counts)
        output_path = REPO_ROOT / "exports" / f"sample_descriptions_phase3_v3_1_run{run_number}.txt"
        output_path.write_text(content, encoding="utf-8")
        print(f"wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())