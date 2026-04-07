from systems.appearance.normalizer import normalize_identity_data
from systems.chargen.flow import APPEARANCE_OPTIONS as CHARGEN_APPEARANCE_OPTIONS
from systems.chargen.flow import GENDER_OPTIONS
from systems.chargen.validators import validate_name
from world.races import RACE_DEFINITIONS, get_race_display_name, resolve_race_name


HAIR_STYLE_OPTIONS = (
    "cropped",
    "braided",
    "curled",
    "loose",
    "straight",
    "shaved",
)


FIELD_LABELS = {
    "gender": "Gender",
    "body_build": "Body Build",
    "skin_tone": "Skin Tone",
    "eye_color": "Eye Color",
    "hair_color": "Hair Color",
    "hair_style": "Hair Style",
}


def _labelize(value):
    return str(value or "").replace("_", " ").title()


def get_character_builder_options():
    race_options = [
        {
            "value": race_key,
            "label": get_race_display_name(race_key),
        }
        for race_key in sorted(RACE_DEFINITIONS.keys())
    ]
    return {
        "races": race_options,
        "genders": [{"value": value, "label": _labelize(value)} for value in GENDER_OPTIONS],
        "body_builds": [{"value": value, "label": _labelize(value)} for value in CHARGEN_APPEARANCE_OPTIONS["build"]],
        "skin_tones": [{"value": value, "label": _labelize(value)} for value in CHARGEN_APPEARANCE_OPTIONS["skin"]],
        "eye_colors": [{"value": value, "label": _labelize(value)} for value in CHARGEN_APPEARANCE_OPTIONS["eyes"]],
        "hair_colors": [{"value": value, "label": _labelize(value)} for value in CHARGEN_APPEARANCE_OPTIONS["hair"]],
        "hair_styles": [{"value": value, "label": _labelize(value)} for value in HAIR_STYLE_OPTIONS],
    }


def get_character_builder_config():
    return {
        "steps": [
            {"key": "name", "label": "Name"},
            {"key": "race", "label": "Race"},
            {"key": "gender", "label": "Gender"},
            {"key": "skin-build", "label": "Skin & Build"},
            {"key": "hair-eyes", "label": "Hair & Eyes"},
            {"key": "review", "label": "Review"},
        ],
        "fields": dict(FIELD_LABELS),
        "options": get_character_builder_options(),
    }


def validate_character_name(name):
    ok, error = validate_name(name)
    normalized = str(name or "").strip()
    return {
        "ok": bool(ok),
        "valid": bool(ok),
        "name": normalized,
        "error": error,
    }


def _normalize_required_choice(value, allowed_values, *, field_name):
    normalized = str(value or "").strip().lower()
    if normalized not in allowed_values:
        raise ValueError(f"Please select a valid {field_name}.")
    return normalized


def normalize_builder_payload(payload):
    raw = dict(payload or {})
    normalized_name = str(raw.get("name") or "").strip()
    name_result = validate_character_name(normalized_name)
    if not name_result["ok"]:
        raise ValueError(name_result["error"])

    race = resolve_race_name(raw.get("race"), default=None)
    if race not in RACE_DEFINITIONS:
        raise ValueError("Please select a valid race.")

    options = get_character_builder_options()
    gender = _normalize_required_choice(raw.get("gender"), {entry["value"] for entry in options["genders"]}, field_name="gender")
    body_build = _normalize_required_choice(raw.get("body_build"), {entry["value"] for entry in options["body_builds"]}, field_name="body build")
    skin_tone = _normalize_required_choice(raw.get("skin_tone"), {entry["value"] for entry in options["skin_tones"]}, field_name="skin tone")
    eye_color = _normalize_required_choice(raw.get("eye_color"), {entry["value"] for entry in options["eye_colors"]}, field_name="eye color")
    hair_color = _normalize_required_choice(raw.get("hair_color"), {entry["value"] for entry in options["hair_colors"]}, field_name="hair color")
    hair_style = _normalize_required_choice(raw.get("hair_style"), {entry["value"] for entry in options["hair_styles"]}, field_name="hair style")

    appearance = {
        "build": body_build,
        "hair": {"color": hair_color, "style": hair_style},
        "eyes": {"color": eye_color},
        "skin": {"tone": skin_tone},
    }
    identity = normalize_identity_data(
        None,
        fallback_race=race,
        fallback_gender=gender,
        fallback_appearance=appearance,
    )

    return {
        "name": normalized_name,
        "race": race,
        "gender": gender,
        "body_build": body_build,
        "skin_tone": skin_tone,
        "eye_color": eye_color,
        "hair_color": hair_color,
        "hair_style": hair_style,
        "appearance": appearance,
        "identity": identity,
    }