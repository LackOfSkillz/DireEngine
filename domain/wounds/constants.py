"""Constants for physical wound modeling."""

from __future__ import annotations


DEFAULT_TEND_STATE = {
	"strength": 0,
	"duration": 0,
	"last_applied": 0.0,
	"min_until": 0.0,
}

DEFAULT_INJURIES = {
	"head": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 100, "vital": True},
	"chest": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 120, "vital": True},
	"abdomen": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 110, "vital": True},
	"back": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 110, "vital": True},
	"left_arm": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 80, "vital": False},
	"right_arm": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 80, "vital": False},
	"left_hand": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 60, "vital": False},
	"right_hand": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 60, "vital": False},
	"left_leg": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 90, "vital": False},
	"right_leg": {"external": 0, "internal": 0, "bruise": 0, "bleed": 0, "scar": 0, "tended": False, "tend": dict(DEFAULT_TEND_STATE), "max": 90, "vital": False},
}

BODY_PART_ORDER = tuple(DEFAULT_INJURIES.keys())

SEVERITY_ADVERBS = {
	"light": "lightly",
	"moderate": "moderately",
	"severe": "severely",
	"critical": "critically",
}

SCAR_RULES = {
	"severity_threshold": 45,
	"trauma_threshold": 70,
	"repeat_threshold": 15,
	"repeat_gate": 25,
	"max_scars": 10,
}

WOUND_APPLICATION_THRESHOLDS = {
	"impact": 8,
	"slice": 4,
	"pierce": 4,
	"stab": 4,
	"default": 9,
}

LOW_HP_WOUND_RATIO = 0.35
BLEED_TICK_SECONDS = 1.0
RECOVERY_TICK_SECONDS = 30.0
RECENT_TEND_WINDOW = 15.0
