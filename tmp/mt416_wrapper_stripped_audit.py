from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.generate_sample_descriptions import (
    FABRICATION_WATCHLIST_TERMS,
    META_MECHANICS_PATTERNS,
    POETIC_FILLER_PHRASES,
    SECOND_PERSON_PATTERNS,
    STUB_PHRASES,
    WRAPPER_LEAKAGE_PATTERNS,
    classify_sentence_count_bucket,
    classify_word_count_bucket,
    count_geometry_flags,
    count_pattern_violations,
    count_phrase_group,
    detect_structural_fabrication,
    is_single_paragraph,
    load_generation_zone,
    sample_is_safe,
    sample_is_useful,
    sentence_count,
    setup_django,
    word_count,
)


EXPORT_PATH = Path("exports/sample_descriptions_mt415.txt")
OUTPUT_PATH = Path("exports/mt415_wrapper_stripped_audit.md")

GENERIC_STERILE_PATTERNS = (
    r"\bthe room is\b",
    r"\bthis room is\b",
    r"\bthe walls are bare\b",
    r"\bthe floor is\b",
    r"\bworn smooth\b",
    r"\bcool to the touch\b",
    r"\bfaint,? musty smell\b",
    r"\bfaint scent\b",
    r"\bdim light\b",
    r"\brough[- ]hewn\b",
)
MINOR_WORD_LOW = 40
MINOR_WORD_HIGH = 100


@dataclass(frozen=True)
class ExportSample:
    zone_name: str
    room_id: str
    original_text: str


def parse_export(path: Path) -> list[ExportSample]:
    lines = path.read_text(encoding="utf-8").splitlines()
    samples: list[ExportSample] = []
    current_zone = ""
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("=== Zone: ") and line.endswith(" ==="):
            current_zone = line[len("=== Zone: ") : -len(" ===")]
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
            samples.append(ExportSample(zone_name=current_zone, room_id=room_id, original_text="\n".join(body).strip()))
        index += 1
    return samples


def room_lookup(samples: list[ExportSample]) -> dict[tuple[str, str], dict[str, Any]]:
    setup_django()
    zone_ids = sorted({sample.zone_name for sample in samples})
    rooms: dict[tuple[str, str], dict[str, Any]] = {}
    for zone_id in zone_ids:
        zone = load_generation_zone(zone_id)
        for room in list(zone.get("rooms") or []):
            room_id = str(room.get("id") or "").strip()
            if room_id:
                rooms[(zone_id, room_id)] = room
    return rooms


def strip_wrapper(text: str) -> tuple[str, list[str]]:
    stripped_lines: list[str] = []
    kept_lines: list[str] = []
    label_pattern = re.compile(
        r"^(Room Data|Atmospheric Tags(?: \(present\))?|Room Description|Description|Structure|Structural Tags|Materials|Tags|Exits?|Exit Count|Exit Directions|Exit Data|Upkeep|Sensory|Surroundings)\s*:\s*(.*)$",
        flags=re.IGNORECASE,
    )
    for raw_line in str(text or "").splitlines():
        working = raw_line.strip()
        if not working:
            continue
        if re.fullmatch(r"#{1,6}\s+.+", working):
            stripped_lines.append(raw_line)
            continue
        if re.fullmatch(r"\*\*[^\n*]+\*\*:?,?", working):
            stripped_lines.append(raw_line)
            continue
        if re.match(r"^[-*]\s+", working):
            stripped_lines.append(raw_line)
            continue
        label_match = label_pattern.match(working)
        if label_match:
            remainder = label_match.group(2).strip()
            if remainder and re.search(r"[.!?]", remainder):
                stripped_lines.append(f"{label_match.group(1)}:")
                kept_lines.append(remainder)
            else:
                stripped_lines.append(raw_line)
            continue
        kept_lines.append(working)
    stripped = re.sub(r"\s+", " ", " ".join(kept_lines)).strip()
    return stripped, stripped_lines


def sterile_pattern_hits(text: str) -> list[str]:
    normalized = str(text or "").lower()
    hits: list[str] = []
    for pattern in GENERIC_STERILE_PATTERNS:
        if re.search(pattern, normalized):
            hits.append(pattern)
    return hits


def original_verdict(text: str) -> str:
    return f"safe={sample_is_safe(text)}, useful={sample_is_useful(text)}"


def stripped_verdict(text: str, *, second_person: int, geometry_total: int, structural_flag: bool) -> str:
    return (
        f"safe={sample_is_safe(text)}, useful={sample_is_useful(text)}, second_person={second_person}, "
        f"geometry={geometry_total}, structural={structural_flag}"
    )


def classify_sample(
    stripped_text: str,
    *,
    second_person: int,
    geometry_total: int,
    structural_flag: bool,
    sterile_hits: list[str],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    safe = sample_is_safe(stripped_text)
    useful = sample_is_useful(stripped_text)
    words = word_count(stripped_text)
    sentences = sentence_count(stripped_text)

    if not stripped_text:
        return "not shippable", ["empty after conservative stripping"]
    if not is_single_paragraph(stripped_text):
        reasons.append("not single paragraph")
    if second_person > 0:
        reasons.append("second-person remains")
    if geometry_total > 0:
        reasons.append("unsupported geometry remains")
    if structural_flag:
        reasons.append("possible unsupported structural detail remains")
    if sterile_hits:
        reasons.append("passes mechanically but reads generic/sterile")

    if useful and second_person == 0 and geometry_total == 0 and not structural_flag and not sterile_hits:
        return "shippable", reasons

    minor_useful_miss = False
    if safe and second_person == 0 and geometry_total == 0 and not structural_flag:
        if not useful:
            if classify_word_count_bucket(stripped_text) != "45_to_90_words" and MINOR_WORD_LOW <= words <= MINOR_WORD_HIGH:
                minor_useful_miss = True
            elif classify_sentence_count_bucket(stripped_text) != "3_to_5_sentences" and sentences in (2, 6):
                minor_useful_miss = True
        elif sterile_hits:
            minor_useful_miss = True

    if safe and (useful or minor_useful_miss) and second_person == 0 and geometry_total == 0 and not structural_flag:
        return "almost-shippable", reasons

    if not safe:
        reasons.append("fails safe rubric after stripping")
    if safe and not useful and not minor_useful_miss:
        reasons.append("fails useful rubric beyond minor tolerance")
    return "not shippable", reasons


def render_report(rows: list[dict[str, Any]]) -> str:
    counts = {
        "shippable": sum(1 for row in rows if row["classification"] == "shippable"),
        "almost-shippable": sum(1 for row in rows if row["classification"] == "almost-shippable"),
        "not shippable": sum(1 for row in rows if row["classification"] == "not shippable"),
    }
    viable = counts["shippable"] + counts["almost-shippable"]
    if viable >= 12:
        recommendation = "Parser-path is viable; consider pivoting MT-417 to a real parser implementation rather than further prompt iteration."
    elif viable >= 7:
        recommendation = "Parser-path is marginal; human review of the actual prose should decide between parser-path and further prompt iteration."
    else:
        recommendation = "Parser-path does not unlock enough quality by itself; continued prompt iteration or a revised diagnosis is justified."

    lines: list[str] = [
        "# MT-415 Wrapper-Stripped Audit",
        "",
        f"Shippable: {counts['shippable']}/17",
        f"Almost-shippable: {counts['almost-shippable']}/17",
        f"Not shippable: {counts['not shippable']}/17",
        "",
        f"Recommendation: {recommendation}",
        "",
        "## Sample Table",
        "",
        "| Zone | Room | Original words | Stripped words | Original verdict | Stripped verdict | Classification | Sterile flag |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['zone_name']} | {row['room_id']} | {row['original_words']} | {row['stripped_words']} | "
            f"{row['original_verdict']} | {row['stripped_verdict']} | {row['classification']} | {row['sterile_flag']} |"
        )

    lines.extend(["", "## Sample Details", ""])
    for row in rows:
        lines.append(f"### {row['zone_name']} / {row['room_id']}")
        lines.append("")
        lines.append(f"- Classification: {row['classification']}")
        lines.append(f"- Original verdict: {row['original_verdict']}")
        lines.append(f"- Stripped verdict: {row['stripped_verdict']}")
        lines.append(f"- Stripped items: {', '.join(row['stripped_lines']) if row['stripped_lines'] else 'none'}")
        lines.append(f"- Notes: {', '.join(row['reasons']) if row['reasons'] else 'none'}")
        lines.append("")

    for classification in ("shippable", "almost-shippable", "not shippable"):
        lines.extend([f"## Examples: {classification}", ""])
        selected = [row for row in rows if row["classification"] == classification][:3]
        if not selected:
            lines.append("No samples in this classification.")
            lines.append("")
            continue
        for row in selected:
            lines.append(f"### {row['zone_name']} / {row['room_id']}")
            lines.append("")
            lines.append("Original:")
            lines.append("")
            lines.append("```text")
            lines.append(row["original_text"])
            lines.append("```")
            lines.append("")
            lines.append("Stripped:")
            lines.append("")
            lines.append("```text")
            lines.append(row["stripped_text"] or "[empty after stripping]")
            lines.append("```")
            lines.append("")
            lines.append(f"Notes: {', '.join(row['reasons']) if row['reasons'] else 'none'}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    samples = parse_export(EXPORT_PATH)
    rooms = room_lookup(samples)
    rows: list[dict[str, Any]] = []
    for sample in samples:
        stripped_text, stripped_lines = strip_wrapper(sample.original_text)
        room = rooms.get((sample.zone_name, sample.room_id), {})
        structural_findings = detect_structural_fabrication(stripped_text, room) if room else {"has_structural_fabrication": False}
        second_person = count_pattern_violations([stripped_text], SECOND_PERSON_PATTERNS)
        geometry_total = sum(count_geometry_flags([stripped_text]).values())
        sterile_hits = sterile_pattern_hits(stripped_text)
        classification, reasons = classify_sample(
            stripped_text,
            second_person=second_person,
            geometry_total=geometry_total,
            structural_flag=bool(structural_findings.get("has_structural_fabrication")),
            sterile_hits=sterile_hits,
        )
        row = {
            "zone_name": sample.zone_name,
            "room_id": sample.room_id,
            "original_text": sample.original_text,
            "stripped_text": stripped_text,
            "original_words": word_count(sample.original_text),
            "stripped_words": word_count(stripped_text),
            "original_verdict": original_verdict(sample.original_text),
            "stripped_verdict": stripped_verdict(
                stripped_text,
                second_person=second_person,
                geometry_total=geometry_total,
                structural_flag=bool(structural_findings.get("has_structural_fabrication")),
            ),
            "classification": classification,
            "sterile_flag": "yes" if sterile_hits else "no",
            "stripped_lines": [line.strip() for line in stripped_lines if line.strip()],
            "reasons": reasons,
        }
        rows.append(row)

    OUTPUT_PATH.write_text(render_report(rows), encoding="utf-8")
    print(f"Audit written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()