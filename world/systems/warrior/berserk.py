BERSERK_DATA = {
    "power": {
        "name": "Power",
        "minimum_tempo_ratio": 0.50,
        "minimum_state": "surging",
        "drain_per_tick": 3,
        "damage_multiplier": 1.20,
        "fatigue_cost_bonus": 3,
        "start_message": "You give yourself over to the rhythm of battle.",
        "end_message": "The fury fades, leaving you exposed.",
    },
    "stone": {
        "name": "Stone",
        "minimum_tempo_ratio": 0.50,
        "minimum_state": "building",
        "drain_per_tick": 2,
        "defense_bonus": 8,
        "balance_resist_bonus": 35,
        "start_message": "You give yourself over to the rhythm of battle.",
        "end_message": "The fury fades, leaving you exposed.",
    },
    "speed": {
        "name": "Speed",
        "minimum_tempo_ratio": 0.50,
        "minimum_state": "surging",
        "drain_per_tick": 4,
        "accuracy_bonus": 5,
        "roundtime_modifier": -1.0,
        "damage_multiplier": 0.90,
        "start_message": "You give yourself over to the rhythm of battle.",
        "end_message": "The fury fades, leaving you exposed.",
    },
}


def format_berserk_name(key):
    return BERSERK_DATA.get(key, {}).get("name", str(key or "").replace("_", " ").title())


def get_berserk_profile(key):
    normalized = str(key or "").strip().lower()
    data = BERSERK_DATA.get(normalized)
    if not data:
        return None
    profile = dict(data)
    profile["key"] = normalized
    return profile