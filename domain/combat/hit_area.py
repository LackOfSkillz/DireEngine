"""Hit area determination per GSL S00047."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
import random


class BodyPart(IntEnum):
    HEAD = 1
    NECK = 2
    RIGHT_ARM = 3
    LEFT_ARM = 4
    RIGHT_LEG = 5
    LEFT_LEG = 6
    RIGHT_HAND = 7
    LEFT_HAND = 8
    CHEST = 9
    ABDOMEN = 10
    BACK = 11
    RIGHT_EYE = 12
    LEFT_EYE = 13
    TAIL = 14


HIT_AREA_LADDER: tuple[tuple[int, BodyPart], ...] = (
    (2, BodyPart.LEFT_EYE),
    (3, BodyPart.RIGHT_EYE),
    (5, BodyPart.HEAD),
    (8, BodyPart.NECK),
    (28, BodyPart.CHEST),
    (33, BodyPart.BACK),
    (43, BodyPart.ABDOMEN),
    (57, BodyPart.LEFT_ARM),
    (71, BodyPart.RIGHT_ARM),
    (75, BodyPart.LEFT_HAND),
    (78, BodyPart.RIGHT_HAND),
    (89, BodyPart.LEFT_LEG),
    (100, BodyPart.RIGHT_LEG),
)

TARGETED_DIFFICULTY: dict[BodyPart, int] = {
    BodyPart.CHEST: 5,
    BodyPart.HEAD: 30,
    BodyPart.NECK: 25,
    BodyPart.LEFT_EYE: 55,
    BodyPart.RIGHT_EYE: 55,
    BodyPart.ABDOMEN: 10,
    BodyPart.BACK: 15,
    BodyPart.LEFT_ARM: 5,
    BodyPart.RIGHT_ARM: 5,
    BodyPart.LEFT_HAND: 20,
    BodyPart.RIGHT_HAND: 20,
    BodyPart.LEFT_LEG: 5,
    BodyPart.RIGHT_LEG: 5,
    BodyPart.TAIL: 15,
}

BODY_PART_KEYS: dict[BodyPart, str] = {
    BodyPart.HEAD: "head",
    BodyPart.NECK: "head",
    BodyPart.RIGHT_ARM: "right_arm",
    BodyPart.LEFT_ARM: "left_arm",
    BodyPart.RIGHT_LEG: "right_leg",
    BodyPart.LEFT_LEG: "left_leg",
    BodyPart.RIGHT_HAND: "right_hand",
    BodyPart.LEFT_HAND: "left_hand",
    BodyPart.CHEST: "chest",
    BodyPart.ABDOMEN: "abdomen",
    BodyPart.BACK: "back",
    BodyPart.RIGHT_EYE: "head",
    BodyPart.LEFT_EYE: "head",
    BodyPart.TAIL: "tail",
}

NAME_TO_BODY_PART: dict[str, BodyPart] = {
    "head": BodyPart.HEAD,
    "neck": BodyPart.NECK,
    "right_arm": BodyPart.RIGHT_ARM,
    "left_arm": BodyPart.LEFT_ARM,
    "right_leg": BodyPart.RIGHT_LEG,
    "left_leg": BodyPart.LEFT_LEG,
    "right_hand": BodyPart.RIGHT_HAND,
    "left_hand": BodyPart.LEFT_HAND,
    "chest": BodyPart.CHEST,
    "abdomen": BodyPart.ABDOMEN,
    "back": BodyPart.BACK,
    "right_eye": BodyPart.RIGHT_EYE,
    "left_eye": BodyPart.LEFT_EYE,
    "tail": BodyPart.TAIL,
}


@dataclass(frozen=True)
class HitAreaResult:
    area: BodyPart
    was_targeted: bool
    targeting_succeeded: bool
    retarget_count: int

    @property
    def area_key(self) -> str:
        return BODY_PART_KEYS[self.area]

    @property
    def area_name(self) -> str:
        return self.area.name.lower()


def body_part_to_key(area: BodyPart) -> str:
    return BODY_PART_KEYS[BodyPart(area)]


def coerce_body_part(value) -> BodyPart | None:
    if value is None:
        return None
    if isinstance(value, BodyPart):
        return value
    try:
        return BodyPart(int(value))
    except (TypeError, ValueError):
        normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "arm": BodyPart.LEFT_ARM,
            "leg": BodyPart.LEFT_LEG,
            "hand": BodyPart.LEFT_HAND,
            "eye": BodyPart.LEFT_EYE,
        }
        return aliases.get(normalized, NAME_TO_BODY_PART.get(normalized))


def _injury_value(defender_injuries: Mapping[str, object] | None, part_key: str) -> int:
    if not isinstance(defender_injuries, Mapping):
        return 0
    part = defender_injuries.get(part_key)
    if not isinstance(part, Mapping):
        return 0
    return max(
        int(part.get("external", 0) or 0),
        int(part.get("internal", 0) or 0),
        int(part.get("bruise", 0) or 0),
    )


def area_exists(area: BodyPart, defender_injuries: Mapping[str, object] | None, *, defender_has_tail: bool = False) -> bool:
    area = BodyPart(area)
    if area == BodyPart.TAIL:
        return False
    if area in {BodyPart.RIGHT_HAND, BodyPart.LEFT_HAND}:
        arm = BodyPart.RIGHT_ARM if area == BodyPart.RIGHT_HAND else BodyPart.LEFT_ARM
        if _injury_value(defender_injuries, body_part_to_key(arm)) >= 60:
            return False
    return _injury_value(defender_injuries, body_part_to_key(area)) < 60


def attempt_targeted_hit(
    *,
    leftover_of: int,
    original_of: int,
    target_area: BodyPart,
    weapon_balance: int,
    attacker_agility: int,
    defender_reflex: int,
) -> bool:
    target_area = BodyPart(target_area)
    base_diff = 100 + int(TARGETED_DIFFICULTY.get(target_area, 5) or 5)
    balance = int(weapon_balance or 50)
    agility_adjust = (int(attacker_agility or 0) * balance) // 100 if balance else 50
    adjusted_diff = base_diff - (agility_adjust - int(defender_reflex or 0))
    total_defenses = max(0, int(original_of or 0) - int(leftover_of or 0))
    final_threshold = (adjusted_diff * total_defenses) // 100
    return int(original_of or 0) > final_threshold


def _roll_bounds(*, verb: str, max_roll: int, is_brawling: bool, attacker_grappled: bool, defender_prone: bool) -> tuple[int, int]:
    verb = str(verb or "attack").strip().lower()
    if is_brawling:
        if attacker_grappled:
            if verb == "kneel":
                return 33, 100
            if verb == "butt":
                return 3, 32
            return 1, 70
        if verb == "kick":
            return (3, 100) if defender_prone else (32, 100)
        return 1, 77

    low = 1
    high = max_roll
    if verb == "sweep":
        high = 40
    elif verb == "chop":
        low = 60
    elif verb == "draw":
        low = 4
    return low, high


def _random_area(
    *,
    verb: str,
    defender_has_tail: bool,
    defender_injuries: Mapping[str, object] | None,
    rng,
    is_brawling: bool,
    attacker_grappled: bool,
    defender_prone: bool,
) -> tuple[BodyPart, int]:
    max_roll = 105 if defender_has_tail else 100
    low, high = _roll_bounds(
        verb=verb,
        max_roll=max_roll,
        is_brawling=is_brawling,
        attacker_grappled=attacker_grappled,
        defender_prone=defender_prone,
    )
    retarget_count = 0
    for _ in range(20):
        roll = rng.randint(low, high)
        area = BodyPart.TAIL
        for threshold, candidate in HIT_AREA_LADDER:
            if roll < threshold:
                area = candidate
                break
        if area_exists(area, defender_injuries, defender_has_tail=defender_has_tail):
            return area, retarget_count
        retarget_count += 1
    for area in BodyPart:
        if area_exists(area, defender_injuries, defender_has_tail=defender_has_tail):
            return area, retarget_count
    return BodyPart.CHEST, retarget_count


def determine_hit_area(
    *,
    leftover_of: int,
    original_of: int,
    weapon_balance: int,
    attacker_agility: int,
    defender_reflex: int,
    defender_has_tail: bool = False,
    verb: str = "attack",
    aimed_at: BodyPart | str | int | None = None,
    defender_injuries: Mapping[str, object] | None = None,
    rng: random.Random | random.Random = None,
    is_brawling: bool = False,
    attacker_grappled: bool = False,
    defender_prone: bool = False,
) -> HitAreaResult:
    rng = rng or random
    aimed_area = coerce_body_part(aimed_at)
    if aimed_area is not None:
        succeeded = area_exists(aimed_area, defender_injuries, defender_has_tail=defender_has_tail) and attempt_targeted_hit(
            leftover_of=leftover_of,
            original_of=original_of,
            target_area=aimed_area,
            weapon_balance=weapon_balance,
            attacker_agility=attacker_agility,
            defender_reflex=defender_reflex,
        )
        if succeeded:
            return HitAreaResult(area=aimed_area, was_targeted=True, targeting_succeeded=True, retarget_count=0)

    area, retarget_count = _random_area(
        verb=verb,
        defender_has_tail=defender_has_tail,
        defender_injuries=defender_injuries,
        rng=rng,
        is_brawling=is_brawling,
        attacker_grappled=attacker_grappled,
        defender_prone=defender_prone,
    )
    return HitAreaResult(
        area=area,
        was_targeted=aimed_area is not None,
        targeting_succeeded=False,
        retarget_count=retarget_count,
    )