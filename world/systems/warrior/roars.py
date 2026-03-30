ROAR_CATEGORIES = {
    "offensive": "Offensive",
    "defensive": "Defensive",
    "control": "Control",
    "group": "Group",
}

ROAR_DATA = {
    "intimidate": {
        "name": "Intimidate",
        "foundation": "intimidate",
        "category": "offensive",
        "slot": "offensive",
        "target_scope": "multi",
        "tempo_cost": 20,
        "duration": 12,
        "pressure_gain": 6,
        "target_accuracy_penalty": 3,
        "start_message": "You unleash a harsh, intimidating roar.",
    },
    "disrupt": {
        "name": "Disrupt",
        "foundation": "intimidate",
        "category": "control",
        "slot": "control",
        "target_scope": "single",
        "tempo_cost": 25,
        "duration": 15,
        "pressure_gain": 8,
        "target_accuracy_penalty": 6,
        "balance_recovery_penalty": 1,
        "start_message": "You roar to disrupt your foe's composure.",
    },
    "unnerving": {
        "name": "Unnerving",
        "foundation": "intimidate",
        "category": "control",
        "slot": "control",
        "target_scope": "single",
        "tempo_cost": 30,
        "duration": 15,
        "pressure_gain": 12,
        "target_accuracy_penalty": 8,
        "start_message": "You loose an unnerving roar that presses in on your enemy.",
    },
    "rally": {
        "name": "Rally",
        "foundation": "rally",
        "category": "defensive",
        "slot": "defensive",
        "target_scope": "self",
        "tempo_cost": 20,
        "duration": 12,
        "defense_bonus": 4,
        "balance_restore": 10,
        "fatigue_restore": 10,
        "start_message": "You roar and reclaim your footing.",
    },
    "challenge": {
        "name": "Challenge",
        "foundation": "rally",
        "category": "defensive",
        "slot": "defensive",
        "target_scope": "single",
        "tempo_cost": 22,
        "duration": 15,
        "defense_bonus": 6,
        "pressure_gain": 5,
        "start_message": "You issue a hard challenge and draw the fight toward you.",
    },
    "rallying": {
        "name": "Rallying Cry",
        "foundation": "rally",
        "category": "group",
        "slot": "group",
        "target_scope": "self",
        "tempo_cost": 25,
        "duration": 15,
        "rhythm_gain_bonus": 1,
        "start_message": "You unleash a rallying cry that steadies your rhythm.",
    },
}


def format_roar_name(key):
    return ROAR_DATA.get(key, {}).get("name", str(key or "").replace("_", " ").title())


def get_roar_profile(key):
    normalized = str(key or "").strip().lower()
    data = ROAR_DATA.get(normalized)
    if not data:
        return None
    profile = dict(data)
    profile["key"] = normalized
    return profile