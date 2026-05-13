from __future__ import annotations

from dataclasses import dataclass

from domain.combat.maneuvers import ManeuverID


@dataclass(frozen=True)
class AttackVerb:
    """Canonical attack verb metadata from GSL S00031-S00037."""

    key: str
    verb_id: int
    rt_seconds: int
    aliases: tuple[str, ...] = ()
    requires_explicit_target: bool = False
    triggers_defender_script: bool = False
    has_terrain_guard: bool = False
    uses_engagement_target: bool = False


@dataclass(frozen=True)
class DefenseVerb:
    """Canonical defensive maneuver metadata from GSL S00039-S00040."""

    key: str
    verb_id: ManeuverID
    already_message: str
    enter_message: str
    aliases: tuple[str, ...] = ()


ATTACK_VERBS: dict[str, AttackVerb] = {
    "thrust": AttackVerb(key="thrust", verb_id=ManeuverID.THRUST, rt_seconds=5),
    "lunge": AttackVerb(key="lunge", verb_id=ManeuverID.LUNGE, rt_seconds=7),
    "slice": AttackVerb(key="slice", verb_id=ManeuverID.SLICE, rt_seconds=5, triggers_defender_script=True),
    "chop": AttackVerb(key="chop", verb_id=ManeuverID.CHOP, rt_seconds=5, has_terrain_guard=True),
    "sweep": AttackVerb(key="sweep", verb_id=ManeuverID.SWEEP, rt_seconds=5),
    "feint": AttackVerb(key="feint", verb_id=ManeuverID.FEINT, rt_seconds=3, uses_engagement_target=True),
    "jab": AttackVerb(key="jab", verb_id=ManeuverID.JAB, rt_seconds=4),
}


DEFENSE_VERBS: dict[str, DefenseVerb] = {
    "parry": DefenseVerb(
        key="parry",
        verb_id=ManeuverID.PARRY,
        already_message="You are already in a position to parry.",
        enter_message="You move into a position to parry.",
        aliases=("par",),
    ),
    "dodge": DefenseVerb(
        key="dodge",
        verb_id=ManeuverID.DODGE,
        already_message="But you are already dodging!",
        enter_message="You move into a position to dodge.",
        aliases=("dod",),
    ),
}
