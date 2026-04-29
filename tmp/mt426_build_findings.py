from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.generate_sample_descriptions import (  # noqa: E402
    WRAPPER_LEAKAGE_PATTERNS,
    build_evaluation_counts,
    count_pattern_violations,
    detect_structural_fabrication,
    load_generation_zone,
    setup_django,
)
from world.builder.prompting.room_description_prompt import PROMPT_VERSION  # noqa: E402


MT426_EXPORT = REPO_ROOT / "exports" / "sample_descriptions_mt426_qwen14b.txt"
FINDINGS_PATH = REPO_ROOT / "exports" / "mt426_findings.md"
ROOM_ORDER = [
    ("demo1", "CRO_500_100"),
    ("demo1", "CRO_500_150"),
    ("crossingV2", "crossingV2_192_132"),
    ("crossingV2", "crossingV2_178_132"),
    ("new_landing", "amberwick-lane-western-run-4213-4213-4213"),
    ("new_landing", "saltward-street-and-amberwick-lane-4217-4217"),
]

PRIOR_FAILURE_CHECKS = {
    "CRO_500_150": [
        ("room-id leakage", [r"\bCRO_500_100\b", r"\bCRO_500_150\b"]),
    ],
    "crossingV2_192_132": [
        ("invented atmosphere", [r"\bfish\b", r"\bspices\b", r"\bmerchants? hawking\b"]),
    ],
    "crossingV2_178_132": [
        ("tavern hallucination", [r"\bhearth\b", r"\bbeams?\b", r"\bale\b", r"\bpatrons?\b"]),
    ],
}

GLOBAL_FAILURE_CHECKS = [
    ("banned phrase: the air is thick with", [r"\bthe air is thick with\b"]),
    ("banned phrase: in the heart of", [r"\bin the heart of\b"]),
    ("second-person", [r"\byou\b", r"\byour\b", r"\bas you\b"]),
]


@dataclass(frozen=True)
class ExportSample:
    zone_name: str
    room_id: str
    text: str


def parse_export(path: Path) -> list[ExportSample]:
    lines = path.read_text(encoding="utf-8").splitlines()
    samples: list[ExportSample] = []
    zone_name = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("=== Zone: ") and line.endswith(" ==="):
            zone_name = line[len("=== Zone: ") : -len(" ===")]
            index += 1
            continue
        if line == "Repeated phrases:":
            while index < len(lines) and not (lines[index].startswith("=== Zone: ") and lines[index].endswith(" ===")):
                index += 1
            continue
        if line.startswith("[Room: ") and line.endswith("]"):
            room_id = line[len("[Room: ") : -1]
            index += 1
            body: list[str] = []
            while index < len(lines) and lines[index] != "---":
                body.append(lines[index])
                index += 1
            samples.append(ExportSample(zone_name=zone_name, room_id=room_id, text="\n".join(body).strip()))
        index += 1
    return samples


def room_indexes() -> dict[str, dict[str, dict[str, Any]]]:
    setup_django()
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for zone_id in {zone_id for zone_id, _ in ROOM_ORDER}:
        zone = load_generation_zone(zone_id)
        indexes[zone_id] = {str(room.get("id") or ""): room for room in list(zone.get("rooms") or [])}
    return indexes


def metric_subset(samples: list[ExportSample], indexes: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    successful_samples = [sample for sample in samples if not sample.text.startswith("[ERROR]")]
    sample_objects = [type("Sample", (), {"text": sample.text})() for sample in successful_samples]
    metrics = build_evaluation_counts(sample_objects)
    metrics["total_samples"] = len(samples)
    metrics["successful_samples"] = len(successful_samples)
    metrics["error_outputs"] = len(samples) - len(successful_samples)
    metrics["wrapper_affected_samples"] = sum(
        1 for sample in successful_samples if count_pattern_violations([sample.text], WRAPPER_LEAKAGE_PATTERNS) > 0
    )
    metrics["poetic_filler_total"] = sum(dict(metrics.get("poetic_filler_counts") or {}).values())
    metrics["structural_fabrication_flag_count"] = sum(
        1
        for sample in successful_samples
        if detect_structural_fabrication(sample.text, indexes[sample.zone_name][sample.room_id]).get("has_structural_fabrication")
    )
    return metrics


def check_patterns(text: str, patterns: list[str]) -> dict[str, int]:
    hits: dict[str, int] = {}
    for pattern in patterns:
        count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        if count:
            hits[pattern] = count
    return hits


def room_failure_checks(room_id: str, text: str) -> list[tuple[str, str, dict[str, int]]]:
    checks: list[tuple[str, str, dict[str, int]]] = []
    for label, patterns in PRIOR_FAILURE_CHECKS.get(room_id, []):
        hits = check_patterns(text, patterns)
        checks.append((label, "recurred" if hits else "suppressed", hits))
    for label, patterns in GLOBAL_FAILURE_CHECKS:
        hits = check_patterns(text, patterns)
        checks.append((label, "recurred" if hits else "suppressed", hits))
    return checks


def metric_row(label: str, value: Any) -> str:
    return f"| {label} | {value} |"


def main() -> int:
    samples_all = parse_export(MT426_EXPORT)
    sample_index = {(sample.zone_name, sample.room_id): sample for sample in samples_all}
    samples = [sample_index[key] for key in ROOM_ORDER]
    indexes = room_indexes()
    metrics = metric_subset(samples, indexes)

    summary = (
        "MT-426 ran a single six-room validation pass after suppressing room-ID leakage in the prompt assembly, "
        "using Qwen 2.5 14B Instruct at temperature 0.5 on the live LM Studio endpoint. The report below checks "
        "the specific leakage fix and preserves the same room-by-room review format used in MT-425."
    )

    lines = [
        "# MT-426 Findings",
        "",
        summary,
        "",
        "## Inputs",
        "",
        "- Endpoint: `http://127.0.0.1:1234`",
        "- Model: `qwen2.5-14b-instruct`",
        "- Temperature: `0.5`",
        f"- Prompt version: `{PROMPT_VERSION}`",
        "- Export: `exports/sample_descriptions_mt426_qwen14b.txt`",
        "- Passes: `1`",
        "",
        "## Standard Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        metric_row("successful outputs", f"{metrics['successful_samples']}/{metrics['total_samples']}"),
        metric_row("request failures", metrics["error_outputs"]),
        metric_row("safe", f"{metrics['safe_samples']}/{metrics['successful_samples']}" if metrics["successful_samples"] else "0/0"),
        metric_row("useful", f"{metrics['useful_samples']}/{metrics['successful_samples']}" if metrics["successful_samples"] else "0/0"),
        metric_row("wrapper", metrics["wrapper_affected_samples"]),
        metric_row("average words", metrics["average_words"]),
        metric_row("under 45 words", metrics["under_45_words"]),
        metric_row("45-90 words", metrics["45_to_90_words"]),
        metric_row("over 90 words", metrics["over_90_words"]),
        metric_row("average sentences", metrics["average_sentences"]),
        metric_row("under 3 sentences", metrics["under_3_sentences"]),
        metric_row("3-5 sentences", metrics["3_to_5_sentences"]),
        metric_row("over 5 sentences", metrics["over_5_sentences"]),
        metric_row("geometry violations", metrics["geometry_violations"]),
        metric_row("second-person violations", metrics["second_person_violations"]),
        metric_row("structural-fabrication flag count", metrics["structural_fabrication_flag_count"]),
        metric_row("poetic filler total", metrics["poetic_filler_total"]),
        "",
        "## Room Reviews",
        "",
    ]

    for zone_id, room_id in ROOM_ORDER:
        sample = sample_index[(zone_id, room_id)]
        checks = room_failure_checks(room_id, sample.text)
        lines.extend(
            [
                f"## {zone_id} / {room_id}",
                "",
                "### Full Output",
                "",
                "```text",
                sample.text,
                "```",
                "",
                "### Prior Failure Check",
                "",
            ]
        )
        for label, verdict, hits in checks:
            if hits:
                hit_summary = ", ".join(f"`{pattern}` x{count}" for pattern, count in hits.items())
                lines.append(f"- {label}: {verdict} ({hit_summary})")
            else:
                lines.append(f"- {label}: {verdict}")
        lines.append("")

    lines.extend(
        [
            "## Conclusion",
            "",
            "This report is single-pass only. Use the room-by-room checks above to confirm that identifier leakage is gone while comparing the qualitative outputs against MT-425.",
            "",
        ]
    )

    FINDINGS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Findings written to {FINDINGS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())