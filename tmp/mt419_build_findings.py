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
    SECOND_PERSON_PATTERNS,
    WRAPPER_LEAKAGE_PATTERNS,
    build_evaluation_counts,
    count_pattern_violations,
    detect_structural_fabrication,
    load_generation_zone,
    setup_django,
)


QWEN_EXPORT = REPO_ROOT / "exports" / "sample_descriptions_mt419_qwen14b.txt"
MT417_EXPORT = REPO_ROOT / "exports" / "sample_descriptions_mt417_run1.txt"
PHASE_A_REPORT = REPO_ROOT / "tmp" / "mt419_phase_a_room_data.md"
FINDINGS_PATH = REPO_ROOT / "exports" / "mt419_findings.md"

ROOM_ORDER = [
    ("demo1", "CRO_500_100"),
    ("demo1", "CRO_500_150"),
    ("crossingV2", "crossingV2_192_132"),
    ("crossingV2", "crossingV2_178_132"),
    ("new_landing", "amberwick-lane-western-run-4213-4213-4213"),
    ("new_landing", "saltward-street-and-amberwick-lane-4217-4217"),
]

NEW_LANDING_EXPECTED = {
    "amberwick-lane-western-run-4213-4213-4213": "urban lane in a city; raw YAML has environment: city and no tags.structure",
    "saltward-street-and-amberwick-lane-4217-4217": "urban street intersection in a city; raw YAML has environment: city and no tags.structure",
}


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


def metric_subset(samples: list[ExportSample]) -> dict[str, Any]:
    sample_objects = [type("Sample", (), {"text": sample.text})() for sample in samples]
    metrics = build_evaluation_counts(sample_objects)
    metrics["wrapper_affected_samples"] = sum(
        1 for sample in samples if count_pattern_violations([sample.text], WRAPPER_LEAKAGE_PATTERNS) > 0
    )
    metrics["structural_fabrication_flag_count"] = 0
    return metrics


def room_indexes() -> dict[str, dict[str, dict[str, Any]]]:
    setup_django()
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for zone_id in {zone_id for zone_id, _ in ROOM_ORDER}:
        zone = load_generation_zone(zone_id)
        indexes[zone_id] = {str(room.get("id") or ""): room for room in list(zone.get("rooms") or [])}
    return indexes


def source_environment(zone_id: str, room_id: str, room: dict[str, Any]) -> str:
    if zone_id == "new_landing" and room_id in NEW_LANDING_EXPECTED:
        return NEW_LANDING_EXPECTED[room_id]
    tags = dict(room.get("tags") or {})
    structure = str(tags.get("structure") or "").strip()
    environment = str(room.get("environment") or "").strip()
    if structure:
        return f"structure tag: {structure}"
    if environment:
        return f"environment: {environment}"
    return "no explicit structure tag in loaded room data"


def output_environment_label(text: str) -> str:
    normalized = str(text or "").lower()
    if re.search(r"\b(cave|cavern|tunnel|passage|corridor|rocky cavern|bioluminescent|fungi)\b", normalized):
        return "cave-like"
    if re.search(r"\b(street|lane|shopfront|cobbles|paving stones|city|urban|facades)\b", normalized):
        return "urban-like"
    if re.search(r"\b(room|chamber|hall)\b", normalized):
        return "generic enclosed room"
    return "unclear"


def environment_verdict(expected: str, text: str) -> str:
    actual = output_environment_label(text)
    expected_lower = expected.lower()
    if "city" in expected_lower or "street" in expected_lower or "lane" in expected_lower or "urban" in expected_lower:
        if actual == "urban-like":
            return "correct urban environment"
        if actual == "cave-like":
            return "incorrect: substituted cave environment"
        return "incorrect: missed urban environment"
    if "cave" in expected_lower or "passage" in expected_lower or "tunnel" in expected_lower:
        if actual == "cave-like":
            return "correct cave environment"
        return "incorrect: missed cave environment"
    return f"source ambiguous; output reads as {actual}"


def metric_row(label: str, mt417_value: Any, mt419_value: Any) -> str:
    if isinstance(mt417_value, float) or isinstance(mt419_value, float):
        delta = round(float(mt419_value) - float(mt417_value), 2)
    else:
        delta = int(mt419_value) - int(mt417_value)
    return f"| {label} | {mt417_value} | {mt419_value} | {delta} |"


def main() -> int:
    qwen_samples_all = parse_export(QWEN_EXPORT)
    mt417_samples_all = parse_export(MT417_EXPORT)
    qwen_index = {(sample.zone_name, sample.room_id): sample for sample in qwen_samples_all}
    mt417_index = {(sample.zone_name, sample.room_id): sample for sample in mt417_samples_all}
    qwen_samples = [qwen_index[key] for key in ROOM_ORDER]
    mt417_samples = [mt417_index[key] for key in ROOM_ORDER]

    indexes = room_indexes()
    qwen_metrics = metric_subset(qwen_samples)
    mt417_metrics = metric_subset(mt417_samples)

    structural_count = 0
    room_rows: list[str] = []
    for zone_id, room_id in ROOM_ORDER:
        room = indexes[zone_id][room_id]
        qwen_sample = qwen_index[(zone_id, room_id)]
        structural = detect_structural_fabrication(qwen_sample.text, room)
        if structural.get("has_structural_fabrication"):
            structural_count += 1
        expected = source_environment(zone_id, room_id, room)
        verdict = environment_verdict(expected, qwen_sample.text)
        room_rows.extend(
            [
                f"## {zone_id} / {room_id}",
                "",
                f"- Source environment: {expected}",
                f"- Environment verdict: {verdict}",
                "",
                "```text",
                qwen_sample.text,
                "```",
                "",
            ]
        )

    qwen_metrics["structural_fabrication_flag_count"] = structural_count
    mt417_structural_count = 0
    for zone_id, room_id in ROOM_ORDER:
        room = indexes[zone_id][room_id]
        mt417_sample = mt417_index[(zone_id, room_id)]
        structural = detect_structural_fabrication(mt417_sample.text, room)
        if structural.get("has_structural_fabrication"):
            mt417_structural_count += 1
    mt417_metrics["structural_fabrication_flag_count"] = mt417_structural_count

    summary = (
        "Phase A shows the checked `new_landing` YAML entries are urban `environment: city` rooms with no "
        "`tags.structure` or `atmosphere.materials` block, so the raw YAML did not encode the MT-417 cave collapse. "
        "Phase C shows Qwen 2.5 removed wrapper leakage on this six-room slice entirely, but it did not preserve environment "
        "context reliably: the two `new_landing` urban rooms still failed to read as streets/lanes, and other rooms were often "
        "recast as generic chambers, corridors, or cave-like spaces. The next step should be to investigate prompt/input structure "
        "and room-data shaping before committing to Qwen as a drop-in replacement."
    )

    lines = [
        "# MT-419 Findings",
        "",
        summary,
        "",
        "## Inputs",
        "",
        "- Endpoint used: `http://127.0.0.1:1234`",
        "- Model used: `qwen2.5-14b-instruct`",
        "- Phase A report: `tmp/mt419_phase_a_room_data.md`",
        "- Qwen export: `exports/sample_descriptions_mt419_qwen14b.txt`",
        "- MT-417 comparison source: `exports/sample_descriptions_mt417_run1.txt` filtered to the same 6 rooms",
        "",
        "## Phase A Verdict",
        "",
        "Finding A2 applies for the checked `new_landing` rooms. The raw YAML is urban and does not encode `cave-passage` in the requested fields.",
        "",
        "## Metric Comparison",
        "",
        "| Metric | MT-417 Slice | MT-419 Qwen | Delta |",
        "| --- | ---: | ---: | ---: |",
        metric_row("Wrapper-affected samples", mt417_metrics["wrapper_affected_samples"], qwen_metrics["wrapper_affected_samples"]),
        metric_row("Safe samples", mt417_metrics["safe_samples"], qwen_metrics["safe_samples"]),
        metric_row("Useful samples", mt417_metrics["useful_samples"], qwen_metrics["useful_samples"]),
        metric_row("Average words", mt417_metrics["average_words"], qwen_metrics["average_words"]),
        metric_row("45-90 word band", mt417_metrics["45_to_90_words"], qwen_metrics["45_to_90_words"]),
        metric_row("3-5 sentence band", mt417_metrics["3_to_5_sentences"], qwen_metrics["3_to_5_sentences"]),
        metric_row("Poetic filler total", sum(dict(mt417_metrics["poetic_filler_counts"]).values()), sum(dict(qwen_metrics["poetic_filler_counts"]).values())),
        metric_row("Geometry violations", mt417_metrics["geometry_violations"], qwen_metrics["geometry_violations"]),
        metric_row("Second-person violations", mt417_metrics["second_person_violations"], qwen_metrics["second_person_violations"]),
        metric_row("Structural-fabrication flag count", mt417_metrics["structural_fabrication_flag_count"], qwen_metrics["structural_fabrication_flag_count"]),
        "",
        "## Room Reviews",
        "",
        *room_rows,
        "## Recommendation",
        "",
        "Qwen is better than MT-417 on wrapper control for this slice, but it is not yet shippable as-is because environment preservation is still unstable and structural fabrication remains present. The next move should be input/prompt-structure investigation, especially how source room identity is represented before the model sees it, rather than more blind model iteration.",
        "",
    ]
    FINDINGS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Findings written to {FINDINGS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())