from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from world.builder.schemas.room_tag_schema import normalize_room_tags
from world.builder.schemas.typed_generation_input_schema import resolve_typed_generation_input


_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "templates" / "room_description_system_prompt.txt"
PROMPT_VERSION = "v8_diremud_required_stateful_fragments"

_STATE_GROUP_VOCABULARY = {
    "time": ("morning", "midday", "evening", "night"),
    "season": ("spring", "summer", "autumn", "winter"),
    "weather": ("rain", "snow", "fog"),
    "invasion": ("invasion",),
}
_INTERIOR_STRUCTURES = {"building-interior", "hallway", "chamber", "threshold", "entrance"}
_URBAN_EXTERIOR_STRUCTURES = {"street", "square", "intersection", "plaza", "alley", "courtyard", "bridge", "dock"}
_INTERIOR_FUNCTIONS = {
    "shop",
    "tavern",
    "inn",
    "temple",
    "guild-hall",
    "forge",
    "bakery",
    "brothel",
    "jail",
    "residence",
    "barracks",
    "library",
    "warehouse",
    "market-stall",
    "kitchen",
    "cellar",
}
_INTERIOR_FEATURES = {"hearth", "altar", "pulpit", "throne", "workbench"}

# ORIGINAL_PROMPT_BASELINE
# System:
# You are writing atmospheric room descriptions for the Dragonsire builder.
# Preserve the grounded facts from the supplied room and zone context.
# Write in concise, vivid fantasy prose with concrete sensory detail.
# Do not invent major landmarks, factions, or props that are not supported by the supplied context.
# Avoid second-person instructions, bullet lists, YAML, or designer commentary.
# User:
# Write a room description for Dragonsire.
# Room name: <room name>
# Zone: <zone name>
# Environment: <environment>
# Short description: <short description>
# Current description to replace: <existing description>
# Zone generation context:
#   Setting type: <setting>
#   Era feel: <era>
#   Climate: <climate>
#   Culture cues: <culture>
#   Mood cues: <mood>
#   Voice notes: <voice>
# Visible exits:
# - <direction>: <target>
# Important detail keys:
# - <detail key>
# Constraints:
# - Return one vivid room description paragraph and nothing else.
# - Mention only details grounded by the provided room, exits, and zone context.
# - Do not mention game mechanics, YAML, metadata, or the player.


@dataclass(frozen=True)
class RoomDescriptionPrompt:
    system_prompt: str
    user_prompt: str
    prompt: str
    trimmed: bool


def load_room_description_system_prompt() -> str:
    return _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _label(value: str) -> str:
    return " ".join(chunk.capitalize() for chunk in str(value or "").replace("_", " ").replace("-", " ").split())


def _normalize_list(value: object, *, preserve_case: bool = False) -> list[str]:
    if not isinstance(value, list):
        return []
    items = []
    seen = set()
    for item in value:
        text = str(item or "").strip()
        if not text:
            continue
        normalized_key = text if preserve_case else text.lower()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        items.append(text if preserve_case else normalized_key)
    return items


def _trim_lines(lines: list[str], max_chars: int) -> tuple[list[str], bool]:
    trimmed = False
    while lines and len("\n".join(lines)) > max_chars:
        lines.pop()
        trimmed = True
    return lines, trimmed


def _natural_join(items: list[str]) -> str:
    cleaned = [str(item or "").strip() for item in items if str(item or "").strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def _context_key(value: object) -> str:
    return str(value or "").strip().rstrip(".").casefold()


def _normalized_exit_directions(room_payload: dict) -> list[str]:
    exits = room_payload.get("exits") or room_payload.get("exitMap") or {}
    directions = []
    for direction, spec in sorted(dict(exits).items()):
        normalized_direction = str(direction or "").strip().lower()
        if not normalized_direction:
            continue
        if isinstance(spec, dict):
            target = str(spec.get("target") or spec.get("target_id") or "").strip()
            if not target:
                continue
        directions.append(normalized_direction)
    return directions


def _derive_shape(exit_directions: list[str]) -> str:
    exit_count = len(exit_directions)
    if exit_count == 1:
        return "dead end"
    if exit_count == 2:
        return "passage"
    if exit_count >= 3:
        return "intersection"
    return "enclosed room"


def _shape_hint(shape: str) -> str:
    if shape == "dead end":
        return "One exit is listed for this space."
    if shape == "passage":
        return "Two exits continue through this space."
    if shape == "intersection":
        return "Multiple exits branch from this space."
    return "No exits are listed for this space."


def _nonempty_text(value: object) -> str:
    return str(value or "").strip()


def _has_vertical_exit(exit_directions: list[str]) -> bool:
    return any(direction in {"up", "down"} for direction in exit_directions)


def determine_applicable_state_groups(
    room_payload: dict | None,
    zone_payload: dict | None,
    generation_context: dict | None = None,
) -> list[str]:
    room_data = room_payload or {}
    zone_data = zone_payload or {}
    context = generation_context or zone_data.get("generation_context") or {}
    room_tags = normalize_room_tags(room_data.get("tags"))
    structure = str(room_tags.get("structure") or "").strip().lower()
    specific_function = str(room_tags.get("specific_function") or "").strip().lower()
    named_feature = str(room_tags.get("named_feature") or "").strip().lower()
    setting_type = _nonempty_text(context.get("setting_type") or room_data.get("environment")).lower()
    room_id = str(room_data.get("id") or "").strip().upper()
    exit_directions = _normalized_exit_directions(room_data)

    is_interior = (
        structure in _INTERIOR_STRUCTURES
        or specific_function in _INTERIOR_FUNCTIONS
        or named_feature in _INTERIOR_FEATURES
    )
    is_urban_exterior = structure in _URBAN_EXTERIOR_STRUCTURES or (setting_type == "city" and not is_interior)
    # Legacy cave rooms can arrive without structure tags. Prefer tags first, but keep a
    # narrow fallback so current underground rooms still get sane state applicability.
    is_underground = (
        setting_type in {"cave", "underground"}
        or structure in {"cave", "cave-passage", "cave-tunnel", "tunnel"}
        or (not setting_type and _has_vertical_exit(exit_directions))
        or room_id.startswith("CRO_")
    )

    if is_underground:
        return ["season"]
    if is_interior:
        return ["season", "time", "invasion"]
    if is_urban_exterior:
        return ["season", "time", "weather", "invasion"]
    return ["season", "time", "weather"]


def determine_applicable_states(
    room_payload: dict | None,
    zone_payload: dict | None,
    generation_context: dict | None = None,
) -> list[str]:
    states: list[str] = []
    for group in determine_applicable_state_groups(room_payload, zone_payload, generation_context):
        states.extend(_STATE_GROUP_VOCABULARY[group])
    return states


def _human_room_name(room_name: str, room_id: str) -> str:
    if not room_name:
        return ""
    if room_name == room_id:
        return ""
    return room_name


def _is_code_like_identifier(value: str) -> bool:
    if not value:
        return False
    if any(character.isdigit() for character in value):
        return True
    if "_" in value:
        return True
    return value.lower() == value and " " not in value


def _human_zone_name(zone_name: str, zone_id: str) -> str:
    if not zone_name:
        return ""
    if zone_name == zone_id and _is_code_like_identifier(zone_name):
        return ""
    if _is_code_like_identifier(zone_name):
        return ""
    return zone_name


def _room_tag_clause(field: str, value: str) -> str:
    label = _label(value).lower()
    if field == "structure":
        article = "an" if label[:1] in {"a", "e", "i", "o", "u"} else "a"
        return f"This space takes the form of {article} {label}."
    if field == "specific_function":
        article = "an" if label[:1] in {"a", "e", "i", "o", "u"} else "a"
        return f"This space serves as {article} {label}."
    if field == "named_feature":
        feature_clauses = {
            "well": "A public well stands here.",
            "fountain": "A fountain anchors the space.",
            "statue": "A statue gives the space a fixed focal point.",
            "signpost": "A signpost marks the space.",
            "gibbet": "A gibbet stands in plain view.",
            "shrine": "A shrine gives the space a devotional focus.",
            "well-house": "A well-house marks the space.",
            "firepit": "A firepit sits within the space.",
            "altar": "An altar gives the space a sacred center.",
            "pulpit": "A pulpit stands within the space.",
            "throne": "A throne dominates the space.",
            "hearth": "A hearth anchors the space.",
            "workbench": "A workbench gives the space a practical focus.",
        }
        return feature_clauses.get(value, f"A notable {label} marks the space.")
    if field == "condition":
        condition_clauses = {
            "pristine": "The space is kept in pristine condition.",
            "well-maintained": "The space is well maintained.",
            "worn": "The space shows plain signs of wear.",
            "crumbling": "The stonework is crumbling, clearly long past its prime.",
            "burnt-out": "The space bears the aftermath of a burn-out.",
            "abandoned": "The space has been left abandoned.",
            "refurbished": "The space has been recently refurbished.",
        }
        return condition_clauses.get(value, f"The space feels {label}.")
    return ""


def _atmosphere_clause(field: str, values: list[str]) -> str:
    labeled_values = [_label(value).lower() for value in values if value]
    if not labeled_values:
        return ""
    if field == "materials":
        return f"Licensed materials: {', '.join(labeled_values)}."
    if field == "social_character":
        return f"Licensed social character: {', '.join(labeled_values)}."
    if field == "surroundings":
        return f"Licensed surroundings: {', '.join(labeled_values)}."
    if field == "sensory":
        return f"Licensed sensory cues: {', '.join(labeled_values)}."
    return ""


def _atmosphere_upkeep_clause(value: str | None) -> str:
    if not value:
        return ""
    return f"Licensed upkeep: {_label(value).lower()}."


def _build_room_tag_sections(room_payload: dict) -> list[str]:
    room_tags = normalize_room_tags(room_payload.get("tags"))
    tag_lines = [
        ("Structure", room_tags.get("structure")),
        ("Function", room_tags.get("specific_function")),
        ("Feature", room_tags.get("named_feature")),
        ("Condition", room_tags.get("condition")),
    ]
    custom_tags = room_tags.get("custom") or []
    clauses = [
        _room_tag_clause(field, value)
        for field, value in (
            ("structure", room_tags.get("structure")),
            ("specific_function", room_tags.get("specific_function")),
            ("named_feature", room_tags.get("named_feature")),
            ("condition", room_tags.get("condition")),
        )
        if value
    ]
    populated_tag_lines = [f"{label}: {_label(value)}." for label, value in tag_lines if value]
    if custom_tags:
        populated_tag_lines.append(f"Custom: {', '.join(str(tag).strip() for tag in custom_tags if str(tag).strip())}.")
        clauses.append(f"Also: {', '.join(str(tag).strip() for tag in custom_tags if str(tag).strip())}.")
    if not populated_tag_lines:
        return []
    return [
        "=== THIS ROOM ===",
        *populated_tag_lines,
        *clauses,
    ]


def _build_room_atmosphere_sections(room_payload: dict) -> list[str]:
    room_tags = normalize_room_tags(room_payload.get("tags"))
    atmosphere = dict(room_tags.get("atmosphere") or {})
    atmosphere_lines: list[str] = []
    for field in ("materials", "social_character", "surroundings", "sensory"):
        values = [str(value).strip() for value in list(atmosphere.get(field) or []) if str(value).strip()]
        if not values:
            continue
        atmosphere_lines.append(f"{_label(field)}: {', '.join(_label(value) for value in values)}.")
    upkeep = str(atmosphere.get("upkeep") or "").strip()
    if upkeep:
        atmosphere_lines.append(f"Upkeep: {_label(upkeep)}.")
    if not atmosphere_lines:
        return []
    return [
        "=== ATMOSPHERE ===",
        *atmosphere_lines,
    ]


def _build_zone_context_sections(zone_name: str, generation_context: dict) -> list[str]:
    culture_values = ", ".join(_label(value) for value in _normalize_list(generation_context.get("culture")))
    mood_values = ", ".join(_label(value) for value in _normalize_list(generation_context.get("mood")))
    zone_context_lines = [
        ("Setting type", _nonempty_text(generation_context.get("setting_type"))),
        ("Era feel", _nonempty_text(generation_context.get("era_feel"))),
        ("Cultural style", culture_values),
        ("Mood", mood_values),
        ("Climate", _nonempty_text(generation_context.get("climate"))),
    ]
    voice = _nonempty_text(generation_context.get("voice"))

    sections: list[str] = []
    populated_zone_lines = [f"{label}: {value}." for label, value in zone_context_lines if value]
    if populated_zone_lines:
        sections.extend([
            "=== ZONE CONTEXT ===",
            f"You are in {zone_name}.",
            *populated_zone_lines,
        ])
    if voice:
        sections.extend([
            "=== VOICE ===",
            voice,
        ])
    return sections


def _extract_area_payload(room_payload: dict, zone_payload: dict) -> dict | None:
    for candidate in (room_payload.get("area"), zone_payload.get("area")):
        if isinstance(candidate, dict):
            return dict(candidate)
    return None


def _build_typed_generation_sections(room_payload: dict, zone_payload: dict) -> list[str]:
    area_payload = _extract_area_payload(room_payload, zone_payload)
    typed_payload = resolve_typed_generation_input(room_payload, zone_payload, area_payload)
    sections: list[str] = []

    def append_section(title: str, items: list[str]) -> None:
        cleaned = [str(item or "").strip() for item in items if str(item or "").strip()]
        if not cleaned:
            return
        sections.extend([f"=== {title} ===", *[f"- {item}" for item in cleaned]])

    append_section("REQUIRED ROOM FACTS", list(typed_payload.get("required_room_facts") or []))
    append_section("ALLOWED BUT NOT REQUIRED DETAILS", list(typed_payload.get("allowed_but_not_required") or []))
    append_section("SOFT ROOM CONTEXT", list(typed_payload.get("soft_room_context") or []))
    append_section("SOFT AREA CONTEXT", list(typed_payload.get("soft_area_context") or []))
    append_section("SOFT ZONE CONTEXT", list(typed_payload.get("soft_zone_context") or []))
    append_section("FORBIDDEN FEATURES", list(typed_payload.get("forbidden_features") or []))

    allowed_exits = list(typed_payload.get("allowed_exits") or [])
    sections.append("=== ALLOWED EXITS ===")
    sections.append("Only these exits may be mentioned:")
    if allowed_exits:
        for item in allowed_exits:
            direction = str(item.get("direction") or "").strip()
            description = str(item.get("description") or item.get("type") or item.get("target") or "").strip()
            if description:
                sections.append(f"- {direction}: {description}")
            else:
                sections.append(f"- {direction}")
    else:
        sections.append("- none")
    sections.append("Do not invent exits beyond this list.")

    interactive_objects = [str(item or "").strip() for item in list(typed_payload.get("interactive_objects") or []) if str(item or "").strip()]
    sections.append("=== INTERACTIVE OBJECTS ===")
    if interactive_objects:
        sections.append("Only these objects may receive look text:")
        sections.extend(f"- {item}" for item in interactive_objects)
    else:
        sections.append("No object look targets may be generated.")

    return sections


def _build_model_prompt_lines(room_payload: dict, zone_payload: dict, generation_context: dict, room_id: str, room_name: str, zone_name: str, shape: str, shape_hint: str, exit_directions: list[str]) -> list[str]:
    area_payload = _extract_area_payload(room_payload, zone_payload)
    typed_payload = resolve_typed_generation_input(room_payload, zone_payload, area_payload)
    applicable_state_groups = determine_applicable_state_groups(room_payload, zone_payload, generation_context)
    applicable_states = determine_applicable_states(room_payload, zone_payload, generation_context)
    display_room_name = _human_room_name(room_name, room_id)
    display_zone_name = _human_zone_name(zone_name, str(zone_payload.get("zone_id") or "").strip())
    lines = [
        "Write one player-facing DireMud room description.",
        "Use only the known facts below.",
    ]

    if display_room_name:
        lines.append(f"The room is named {display_room_name}.")
    if display_zone_name:
        lines.append(f"It is in {display_zone_name}.")

    setting_type = _nonempty_text(generation_context.get("setting_type") or room_payload.get("environment"))
    if setting_type:
        lines.append(f"The broader environment is {setting_type}.")
    era_feel = _nonempty_text(generation_context.get("era_feel"))
    if era_feel:
        lines.append(f"The era feel is {era_feel}.")
    culture = _natural_join([_label(value) for value in _normalize_list(generation_context.get("culture"))])
    if culture:
        lines.append(f"Cultural cues include {culture}.")
    mood = _natural_join([_label(value) for value in _normalize_list(generation_context.get("mood"))])
    if mood:
        lines.append(f"Mood cues include {mood}.")
    climate = _nonempty_text(generation_context.get("climate"))
    if climate:
        lines.append(f"The climate is {climate}.")
    voice = _nonempty_text(generation_context.get("voice"))
    if voice:
        lines.append(f"Voice guidance is {voice.rstrip('.')}.")
    banned_phrases = _normalize_list(generation_context.get("banned_phrases"), preserve_case=True)
    if banned_phrases:
        lines.append(f"Avoid these phrases: {_natural_join(banned_phrases)}.")

    lines.append(f"The room shape is {shape}. {shape_hint}")
    if exit_directions:
        lines.append(f"The listed exits run {_natural_join(exit_directions)}.")
    else:
        lines.append("No exits are listed for this room.")

    room_tags = normalize_room_tags(room_payload.get("tags"))
    for field, value in (
        ("structure", room_tags.get("structure")),
        ("specific_function", room_tags.get("specific_function")),
        ("named_feature", room_tags.get("named_feature")),
        ("condition", room_tags.get("condition")),
    ):
        if value:
            clause = _room_tag_clause(field, value)
            if clause:
                lines.append(clause)
    custom_tags = [str(tag).strip() for tag in room_tags.get("custom") or [] if str(tag).strip()]
    if custom_tags:
        lines.append(f"Additional custom cues include {_natural_join(custom_tags)}.")

    atmosphere = dict(room_tags.get("atmosphere") or {})
    materials = [_label(value).lower() for value in list(atmosphere.get("materials") or []) if str(value).strip()]
    if materials:
        lines.append(f"Allowed materials include {_natural_join(materials)}.")
    social = [_label(value).lower() for value in list(atmosphere.get("social_character") or []) if str(value).strip()]
    if social:
        lines.append(f"Allowed social character cues include {_natural_join(social)}.")
    surroundings = [_label(value).lower() for value in list(atmosphere.get("surroundings") or []) if str(value).strip()]
    if surroundings:
        lines.append(f"Allowed surrounding cues include {_natural_join(surroundings)}.")
    sensory = [_label(value).lower() for value in list(atmosphere.get("sensory") or []) if str(value).strip()]
    if sensory:
        lines.append(f"Allowed sensory cues include {_natural_join(sensory)}.")
    upkeep = _nonempty_text(atmosphere.get("upkeep"))
    if upkeep:
        lines.append(f"Allowed upkeep cues include {_label(upkeep).lower()}.")

    required_facts = [str(item).strip() for item in list(typed_payload.get("required_room_facts") or []) if str(item).strip()]
    if required_facts:
        lines.append(f"Required room facts include {_natural_join(required_facts)}.")
    optional_facts = [str(item).strip() for item in list(typed_payload.get("allowed_but_not_required") or []) if str(item).strip()]
    if optional_facts:
        lines.append(f"Allowed but optional details include {_natural_join(optional_facts)}.")
    soft_room = [str(item).strip() for item in list(typed_payload.get("soft_room_context") or []) if str(item).strip()]
    if soft_room:
        lines.append(f"Soft room context includes {_natural_join(soft_room)}.")
    soft_area = [str(item).strip() for item in list(typed_payload.get("soft_area_context") or []) if str(item).strip()]
    area_name = _nonempty_text((area_payload or {}).get("name"))
    if area_name:
        lines.append(f"The area is {area_name}.")
        soft_area = [item for item in soft_area if _context_key(item) != _context_key(area_name)]
    if soft_area:
        lines.append(f"Area context includes {_natural_join(soft_area)}.")
    soft_zone = [str(item).strip() for item in list(typed_payload.get("soft_zone_context") or []) if str(item).strip()]
    zone_duplicates = {
        _context_key(value)
        for value in [
            zone_name,
            setting_type or "",
            era_feel or "",
            climate or "",
            voice.rstrip(".") if voice else "",
            *[_label(value) for value in _normalize_list(generation_context.get("culture"))],
            *[_label(value) for value in _normalize_list(generation_context.get("mood"))],
        ]
        if str(value).strip()
    }
    soft_zone = [item for item in soft_zone if _context_key(item) not in zone_duplicates]
    if soft_zone:
        lines.append(f"Zone context includes {_natural_join(soft_zone)}.")
    forbidden = [str(item).strip() for item in list(typed_payload.get("forbidden_features") or []) if str(item).strip()]
    if forbidden:
        lines.append(f"Forbidden features include {_natural_join(forbidden)}.")
    if applicable_state_groups:
        lines.append(f"Applicable state groups for this room are {_natural_join(applicable_state_groups)}.")
    if applicable_states:
        lines.append(f"The applicable_states list for this room is {_natural_join(applicable_states)}.")
    else:
        lines.append("The applicable_states list for this room is empty.")

    allowed_exits = list(typed_payload.get("allowed_exits") or [])
    if allowed_exits:
        allowed_exit_text = []
        for item in allowed_exits:
            direction = str(item.get("direction") or "").strip()
            if not direction:
                continue
            description = str(item.get("description") or item.get("type") or "").strip()
            if description:
                allowed_exit_text.append(f"{direction} via {description}")
            else:
                allowed_exit_text.append(direction)
        if allowed_exit_text:
            lines.append(f"If exits are mentioned, only {_natural_join(allowed_exit_text)} may appear.")
    else:
        lines.append("No exits may be mentioned in the description.")

    interactive_objects = [str(item).strip() for item in list(typed_payload.get("interactive_objects") or []) if str(item).strip()]
    if interactive_objects:
        lines.append(f"Only these objects may receive look text: {_natural_join(interactive_objects)}.")
    else:
        lines.append("No object look targets may be generated.")

    lines.append("Use only those facts. Return one plain paragraph only.")
    return lines


def assemble_room_description_prompt(room: dict | None, zone: dict | None, *, max_prompt_chars: int = 22000) -> RoomDescriptionPrompt:
    room_payload = room or {}
    zone_payload = zone or {}
    generation_context = zone_payload.get("generation_context") or {}
    system_prompt = load_room_description_system_prompt()

    if max_prompt_chars < len(system_prompt) + 2000:
        raise ValueError(
            f"max_prompt_chars ({max_prompt_chars}) is too small to fit "
            f"the system prompt ({len(system_prompt)} chars) plus minimum "
            f"room context."
        )

    room_id = str(room_payload.get("id") or room_payload.get("name") or "unnamed_room").strip() or "unnamed_room"
    room_name = str(room_payload.get("name") or "").strip()
    zone_name = str(zone_payload.get("name") or zone_payload.get("zone_id") or "Unknown Zone").strip()
    exit_directions = _normalized_exit_directions(room_payload)
    shape = _derive_shape(exit_directions)
    shape_hint = _shape_hint(shape)
    legacy_exit_lines = []
    exits = room_payload.get("exits") or room_payload.get("exitMap") or {}
    for direction, spec in sorted(dict(exits).items()):
        if isinstance(spec, dict):
            target = str(spec.get("target") or spec.get("target_id") or "unknown").strip()
        else:
            target = str(spec or "unknown").strip()
        if str(direction or "").strip():
            legacy_exit_lines.append(f"- {direction}: {target}")
    detail_lines = [f"- {key}" for key in sorted((room_payload.get("details") or {}).keys())]
    context_lines = [
        f"Setting type: {generation_context.get('setting_type') or 'unspecified'}",
        f"Era feel: {generation_context.get('era_feel') or 'unspecified'}",
        f"Climate: {generation_context.get('climate') or 'unspecified'}",
        f"Culture cues: {', '.join(_label(value) for value in _normalize_list(generation_context.get('culture'))) or 'unspecified'}",
        f"Mood cues: {', '.join(_label(value) for value in _normalize_list(generation_context.get('mood'))) or 'unspecified'}",
        f"Voice notes: {str(generation_context.get('voice') or 'unspecified').strip() or 'unspecified'}",
    ]
    banned_phrases = _normalize_list(generation_context.get("banned_phrases"), preserve_case=True)
    if banned_phrases:
        context_lines.append(f"Avoid these phrases: {', '.join(banned_phrases)}")

    legacy_user_lines = [
        "Write a room description for Dragonsire.",
        f"Room name: {room_name or room_id}",
        f"Zone: {zone_name}",
        "Zone generation context:",
        *[f"  {line}" for line in context_lines],
        "Visible exits:",
        *(legacy_exit_lines or ["- none"]),
        "Important detail keys:",
        *(detail_lines or ["- none"]),
    ]

    model_user_lines = _build_model_prompt_lines(
        room_payload,
        zone_payload,
        generation_context,
        room_id,
        room_name,
        zone_name,
        shape,
        shape_hint,
        exit_directions,
    )

    base_prompt = f"{system_prompt}\n\n" + "\n".join(model_user_lines)
    if len(base_prompt) <= max_prompt_chars:
        return RoomDescriptionPrompt(system_prompt=system_prompt, user_prompt="\n".join(legacy_user_lines), prompt=base_prompt, trimmed=False)

    trimmed = False
    if legacy_exit_lines:
        legacy_exit_lines, legacy_exit_trimmed = _trim_lines(legacy_exit_lines, max(1, max_prompt_chars - len(system_prompt) - 300))
        trimmed = trimmed or legacy_exit_trimmed
    if detail_lines and len("\n".join(legacy_user_lines)) > max_prompt_chars:
        detail_lines, detail_trimmed = _trim_lines(detail_lines, max(1, max_prompt_chars - len(system_prompt) - 300))
        trimmed = trimmed or detail_trimmed

    legacy_user_lines = [
        "Write a room description for Dragonsire.",
        f"Room name: {room_name or room_id}",
        f"Zone: {zone_name}",
        "Zone generation context:",
        *[f"  {line}" for line in context_lines],
        "Visible exits:",
        *(legacy_exit_lines or ["- none"]),
        "Important detail keys:",
        *(detail_lines or ["- none"]),
    ]

    model_user_lines = _build_model_prompt_lines(
        room_payload,
        zone_payload,
        generation_context,
        room_id,
        room_name,
        zone_name,
        shape,
        shape_hint,
        exit_directions,
    )
    model_user_lines, model_trimmed = _trim_lines(model_user_lines, max(1, max_prompt_chars - len(system_prompt) - 2))
    trimmed = trimmed or model_trimmed
    user_prompt = "\n".join(legacy_user_lines)
    prompt = f"{system_prompt}\n\n" + "\n".join(model_user_lines)
    if len(prompt) > max_prompt_chars:
        prompt = prompt[:max_prompt_chars].rstrip()
        trimmed = True
    return RoomDescriptionPrompt(system_prompt=system_prompt, user_prompt=user_prompt, prompt=prompt, trimmed=trimmed)