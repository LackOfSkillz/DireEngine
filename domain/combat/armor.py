from __future__ import annotations

from dataclasses import dataclass

from domain.combat.damage import RawDamage


@dataclass(frozen=True)
class ArmorReduction:
    puncture: int
    slice: int
    impact: int
    fire: int = 0
    cold: int = 0
    electric: int = 0
    flat_reduction: tuple[int, int, int] = (0, 0, 0)
    percent_reduction: tuple[int, int, int, int, int, int] = (0, 0, 0, 0, 0, 0)

    @property
    def total(self) -> int:
        return self.puncture + self.slice + self.impact + self.fire + self.cold + self.electric


def _durability_pct(damage: int, strength: int) -> int:
    strength = max(1, int(strength or 1))
    damage = max(0, int(damage or 0))
    return max(0, 100 - ((damage * 100) // strength))


def _random_between(rng, first: int, second: int) -> int:
    low, high = sorted((int(first), int(second)))
    return int(rng.randint(low, high)) if high > low else low


def _split_encoded_resistance(encoded: int, durability_pct: int) -> tuple[int, int]:
    encoded = max(0, int(encoded or 0))
    flat = ((encoded // 100) * durability_pct) // 100
    percent = ((encoded % 100) * durability_pct) // 100
    return flat, percent


def _apply_flat_stage(damage: int, flat: int, armor_skill: int, maneuver_mod: int, multi_armor_penalty: int, rng) -> tuple[int, int]:
    if damage <= 0 or flat <= 0:
        return max(0, damage), 0
    skill = max(1, int(armor_skill or 1))
    if maneuver_mod < 10:
        skill = max(1, (skill * max(0, int(maneuver_mod or 0))) // 10)
    if multi_armor_penalty:
        skill = max(1, skill - (max(0, int(multi_armor_penalty)) // 4))
    scaled = max(flat, (skill * flat) // 150)
    stage_one = _random_between(rng, (flat + scaled) // 2, scaled)
    flat_removed = min(damage, _random_between(rng, flat, stage_one))
    return max(0, damage - flat_removed), flat_removed


def _apply_percent_stage(damage: int, percent: int, variance: int) -> tuple[int, int]:
    percent = max(0, min(100, int(percent) + int(variance)))
    through_pct = max(0, 100 - percent)
    remaining = (max(0, int(damage)) * through_pct) // 100
    absorbed = max(0, int(damage) - remaining)
    return remaining, percent if absorbed else 0


def apply_armor_reduction(
    raw_damage: RawDamage,
    armor_profile: dict,
    *,
    armor_skill: int,
    maneuver_mod: int,
    multi_armor_penalty: int,
    rng,
) -> ArmorReduction:
    durability_pct = _durability_pct(armor_profile.get("damage", 0), armor_profile.get("strength", 100))
    punc_flat, punc_pct = _split_encoded_resistance(armor_profile.get("punc_res", 0), durability_pct)
    slic_flat, slic_pct = _split_encoded_resistance(armor_profile.get("slic_res", 0), durability_pct)
    impa_flat, impa_pct = _split_encoded_resistance(armor_profile.get("impa_res", 0), durability_pct)
    fire_flat, fire_pct = _split_encoded_resistance(armor_profile.get("fire_res", 0), durability_pct)
    cold_flat, cold_pct = _split_encoded_resistance(armor_profile.get("cold_res", 0), durability_pct)
    elec_flat, elec_pct = _split_encoded_resistance(armor_profile.get("elec_res", 0), durability_pct)

    puncture_after, puncture_flat = _apply_flat_stage(raw_damage.puncture, punc_flat, armor_skill, maneuver_mod, multi_armor_penalty, rng)
    slice_after, slice_flat = _apply_flat_stage(raw_damage.slice, slic_flat, armor_skill, maneuver_mod, multi_armor_penalty, rng)
    impact_after, impact_flat = _apply_flat_stage(raw_damage.impact, impa_flat, armor_skill, maneuver_mod, multi_armor_penalty, rng)
    fire_after, _ = _apply_flat_stage(raw_damage.fire, fire_flat, armor_skill, maneuver_mod, multi_armor_penalty, rng)
    cold_after, _ = _apply_flat_stage(raw_damage.cold, cold_flat, armor_skill, maneuver_mod, multi_armor_penalty, rng)
    elec_after, _ = _apply_flat_stage(raw_damage.electric, elec_flat, armor_skill, maneuver_mod, multi_armor_penalty, rng)

    variance = rng.randint(-5, 5)
    puncture_final, puncture_pct = _apply_percent_stage(puncture_after, punc_pct, variance)
    slice_final, slice_pct = _apply_percent_stage(slice_after, slic_pct, variance)
    impact_final, impact_pct = _apply_percent_stage(impact_after, impa_pct, variance)
    fire_final, fire_pct_used = _apply_percent_stage(fire_after, fire_pct, variance)
    cold_final, cold_pct_used = _apply_percent_stage(cold_after, cold_pct, variance)
    elec_final, elec_pct_used = _apply_percent_stage(elec_after, elec_pct, variance)

    return ArmorReduction(
        puncture=puncture_final,
        slice=slice_final,
        impact=impact_final,
        fire=fire_final,
        cold=cold_final,
        electric=elec_final,
        flat_reduction=(puncture_flat, slice_flat, impact_flat),
        percent_reduction=(puncture_pct, slice_pct, impact_pct, fire_pct_used, cold_pct_used, elec_pct_used),
    )