VALID_ENVIRONMENT_TYPES = {"wilderness", "urban", "underground", "coastal"}
VALID_TERRAIN_TYPES = {"forest", "plains", "swamp", "mountain", "urban", "coastal", "underground"}
NATURAL_TERRAIN_TYPES = {"forest", "plains", "swamp", "mountain", "coastal"}

TERRAIN_TRACKING_BONUSES = {
    "forest": 6,
    "plains": 3,
    "swamp": 5,
    "mountain": 4,
    "urban": -6,
    "coastal": 4,
    "underground": 1,
}

TERRAIN_STEALTH_BONUSES = {
    "forest": 5,
    "plains": 1,
    "swamp": 4,
    "mountain": 3,
    "urban": -5,
    "coastal": 2,
    "underground": 1,
}

TERRAIN_SNIPE_RETENTION_BONUSES = {
    "forest": 8,
    "plains": 2,
    "swamp": 6,
    "mountain": 4,
    "urban": -8,
    "coastal": 3,
    "underground": 1,
}

TERRAIN_LABELS = {
    "forest": "Forest",
    "plains": "Plains",
    "swamp": "Swamp",
    "mountain": "Mountain",
    "urban": "Urban",
    "coastal": "Coastal",
    "underground": "Underground",
}

WILDERNESS_BOND_STATES = (
    (0, 20, "disconnected", "Disconnected"),
    (20, 50, "distant", "Distant"),
    (50, 80, "attuned", "Attuned"),
    (80, 101, "wildbound", "Wildbound"),
)

ENVIRONMENT_BOND_DELTAS = {
    "wilderness": 3,
    "coastal": 2,
    "urban": -3,
    "underground": -2,
}

NATURE_FOCUS_MAX = 100

ENVIRONMENT_NATURE_FOCUS_DELTAS = {
    "wilderness": 2,
    "coastal": 1,
    "urban": -4,
    "underground": -1,
}

NATURE_FOCUS_ACTION_GAINS = {
    "focus": 12,
    "track": 5,
    "scout": 4,
    "follow_trail": 4,
    "read_land": 3,
    "blend": 2,
}

RANGER_SNIPE_CONFIG = {
    "aim_accuracy_per_stack": 5,
    "aim_damage_per_stack": 0.05,
    "bond_accuracy_scale": 8,
    "focus_accuracy_scale": 12,
    "focus_damage_scale": 20,
    "mastery_focus_threshold": 60,
    "mastery_bond_threshold": 80,
    "mastery_retention_bonus": 10,
    "mastery_crit_bonus": 8,
}

TRACKING_BONUSES = {
    "disconnected": -15,
    "distant": -5,
    "attuned": 5,
    "wildbound": 10,
}

STEALTH_BONUSES = {
    "disconnected": 0,
    "distant": 0,
    "attuned": 3,
    "wildbound": 6,
}

PERCEPTION_BONUSES = {
    "disconnected": 0,
    "distant": 0,
    "attuned": 2,
    "wildbound": 4,
}

TRAIL_DECAY_SECONDS = {
    "wilderness": 180,
    "coastal": 150,
    "urban": 75,
    "underground": 120,
}

TRACK_DIFFICULTY_BASE = {
    "wilderness": 35,
    "coastal": 40,
    "urban": 55,
    "underground": 45,
}

TRAIL_QUALITY_LABELS = (
    (75, "Fresh"),
    (45, "Clear"),
    (20, "Faint"),
    (0, "Weak"),
)


def normalize_environment_type(value, default="urban"):
    normalized = str(value or "").strip().lower()
    if normalized in VALID_ENVIRONMENT_TYPES:
        return normalized
    return default


def normalize_terrain_type(value, default="urban"):
    normalized = str(value or "").strip().lower()
    if normalized in VALID_TERRAIN_TYPES:
        return normalized
    return default


def infer_environment_type(room_key="", room_desc=""):
    text = f"{room_key} {room_desc}".lower()
    if any(token in text for token in ("beach", "dock", "shore", "coast", "harbor", "sea", "ocean")):
        return "coastal"
    if any(token in text for token in ("cave", "tunnel", "vault", "cellar", "mine", "underground", "crypt")):
        return "underground"
    if any(token in text for token in ("forest", "trail", "grove", "wild", "glade", "swamp", "wood", "riverbank", "field")):
        return "wilderness"
    return "urban"


def infer_terrain_type(room_key="", room_desc="", environment_type=""):
    text = f"{room_key} {room_desc}".lower()
    environment = normalize_environment_type(environment_type, default=infer_environment_type(room_key, room_desc))
    if any(token in text for token in ("swamp", "bog", "marsh", "fen")):
        return "swamp"
    if any(token in text for token in ("mountain", "ridge", "cliff", "peak", "crag")):
        return "mountain"
    if any(token in text for token in ("plains", "field", "grass", "meadow", "prairie")):
        return "plains"
    if any(token in text for token in ("beach", "dock", "shore", "coast", "harbor", "sea", "ocean")):
        return "coastal"
    if any(token in text for token in ("cave", "tunnel", "vault", "cellar", "mine", "underground", "crypt")):
        return "underground"
    if any(token in text for token in ("forest", "trail", "grove", "wild", "glade", "wood", "riverbank")):
        return "forest"
    if environment == "coastal":
        return "coastal"
    if environment == "underground":
        return "underground"
    if environment == "wilderness":
        return "forest"
    return "urban"


def get_wilderness_bond_profile(value):
    amount = max(0, min(100, int(value or 0)))
    for minimum, maximum, key, label in WILDERNESS_BOND_STATES:
        if minimum <= amount < maximum:
            return {"minimum": minimum, "maximum": maximum, "key": key, "label": label}
    return {"minimum": 80, "maximum": 101, "key": "wildbound", "label": "Wildbound"}


def get_trail_quality_label(strength):
    amount = max(0, min(100, int(strength or 0)))
    for minimum, label in TRAIL_QUALITY_LABELS:
        if amount >= minimum:
            return label
    return "Weak"


def get_terrain_label(value):
    return TERRAIN_LABELS.get(normalize_terrain_type(value), "Urban")