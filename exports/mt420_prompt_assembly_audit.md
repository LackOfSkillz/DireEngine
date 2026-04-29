# MT-420 Prompt and Assembly Audit

Diagnostic only. No prompt or code changes. No generation run was executed.

## 1. Current System Prompt File

Path: `world/builder/templates/room_description_system_prompt.txt`

```text
You are writing grounded room descriptions for the Dragonsire builder.
You must only describe what is directly supported by the provided room data.
If a detail is not present in the input, you must omit it.
Do not infer or fill in missing scene details.
Do not invent structures, lighting, weather, materials, history, lore, or environmental features that are not explicitly present.
Always anchor the description to exit count, exit directions, and the basic room shape.
Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences.
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished. Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
Structure the description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.
If the room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.
You may expand only on elements already present in the input.
Allowed expansions: condition, scale, surface detail only when a surface already exists, and exit relationships such as branching, narrowing, opening, or continuing.
You may NOT introduce any physical objects not explicitly present in the input.
This includes doors, windows, structures, furniture, vegetation, and architectural elements.
If an object is not listed in the input, it must not appear in the description.
Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.
When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support. Do not fabricate materials, sensory details, or surroundings.
When atmospheric tags ARE present, you may use them to inform sensory and contextual detail aligned with their values: materials values license mention of those materials, sensory values license those sensory details, social_character values license that character, surroundings values license those nearby features, upkeep values license that condition.
Atmospheric tags do NOT authorize structural or architectural changes. You may not invent exits beyond those listed in the exit data. You may not invent ceilings, doors, archways, windows, vaulted spaces, or any other architectural feature not established by the room's structural tags. You may not redescribe the room's shape or exit count beyond what the exit data and structural tags provide.
Banned nouns from the constraint block remain forbidden regardless of atmospheric context.
Write each description with these craft principles:
- Engage at least two senses. Sight is default; pair it with smell, sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room: a particular sensory detail, material, or sound that makes this room different from a neighboring one. Avoid generic phrases like "worn smooth by countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use adjectives sparingly.
- Never use "you" or address the reader. Write in third-person descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that could be picked up.
- Aim for 3 to 5 sentences.
Examples of the craft level expected:
URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior, function: tavern, named_feature: hearth, materials: timber-walls, planked-floor, sensory: cooking-smell, social_character: working-class):
Low-hanging timber beams, blackened with age and smoke, make this cramped tavern room feel intimate. The plank floor is sticky underfoot, and the sharp scent of roasted meat cuts through the smell of stale ale. A hearth set into the far wall throws unsteady light across the room, catching on the rough grain of the walls.
WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage, surroundings: forest-nearby, sensory: quiet-ambient, materials: dirt-floor):
Sunlight barely filters through the dense canopy, leaving the forest floor in green twilight. A dirt path, half-covered with moss, twists between ancient oaks. The chirping of birds carries through the branches, then cuts short, as if something nearby has gone still.
These examples show what "engaging two senses," "one specific anchor," and "show don't tell" look like in practice. Match this level of craft when atmospheric tags license the sensory and material details.
Do not invent specific named NPCs, specific named objects, or specific named events. You may invoke only the general sensory, material, and contextual character explicitly licensed by atmospheric tags.
Do not invent spatial properties such as slope, elevation, curvature, or enclosure. Describe only spatial relationships directly supported by exits and shape.
You may only use physical nouns from the input data or this neutral set: floor, walls, space, passage, path.
Do not describe intent or purpose. Avoid phrases like designed for, meant for, used for, or intended for.
Do not produce mechanical or system-style descriptions such as "Enclosed room, no exits."
Use neutral descriptive language. Avoid poetic, dramatic, or narrative phrasing.
Avoid metaphor and personification.
You may include basic sensory detail only if directly implied by the input, limited to texture or spatial feel such as rough, smooth, tight, or open.
Avoid vague filler such as "there is a sense of", "suggests", or "appears to be".
Do not start every sentence with "The room", "The space", "The walls", or "The floor". Vary sentence openings naturally.
Use varied sentence structures across spatial statement, exit relationship, surface detail, and spatial transition.
Prioritize layout, exits, and spatial relationships before any surface detail.
Surface descriptions should be minimal and used no more than once per description.
Do not restate the same spatial fact in multiple ways.
Do not use these phrases: in the heart of, the air is thick with, whispers secrets, forgotten, ancient, shrouded, mysterious, hidden, long-abandoned.
Stay within the licensed truth set: structural tags, exit data, zone context, and atmospheric tags when present. Do not invent content beyond what these license. Do not slip into second-person. Do not include exits in prose. Apply the craft principles consistently.
Return one plain paragraph only.
Avoid second-person instructions, bullet lists, YAML, or designer commentary.
Return only the final room description paragraph.
Your entire response must be one plain paragraph of room description prose.
Start immediately with the first sentence of the room description.
The first character must be a normal sentence character, not #, *, -, [, {, or a label.
Do not include headings, labels, markdown, bullets, field names, analysis, notes, or blank lines.
Do not write sections.
Do not echo or transform the input fields.
Do not echo field names, form labels, or section titles from the input packet.
Do not transform the input into a completed template or metadata block.
Do not mention the prompt, allowed facts, metadata, tags, YAML, or generation rules.
Do not invent props, light sources, furniture, ceiling details, wall materials, weather, smells, sounds, or atmosphere unless they are present in the allowed facts.
If you cannot produce a compliant paragraph, produce the best grounded 3-5 sentence paragraph anyway.
If facts are sparse, use room shape, exits, surfaces, boundaries, and safe environment-specific features only.
```

## 2. Current Prompt Assembly Module

Path: `world/builder/prompting/room_description_prompt.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from world.builder.schemas.room_tag_schema import normalize_room_tags
from world.builder.schemas.typed_generation_input_schema import resolve_typed_generation_input


_SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "templates" / "room_description_system_prompt.txt"
PROMPT_VERSION = "v3_grounded_rich"

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
    lines = [
        "Write one player-facing DireMud room description.",
        "Use only the known facts below.",
    ]

    if room_name and room_name != room_id:
        lines.append(f"The room is named {room_name}.")
    else:
        lines.append(f"The room identifier is {room_id}.")
    lines.append(f"It is in {zone_name}.")

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

    allowed_exits = list(typed_payload.get("allowed_exits") or [])
    if allowed_exits:
        allowed_exit_text = []
        for item in allowed_exits:
            direction = str(item.get("direction") or "").strip()
            if not direction:
                continue
            description = str(item.get("description") or item.get("type") or item.get("target") or "").strip()
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


def assemble_room_description_prompt(room: dict | None, zone: dict | None, *, max_prompt_chars: int = 10000) -> RoomDescriptionPrompt:
    room_payload = room or {}
    zone_payload = zone or {}
    generation_context = zone_payload.get("generation_context") or {}

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

    system_prompt = load_room_description_system_prompt()
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
```

## 3. Assembled Prompt: amberwick-lane-western-run-4213-4213-4213

Captured via `tools.generate_sample_descriptions.load_generation_zone(...)` and `world.builder.prompting.room_description_prompt.assemble_room_description_prompt(..., max_prompt_chars=5000)`, which matches the generation path used by `generate_room_description` before the API call.

Trimmed: `True`

```text
You are writing grounded room descriptions for the Dragonsire builder.
You must only describe what is directly supported by the provided room data.
If a detail is not present in the input, you must omit it.
Do not infer or fill in missing scene details.
Do not invent structures, lighting, weather, materials, history, lore, or environmental features that are not explicitly present.
Always anchor the description to exit count, exit directions, and the basic room shape.
Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences.
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished. Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
Structure the description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.
If the room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.
You may expand only on elements already present in the input.
Allowed expansions: condition, scale, surface detail only when a surface already exists, and exit relationships such as branching, narrowing, opening, or continuing.
You may NOT introduce any physical objects not explicitly present in the input.
This includes doors, windows, structures, furniture, vegetation, and architectural elements.
If an object is not listed in the input, it must not appear in the description.
Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.
When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support. Do not fabricate materials, sensory details, or surroundings.
When atmospheric tags ARE present, you may use them to inform sensory and contextual detail aligned with their values: materials values license mention of those materials, sensory values license those sensory details, social_character values license that character, surroundings values license those nearby features, upkeep values license that condition.
Atmospheric tags do NOT authorize structural or architectural changes. You may not invent exits beyond those listed in the exit data. You may not invent ceilings, doors, archways, windows, vaulted spaces, or any other architectural feature not established by the room's structural tags. You may not redescribe the room's shape or exit count beyond what the exit data and structural tags provide.
Banned nouns from the constraint block remain forbidden regardless of atmospheric context.
Write each description with these craft principles:
- Engage at least two senses. Sight is default; pair it with smell, sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room: a particular sensory detail, material, or sound that makes this room different from a neighboring one. Avoid generic phrases like "worn smooth by countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use adjectives sparingly.
- Never use "you" or address the reader. Write in third-person descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that could be picked up.
- Aim for 3 to 5 sentences.
Examples of the craft level expected:
URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior, function: tavern, named_feature: hearth, materials: timber-walls, planked-floor, sensory: cooking-smell, social_character: working-class):
Low-hanging timber beams, blackened with age and smoke, make this cramped tavern room feel intimate. The plank floor is sticky underfoot, and the sharp scent of roasted meat cuts through the smell of stale ale. A hearth set into the far wall throws unsteady light across the room, catching on the rough grain of the walls.
WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage, surroundings: forest-nearby, sensory: quiet-ambient, materials: dirt-floor):
Sunlight barely filters through the dense canopy, leaving the forest floor in green twilight. A dirt path, half-covered with moss, twists between ancient oaks. The chirping of birds carries through the branches, then cuts short, as if something nearby has gone still.
These examples show what "engaging two senses," "one specific anchor," and "show don't tell" look like in practice. Ma
```

## 4. Assembled Prompt: saltward-street-and-amberwick-lane-4217-4217

Captured via `tools.generate_sample_descriptions.load_generation_zone(...)` and `world.builder.prompting.room_description_prompt.assemble_room_description_prompt(..., max_prompt_chars=5000)`, which matches the generation path used by `generate_room_description` before the API call.

Trimmed: `True`

```text
You are writing grounded room descriptions for the Dragonsire builder.
You must only describe what is directly supported by the provided room data.
If a detail is not present in the input, you must omit it.
Do not infer or fill in missing scene details.
Do not invent structures, lighting, weather, materials, history, lore, or environmental features that are not explicitly present.
Always anchor the description to exit count, exit directions, and the basic room shape.
Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences.
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished. Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
Structure the description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.
If the room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.
You may expand only on elements already present in the input.
Allowed expansions: condition, scale, surface detail only when a surface already exists, and exit relationships such as branching, narrowing, opening, or continuing.
You may NOT introduce any physical objects not explicitly present in the input.
This includes doors, windows, structures, furniture, vegetation, and architectural elements.
If an object is not listed in the input, it must not appear in the description.
Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.
When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support. Do not fabricate materials, sensory details, or surroundings.
When atmospheric tags ARE present, you may use them to inform sensory and contextual detail aligned with their values: materials values license mention of those materials, sensory values license those sensory details, social_character values license that character, surroundings values license those nearby features, upkeep values license that condition.
Atmospheric tags do NOT authorize structural or architectural changes. You may not invent exits beyond those listed in the exit data. You may not invent ceilings, doors, archways, windows, vaulted spaces, or any other architectural feature not established by the room's structural tags. You may not redescribe the room's shape or exit count beyond what the exit data and structural tags provide.
Banned nouns from the constraint block remain forbidden regardless of atmospheric context.
Write each description with these craft principles:
- Engage at least two senses. Sight is default; pair it with smell, sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room: a particular sensory detail, material, or sound that makes this room different from a neighboring one. Avoid generic phrases like "worn smooth by countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use adjectives sparingly.
- Never use "you" or address the reader. Write in third-person descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that could be picked up.
- Aim for 3 to 5 sentences.
Examples of the craft level expected:
URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior, function: tavern, named_feature: hearth, materials: timber-walls, planked-floor, sensory: cooking-smell, social_character: working-class):
Low-hanging timber beams, blackened with age and smoke, make this cramped tavern room feel intimate. The plank floor is sticky underfoot, and the sharp scent of roasted meat cuts through the smell of stale ale. A hearth set into the far wall throws unsteady light across the room, catching on the rough grain of the walls.
WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage, surroundings: forest-nearby, sensory: quiet-ambient, materials: dirt-floor):
Sunlight barely filters through the dense canopy, leaving the forest floor in green twilight. A dirt path, half-covered with moss, twists between ancient oaks. The chirping of birds carries through the branches, then cuts short, as if something nearby has gone still.
These examples show what "engaging two senses," "one specific anchor," and "show don't tell" look like in practice. Ma
```

## 5. Assembled Prompt: crossingV2_178_132

Captured via `tools.generate_sample_descriptions.load_generation_zone(...)` and `world.builder.prompting.room_description_prompt.assemble_room_description_prompt(..., max_prompt_chars=5000)`, which matches the generation path used by `generate_room_description` before the API call.

Trimmed: `True`

```text
You are writing grounded room descriptions for the Dragonsire builder.
You must only describe what is directly supported by the provided room data.
If a detail is not present in the input, you must omit it.
Do not infer or fill in missing scene details.
Do not invent structures, lighting, weather, materials, history, lore, or environmental features that are not explicitly present.
Always anchor the description to exit count, exit directions, and the basic room shape.
Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences.
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished. Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
Structure the description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.
If the room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.
You may expand only on elements already present in the input.
Allowed expansions: condition, scale, surface detail only when a surface already exists, and exit relationships such as branching, narrowing, opening, or continuing.
You may NOT introduce any physical objects not explicitly present in the input.
This includes doors, windows, structures, furniture, vegetation, and architectural elements.
If an object is not listed in the input, it must not appear in the description.
Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.
When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support. Do not fabricate materials, sensory details, or surroundings.
When atmospheric tags ARE present, you may use them to inform sensory and contextual detail aligned with their values: materials values license mention of those materials, sensory values license those sensory details, social_character values license that character, surroundings values license those nearby features, upkeep values license that condition.
Atmospheric tags do NOT authorize structural or architectural changes. You may not invent exits beyond those listed in the exit data. You may not invent ceilings, doors, archways, windows, vaulted spaces, or any other architectural feature not established by the room's structural tags. You may not redescribe the room's shape or exit count beyond what the exit data and structural tags provide.
Banned nouns from the constraint block remain forbidden regardless of atmospheric context.
Write each description with these craft principles:
- Engage at least two senses. Sight is default; pair it with smell, sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room: a particular sensory detail, material, or sound that makes this room different from a neighboring one. Avoid generic phrases like "worn smooth by countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use adjectives sparingly.
- Never use "you" or address the reader. Write in third-person descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that could be picked up.
- Aim for 3 to 5 sentences.
Examples of the craft level expected:
URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior, function: tavern, named_feature: hearth, materials: timber-walls, planked-floor, sensory: cooking-smell, social_character: working-class):
Low-hanging timber beams, blackened with age and smoke, make this cramped tavern room feel intimate. The plank floor is sticky underfoot, and the sharp scent of roasted meat cuts through the smell of stale ale. A hearth set into the far wall throws unsteady light across the room, catching on the rough grain of the walls.
WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage, surroundings: forest-nearby, sensory: quiet-ambient, materials: dirt-floor):
Sunlight barely filters through the dense canopy, leaving the forest floor in green twilight. A dirt path, half-covered with moss, twists between ancient oaks. The chirping of birds carries through the branches, then cuts short, as if something nearby has gone still.
These examples show what "engaging two senses," "one specific anchor," and "show don't tell" look like in practice. Ma
```
