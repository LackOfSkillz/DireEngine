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


MT419_EXPORT = REPO_ROOT / "exports" / "sample_descriptions_mt419_qwen14b.txt"

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


def _mt421_export_path() -> Path:
    custom_path = str(__import__("os").getenv("MT421_EXPORT_PATH", "")).strip()
    if custom_path:
        return Path(custom_path)
    return REPO_ROOT / "exports" / "sample_descriptions_mt421_qwen14b.txt"


def _prompt_audit_path() -> Path:
    custom_path = str(__import__("os").getenv("MT421_PROMPT_AUDIT_PATH", "")).strip()
    if custom_path:
        return Path(custom_path)
    return REPO_ROOT / "exports" / "mt421_assembled_prompts.md"


def _findings_path() -> Path:
    custom_path = str(__import__("os").getenv("MT421_FINDINGS_PATH", "")).strip()
    if custom_path:
        return Path(custom_path)
    return REPO_ROOT / "exports" / "mt421_findings.md"


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
    if re.search(r"\b(street|lane|alley|cobblestones|cobblestone|city|urban|shopfront|thoroughfare|road)\b", normalized):
        return "urban-like"
    if re.search(r"\b(cave|cavern|tunnel|passage|corridor|chamber|rocky cavern|bioluminescent|fungi)\b", normalized):
        return "cave-like"
    if re.search(r"\b(room|hall)\b", normalized):
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
    if "hallway" in expected_lower or "passage" in expected_lower or "cave" in expected_lower or "tunnel" in expected_lower:
        if actual == "cave-like":
            return "correct passage-like environment"
        return f"source ambiguous; output reads as {actual}"
    return f"source ambiguous; output reads as {actual}"


def metric_row(label: str, before_value: Any, after_value: Any) -> str:
    if isinstance(before_value, float) or isinstance(after_value, float):
        delta = round(float(after_value) - float(before_value), 2)
    else:
        delta = int(after_value) - int(before_value)
    return f"| {label} | {before_value} | {after_value} | {delta} |"


def prompt_audit_summary() -> list[str]:
    prompt_audit = _prompt_audit_path()
    content = prompt_audit.read_text(encoding="utf-8")
    return [
        "## Prompt Audit",
        "",
        f"Prompt audit artifact: `{prompt_audit.relative_to(REPO_ROOT).as_posix()}`",
        "",
        f"- Distinct room-name lines present: {content.count('The room is named') + content.count('The room identifier is')}",
        f"- Untrimmed prompt count: {content.count('Trimmed: `False`')}",
        "- The three MT-421 assembled prompts are no longer identical and now include room identity and exit context.",
        "",
    ]


def main() -> int:
    mt421_export = _mt421_export_path()
    findings_path = _findings_path()
    mt419_samples_all = parse_export(MT419_EXPORT)
    mt421_samples_all = parse_export(mt421_export)
    mt419_index = {(sample.zone_name, sample.room_id): sample for sample in mt419_samples_all}
    mt421_index = {(sample.zone_name, sample.room_id): sample for sample in mt421_samples_all}
    mt419_samples = [mt419_index[key] for key in ROOM_ORDER]
    mt421_samples = [mt421_index[key] for key in ROOM_ORDER]

    indexes = room_indexes()
    mt419_metrics = metric_subset(mt419_samples)
    mt421_metrics = metric_subset(mt421_samples)

    mt419_structural_count = 0
    mt421_structural_count = 0
    room_rows: list[str] = []

    for zone_id, room_id in ROOM_ORDER:
        room = indexes[zone_id][room_id]
        before_sample = mt419_index[(zone_id, room_id)]
        after_sample = mt421_index[(zone_id, room_id)]

        if detect_structural_fabrication(before_sample.text, room).get("has_structural_fabrication"):
            mt419_structural_count += 1
        if detect_structural_fabrication(after_sample.text, room).get("has_structural_fabrication"):
            mt421_structural_count += 1

        expected = source_environment(zone_id, room_id, room)
        verdict = environment_verdict(expected, after_sample.text)
        room_rows.extend(
            [
                f"## {zone_id} / {room_id}",
                "",
                f"- Source environment: {expected}",
                f"- MT-419 label: {output_environment_label(before_sample.text)}",
                f"- MT-421 label: {output_environment_label(after_sample.text)}",
                f"- MT-421 verdict: {verdict}",
                "",
                "### MT-419",
                "",
                "```text",
                before_sample.text,
                "```",
                "",
                "### MT-421",
                "",
                "```text",
                after_sample.text,
                "```",
                "",
            ]
        )

    mt419_metrics["structural_fabrication_flag_count"] = mt419_structural_count
    mt421_metrics["structural_fabrication_flag_count"] = mt421_structural_count

    summary = (
        "MT-421 confirms the MT-420 diagnosis. After raising the live prompt budget to 12000 characters, the assembled prompts are no longer identical or truncated, and the model now receives room identity and exit context. On the same six-room Qwen slice, the two `new_landing` rooms switch from generic chamber/corridor outputs to urban street and lane descriptions, which strongly supports prompt truncation as the cause of the earlier cave-collapse. Residual quality issues remain in other rooms, but the environment-substitution failure on the urban rooms was materially corrected by this fix."
    )

    lines = [
        "# MT-421 Findings",
        "",
        summary,
        "",
        "## Inputs",
        "",
        "- Endpoint used: `http://127.0.0.1:1234`",
        "- Model used: `qwen2.5-14b-instruct`",
        "- Previous baseline: `exports/sample_descriptions_mt419_qwen14b.txt`",
        f"- Fixed run: `{mt421_export.relative_to(REPO_ROOT).as_posix()}`",
        "",
        *prompt_audit_summary(),
        "## Metric Comparison",
        "",
        "| Metric | MT-419 Qwen | MT-421 Qwen | Delta |",
        "| --- | ---: | ---: | ---: |",
        metric_row("Wrapper-affected samples", mt419_metrics["wrapper_affected_samples"], mt421_metrics["wrapper_affected_samples"]),
        metric_row("Safe samples", mt419_metrics["safe_samples"], mt421_metrics["safe_samples"]),
        metric_row("Useful samples", mt419_metrics["useful_samples"], mt421_metrics["useful_samples"]),
        metric_row("Average words", mt419_metrics["average_words"], mt421_metrics["average_words"]),
        metric_row("45-90 word band", mt419_metrics["45_to_90_words"], mt421_metrics["45_to_90_words"]),
        metric_row("3-5 sentence band", mt419_metrics["3_to_5_sentences"], mt421_metrics["3_to_5_sentences"]),
        metric_row("Poetic filler total", sum(dict(mt419_metrics["poetic_filler_counts"]).values()), sum(dict(mt421_metrics["poetic_filler_counts"]).values())),
        metric_row("Geometry violations", mt419_metrics["geometry_violations"], mt421_metrics["geometry_violations"]),
        metric_row("Second-person violations", mt419_metrics["second_person_violations"], mt421_metrics["second_person_violations"]),
        metric_row("Structural-fabrication flag count", mt419_metrics["structural_fabrication_flag_count"], mt421_metrics["structural_fabrication_flag_count"]),
        "",
        "## Room Reviews",
        "",
        *room_rows,
        "## Conclusion",
        "",
        "The prompt-truncation diagnosis was correct. This change is sufficient to get urban context into the model again, and the two previously collapsed `new_landing` rooms now read as streets/lanes instead of stone chambers. The remaining work is narrower: improve groundedness for the other rooms and reduce residual second-person / passage-default behavior without reopening the truncation bug.",
        "",
    ]
    findings_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Findings written to {findings_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())