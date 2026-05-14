"""Canonical modern-DR mindstate band data.

LEARN-003a ships the authoritative 35-band map and helper accessors. Runtime
drain behavior remains unchanged until LEARN-003b swaps the pulse internals to
consume this data.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MindstateBand:
    """One canonical mindstate band on the 0-34 scale."""

    value: int
    name: str
    short_name: str
    description: str
    is_locked: bool
    pulse_modifier: float


MINDSTATE_BANDS: dict[int, MindstateBand] = {
    0: MindstateBand(0, "clear", "clr", "Ready to absorb new experience.", False, 1.00),
    1: MindstateBand(1, "dabbling", "dab", "Just beginning to engage with the subject.", False, 1.00),
    2: MindstateBand(2, "perusing", "per", "Glancing over the material.", False, 1.05),
    3: MindstateBand(3, "learning", "lrn", "Actively absorbing new knowledge.", False, 1.10),
    4: MindstateBand(4, "thoughtful", "tho", "Thinking carefully about what was observed.", False, 1.15),
    5: MindstateBand(5, "thinking", "thk", "Working ideas through deliberately.", False, 1.20),
    6: MindstateBand(6, "considering", "csd", "Weighing the implications of the experience.", False, 1.25),
    7: MindstateBand(7, "pondering", "pdr", "Sustained reflection.", False, 1.30),
    8: MindstateBand(8, "ruminating", "rmn", "Chewing over what was learned.", False, 1.35),
    9: MindstateBand(9, "concentrating", "cnc", "Focused effort on integrating new material.", False, 1.40),
    10: MindstateBand(10, "attentive", "att", "Holding firm attention on the subject.", False, 1.45),
    11: MindstateBand(11, "deliberative", "del", "Careful, measured thought.", False, 1.50),
    12: MindstateBand(12, "interested", "int", "Genuinely interested in continuing to learn.", False, 1.55),
    13: MindstateBand(13, "examining", "exm", "Inspecting the material from multiple angles.", False, 1.60),
    14: MindstateBand(14, "understanding", "und", "Beginning to grasp the patterns.", False, 1.65),
    15: MindstateBand(15, "absorbing", "abs", "Steady absorption is happening.", False, 1.70),
    16: MindstateBand(16, "intrigued", "ing", "Drawn deeper into the subject.", False, 1.75),
    17: MindstateBand(17, "scrutinizing", "scr", "Detailed examination underway.", False, 1.80),
    18: MindstateBand(18, "analyzing", "ana", "Breaking the experience down systematically.", False, 1.85),
    19: MindstateBand(19, "studious", "stu", "Disciplined study posture.", False, 1.90),
    20: MindstateBand(20, "focused", "foc", "Tight, single-purpose attention.", False, 1.95),
    21: MindstateBand(21, "very focused", "vfc", "Intensely sustained focus.", False, 2.00),
    22: MindstateBand(22, "engaged", "eng", "Fully present with the material.", False, 2.05),
    23: MindstateBand(23, "very engaged", "veg", "Deeply present.", False, 2.10),
    24: MindstateBand(24, "cogitating", "cog", "Hard thinking; the mind is working at capacity.", False, 2.15),
    25: MindstateBand(25, "fascinated", "fas", "Captured by the subject.", False, 2.20),
    26: MindstateBand(26, "captivated", "cap", "Held by the work.", False, 2.25),
    27: MindstateBand(27, "engrossed", "egs", "Consumed by the practice.", False, 2.30),
    28: MindstateBand(28, "riveted", "riv", "Cannot easily look away.", False, 2.35),
    29: MindstateBand(29, "very riveted", "vrv", "Locked into the work.", False, 2.40),
    30: MindstateBand(30, "rapt", "rap", "Mind is operating near its limit.", False, 2.45),
    31: MindstateBand(31, "very rapt", "vrp", "At the edge of absorption capacity.", False, 2.50),
    32: MindstateBand(32, "enthralled", "ent", "Approaching the lock; mind nearly full.", False, 2.55),
    33: MindstateBand(33, "nearly locked", "nlk", "One step from mind lock.", False, 2.60),
    34: MindstateBand(34, "mind lock", "lok", "The mind cannot absorb more in this skill until it drains.", True, 2.65),
}


def get_mindstate_band(value: int) -> MindstateBand:
    """Return the canonical band for a 0-34 mindstate value."""

    normalized = int(value or 0)
    if normalized < 0 or normalized > 34:
        return MINDSTATE_BANDS[0]
    return MINDSTATE_BANDS[normalized]


def get_mindstate_name(value: int) -> str:
    """Return the canonical display name for a mindstate value."""

    return get_mindstate_band(value).name


def is_mind_locked(value: int) -> bool:
    """Return whether the given value is the canonical lock state."""

    return get_mindstate_band(value).is_locked