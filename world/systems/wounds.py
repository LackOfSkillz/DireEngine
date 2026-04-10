WOUND_RULES = {
    "fatigue": {
        "pressure": "recovery-cost",
    },
    "vitality": {
        "transfer_risk": "deceptive",
    },
    "bleeding": {
        "transfer_speed": "fast",
        "danger": "spike",
    },
    "poison": {
        "transfer_risk": "immediate",
    },
    "disease": {
        "transfer_risk": "long-term",
    },
}


def describe_wound(value):
    amount = max(0, int(value or 0))
    if amount < 20:
        return "None"
    if amount < 40:
        return "Light"
    if amount < 70:
        return "Moderate"
    return "Severe"


def apply_poison_tick(char):
    wounds = dict(getattr(getattr(char, "db", None), "wounds", {}) or {})
    poison = max(0, int(wounds.get("poison", 0) or 0))
    if poison <= 0:
        return 0
    damage = max(1, int(poison * 0.05))
    if damage <= 0:
        return 0
    wounds["vitality"] = max(0, min(100, int(wounds.get("vitality", 0) or 0) + damage))
    char.db.wounds = wounds
    if hasattr(char, "sync_client_state"):
        char.sync_client_state()
    return damage


def get_disease_penalty(char):
    wounds = dict(getattr(getattr(char, "db", None), "wounds", {}) or {})
    disease = max(0, int(wounds.get("disease", 0) or 0))
    return 1 + (disease / 100.0)