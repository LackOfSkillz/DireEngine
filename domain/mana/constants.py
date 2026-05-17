# DRG-CLERIC-01 / DRG-EMPATH-01: Holy and Life remain the canonical named
# mana-realm registrations for Cleric and Empath routing. The project keeps
# the existing named realms instead of replacing them with raw GSL numeric ids.
# provenance: gsl_2004 (Life/Empath alignment), directengine_canon (named-realm registry form)
MANA_REALMS = ("holy", "life", "elemental", "lunar")

MANA_MIN = 0.0
MANA_MAX = 2.0

DEFAULT_ROOM_MANA = {
    "holy": 1.0,
    "life": 1.0,
    "elemental": 1.0,
    "lunar": 1.0,
}

DEFAULT_GLOBAL_MANA_MODIFIER = 1.0
DEFAULT_PROFESSION_MANA_MODIFIER = 1.0

MANA_PULSE_INTERVAL = 5
DEVOTION_PULSE_INTERVAL = 60
CAMBRINTH_HALF_LIFE_SECONDS = 600
MAX_FINAL_POWER_MULTIPLIER = 2.5
MAX_BACKLASH_CHANCE = 40.0
MIN_HARNESS_EFFICIENCY = 0.60
MAX_HARNESS_EFFICIENCY = 0.95