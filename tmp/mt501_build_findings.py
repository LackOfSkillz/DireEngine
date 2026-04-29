from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.generate_sample_descriptions import load_generation_zone, setup_django  # noqa: E402
from world.builder.prompting.room_description_prompt import determine_applicable_states  # noqa: E402


EXPORT_PATH = REPO_ROOT / "exports" / "mt501_stateful_test.txt"
FINDINGS_PATH = REPO_ROOT / "exports" / "mt501_findings.md"
ROOM_TARGETS = [
    ("crossingV2", "crossingV2_192_132"),
    ("crossingV2", "crossingV2_178_132"),
    ("demo1", "CRO_500_100"),
]
STATE_GROUPS = {
    "morning": "time",
    "midday": "time",
    "evening": "time",
    "night": "time",
    "spring": "season",
    "summer": "season",
    "autumn": "season",
    "winter": "season",
    "rain": "weather",
    "snow": "weather",
    "fog": "weather",
    "invasion": "invasion",
    "dark": "room",
    "flooded": "room",
    "burning": "room",
}
PERMANENT_FEATURE_TERMS = {"north", "south", "east", "west", "up", "down", "exit", "exits", "layout", "building", "buildings", "lane", "street", "hallway", "passage"}


@dataclass(frozen=True)
class ExportSample:
    zone_id: str
    room_id: str
    applicable_states: list[str]
    text: str


def parse_export(path: Path) -> list[ExportSample]:
    lines = path.read_text(encoding="utf-8").splitlines()
    samples: list[ExportSample] = []
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line.startswith("[Room: "):
            index += 1
            continue
        room_id = line[len("[Room: ") : -1]
        zone_id = ""
        applicable_states: list[str] = []
        description = ""
        index += 1
        while index < len(lines) and lines[index].strip() != "---":
            current = lines[index]
            if current.startswith("Zone: "):
                zone_id = current[len("Zone: ") :].strip()
            elif current.startswith("Applicable states: "):
                raw = current[len("Applicable states: ") :].strip()
                applicable_states = [item.strip() for item in raw.split(",") if item.strip() and raw != "none"]
            elif current == "Description:" and index + 1 < len(lines):
                description = lines[index + 1].strip()
                index += 1
            index += 1
        samples.append(ExportSample(zone_id=zone_id, room_id=room_id, applicable_states=applicable_states, text=description))
        index += 1
    return samples


def parse_state_fragments(text: str) -> tuple[list[dict[str, object]], list[str]]:
    fragments: list[dict[str, object]] = []
    errors: list[str] = []
    index = 0
    while index < len(text):
        start = text.find("$state(", index)
        if start == -1:
            break
        cursor = start + len("$state(")
        depth = 1
        comma_index: int | None = None
        end_index: int | None = None
        while cursor < len(text):
            character = text[cursor]
            if character == "(" and comma_index is not None:
                depth += 1
            elif character == ")":
                depth -= 1
                if depth == 0:
                    end_index = cursor
                    break
            elif character == "," and depth == 1 and comma_index is None:
                comma_index = cursor
            cursor += 1
        if comma_index is None or end_index is None:
            errors.append(f"Malformed fragment starting at character {start}.")
            break
        state_name = text[start + len("$state(") : comma_index].strip()
        content = text[comma_index + 1 : end_index]
        if not state_name:
            errors.append(f"Empty state name in fragment starting at character {start}.")
        fragments.append(
            {
                "start": start,
                "end": end_index + 1,
                "state": state_name,
                "content": content,
            }
        )
        index = end_index + 1
    return fragments, errors


def render_text(text: str, fragments: list[dict[str, object]], active_states: set[str]) -> str:
    parts: list[str] = []
    cursor = 0
    for fragment in fragments:
        start = int(fragment["start"])
        end = int(fragment["end"])
        parts.append(text[cursor:start])
        if str(fragment["state"]) in active_states:
            parts.append(str(fragment["content"]))
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


def whitespace_ok(text: str) -> bool:
    return "  " not in text and not re.search(r"\s+[,.!?;:]", text)


def optional_prose_ok(text: str) -> bool:
    return bool(text.strip()) and "$state(" not in text and whitespace_ok(text)


def fragment_integration_ok(text: str, fragments: list[dict[str, object]]) -> bool:
    for fragment in fragments:
        rendered = render_text(text, fragments, {str(fragment["state"])})
        default_render = render_text(text, fragments, set())
        if not whitespace_ok(rendered) or not whitespace_ok(default_render):
            return False
    return True


def permanent_features_inside_fragments(fragments: list[dict[str, object]], exit_directions: list[str]) -> list[str]:
    findings: list[str] = []
    protected_terms = PERMANENT_FEATURE_TERMS | set(exit_directions)
    for fragment in fragments:
        lowered = str(fragment["content"]).lower()
        hits = sorted(term for term in protected_terms if re.search(rf"\b{re.escape(term)}\b", lowered))
        if hits:
            findings.append(f"{fragment['state']}: {', '.join(hits)}")
    return findings


def choose_one_state(applicable_states: list[str], fragment_states: list[str]) -> list[str]:
    if fragment_states:
        return [fragment_states[0]]
    return applicable_states[:1]


def choose_multiple_states(applicable_states: list[str], fragment_states: list[str]) -> tuple[list[str], str | None]:
    unique_fragment_states: list[str] = []
    for state in fragment_states:
        if state not in unique_fragment_states:
            unique_fragment_states.append(state)
    for first_index, first_state in enumerate(unique_fragment_states):
        for second_state in unique_fragment_states[first_index + 1 :]:
            if STATE_GROUPS.get(first_state) != STATE_GROUPS.get(second_state):
                return [first_state, second_state], None
    if "invasion" in applicable_states and unique_fragment_states and unique_fragment_states[0] != "invasion":
        return [unique_fragment_states[0], "invasion"], "Second state chosen from applicable list because only one fragment state was emitted."
    return [], "No compatible multi-state combination was available for this room."


def main() -> int:
    setup_django()
    samples = parse_export(EXPORT_PATH)
    zone_cache: dict[str, dict] = {}
    room_cache: dict[tuple[str, str], dict] = {}
    for zone_id, room_id in ROOM_TARGETS:
        zone = zone_cache.setdefault(zone_id, load_generation_zone(zone_id))
        room_cache[(zone_id, room_id)] = {str(room.get("id") or "").strip(): room for room in zone.get("rooms") or []}[room_id]

    lines = [
        "# MT-501 Findings",
        "",
        "Single-pass evaluation only. No prompt iteration was performed.",
        "",
    ]

    for sample in samples:
        zone = zone_cache[sample.zone_id]
        room = room_cache[(sample.zone_id, sample.room_id)]
        actual_applicable_states = determine_applicable_states(room, zone)
        fragments, syntax_errors = parse_state_fragments(sample.text)
        fragment_states = [str(fragment["state"]) for fragment in fragments]
        default_render = render_text(sample.text, fragments, set())
        one_state = choose_one_state(actual_applicable_states, fragment_states)
        one_state_render = render_text(sample.text, fragments, set(one_state)) if one_state else default_render
        multiple_states, multiple_note = choose_multiple_states(actual_applicable_states, fragment_states)
        multiple_render = render_text(sample.text, fragments, set(multiple_states)) if multiple_states else "N/A"
        permanent_feature_findings = permanent_features_inside_fragments(fragments, sorted((room.get("exits") or {}).keys()))
        states_only_from_list = all(state in actual_applicable_states for state in fragment_states)

        lines.extend(
            [
                f"## {sample.zone_id} / {sample.room_id}",
                "",
                f"- applicable_states: {', '.join(actual_applicable_states) or 'none'}",
                f"- fragments found: {len(fragments)}",
                f"- syntactically correct: {'yes' if not syntax_errors else 'no'}",
                f"- only allowed states used: {'yes' if states_only_from_list else 'no'}",
                f"- prose reads correctly with all fragments removed: {'yes' if optional_prose_ok(default_render) else 'no'}",
                f"- fragment integration looks grammatical: {'yes' if fragment_integration_ok(sample.text, fragments) else 'no'}",
                f"- whitespace check passes: {'yes' if whitespace_ok(default_render) and (multiple_render == 'N/A' or whitespace_ok(multiple_render)) and whitespace_ok(one_state_render) else 'no'}",
                f"- permanent features kept outside fragments: {'yes' if not permanent_feature_findings else 'no'}",
            ]
        )
        if syntax_errors:
            lines.append(f"- syntax issues: {'; '.join(syntax_errors)}")
        if permanent_feature_findings:
            lines.append(f"- permanent feature findings: {'; '.join(permanent_feature_findings)}")
        if multiple_note:
            lines.append(f"- multi-state note: {multiple_note}")
        lines.extend(
            [
                "",
                "### Raw Output",
                "",
                "```text",
                sample.text,
                "```",
                "",
                "### Parsed Fragments",
                "",
            ]
        )
        if fragments:
            for fragment in fragments:
                lines.append(f"- `{fragment['state']}` -> `{fragment['content']}`")
        else:
            lines.append("- none")
        lines.extend(
            [
                "",
                "### Rendered Versions",
                "",
                "Default state (no fragments active):",
                "",
                "```text",
                default_render,
                "```",
                "",
                f"One state active ({', '.join(one_state) if one_state else 'none selected'}):",
                "",
                "```text",
                one_state_render,
                "```",
                "",
                f"Multiple compatible states active ({', '.join(multiple_states) if multiple_states else 'not available'}):",
                "",
                "```text",
                multiple_render,
                "```",
                "",
            ]
        )

    FINDINGS_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Findings written to {FINDINGS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())