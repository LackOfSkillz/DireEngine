WARRIOR_UNLOCKS = {
    5: ["surge"],
    10: ["intimidate"],
    15: ["rally"],
    20: ["crush"],
    25: ["press"],
    30: ["sweep"],
    35: ["secondwind"],
    40: ["whirl"],
    45: ["hold"],
    50: ["frenzy"],
}

WARRIOR_PASSIVES = {
    1: ["war_tempo"],
    3: ["fatigue_reduction_1"],
    7: ["tempo_gain_1"],
    12: ["balance_recovery_1"],
    17: ["tempo_decay_1"],
    22: ["weapon_handling_1"],
    27: ["balance_resist_1"],
    32: ["fatigue_resist_1"],
    37: ["multitarget_defense_1"],
    42: ["roar_duration_1"],
    47: ["overwhelmed_penalty_1"],
}

WARRIOR_ABILITY_CATEGORIES = {
    "surge": "strikes",
    "intimidate": "roars",
    "rally": "survival",
    "crush": "strikes",
    "press": "strikes",
    "sweep": "strikes",
    "secondwind": "survival",
    "whirl": "strikes",
    "hold": "survival",
    "frenzy": "survival",
}

WARRIOR_MAJOR_UNLOCKS = {"crush", "sweep", "whirl", "frenzy"}

WARRIOR_TEMPO_STATES = {
    "calm": {"name": "Calm", "minimum_ratio": 0.0, "maximum_ratio": 0.10},
    "building": {"name": "Building", "minimum_ratio": 0.10, "maximum_ratio": 0.40},
    "surging": {"name": "Surging", "minimum_ratio": 0.40, "maximum_ratio": 0.80},
    "frenzied": {"name": "Frenzied", "minimum_ratio": 0.80, "maximum_ratio": 1.01},
}

WARRIOR_ABILITY_DATA = {
    "surge": {
        "name": "Surge",
        "category": "strikes",
        "unlock_message": "You have learned Surge.",
    },
    "intimidate": {
        "name": "Intimidate",
        "category": "roars",
        "unlock_message": "You have learned Intimidate.",
    },
    "rally": {
        "name": "Rally",
        "category": "roars",
        "unlock_message": "You have learned Rally.",
    },
    "crush": {
        "name": "Crushing Blow",
        "category": "strikes",
        "unlock_message": "You have learned Crushing Blow. You feel your strikes carry new weight.",
    },
    "press": {
        "name": "Press Advantage",
        "category": "strikes",
        "unlock_message": "You have learned Press Advantage.",
    },
    "sweep": {
        "name": "Sweep",
        "category": "strikes",
        "unlock_message": "You have learned Sweep. You feel ready to seize control of a fight.",
    },
    "secondwind": {
        "name": "Second Wind",
        "category": "survival",
        "unlock_message": "You have learned Second Wind.",
    },
    "whirl": {
        "name": "Whirl",
        "category": "strikes",
        "unlock_message": "You have learned Whirl. Your reach now feels wide enough for a crowd.",
    },
    "hold": {
        "name": "Hold Ground",
        "category": "survival",
        "unlock_message": "You have learned Hold Ground.",
    },
    "frenzy": {
        "name": "Frenzy",
        "category": "survival",
        "unlock_message": "You have learned Frenzy. You stand at the edge of control and step beyond it.",
    },
}

WARRIOR_PASSIVE_DATA = {
    "war_tempo": {"name": "War Tempo", "message": "You begin to feel the rhythm of battle."},
    "fatigue_reduction_1": {"name": "Minor Fatigue Reduction", "message": "You feel your endurance improving."},
    "tempo_gain_1": {"name": "Tempo Gain I", "message": "You feel yourself settling into combat more quickly."},
    "balance_recovery_1": {"name": "Balance Recovery I", "message": "Your footing feels surer."},
    "tempo_decay_1": {"name": "Tempo Retention I", "message": "The rhythm of battle stays with you longer."},
    "weapon_handling_1": {"name": "Weapon Handling I", "message": "Your weapon handling grows more efficient."},
    "balance_resist_1": {"name": "Balance Resistance I", "message": "You feel harder to throw off balance."},
    "fatigue_resist_1": {"name": "Fatigue Resistance I", "message": "Your endurance deepens under pressure."},
    "multitarget_defense_1": {"name": "Multi-Target Defense I", "message": "You grow more aware of threats crowding in."},
    "roar_duration_1": {"name": "Roar Duration I", "message": "Your voice seems to carry farther across a fight."},
    "overwhelmed_penalty_1": {"name": "Overwhelmed Penalty I", "message": "You feel less shaken when pressed from all sides."},
}


def format_warrior_ability_name(key):
    return WARRIOR_ABILITY_DATA.get(key, {}).get("name", str(key or "").replace("_", " ").title())


def format_warrior_passive_name(key):
    return WARRIOR_PASSIVE_DATA.get(key, {}).get("name", str(key or "").replace("_", " ").title())


def format_warrior_tempo_state(state_key):
    return WARRIOR_TEMPO_STATES.get(state_key, {}).get("name", str(state_key or "").replace("_", " ").title())


def get_warrior_tempo_state(tempo, maximum=100):
    maximum = max(1, int(maximum or 100))
    ratio = max(0.0, min(1.0, float(tempo or 0) / maximum))

    if ratio <= 0.10:
        return "calm"
    if ratio <= 0.40:
        return "building"
    if ratio <= 0.80:
        return "surging"
    return "frenzied"


def get_warrior_abilities_for_circle(circle):
    circle = max(1, int(circle or 1))
    abilities = []
    for unlock_circle in sorted(WARRIOR_UNLOCKS):
        if unlock_circle > circle:
            continue
        abilities.extend(WARRIOR_UNLOCKS[unlock_circle])
    return abilities


def get_warrior_passives_for_circle(circle):
    circle = max(1, int(circle or 1))
    passives = []
    for unlock_circle in sorted(WARRIOR_PASSIVES):
        if unlock_circle > circle:
            continue
        passives.extend(WARRIOR_PASSIVES[unlock_circle])
    return passives


def get_next_warrior_unlock(circle):
    circle = max(1, int(circle or 1))
    upcoming = []
    for unlock_circle, abilities in sorted(WARRIOR_UNLOCKS.items()):
        if unlock_circle > circle:
            upcoming.extend((unlock_circle, ability_key) for ability_key in abilities)
            break
    return upcoming
