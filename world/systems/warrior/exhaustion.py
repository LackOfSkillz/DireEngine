EXHAUSTION_GAIN_RATES = {
    "combat_tick": 1,
    "frenzy_end_spike": 18,
    "recover_amount": 35,
    "abilities": {
        "surge": 4,
        "intimidate": 3,
        "rally": 4,
        "crush": 10,
        "press": 6,
        "sweep": 8,
        "secondwind": 5,
        "whirl": 14,
        "hold": 5,
        "frenzy": 16,
    },
    "berserk_tick": {
        "power": 3,
        "stone": 2,
        "speed": 3,
    },
}

EXHAUSTION_PENALTIES = {
    "fresh": {
        "minimum": 0,
        "maximum": 20,
        "label": "Fresh",
        "fatigue_multiplier": 1.0,
        "tempo_gain_multiplier": 1.0,
        "balance_recovery_penalty": 0,
        "accuracy_penalty": 0,
        "defense_penalty": 0,
        "action_delay_chance": 0.0,
        "collapse_chance": 0.0,
    },
    "strained": {
        "minimum": 20,
        "maximum": 40,
        "label": "Strained",
        "fatigue_multiplier": 1.1,
        "tempo_gain_multiplier": 0.95,
        "balance_recovery_penalty": 0,
        "accuracy_penalty": 0,
        "defense_penalty": 0,
        "action_delay_chance": 0.0,
        "collapse_chance": 0.0,
    },
    "faltering": {
        "minimum": 40,
        "maximum": 70,
        "label": "Faltering",
        "fatigue_multiplier": 1.2,
        "tempo_gain_multiplier": 0.85,
        "balance_recovery_penalty": 1,
        "accuracy_penalty": 4,
        "defense_penalty": 2,
        "action_delay_chance": 0.04,
        "collapse_chance": 0.0,
    },
    "severe": {
        "minimum": 70,
        "maximum": 90,
        "label": "Severe",
        "fatigue_multiplier": 1.35,
        "tempo_gain_multiplier": 0.7,
        "balance_recovery_penalty": 2,
        "accuracy_penalty": 8,
        "defense_penalty": 5,
        "action_delay_chance": 0.10,
        "collapse_chance": 0.05,
    },
    "collapse": {
        "minimum": 90,
        "maximum": 101,
        "label": "Near Collapse",
        "fatigue_multiplier": 1.5,
        "tempo_gain_multiplier": 0.5,
        "balance_recovery_penalty": 3,
        "accuracy_penalty": 12,
        "defense_penalty": 8,
        "action_delay_chance": 0.18,
        "collapse_chance": 0.12,
    },
}

RECOVERY_RATES = {
    "in_combat": 1,
    "out_of_combat": 6,
}


def get_exhaustion_profile(value):
    amount = max(0, min(100, int(value or 0)))
    for key, profile in EXHAUSTION_PENALTIES.items():
        minimum = int(profile.get("minimum", 0) or 0)
        maximum = int(profile.get("maximum", 100) or 100)
        if minimum <= amount < maximum:
            result = dict(profile)
            result["key"] = key
            return result
    fallback = dict(EXHAUSTION_PENALTIES["collapse"])
    fallback["key"] = "collapse"
    return fallback