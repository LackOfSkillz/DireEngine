RACE_STATS = (
    "strength",
    "agility",
    "reflex",
    "intelligence",
    "wisdom",
    "stamina",
)

RACE_LEARNING_CATEGORIES = (
    "combat",
    "survival",
    "magic",
    "stealth",
    "lore",
)

SIZE_CATEGORIES = ("small", "medium", "large")

DEFAULT_RACE = "human"
BASE_STAT_CAP = 100
BASE_CARRY_WEIGHT = 100.0
MIN_STAT_MODIFIER = -2
MAX_STAT_MODIFIER = 2
MIN_STAT_CAP = 95
MAX_STAT_CAP = 110
MIN_LEARNING_MODIFIER = 0.85
MAX_LEARNING_MODIFIER = 1.15
MIN_CARRY_MODIFIER = 0.8
MAX_CARRY_MODIFIER = 1.3

RACE_ALIASES = {
    "gor tog": "gor_togh",
    "gor-togh": "gor_togh",
    "gor'togh": "gor_togh",
    "gortogh": "gor_togh",
    "s'kra mur": "s_kra_mur",
    "s’kra mur": "s_kra_mur",
    "s-kra mur": "s_kra_mur",
    "skra mur": "s_kra_mur",
    "skramur": "s_kra_mur",
}

RACE_DEFINITIONS = {
    "human": {
        "name": "Human",
        "stat_modifiers": {stat: 0 for stat in RACE_STATS},
        "stat_caps": {stat: BASE_STAT_CAP for stat in RACE_STATS},
        "learning_modifiers": {category: 1.0 for category in RACE_LEARNING_CATEGORIES},
        "size": "medium",
        "carry_modifier": 1.0,
        "description": "Humans are balanced generalists with no strong racial extremes.",
    },
    "elf": {
        "name": "Elf",
        "stat_modifiers": {
            "strength": -1,
            "agility": 2,
            "reflex": 1,
            "intelligence": 1,
            "wisdom": 0,
            "stamina": -1,
        },
        "stat_caps": {
            "strength": 95,
            "agility": 110,
            "reflex": 108,
            "intelligence": 105,
            "wisdom": 100,
            "stamina": 95,
        },
        "learning_modifiers": {
            "combat": 0.95,
            "survival": 1.0,
            "magic": 1.15,
            "stealth": 1.05,
            "lore": 1.05,
        },
        "size": "medium",
        "carry_modifier": 0.9,
        "description": "Elves favor agility, reflex, and arcane refinement over raw endurance.",
    },
    "dwarf": {
        "name": "Dwarf",
        "stat_modifiers": {
            "strength": 2,
            "agility": -1,
            "reflex": -1,
            "intelligence": 0,
            "wisdom": 0,
            "stamina": 2,
        },
        "stat_caps": {
            "strength": 110,
            "agility": 95,
            "reflex": 95,
            "intelligence": 100,
            "wisdom": 100,
            "stamina": 110,
        },
        "learning_modifiers": {
            "combat": 1.15,
            "survival": 1.05,
            "magic": 0.9,
            "stealth": 0.9,
            "lore": 1.0,
        },
        "size": "medium",
        "carry_modifier": 1.2,
        "description": "Dwarves trade speed for durability, strength, and deep physical resilience.",
    },
    "halfling": {
        "name": "Halfling",
        "stat_modifiers": {
            "strength": -1,
            "agility": 2,
            "reflex": 2,
            "intelligence": 0,
            "wisdom": 0,
            "stamina": -1,
        },
        "stat_caps": {
            "strength": 95,
            "agility": 110,
            "reflex": 110,
            "intelligence": 100,
            "wisdom": 100,
            "stamina": 95,
        },
        "learning_modifiers": {
            "combat": 0.95,
            "survival": 1.05,
            "magic": 0.95,
            "stealth": 1.15,
            "lore": 1.0,
        },
        "size": "small",
        "carry_modifier": 0.8,
        "description": "Halflings are quick, subtle, and hard to pin down, but lightly built.",
    },
    "gnome": {
        "name": "Gnome",
        "stat_modifiers": {
            "strength": -1,
            "agility": 1,
            "reflex": 0,
            "intelligence": 2,
            "wisdom": 1,
            "stamina": -1,
        },
        "stat_caps": {
            "strength": 95,
            "agility": 105,
            "reflex": 100,
            "intelligence": 110,
            "wisdom": 105,
            "stamina": 95,
        },
        "learning_modifiers": {
            "combat": 0.95,
            "survival": 1.0,
            "magic": 1.1,
            "stealth": 1.0,
            "lore": 1.15,
        },
        "size": "small",
        "carry_modifier": 0.9,
        "description": "Gnomes lean toward intellect and lore, with sharp minds and modest frames.",
    },
    "gor_togh": {
        "name": "Gor'Togh",
        "stat_modifiers": {
            "strength": 2,
            "agility": -2,
            "reflex": -1,
            "intelligence": -1,
            "wisdom": 0,
            "stamina": 2,
        },
        "stat_caps": {
            "strength": 110,
            "agility": 95,
            "reflex": 95,
            "intelligence": 95,
            "wisdom": 100,
            "stamina": 110,
        },
        "learning_modifiers": {
            "combat": 1.15,
            "survival": 1.05,
            "magic": 0.85,
            "stealth": 0.85,
            "lore": 0.95,
        },
        "size": "large",
        "carry_modifier": 1.3,
        "description": "Gor'Togh are immense and powerful, built to bear strain rather than move lightly.",
    },
    "s_kra_mur": {
        "name": "S'Kra Mur",
        "stat_modifiers": {
            "strength": 1,
            "agility": 0,
            "reflex": 0,
            "intelligence": 0,
            "wisdom": 1,
            "stamina": 1,
        },
        "stat_caps": {
            "strength": 105,
            "agility": 100,
            "reflex": 100,
            "intelligence": 100,
            "wisdom": 105,
            "stamina": 105,
        },
        "learning_modifiers": {
            "combat": 1.05,
            "survival": 1.1,
            "magic": 1.0,
            "stealth": 0.95,
            "lore": 1.0,
        },
        "size": "medium",
        "carry_modifier": 1.1,
        "description": "S'Kra Mur balance hardiness and instinct, with a steady edge in survival.",
    },
    "kaldar": {
        "name": "Kaldar",
        "stat_modifiers": {
            "strength": 2,
            "agility": 0,
            "reflex": 0,
            "intelligence": -1,
            "wisdom": 0,
            "stamina": 1,
        },
        "stat_caps": {
            "strength": 110,
            "agility": 100,
            "reflex": 100,
            "intelligence": 95,
            "wisdom": 100,
            "stamina": 105,
        },
        "learning_modifiers": {
            "combat": 1.1,
            "survival": 1.05,
            "magic": 0.95,
            "stealth": 0.95,
            "lore": 1.0,
        },
        "size": "medium",
        "carry_modifier": 1.15,
        "description": "Kaldar emphasize strength and stamina, with a bluntly practical physical bias.",
    },
}


def _validate_race_definitions():
    for race_key, profile in RACE_DEFINITIONS.items():
        stat_modifiers = dict(profile.get("stat_modifiers", {}))
        stat_caps = dict(profile.get("stat_caps", {}))
        learning_modifiers = dict(profile.get("learning_modifiers", {}))
        size = str(profile.get("size", "")).strip().lower()
        carry_modifier = float(profile.get("carry_modifier", 1.0) or 1.0)

        if tuple(sorted(stat_modifiers.keys())) != tuple(sorted(RACE_STATS)):
            raise ValueError(f"Race {race_key} must define exactly the locked race stats.")
        if tuple(sorted(stat_caps.keys())) != tuple(sorted(RACE_STATS)):
            raise ValueError(f"Race {race_key} must define exactly the locked race stat caps.")
        if tuple(sorted(learning_modifiers.keys())) != tuple(sorted(RACE_LEARNING_CATEGORIES)):
            raise ValueError(f"Race {race_key} must define exactly the locked learning categories.")
        if size not in SIZE_CATEGORIES:
            raise ValueError(f"Race {race_key} has invalid size {size!r}.")
        if not (MIN_CARRY_MODIFIER <= carry_modifier <= MAX_CARRY_MODIFIER):
            raise ValueError(f"Race {race_key} has invalid carry modifier {carry_modifier}.")

        for stat, value in stat_modifiers.items():
            value = int(value or 0)
            if value < MIN_STAT_MODIFIER or value > MAX_STAT_MODIFIER:
                raise ValueError(f"Race {race_key} modifier for {stat} is out of range: {value}.")

        for stat, value in stat_caps.items():
            value = int(value or 0)
            if value < MIN_STAT_CAP or value > MAX_STAT_CAP:
                raise ValueError(f"Race {race_key} stat cap for {stat} is out of range: {value}.")

        for category, value in learning_modifiers.items():
            value = float(value or 0)
            if value < MIN_LEARNING_MODIFIER or value > MAX_LEARNING_MODIFIER:
                raise ValueError(f"Race {race_key} learning modifier for {category} is out of range: {value}.")

        average_learning = sum(float(value or 0) for value in learning_modifiers.values()) / len(RACE_LEARNING_CATEGORIES)
        if abs(average_learning - 1.0) > 0.05:
            raise ValueError(f"Race {race_key} learning modifiers average out to {average_learning:.2f}.")


_validate_race_definitions()