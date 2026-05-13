from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class ManeuverID(IntEnum):
    NONE = 0
    UNSKILLED_ATTACK = 1
    THRUST = 2
    LUNGE = 3
    SLICE = 4
    CHOP = 5
    SWEEP = 6
    FEINT = 7
    JAB = 8
    DRAW = 9
    SHIELD_BASH = 10
    WHIRLWIND = 11
    UNSKILLED_PARRY = 12
    PARRY = 13
    PARRY_RETREAT = 14
    DISARM = 15
    RETREAT = 16
    DODGE = 17
    BACKSTAB = 18
    CIRCLE_WEAVE = 21
    GRAPPLE = 22
    TACKLE = 23
    SHOVE = 24
    PUNCH = 25
    CLAW = 26
    GOUGE = 27
    KICK_KNEE = 28
    ELBOW = 29
    SLAP = 30
    BITE = 31
    BUTT = 32
    GRAPPLED_CIRCLE = 33


@dataclass(frozen=True)
class DefenseScaling:
    evasion_pct: int
    parry_pct: int
    shield_pct: int


DEFENSE_SCALING: dict[int, DefenseScaling] = {
    ManeuverID.NONE: DefenseScaling(80, 80, 80),
    ManeuverID.UNSKILLED_ATTACK: DefenseScaling(60, 60, 60),
    ManeuverID.THRUST: DefenseScaling(65, 80, 80),
    ManeuverID.LUNGE: DefenseScaling(40, 60, 40),
    ManeuverID.SLICE: DefenseScaling(75, 70, 75),
    ManeuverID.CHOP: DefenseScaling(75, 70, 70),
    ManeuverID.SWEEP: DefenseScaling(75, 60, 80),
    ManeuverID.FEINT: DefenseScaling(80, 90, 85),
    ManeuverID.JAB: DefenseScaling(80, 80, 80),
    ManeuverID.DRAW: DefenseScaling(70, 80, 70),
    ManeuverID.SHIELD_BASH: DefenseScaling(60, 85, 30),
    ManeuverID.WHIRLWIND: DefenseScaling(40, 40, 40),
    ManeuverID.PARRY: DefenseScaling(90, 100, 85),
    ManeuverID.DISARM: DefenseScaling(75, 70, 65),
    ManeuverID.RETREAT: DefenseScaling(70, 65, 70),
    ManeuverID.DODGE: DefenseScaling(100, 90, 85),
    ManeuverID.BACKSTAB: DefenseScaling(65, 80, 80),
    ManeuverID.CIRCLE_WEAVE: DefenseScaling(75, 85, 85),
    ManeuverID.GRAPPLE: DefenseScaling(20, 20, 20),
    ManeuverID.TACKLE: DefenseScaling(45, 10, 10),
    ManeuverID.SHOVE: DefenseScaling(75, 60, 60),
    ManeuverID.PUNCH: DefenseScaling(75, 75, 75),
    ManeuverID.CLAW: DefenseScaling(70, 75, 80),
    ManeuverID.GOUGE: DefenseScaling(70, 65, 75),
    ManeuverID.KICK_KNEE: DefenseScaling(60, 70, 70),
    ManeuverID.ELBOW: DefenseScaling(70, 60, 70),
    ManeuverID.SLAP: DefenseScaling(70, 65, 75),
    ManeuverID.BITE: DefenseScaling(50, 60, 60),
    ManeuverID.BUTT: DefenseScaling(30, 45, 50),
    ManeuverID.GRAPPLED_CIRCLE: DefenseScaling(30, 30, 30),
}


DEFAULT_DEFENSE_SCALING = DEFENSE_SCALING[ManeuverID.NONE]


def coerce_maneuver_id(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return int(ManeuverID.NONE)


def get_defense_scaling(maneuver_id) -> DefenseScaling:
    return DEFENSE_SCALING.get(coerce_maneuver_id(maneuver_id), DEFAULT_DEFENSE_SCALING)