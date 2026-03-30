BESEECH_PROFILES = {
    "wind": {
        "cost": 20,
        "duration": 16,
        "requires": "airflow",
        "label": "Wind",
        "self_message": "You call to the wind, and it answers.",
        "room_message": "The air shifts subtly around {name}.",
        "effects": {
            "accuracy_bonus": 10,
            "stealth_retention_bonus": 12,
        },
    },
    "earth": {
        "cost": 18,
        "duration": 18,
        "requires": "natural",
        "label": "Earth",
        "self_message": "You call to the earth, and it answers.",
        "room_message": "The ground settles with quiet intent around {name}.",
        "effects": {
            "stealth_bonus": 10,
            "tracking_bonus": 12,
        },
    },
    "sky": {
        "cost": 22,
        "duration": 14,
        "requires": "open_sky",
        "label": "Sky",
        "self_message": "You call to the sky, and it answers.",
        "room_message": "A high stillness gathers around {name}.",
        "effects": {
            "perception_bonus": 12,
            "detection_bonus": 15,
        },
    },
}


def get_beseech_profile(kind):
    key = str(kind or "").strip().lower()
    return BESEECH_PROFILES.get(key)


def get_beseech_kinds():
    return tuple(BESEECH_PROFILES.keys())