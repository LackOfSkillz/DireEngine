from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from world.builder.schemas.room_tag_schema import normalize_room_tags


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


def assemble_room_description_prompt(room: dict | None, zone: dict | None, *, max_prompt_chars: int = 5000) -> RoomDescriptionPrompt:
    room_payload = room or {}
    zone_payload = zone or {}
    generation_context = zone_payload.get("generation_context") or {}

    room_id = str(room_payload.get("id") or room_payload.get("name") or "unnamed_room").strip() or "unnamed_room"
    room_name = str(room_payload.get("name") or "").strip()
    zone_name = str(zone_payload.get("name") or zone_payload.get("zone_id") or "Unknown Zone").strip()
    exit_directions = _normalized_exit_directions(room_payload)
    shape = _derive_shape(exit_directions)
    shape_hint = _shape_hint(shape)
    zone_context_sections = _build_zone_context_sections(zone_name, generation_context)
    room_tag_sections = _build_room_tag_sections(room_payload)
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

    model_user_lines = [
        "Write a room description for Dragonsire.",
        f"Prompt version: {PROMPT_VERSION}",
        f"Room id: {room_id}",
    ]
    if room_name and room_name != room_id:
        model_user_lines.append(f"Room name: {room_name}")
    if zone_context_sections:
        model_user_lines.extend(zone_context_sections)
    if room_tag_sections:
        model_user_lines.extend(room_tag_sections)
    model_user_lines.extend([
        f"Zone: {zone_name}",
        f"Room shape: {shape}",
        f"Number of exits: {len(exit_directions)}",
        f"Shape hint: {shape_hint}",
        "Exits:",
        *([f"- {direction}" for direction in exit_directions] or ["- none"]),
        "Constraints:",
        "- You must only describe what is directly supported by the provided room data.",
        "- If a detail is not present in the input, you must omit it.",
        "- Do not infer or fill in missing scene details.",
        "- Do not invent structures, lighting, weather, materials, history, lore, or environmental features not explicitly present.",
        "- Write 3 to 5 sentences.",
        "- Do not write fewer than 3 sentences.",
        "- Do not exceed 5 sentences.",
        "- Structure your description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.",
        "- Descriptions shorter than 3 sentences are invalid.",
        "- You may expand only on elements that already exist in the input.",
        "- Allowed expansions: condition, scale, surface detail only when a surface is already present, and spatial relationships tied to exits.",
        "- You may describe how exits branch, narrow, open, or continue from the space.",
        "- You may NOT introduce any physical objects not explicitly present in the input.",
        "- This includes doors, windows, structures, furniture, vegetation, and architectural elements.",
        "- If an object is not listed in the input, it must not appear in the description.",
        "- Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.",
        "- Do not invent spatial properties such as slope, elevation, curvature, or enclosure. Describe only spatial relationships directly supported by exits and shape.",
        "- You may only use physical nouns from the input data or this neutral set: floor, walls, space, passage, path.",
        "- Do not describe intent or purpose. Avoid phrases like designed for, meant for, used for, or intended for.",
        "- If room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.",
        "- Do not produce mechanical or system-style descriptions such as 'Enclosed room, no exits.'",
        "- Always anchor the description to exit count, exit directions, and room shape.",
        "- Use neutral descriptive language. Avoid poetic, dramatic, or narrative phrasing.",
        "- Avoid metaphor and personification.",
        "- You may include basic sensory detail only if directly implied by the input, limited to texture or spatial feel such as rough, smooth, tight, or open.",
        "- Avoid vague filler such as 'there is a sense of', 'suggests', or 'appears to be'.",
        "- Do not start every sentence with 'The room', 'The space', 'The walls', or 'The floor'. Vary sentence openings naturally.",
        "- Use varied sentence structures across spatial statement, exit relationship, surface detail, and spatial transition.",
        "- Prioritize describing layout, exits, and spatial relationships before any surface detail.",
        "- Surface descriptions should be minimal and used no more than once per description.",
        "- Do not restate the same spatial fact in multiple ways.",
        "- Do not use these phrases: in the heart of, the air is thick with, whispers secrets, forgotten, ancient, shrouded, mysterious, hidden, long-abandoned.",
        "- Return one plain paragraph only.",
        "- Do not mention game mechanics, YAML, metadata, or the player.",
    ])

    system_prompt = load_room_description_system_prompt()
    base_prompt = f"{system_prompt}\n\n" + "\n".join(model_user_lines)
    if len(base_prompt) <= max_prompt_chars:
        return RoomDescriptionPrompt(system_prompt=system_prompt, user_prompt="\n".join(legacy_user_lines), prompt=base_prompt, trimmed=False)

    trimmed = False
    compact_exit_lines = [f"- {direction}" for direction in exit_directions]
    if compact_exit_lines:
        compact_exit_lines, exit_trimmed = _trim_lines(compact_exit_lines, max(1, max_prompt_chars - len(system_prompt) - 300))
        trimmed = trimmed or exit_trimmed
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

    model_user_lines = [
        "Write a room description for Dragonsire.",
        f"Prompt version: {PROMPT_VERSION}",
        f"Room id: {room_id}",
    ]
    if room_name and room_name != room_id:
        model_user_lines.append(f"Room name: {room_name}")
    if zone_context_sections:
        model_user_lines.extend(zone_context_sections)
    if room_tag_sections:
        model_user_lines.extend(room_tag_sections)
    model_user_lines.extend([
        f"Zone: {zone_name}",
        f"Room shape: {shape}",
        f"Number of exits: {len(exit_directions)}",
        f"Shape hint: {shape_hint}",
        "Exits:",
        *(compact_exit_lines or ["- none"]),
        "Constraints:",
        "- Use only directly supported room data.",
        "- Omit any detail not present in the input.",
        "- Write 3 to 5 neutral descriptive sentences.",
        "- Anchor to exits and room shape.",
        "- Expand only with condition, scale, one minimal surface detail when supported, and exit relationships.",
        "- For sparse rooms, still produce 3 sentences without introducing new features.",
        "- Do not introduce new physical nouns or implied objects.",
        "- Use only input nouns plus floor, walls, space, passage, or path.",
        "- Do not invent slope, elevation, curvature, or enclosure.",
        "- Do not describe purpose or intent.",
        "- Do not produce mechanical or system-style wording.",
        "- Use plain, concrete language only.",
        "- Vary sentence openings.",
        "- Prioritize layout, exits, and spatial relationships before surface detail.",
        "- Do not restate the same spatial fact twice.",
        "- Do not use banned fantasy filler phrases.",
        "- Do not mention game mechanics, YAML, metadata, or the player.",
    ])
    user_prompt = "\n".join(legacy_user_lines)
    prompt = f"{system_prompt}\n\n" + "\n".join(model_user_lines)
    if len(prompt) > max_prompt_chars:
        prompt = prompt[:max_prompt_chars].rstrip()
        trimmed = True
    return RoomDescriptionPrompt(system_prompt=system_prompt, user_prompt=user_prompt, prompt=prompt, trimmed=trimmed)