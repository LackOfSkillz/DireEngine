import hashlib
import re
from collections.abc import Mapping


_WORD_RE = re.compile(r"^(?P<core>[A-Za-z0-9']+)(?P<suffix>[^A-Za-z0-9']*)$")


def _normalize_language_name(language_name, default="common"):
    normalized = str(language_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or default


def _clamp_level(level):
    try:
        value = float(level)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, value))


def _stable_fraction(*parts):
    seed = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return int(digest, 16) / 0xFFFFFFFF


def get_comprehension_level(listener, language):
    language_key = _normalize_language_name(language)
    overrides = getattr(getattr(listener, "db", None), "language_comprehension_overrides", None)
    if isinstance(overrides, Mapping) and language_key in overrides:
        return _clamp_level(overrides.get(language_key))

    if listener and hasattr(listener, "get_language_proficiency"):
        return _clamp_level(listener.get_language_proficiency(language_key))

    return 0.0


def apply_language_exposure(listener, language, amount=0.01):
    language_key = _normalize_language_name(language)
    if not listener or not hasattr(listener, "learn_language"):
        return 0.0
    return listener.learn_language(language_key, amount)


def garble_text(text):
    symbols = ("?", "*", "#")
    output = []
    for index, char in enumerate(str(text or "")):
        if char.isspace() or not char.isalnum():
            output.append(char)
        else:
            output.append(symbols[index % len(symbols)])
    return "".join(output)


def partial_text(text, level=0.5, seed=None):
    comprehension = _clamp_level(level)
    tokens = re.split(r"(\s+)", str(text or ""))
    visible_threshold = comprehension
    entries = []

    for index, token in enumerate(tokens):
        if not token or token.isspace():
            entries.append({"token": token, "eligible": False, "visible": True, "score": None, "suffix": ""})
            continue
        if not any(char.isalnum() for char in token):
            entries.append({"token": token, "eligible": False, "visible": True, "score": None, "suffix": ""})
            continue

        match = _WORD_RE.match(token)
        if match:
            core = match.group("core")
            suffix = match.group("suffix")
        else:
            core = token
            suffix = ""

        score = _stable_fraction(seed, index, core.lower())
        entries.append(
            {
                "token": token,
                "eligible": True,
                "visible": score <= visible_threshold,
                "score": score,
                "suffix": suffix,
            }
        )

    eligible_indexes = [index for index, entry in enumerate(entries) if entry["eligible"]]
    if len(eligible_indexes) > 1 and 0.0 < comprehension < 1.0:
        visible_indexes = [index for index in eligible_indexes if entries[index]["visible"]]
        hidden_indexes = [index for index in eligible_indexes if not entries[index]["visible"]]
        if not visible_indexes:
            reveal_index = min(eligible_indexes, key=lambda index: entries[index]["score"])
            entries[reveal_index]["visible"] = True
            hidden_indexes = [index for index in eligible_indexes if not entries[index]["visible"]]
        if not hidden_indexes:
            hide_index = max(eligible_indexes, key=lambda index: entries[index]["score"])
            entries[hide_index]["visible"] = False

    output = []
    for entry in entries:
        if not entry["eligible"] or entry["visible"]:
            output.append(entry["token"])
        else:
            output.append(f"...{entry['suffix']}")
    return "".join(output)


def apply_comprehension(text, level, seed=None):
    comprehension = _clamp_level(level)
    if comprehension >= 1.0:
        return str(text or "")
    if comprehension <= 0.0:
        return garble_text(text)
    return partial_text(text, level=comprehension, seed=seed)