HOT = "hot"
WARM = "warm"
COLD = "cold"
DORMANT = "dormant"


def normalize_tier(value):
    if value in {HOT, WARM, COLD, DORMANT}:
        return value
    return COLD