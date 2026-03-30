import re
from collections.abc import Mapping

from evennia.objects.models import ObjectDB

from .flow import APPEARANCE_FIELDS, APPEARANCE_OPTIONS, GENDER_OPTIONS, format_stats_preview
from .state import CHARGEN_BASE_STATS, CHARGEN_POINT_POOL
from world.professions.professions import PROFESSION_PROFILES, resolve_profession_name
from world.races import RACE_DEFINITIONS, RACE_STATS, apply_race_modifiers_to_stats, resolve_race_name


NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z'\-]{1,23}$")
CHARGEN_MIN_STAT = 5
CHARGEN_MAX_STAT = 20
_RESERVED_NAMES = set()


def _normalize_name(name):
    text = str(name or "").strip()
    return text or None


def _normalize_race_choice(race_name):
    text = str(race_name or "").strip()
    if not text:
        return None
    normalized = resolve_race_name(text, default=None)
    if normalized in RACE_DEFINITIONS:
        return normalized
    return None


def _normalize_profession_choice(profession_name):
    text = str(profession_name or "").strip()
    if not text:
        return None
    normalized = resolve_profession_name(text, default=None)
    if normalized in PROFESSION_PROFILES:
        return normalized
    return None


def is_name_available(name, allow_reserved=False):
    normalized = _normalize_name(name)
    if not normalized:
        return False
    lowered = normalized.lower()
    if not allow_reserved and lowered in _RESERVED_NAMES:
        return False
    return not ObjectDB.objects.filter(
        db_key__iexact=normalized,
        db_typeclass_path="typeclasses.characters.Character",
    ).exists()


def validate_name(name, allow_reserved=False, check_availability=True):
    normalized = _normalize_name(name)
    if not normalized:
        return False, "You must choose a name."
    if not NAME_PATTERN.match(normalized):
        return False, "Names must be 2-24 letters and may include apostrophes or hyphens."
    if check_availability and not is_name_available(normalized, allow_reserved=allow_reserved):
        return False, "That name is not available."
    return True, None


def reserve_name(name):
    normalized = _normalize_name(name)
    ok, error = validate_name(normalized)
    if not ok:
        return False, error
    _RESERVED_NAMES.add(normalized.lower())
    return True, None


def release_name(name):
    normalized = _normalize_name(name)
    if not normalized:
        return
    _RESERVED_NAMES.discard(normalized.lower())


def preview_race_stats(base_stats, race_key):
    normalized_race = _normalize_race_choice(race_key)
    if not normalized_race:
        raise ValueError(f"Unknown race: {race_key}")
    return apply_race_modifiers_to_stats(base_stats, normalized_race, minimum=CHARGEN_MIN_STAT, maximum=CHARGEN_MAX_STAT)


def validate_stats(stats):
    if not isinstance(stats, Mapping):
        return False, "Stats must be a mapping."
    for stat_name in RACE_STATS:
        if stat_name not in stats:
            return False, f"Missing stat: {stat_name}"
        try:
            value = int(stats.get(stat_name))
        except (TypeError, ValueError):
            return False, f"Invalid stat value for {stat_name}."
        if value < CHARGEN_MIN_STAT or value > CHARGEN_MAX_STAT:
            return False, f"{stat_name.capitalize()} must stay between {CHARGEN_MIN_STAT} and {CHARGEN_MAX_STAT}."
    return True, None


def validate_profession(profession, required=False):
    if profession in (None, ""):
        return (False, "You must choose a profession.") if required else (True, None)
    if not _normalize_profession_choice(profession):
        return False, f"Unknown profession: {profession}"
    return True, None


def validate_race(race_key):
    if not _normalize_race_choice(race_key):
        return False, f"Unknown race: {race_key}"
    return True, None


def validate_gender(gender):
    normalized = str(gender or "").strip().lower()
    if normalized not in GENDER_OPTIONS:
        return False, f"Choose one of these gender values: {', '.join(GENDER_OPTIONS)}."
    return True, None


def validate_step_input(step, value, state=None):
    normalized_step = str(step or "").strip().lower()
    if normalized_step == "name":
        return validate_name(value)
    if normalized_step == "race":
        return validate_race(value)
    if normalized_step == "gender":
        return validate_gender(value)
    if normalized_step == "profession":
        return validate_profession(value, required=False)
    if normalized_step == "stats":
        return validate_stats(value)
    if normalized_step == "description":
        return validate_appearance_complete(state)
    if normalized_step == "confirm":
        return True, None
    return False, f"Unknown chargen step: {step}"


def validate_appearance_value(field, value):
    normalized_field = str(field or "").strip().lower()
    if normalized_field not in APPEARANCE_OPTIONS:
        return False, f"Unknown appearance field: {field}"
    normalized_value = str(value or "").strip().lower()
    if normalized_value not in APPEARANCE_OPTIONS[normalized_field]:
        choices = ", ".join(APPEARANCE_OPTIONS[normalized_field])
        return False, f"Choose one of these {normalized_field} values: {choices}."
    return True, None


def validate_appearance_complete(state):
    appearance = dict(getattr(state, "appearance", {}) or {})
    missing = [field for field in APPEARANCE_FIELDS if not appearance.get(field)]
    if missing:
        return False, "Finish your appearance selections first: " + ", ".join(missing)
    return True, None


def build_description_from_appearance(state):
    ok, error = validate_appearance_complete(state)
    if not ok:
        raise ValueError(error)
    appearance = dict(getattr(state, "appearance", {}) or {})
    article = "An" if str(appearance["height"])[0].lower() in "aeiou" else "A"
    return (
        f"{article} {appearance['height']}, {appearance['build']} figure with {appearance['skin']} skin, "
        f"{appearance['hair']} hair, and {appearance['eyes']} eyes."
    )


def format_stat_assignment_summary(state):
    return format_stats_preview(build_final_stats(state), getattr(state, "points_remaining", 0))


def reset_stat_allocation(state):
    state.base_stats = dict(CHARGEN_BASE_STATS)
    state.allocated_points = {}
    state.points_remaining = CHARGEN_POINT_POOL
    return build_final_stats(state)


def apply_stat_allocation(state, stat, amount):
    stat_name = str(stat or "").strip().lower()
    if stat_name not in RACE_STATS:
        raise ValueError(f"Unknown stat: {stat}")

    delta = int(amount or 0)
    base_stats = dict(getattr(state, "base_stats", {}) or {})
    allocated = dict(getattr(state, "allocated_points", {}) or {})
    current_base = int(base_stats.get(stat_name, CHARGEN_MIN_STAT))
    current_bonus = int(allocated.get(stat_name, 0) or 0)
    new_value = current_base + current_bonus + delta
    if new_value < CHARGEN_MIN_STAT or new_value > CHARGEN_MAX_STAT:
        raise ValueError(f"{stat_name} must stay between {CHARGEN_MIN_STAT} and {CHARGEN_MAX_STAT}.")

    points_remaining = int(getattr(state, "points_remaining", 0) or 0)
    if delta > points_remaining:
        raise ValueError("Not enough points remaining.")

    allocated[stat_name] = current_bonus + delta
    state.allocated_points = allocated
    state.points_remaining = points_remaining - delta
    return build_final_stats(state)


def build_final_stats(state):
    base_stats = dict(getattr(state, "base_stats", {}) or {})
    allocated = dict(getattr(state, "allocated_points", {}) or {})
    combined = {}
    for stat_name in RACE_STATS:
        combined[stat_name] = int(base_stats.get(stat_name, CHARGEN_MIN_STAT) or CHARGEN_MIN_STAT) + int(allocated.get(stat_name, 0) or 0)

    race_key = getattr(getattr(state, "blueprint", None), "race", None)
    if race_key:
        return preview_race_stats(combined, race_key)
    return combined
