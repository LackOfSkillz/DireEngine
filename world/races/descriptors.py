from .utils import resolve_race_name


DEFAULT_AGE = 25
UNKNOWN_RACE_DESCRIPTOR = "an unidentified figure"
GENERIC_RACE_DESCRIPTOR = "an individual"


AGE_BRACKETS = (
    (0, 12, "child"),
    (13, 19, "young"),
    (20, 40, "adult"),
    (41, 60, "mature"),
    (61, 200, "elder"),
)


RACE_AGE_DESCRIPTORS = {
    "human": {
        "child": "a young child",
        "young": "a young person",
        "adult": "an adult",
        "mature": "a mature individual",
        "elder": "an elderly figure",
    },
    "elf": {
        "child": "a youthful elf",
        "young": "a young elf",
        "adult": "a composed elf",
        "mature": "a refined elf",
        "elder": "an ancient elf",
    },
    "dwarf": {
        "child": "a dwarven child",
        "young": "a beardless dwarf",
        "adult": "a stout dwarf",
        "mature": "a seasoned dwarf",
        "elder": "an elder dwarf",
    },
    "halfling": {
        "child": "a small child",
        "young": "a lively halfling",
        "adult": "a nimble halfling",
        "mature": "a steady halfling",
        "elder": "an aged halfling",
    },
    "gnome": {
        "child": "a curious child",
        "young": "a young gnome",
        "adult": "an attentive gnome",
        "mature": "a thoughtful gnome",
        "elder": "an elder gnome",
    },
    "volgrin": {
        "child": "a heavy-set youth",
        "young": "a growing Volgrin",
        "adult": "a massive Volgrin",
        "mature": "a battle-hardened Volgrin",
        "elder": "a towering elder Volgrin",
    },
    "saurathi": {
        "child": "a small scaled youth",
        "young": "a developing Saurathi",
        "adult": "a composed Saurathi",
        "mature": "a disciplined Saurathi",
        "elder": "an elder Saurathi",
    },
    "valran": {
        "child": "a rugged child",
        "young": "a hardened youth",
        "adult": "a hardened Valran",
        "mature": "a weathered Valran",
        "elder": "a worn but enduring Valran",
    },
    "aethari": {
        "child": "a quiet child",
        "young": "a contemplative youth",
        "adult": "a focused Aethari",
        "mature": "a deeply composed Aethari",
        "elder": "an introspective elder",
    },
    "felari": {
        "child": "a small feline youth",
        "young": "a playful Felari",
        "adult": "a sleek Felari",
        "mature": "a poised Felari",
        "elder": "a seasoned Felari",
    },
    "lunari": {
        "child": "a restless child",
        "young": "a shifting youth",
        "adult": "a tense Lunari",
        "mature": "a controlled Lunari",
        "elder": "a weathered Lunari",
    },
}


def resolve_age_bracket(age, default="adult"):
    try:
        numeric_age = int(age)
    except (TypeError, ValueError):
        numeric_age = DEFAULT_AGE

    for min_age, max_age, label in AGE_BRACKETS:
        if min_age <= numeric_age <= max_age:
            return label

    if numeric_age > AGE_BRACKETS[-1][1]:
        return AGE_BRACKETS[-1][2]
    return default


def get_race_age_descriptor(race_name, age, default=UNKNOWN_RACE_DESCRIPTOR):
    race_key = resolve_race_name(race_name, default=None)
    if not race_key:
        return default

    bracket = resolve_age_bracket(age)
    race_descriptors = RACE_AGE_DESCRIPTORS.get(race_key, {})
    return race_descriptors.get(bracket, GENERIC_RACE_DESCRIPTOR)