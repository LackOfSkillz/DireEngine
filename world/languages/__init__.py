from .accents import apply_accent
from .comprehension import apply_comprehension, apply_language_exposure, get_comprehension_level, garble_text, partial_text
from .definitions import LANGUAGES
from .eavesdrop import get_eavesdrop_level
from .race_map import RACE_LANGUAGES, get_languages_for_race


def normalize_language_name(language_name, default="common"):
    normalized = str(language_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in LANGUAGES:
        return normalized
    return default


def get_language_profile(language_name):
    language_key = normalize_language_name(language_name)
    profile = dict(LANGUAGES.get(language_key, LANGUAGES["common"]))
    profile["key"] = language_key
    return profile


def get_language_display_name(language_name):
    return get_language_profile(language_name).get("name", "Common")


__all__ = [
    "LANGUAGES",
    "RACE_LANGUAGES",
    "apply_accent",
    "apply_comprehension",
    "apply_language_exposure",
    "get_eavesdrop_level",
    "get_comprehension_level",
    "garble_text",
    "get_language_display_name",
    "get_language_profile",
    "get_languages_for_race",
    "normalize_language_name",
    "partial_text",
]