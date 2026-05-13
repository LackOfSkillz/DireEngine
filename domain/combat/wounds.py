from __future__ import annotations

from dataclasses import dataclass
import math

from domain.combat.damage import RawDamage
from domain.combat.hit_area import BodyPart, body_part_to_key


EXTERNAL_MULTIPLIERS = {
    "puncture": 6,
    "slice": 8,
    "impact": 3,
    "fire": 7,
    "cold": 7,
    "electric": 7,
}

INTERNAL_MULTIPLIERS = {
    "puncture": 6,
    "slice": 3,
    "impact": 7,
    "fire": 7,
    "cold": 7,
    "electric": 7,
}


@dataclass(frozen=True)
class WoundResult:
    area: str
    external_wound_level: int
    internal_wound_level: int
    wound_level: int
    hp_damage: int
    stamina_denominator: int
    raw_damage_total: int
    destroyed_parts: tuple[str, ...] = ()


def _stamina_denominator(current_hp: int, rng) -> int:
    current_hp = max(1, int(current_hp or 1))
    max_reduction = max(80, int(math.log(current_hp * 100) * 100) - 260)
    first = rng.randint(max(80, max_reduction // 2), max_reduction)
    second = rng.randint(80, first)
    return max(80, second)


def _crit_level(damage: int, multiplier: int, existing_level: int) -> int:
    if damage <= 0:
        return 0
    v3 = min(600, max(0, int(damage * multiplier)))
    v4 = min(6, v3 // 100)
    v5 = (v3 % 100) // 10
    level = (v4 * 10) + v5
    existing_level = max(0, int(existing_level or 0))
    if ((level + existing_level) // 10) > (existing_level // 10):
        level = max(level, min(60, ((level + existing_level) // 10) * 10))
    return min(60, level)


def _scaled_damage(raw_damage: RawDamage, denominator: int) -> RawDamage:
    return RawDamage(
        puncture=(raw_damage.puncture * 100) // denominator,
        slice=(raw_damage.slice * 100) // denominator,
        impact=(raw_damage.impact * 100) // denominator,
        fire=(raw_damage.fire * 100) // denominator,
        cold=(raw_damage.cold * 100) // denominator,
        electric=(raw_damage.electric * 100) // denominator,
        multiplier_seed=raw_damage.multiplier_seed,
    )


def _bodypart_cap(body_part: BodyPart, external_wound: int, internal_wound: int, max_hp: int) -> int:
    if body_part in {BodyPart.RIGHT_ARM, BodyPart.LEFT_ARM, BodyPart.RIGHT_LEG, BodyPart.LEFT_LEG}:
        return max_hp // 2
    if body_part in {BodyPart.RIGHT_HAND, BodyPart.LEFT_HAND}:
        return (max_hp * 35) // 100
    if body_part is BodyPart.TAIL and external_wound < 60 and internal_wound < 60:
        return (max_hp * 2) // 5
    if external_wound < 50 and internal_wound < 50:
        return (max_hp * 9) // 10
    return max_hp


def _current_hp_cap(current_hp: int) -> int | None:
    current_hp = max(0, int(current_hp or 0))
    if current_hp < 5:
        return 1
    if current_hp < 10:
        return 4
    if current_hp < 20:
        return 8
    if current_hp < 30:
        return 12
    if current_hp < 40:
        return 25
    if current_hp < 60:
        return 50
    return None


def apply_wounds(
    raw_damage: RawDamage,
    *,
    body_part: BodyPart,
    max_hp: int,
    current_hp: int,
    rng,
    existing_external: int = 0,
    existing_internal: int = 0,
) -> WoundResult:
    denominator = _stamina_denominator(current_hp, rng)
    scaled = _scaled_damage(raw_damage, denominator)

    external_wound = max(
        _crit_level(scaled.puncture, EXTERNAL_MULTIPLIERS["puncture"], existing_external),
        _crit_level(scaled.slice, EXTERNAL_MULTIPLIERS["slice"], existing_external),
        _crit_level(scaled.impact, EXTERNAL_MULTIPLIERS["impact"], existing_external),
        _crit_level(scaled.fire, EXTERNAL_MULTIPLIERS["fire"], existing_external),
        _crit_level(scaled.cold, EXTERNAL_MULTIPLIERS["cold"], existing_external),
        _crit_level(scaled.electric, EXTERNAL_MULTIPLIERS["electric"], existing_external),
    )
    internal_wound = max(
        _crit_level(scaled.puncture, INTERNAL_MULTIPLIERS["puncture"], existing_internal),
        _crit_level(scaled.slice, INTERNAL_MULTIPLIERS["slice"], existing_internal),
        _crit_level(scaled.impact, INTERNAL_MULTIPLIERS["impact"], existing_internal),
        _crit_level(scaled.fire, INTERNAL_MULTIPLIERS["fire"], existing_internal),
        _crit_level(scaled.cold, INTERNAL_MULTIPLIERS["cold"], existing_internal),
        _crit_level(scaled.electric, INTERNAL_MULTIPLIERS["electric"], existing_internal),
    )

    hp_damage = max(1, scaled.total)
    hp_damage = min(hp_damage, _bodypart_cap(body_part, external_wound, internal_wound, max(1, int(max_hp or 1))))
    current_hp_cap = _current_hp_cap(current_hp)
    if current_hp_cap is not None and external_wound <= 29 and internal_wound <= 29:
        hp_damage = min(hp_damage, current_hp_cap)
    hp_damage = max(1, ((hp_damage * 9) // 10) + 1)

    destroyed_parts = []
    if external_wound > 59:
        if body_part is BodyPart.RIGHT_ARM:
            destroyed_parts.append(body_part_to_key(body_part))
            destroyed_parts.append(body_part_to_key(BodyPart.RIGHT_HAND))
        elif body_part is BodyPart.LEFT_ARM:
            destroyed_parts.append(body_part_to_key(body_part))
            destroyed_parts.append(body_part_to_key(BodyPart.LEFT_HAND))
        else:
            destroyed_parts.append(body_part_to_key(body_part))

    return WoundResult(
        area=body_part_to_key(body_part),
        external_wound_level=external_wound,
        internal_wound_level=internal_wound,
        wound_level=max(external_wound, internal_wound),
        hp_damage=hp_damage,
        stamina_denominator=denominator,
        raw_damage_total=scaled.total,
        destroyed_parts=tuple(destroyed_parts),
    )