"""Central empath rank unlock thresholds."""

EMPATH_UNLOCKS = {
    "internal_transfer": {
        "rank": 6,
        "label": "Internal Transfer",
        "failure_message": "You are not yet ready to handle internal wounds that way.",
    },
    "external_scar_transfer": {
        "rank": 7,
        "label": "External Scar Transfer",
        "failure_message": "You are not yet ready to ease another's scars.",
    },
    "internal_scar_transfer": {
        "rank": 8,
        "label": "Internal Scar Transfer",
        "failure_message": "You are not yet ready to work old scars from your own body.",
    },
    "manipulate": {
        "rank": 9,
        "label": "Manipulate",
        "failure_message": "You are not yet ready to impose calm on another mind.",
    },
    "poison_transfer": {
        "rank": 10,
        "label": "Poison Transfer",
        "failure_message": "You are not yet ready to take poison into yourself.",
    },
    "perceive_health": {
        "rank": 12,
        "label": "Perceive Health",
        "failure_message": "You are not yet ready to read nearby life forces clearly.",
    },
    "disease_transfer": {
        "rank": 15,
        "label": "Disease Transfer",
        "failure_message": "You are not yet ready to take disease into yourself.",
    },
    "persistent_link": {
        "rank": 20,
        "label": "Persistent Link",
        "failure_message": "You are not yet ready to hold a persistent empathic link.",
    },
    "wound_redirection": {
        "rank": 25,
        "label": "Wound Redirection",
        "failure_message": "You are not yet ready to redirect wounds through yourself.",
    },
    "unity_link": {
        "rank": 30,
        "label": "Unity Link",
        "failure_message": "You are not yet ready to weave unity between burdens.",
    },
    "hand_of_hodierna": {
        "rank": 35,
        "label": "Hand of Hodierna",
        "failure_message": "You are not yet ready to sustain that healing channel.",
    },
    "wound_reduction": {
        "rank": 40,
        "label": "Wound Reduction",
        "failure_message": "You have not yet learned to soften transferred wounds.",
    },
}

EMPATH_ABILITY_UNLOCKS = {
    "manipulate": "manipulate",
    "perceive": "perceive_health",
    "perceive_health": "perceive_health",
    "perceive_target": "perceive_health",
    "redirect": "wound_redirection",
    "unity": "unity_link",
    "channel": "hand_of_hodierna",
}


def get_empath_unlock(key):
    return dict(EMPATH_UNLOCKS.get(str(key or "").strip().lower(), {}))


def get_empath_unlock_rank(key):
    return int(get_empath_unlock(key).get("rank", 0) or 0)


def format_empath_unlock_name(key):
    data = get_empath_unlock(key)
    return data.get("label", str(key or "").replace("_", " ").title())


def get_next_empath_unlock(rank):
    current_rank = max(0, int(rank or 0))
    for unlock_key, data in sorted(EMPATH_UNLOCKS.items(), key=lambda entry: (int(entry[1].get("rank", 0) or 0), entry[0])):
        required_rank = int(data.get("rank", 0) or 0)
        if required_rank > current_rank:
            return unlock_key, dict(data)
    return None, None