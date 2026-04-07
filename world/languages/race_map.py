RACE_LANGUAGES = {
    "human": ("common",),
    "elf": ("common",),
    "dwarf": ("common",),
    "halfling": ("common",),
    "gnome": ("common",),
    "volgrin": ("common", "volgrin"),
    "saurathi": ("common", "saurathi"),
    "valran": ("common", "valran"),
    "aethari": ("common", "aethari"),
    "felari": ("common", "felari"),
    "lunari": ("common", "lunari"),
}


def _normalize_race_name(race_name, default="human"):
    normalized = str(race_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in RACE_LANGUAGES:
        return normalized
    return default


def get_languages_for_race(race_name):
    race_key = _normalize_race_name(race_name)
    return tuple(RACE_LANGUAGES.get(race_key, ("common",)))