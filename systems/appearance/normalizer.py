from collections.abc import Mapping
import logging
import re


LOGGER = logging.getLogger(__name__)

_APPEARANCE_SENTENCE_RE = re.compile(
    r"^(?:you are a|you are an|a|an)\s+(?P<height>[a-z][a-z\-]*)\s+(?P<build>[a-z][a-z\-]*)\s+(?P<race>[a-z][a-z\- ]*?)(?:\s+with\s+(?P<details>.+))?\.?$",
    re.IGNORECASE,
)


def _normalize_text(value):
    text = str(value or "").strip()
    return text or None


def _normalize_feature_list(value):
    if isinstance(value, list):
        return [str(entry).strip() for entry in value if str(entry or "").strip()]
    return []


def _merge_nonempty_nested_dict(base, override):
    merged = dict(base or {})
    for key, value in dict(override or {}).items():
        existing = merged.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            merged[key] = _merge_nonempty_nested_dict(existing, value)
            continue
        if value in (None, "", []):
            continue
        merged[key] = value
    return merged


def normalize_appearance_data(appearance=None):
    raw = dict(appearance or {}) if isinstance(appearance, Mapping) else {}

    hair_raw = raw.get("hair")
    eyes_raw = raw.get("eyes")
    skin_raw = raw.get("skin")

    hair = dict(hair_raw) if isinstance(hair_raw, Mapping) else {}
    eyes = dict(eyes_raw) if isinstance(eyes_raw, Mapping) else {}
    skin = dict(skin_raw) if isinstance(skin_raw, Mapping) else {}

    if raw.get("hair") and not isinstance(hair_raw, Mapping):
        hair["color"] = raw.get("hair")
    if raw.get("hair_color"):
        hair["color"] = raw.get("hair_color")
    if raw.get("hair_style"):
        hair["style"] = raw.get("hair_style")

    if raw.get("eyes") and not isinstance(eyes_raw, Mapping):
        eyes["color"] = raw.get("eyes")
    if raw.get("eye_color"):
        eyes["color"] = raw.get("eye_color")

    if raw.get("skin") and not isinstance(skin_raw, Mapping):
        skin["tone"] = raw.get("skin")
    if raw.get("skin_tone"):
        skin["tone"] = raw.get("skin_tone")

    return {
        "build": _normalize_text(raw.get("build")),
        "height": _normalize_text(raw.get("height")),
        "hair": {
            "color": _normalize_text(hair.get("color")),
            "style": _normalize_text(hair.get("style")),
        },
        "eyes": {
            "color": _normalize_text(eyes.get("color")),
        },
        "skin": {
            "tone": _normalize_text(skin.get("tone")),
        },
        "age": _normalize_text(raw.get("age")),
        "features": _normalize_feature_list(raw.get("features")),
    }


def _extract_appearance_from_desc(desc):
    text = str(desc or "").strip().rstrip(".")
    if not text:
        return {}

    match = _APPEARANCE_SENTENCE_RE.match(text)
    if not match:
        return {}

    details = str(match.group("details") or "").strip()
    appearance = {
        "height": _normalize_text(match.group("height")),
        "build": _normalize_text(match.group("build")),
    }

    hair = {}
    eyes = {}
    skin = {}
    if details:
        detail_entries = re.split(r",\s+and\s+|,\s*|\s+and\s+", details)
        for entry in detail_entries:
            normalized = _normalize_text(entry)
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered.endswith(" hair"):
                hair["color"] = normalized[:-5].strip()
            elif lowered.endswith(" eyes"):
                eyes["color"] = normalized[:-5].strip()
            elif lowered.endswith(" skin"):
                skin["tone"] = normalized[:-5].strip()

    if hair:
        appearance["hair"] = hair
    if eyes:
        appearance["eyes"] = eyes
    if skin:
        appearance["skin"] = skin
    return appearance


def extract_identity_hints_from_desc(desc):
    text = str(desc or "").strip().rstrip(".")
    if not text:
        return {}

    match = _APPEARANCE_SENTENCE_RE.match(text)
    if not match:
        return {}

    return {
        "race": _normalize_text(match.group("race")),
        "appearance": _extract_appearance_from_desc(text),
    }


def normalize_identity_data(identity=None, *, fallback_race=None, fallback_gender=None, fallback_appearance=None):
    raw = dict(identity or {}) if isinstance(identity, Mapping) else {}
    base_appearance = normalize_appearance_data(fallback_appearance)
    raw_appearance_source = raw.get("appearance") if isinstance(raw.get("appearance"), Mapping) else {}
    raw_appearance = normalize_appearance_data(raw_appearance_source)
    return {
        "race": _normalize_text(raw.get("race")) or _normalize_text(fallback_race),
        "gender": _normalize_text(raw.get("gender")) or _normalize_text(fallback_gender),
        "appearance": _merge_nonempty_nested_dict(base_appearance, raw_appearance),
    }


def is_identity_renderable(identity):
    appearance = dict((identity or {}).get("appearance") or {})
    hair = dict(appearance.get("hair") or {})
    eyes = dict(appearance.get("eyes") or {})
    return bool(appearance.get("build") and appearance.get("height") and hair.get("color") and eyes.get("color"))


def build_identity_report(character):
    dbref = getattr(character, "db", None)
    raw_identity = getattr(dbref, "identity", None)
    raw_identity_dict = dict(raw_identity) if isinstance(raw_identity, Mapping) else {}
    desc_hints = extract_identity_hints_from_desc(getattr(dbref, "desc", None))
    normalized_identity = normalize_identity_data(
        raw_identity,
        fallback_race=getattr(dbref, "race", None) or desc_hints.get("race"),
        fallback_gender=getattr(dbref, "gender", None),
        fallback_appearance=desc_hints.get("appearance"),
    )
    return {
        "missing_identity": not isinstance(raw_identity, Mapping) or not raw_identity_dict,
        "needs_repair": raw_identity_dict != normalized_identity,
        "renderable": is_identity_renderable(normalized_identity),
        "fallback_used": bool(getattr(getattr(character, "ndb", None), "_identity_fallback_used", False)),
        "identity": normalized_identity,
        "raw_identity": raw_identity_dict,
    }


def normalize_character_identity(character, *, log_repairs=True):
    dbref = getattr(character, "db", None)
    report = build_identity_report(character)
    normalized_identity = report["identity"]
    repaired = report["needs_repair"]
    if repaired:
        dbref.identity = normalized_identity
        if log_repairs and not getattr(getattr(character, "ndb", None), "_identity_auto_heal_logged", False):
            LOGGER.info("[IDENTITY AUTO-HEAL] %s", getattr(character, "key", character))
            character.ndb._identity_auto_heal_logged = True
        if getattr(character, "ndb", None) is not None:
            character.ndb._identity_auto_healed = True
    return normalized_identity, repaired


def inspect_character_identity(character):
    return build_identity_report(character)
