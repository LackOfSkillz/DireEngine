from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.generate_sample_descriptions import (
    build_evaluation_counts,
    collect_repeated_phrases,
    detect_structural_fabrication,
    load_generation_zone,
    setup_django,
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
setup_django()

PHASE2_PATH = Path("exports/sample_descriptions_phase2_real_use_run1.txt")
PHASE3_BATCH1_PATHS = [Path(f"exports/sample_descriptions_phase3_real_use_run{i}.txt") for i in range(1, 5)]
PHASE3_V31_PATHS = [Path(f"exports/sample_descriptions_phase3_v3_1_run{i}.txt") for i in range(1, 5)]
SUMMARY_PATH = Path("exports/sample_descriptions_phase3_v3_1_summary.json")
REPORT_PATH = Path("exports/phase3_v3_1_comparison.md")

ALL_ROOM_IDS = [
    "crossingV2_686_294", "crossingV2_204_360", "crossingV2_350_362", "crossingV2_456_402", "crossingV2_640_546",
    "crossingV2_228_706", "crossingV2_552_238", "crossingV2_318_564", "crossingV2_120_702", "crossingV2_96_918",
    "crossingV2_352_326", "crossingV2_456_430", "crossingV2_606_546", "crossingV2_650_576", "crossingV2_472_564",
    "crossingV2_556_616", "crossingV2_520_642", "crossingV2_64_698", "crossingV2_66_734", "crossingV2_252_536",
]
ATMOSPHERE_TAGGED_ROOM_IDS = [
    "crossingV2_204_360", "crossingV2_120_702", "crossingV2_96_918",
    "crossingV2_352_326", "crossingV2_252_536", "crossingV2_64_698",
]
UNTAGGED_SAMPLE_ROOM_IDS = ["crossingV2_472_564", "crossingV2_686_294", "crossingV2_350_362"]
SPOTCHECK_ROOM_IDS = ["crossingV2_252_536", "crossingV2_96_918", "crossingV2_204_360", "crossingV2_472_564", "crossingV2_318_564"]
ROOM_ATMOSPHERE_KEYWORDS = {
    "crossingV2_204_360": ["cobbled", "stone", "shop", "market", "commerce", "cooking", "dust"],
    "crossingV2_120_702": ["stone", "flagstone", "religious", "genteel", "quiet", "water", "river"],
    "crossingV2_96_918": ["timber", "wood", "planked", "working-class", "working class", "commercial", "tavern", "housing", "cooking", "commerce"],
    "crossingV2_352_326": ["cobbled", "plaster", "shop", "market", "traffic", "commerce", "dust"],
    "crossingV2_252_536": ["timber", "planked", "beam", "residential", "working-class", "working class", "housing", "quiet", "cooking"],
    "crossingV2_64_698": ["cobbled", "plaster", "residential", "working-class", "working class", "housing", "children", "rain"],
}
UNAUTHORIZED_ATMOSPHERE_CUES = [
    "stone", "timber", "wood", "plaster", "brick", "mud", "log", "flagstone", "cobbled", "planked", "earthen",
    "thatched", "slate", "tile", "shop", "market", "tavern", "housing", "warehouse", "dock", "water", "forest",
    "smoke", "cooking", "fish", "tar", "dung", "flowers", "sea", "rain", "dust", "bells", "children", "commerce",
]


def parse_export(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    rooms: dict[str, str] = {}
    current_room_id: str | None = None
    buffer: list[str] = []
    in_body = False
    for line in lines:
        if line.startswith("[Room: "):
            if current_room_id is not None:
                rooms[current_room_id] = "\n".join(buffer).strip()
            current_room_id = line[len("[Room: "):-1]
            buffer = []
            in_body = True
            continue
        if in_body and line == "---":
            rooms[current_room_id] = "\n".join(buffer).strip()
            current_room_id = None
            buffer = []
            in_body = False
            continue
        if in_body:
            buffer.append(line)
    if current_room_id is not None:
        rooms[current_room_id] = "\n".join(buffer).strip()
    return rooms


def count_keywords(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    total = 0
    for keyword in keywords:
        if " " in keyword:
            total += lowered.count(keyword)
        else:
            total += len(re.findall(rf"\b{re.escape(keyword)}\b", lowered))
    return total


def unauthorized_cues(text: str) -> dict[str, int]:
    lowered = text.lower()
    counts: dict[str, int] = {}
    for cue in UNAUTHORIZED_ATMOSPHERE_CUES:
        if " " in cue:
            hits = lowered.count(cue)
        else:
            hits = len(re.findall(rf"\b{re.escape(cue)}\b", lowered))
        if hits:
            counts[cue] = hits
    return counts


def sample_to_eval(rooms: dict[str, str]):
    return [type("Sample", (), {"text": rooms[room_id]})() for room_id in ALL_ROOM_IDS]


def evaluate_run(label: str, rooms: dict[str, str], room_index: dict[str, dict]) -> dict:
    evaluation_counts = build_evaluation_counts(sample_to_eval(rooms))
    structural = {}
    for room_id in ATMOSPHERE_TAGGED_ROOM_IDS:
        structural[room_id] = detect_structural_fabrication(rooms[room_id], room_index[room_id])
    return {
        "run": label,
        "evaluation_counts": evaluation_counts,
        "structural_fabrication_per_room": structural,
    }


def drift_verdict(entry: dict) -> str:
    return "drifted" if entry.get("drifted") else "clean"


def room_structural_counts(evals: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for room_id in ATMOSPHERE_TAGGED_ROOM_IDS:
        counts[room_id] = sum(1 for item in evals if item["structural_fabrication_per_room"][room_id]["has_structural_fabrication"])
    return counts


def build_spotcheck_verdict(room_id: str, text: str, structural: dict, drift_entry: dict | None = None) -> str:
    lowered = text.lower()
    if room_id == "crossingV2_252_536":
        return "failed: still invents structure or exits" if structural.get("has_structural_fabrication") else "passed: remained enclosed"
    if room_id == "crossingV2_96_918":
        return "failed: still invents exits or room shape" if structural.get("has_structural_fabrication") else "passed: exit fabrication stopped"
    if room_id == "crossingV2_204_360":
        rich = any(term in lowered for term in ("cobbled", "commerce", "market", "cooking", "dust", "shop"))
        if structural.get("has_structural_fabrication"):
            return "mixed: retains some atmosphere but still fabricates structure"
        return "passed: retained atmospheric richness" if rich else "failed: tightened prompt sterilized the room"
    if room_id == "crossingV2_472_564":
        return "failed: untagged drift remains" if drift_entry and drift_entry.get("drifted") else "passed: untagged drift removed"
    if room_id == "crossingV2_318_564":
        leaked = any(term in lowered for term in ("hall", "door", "doors"))
        return "failed: banned-noun leak remains" if leaked else "passed: banned-noun leak removed"
    return "reviewed"


zone = load_generation_zone("crossingV2")
room_index = {room["id"]: room for room in zone["rooms"]}
phase2_rooms = parse_export(PHASE2_PATH)
phase3_batch1_runs = {f"run{i}": parse_export(path) for i, path in enumerate(PHASE3_BATCH1_PATHS, start=1)}
phase3_v31_runs = {f"run{i}": parse_export(path) for i, path in enumerate(PHASE3_V31_PATHS, start=1)}

batch1_evals = [evaluate_run(label, rooms, room_index) for label, rooms in phase3_batch1_runs.items()]
v31_evals = [evaluate_run(label, rooms, room_index) for label, rooms in phase3_v31_runs.items()]

batch1_leak_rate = sum(1 for item in batch1_evals if int(item["evaluation_counts"]["noun_violations"]) > 0)
v31_leak_rate = sum(1 for item in v31_evals if int(item["evaluation_counts"]["noun_violations"]) > 0)
batch1_geometry = [item["run"] for item in batch1_evals if int(item["evaluation_counts"]["geometry_violations"]) > 0]
v31_geometry = [item["run"] for item in v31_evals if int(item["evaluation_counts"]["geometry_violations"]) > 0]
v31_second_person_per_run = {item["run"]: int(item["evaluation_counts"]["second_person_violations"]) for item in v31_evals}
v31_player_assumption_per_run = {item["run"]: int(item["evaluation_counts"]["player_assumption_violations"]) for item in v31_evals}

batch1_keyword_hits = {}
v31_keyword_hits = {}
for room_id in ATMOSPHERE_TAGGED_ROOM_IDS:
    keywords = ROOM_ATMOSPHERE_KEYWORDS[room_id]
    batch1_keyword_hits[room_id] = {label: count_keywords(rooms[room_id], keywords) for label, rooms in phase3_batch1_runs.items()}
    v31_keyword_hits[room_id] = {label: count_keywords(rooms[room_id], keywords) for label, rooms in phase3_v31_runs.items()}

batch1_keyword_avg = {room_id: mean(values.values()) for room_id, values in batch1_keyword_hits.items()}
v31_keyword_avg = {room_id: mean(values.values()) for room_id, values in v31_keyword_hits.items()}

batch1_untagged_drift = {}
v31_untagged_drift = {}
for room_id in UNTAGGED_SAMPLE_ROOM_IDS:
    baseline_count = sum(unauthorized_cues(phase2_rooms[room_id]).values())
    batch1_counts = {label: sum(unauthorized_cues(rooms[room_id]).values()) for label, rooms in phase3_batch1_runs.items()}
    v31_counts = {label: sum(unauthorized_cues(rooms[room_id]).values()) for label, rooms in phase3_v31_runs.items()}
    batch1_untagged_drift[room_id] = {"baseline": baseline_count, "runs": batch1_counts, "drifted": any(count > baseline_count for count in batch1_counts.values())}
    v31_untagged_drift[room_id] = {"baseline": baseline_count, "runs": v31_counts, "drifted": any(count > baseline_count for count in v31_counts.values())}

spotchecks = {}
for room_id in SPOTCHECK_ROOM_IDS:
    structural = detect_structural_fabrication(phase3_v31_runs["run1"][room_id], room_index[room_id]) if room_id in room_index else {}
    verdict = build_spotcheck_verdict(room_id, phase3_v31_runs["run1"][room_id], structural, v31_untagged_drift.get(room_id))
    spotchecks[room_id] = {
        "phase2": phase2_rooms[room_id],
        "v31_run1": phase3_v31_runs["run1"][room_id],
        "v31_run1_structural": structural,
        "verdict": verdict,
    }

all_v31_texts = [phase3_v31_runs[label][room_id] for label in phase3_v31_runs for room_id in ALL_ROOM_IDS]
repeated_phrases = collect_repeated_phrases(all_v31_texts, limit=10)
structural_counts = room_structural_counts(v31_evals)
structural_by_run = {item["run"]: item["structural_fabrication_per_room"] for item in v31_evals}

stop_conditions = {
    "banned_noun_leak_rate_above_2_of_4": v31_leak_rate > 2,
    "structural_fabrication_still_present_on_252_536": any(item["structural_fabrication_per_room"]["crossingV2_252_536"]["has_structural_fabrication"] for item in v31_evals),
    "structural_fabrication_still_present_on_96_918": any(item["structural_fabrication_per_room"]["crossingV2_96_918"]["has_structural_fabrication"] for item in v31_evals),
    "tagged_room_keyword_drop_more_than_50_percent": any(v31_keyword_avg[room_id] < (batch1_keyword_avg[room_id] * 0.5) for room_id in ATMOSPHERE_TAGGED_ROOM_IDS),
    "second_person_violations_present": any(v31_second_person_per_run.values()),
}

if stop_conditions["banned_noun_leak_rate_above_2_of_4"] or stop_conditions["structural_fabrication_still_present_on_252_536"] or stop_conditions["structural_fabrication_still_present_on_96_918"]:
    overall_verdict = "Approach not viable at this model size"
elif stop_conditions["tagged_room_keyword_drop_more_than_50_percent"] or stop_conditions["second_person_violations_present"]:
    overall_verdict = "Needs another pass"
else:
    overall_verdict = "Ready to ship Phase 3"

summary = {
    "inputs": {
        "phase2": str(PHASE2_PATH),
        "phase3_batch1_runs": [str(path) for path in PHASE3_BATCH1_PATHS],
        "phase3_v3_1_runs": [str(path) for path in PHASE3_V31_PATHS],
        "tagged_rooms": ATMOSPHERE_TAGGED_ROOM_IDS,
        "untagged_sample_rooms": UNTAGGED_SAMPLE_ROOM_IDS,
        "spotcheck_rooms": SPOTCHECK_ROOM_IDS,
    },
    "comparison": {
        "banned_noun_leak_rate": {
            "phase3_batch1": f"{batch1_leak_rate}/4",
            "phase3_v3_1": f"{v31_leak_rate}/4",
        },
        "geometry_violation_runs": {
            "phase3_batch1": batch1_geometry,
            "phase3_v3_1": v31_geometry,
        },
        "tagged_room_atmosphere_keyword_hits_average": {
            room_id: {
                "phase3_batch1": round(batch1_keyword_avg[room_id], 2),
                "phase3_v3_1": round(v31_keyword_avg[room_id], 2),
            }
            for room_id in ATMOSPHERE_TAGGED_ROOM_IDS
        },
        "untagged_drift": {
            room_id: {
                "phase3_batch1": batch1_untagged_drift[room_id],
                "phase3_v3_1": v31_untagged_drift[room_id],
            }
            for room_id in UNTAGGED_SAMPLE_ROOM_IDS
        },
    },
    "structural_fabrication_per_room": structural_by_run,
    "second_person_violations_per_run": v31_second_person_per_run,
    "player_assumption_violations_per_run": v31_player_assumption_per_run,
    "phase3_v3_1_runs": v31_evals,
    "repeated_phrases_top_10": [{"phrase": phrase, "count": count} for phrase, count in repeated_phrases],
    "spotchecks": spotchecks,
    "stop_conditions": stop_conditions,
    "overall_verdict": overall_verdict,
}

SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

report_lines = [
    "# Phase 3 v3.1 Comparison",
    "",
    f"Overall verdict: {overall_verdict}",
    "",
    "## Compliance metrics",
    f"- Banned-noun leak rate: {batch1_leak_rate}/4 in Phase 3 batch 1 vs {v31_leak_rate}/4 in v3.1.",
    f"- Geometry violations: {batch1_geometry or ['none']} in Phase 3 batch 1 vs {v31_geometry or ['none']} in v3.1.",
    "- Structural fabrication on tagged rooms:",
]
for room_id in ATMOSPHERE_TAGGED_ROOM_IDS:
    report_lines.append(f"  - {room_id}: {structural_counts[room_id]}/4 runs flagged.")
report_lines.extend([
    f"- Second-person violations: {sum(v31_second_person_per_run.values())} total across runs ({v31_second_person_per_run}).",
    f"- Player-assumption violations: {sum(v31_player_assumption_per_run.values())} total across runs ({v31_player_assumption_per_run}).",
    "- Untagged drift sample:",
])
for room_id in UNTAGGED_SAMPLE_ROOM_IDS:
    report_lines.append(f"  - {room_id}: {drift_verdict(v31_untagged_drift[room_id])} in v3.1; batch 1 was {drift_verdict(batch1_untagged_drift[room_id])}.")
report_lines.extend([
    "",
    "## Quality metrics",
    "- Atmospheric keyword hits on tagged rooms:",
])
for room_id in ATMOSPHERE_TAGGED_ROOM_IDS:
    report_lines.append(f"  - {room_id}: {round(batch1_keyword_avg[room_id], 2)} in Phase 3 batch 1 vs {round(v31_keyword_avg[room_id], 2)} in v3.1.")
report_lines.append("- Repeated phrases top 10:")
for phrase, count in repeated_phrases:
    report_lines.append(f"  - {phrase} ({count})")
report_lines.extend([
    "",
    "## Spot checks",
])
for room_id in SPOTCHECK_ROOM_IDS:
    report_lines.append(f"- {room_id}: {spotchecks[room_id]['verdict']}")

REPORT_PATH.write_text("\n".join(report_lines).rstrip() + "\n", encoding="utf-8")

print(json.dumps({
    "summary_path": str(SUMMARY_PATH),
    "report_path": str(REPORT_PATH),
    "phase3_v3_1_banned_noun_leak_rate": f"{v31_leak_rate}/4",
    "phase3_v3_1_geometry_runs": v31_geometry,
    "second_person_violations": v31_second_person_per_run,
    "player_assumption_violations": v31_player_assumption_per_run,
    "structural_fabrication_252_536": stop_conditions["structural_fabrication_still_present_on_252_536"],
    "structural_fabrication_96_918": stop_conditions["structural_fabrication_still_present_on_96_918"],
    "keyword_drop_over_50_percent": stop_conditions["tagged_room_keyword_drop_more_than_50_percent"],
    "overall_verdict": overall_verdict,
}, indent=2))