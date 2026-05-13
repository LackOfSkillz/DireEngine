from __future__ import annotations

from dataclasses import dataclass


MANEUVER_DAMAGE_MODS = {
    "swing wildly": {"puncture": 10, "slice": 40, "impact": 40, "impact_weapon_impact": 60},
    "thrust": {"puncture": 80, "slice": 10, "impact": 20},
    "lunge": {"puncture": 110, "slice": 10, "impact": 30},
    "slice": {"puncture": 10, "slice": 100, "impact": 40, "impact_weapon_impact": 80},
    "swing": {"puncture": 10, "slice": 100, "impact": 40, "impact_weapon_impact": 80},
    "chop": {"puncture": 10, "slice": 80, "impact": 60, "impact_weapon_impact": 100},
    "sweep": {"puncture": 10, "slice": 70, "impact": 40, "impact_weapon_impact": 70},
    "feint": {"puncture": 20, "slice": 20, "impact": 20},
    "jab": {"puncture": 60, "slice": 10, "impact": 10},
    "draw": {"puncture": 10, "slice": 110, "impact": 10, "impact_weapon_impact": 55},
    "punch": {"puncture": 0, "slice": 0, "impact": 70},
    "kick": {"puncture": 0, "slice": 0, "impact": 85},
    "knee": {"puncture": 0, "slice": 0, "impact": 75},
    "butt": {"puncture": 0, "slice": 0, "impact": 65},
    "bite": {"puncture": 55, "slice": 35, "impact": 10},
}


@dataclass(frozen=True)
class RawDamage:
    puncture: int
    slice: int
    impact: int
    fire: int = 0
    cold: int = 0
    electric: int = 0
    multiplier_seed: int = 100

    @property
    def total(self) -> int:
        return self.puncture + self.slice + self.impact + self.fire + self.cold + self.electric

    @property
    def dominant_type(self) -> str:
        values = {
            "puncture": self.puncture,
            "slice": self.slice,
            "impact": self.impact,
            "fire": self.fire,
            "cold": self.cold,
            "electric": self.electric,
        }
        return max(values.items(), key=lambda item: item[1])[0]


def _average_roll(rng, ceiling: int) -> int:
    if ceiling <= 0:
        return 0
    floor = max(1, ceiling // 2)
    return (rng.randint(floor, ceiling) + rng.randint(floor, ceiling)) // 2


def _durability_pct(current_damage: int, strength: int) -> int:
    strength = max(1, int(strength or 1))
    current_damage = max(0, int(current_damage or 0))
    return max(0, 100 - ((current_damage * 100) // strength))


def _leftover_multiplier(leftover_of: int, combat_rng, rng) -> int:
    if leftover_of <= 0:
        return 100
    seed = max(1, int((combat_rng.roll() if combat_rng is not None else rng.randint(1, 100)) / 2))
    total = seed
    current = seed
    while current > 45:
        current = rng.randint(1, 50)
        total += current
    return 100 + ((leftover_of * 3) // 2) + total


def _apply_ammo_scale(value: int, ammo_profile: dict | None, key: str) -> int:
    if not ammo_profile:
        return value
    pct = int(ammo_profile.get(key, ammo_profile.get(f"{key}_pct", 100)) or 100)
    return max(0, (value * pct) // 100)


def compute_damage(
    weapon_profile: dict,
    *,
    attacker_strength: int,
    leftover_of: int,
    maneuver: str | None,
    rng,
    combat_rng=None,
    ammo_profile: dict | None = None,
) -> RawDamage:
    puncture = int(weapon_profile.get("puncture", 0) or 0)
    slice_damage = int(weapon_profile.get("slice", 0) or 0)
    impact = int(weapon_profile.get("impact", 0) or 0)

    if not any((puncture, slice_damage, impact)):
        base = max(1, int(weapon_profile.get("damage_max", weapon_profile.get("damage", 1)) or 1))
        puncture = max(0, int(base * 0.2))
        slice_damage = max(0, int(base * 0.4))
        impact = max(0, base - puncture - slice_damage)

    puncture = _apply_ammo_scale(puncture, ammo_profile, "puncture")
    slice_damage = _apply_ammo_scale(slice_damage, ammo_profile, "slice")
    impact = _apply_ammo_scale(impact, ammo_profile, "impact")

    durability_pct = _durability_pct(weapon_profile.get("current_damage", 0), weapon_profile.get("strength", 100))
    puncture = (puncture * durability_pct) // 100
    slice_damage = (slice_damage * durability_pct) // 100
    impact = (impact * durability_pct) // 100

    puncture_roll = _average_roll(rng, puncture)
    slice_roll = _average_roll(rng, slice_damage)
    impact_roll = _average_roll(rng, impact)

    power = max(0, int(weapon_profile.get("power", 0) or 0))
    strength_bonus = max(0, (max(0, int(attacker_strength or 0)) * power) // 100)
    strength_bonus //= 2

    puncture_roll += min(puncture_roll, strength_bonus)
    slice_roll += min(slice_roll, strength_bonus)
    impact_roll += min(impact_roll, strength_bonus)

    multiplier_seed = _leftover_multiplier(leftover_of, combat_rng, rng)
    puncture_roll = (puncture_roll * multiplier_seed) // 100
    slice_roll = (slice_roll * multiplier_seed) // 100
    impact_roll = (impact_roll * multiplier_seed) // 100

    maneuver_key = str(maneuver or "swing").lower()
    maneuver_mods = MANEUVER_DAMAGE_MODS.get(maneuver_key, MANEUVER_DAMAGE_MODS["swing"])
    if impact > max(puncture, slice_damage):
        impact_pct = maneuver_mods.get("impact_weapon_impact", maneuver_mods.get("impact", 100))
    else:
        impact_pct = maneuver_mods.get("impact", 100)

    puncture_roll = (puncture_roll * int(maneuver_mods.get("puncture", 100))) // 100
    slice_roll = (slice_roll * int(maneuver_mods.get("slice", 100))) // 100
    impact_roll = (impact_roll * int(impact_pct)) // 100

    return RawDamage(
        puncture=max(0, puncture_roll),
        slice=max(0, slice_roll),
        impact=max(0, impact_roll),
        multiplier_seed=multiplier_seed,
    )