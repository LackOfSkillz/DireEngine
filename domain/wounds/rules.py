"""Pure rules for physical wounds, bleed, and penalties."""

from __future__ import annotations

import math
import random
import time

from domain.wounds.constants import (
	BLEED_TICK_SECONDS,
	BODY_PART_ORDER,
	LOW_HP_WOUND_RATIO,
	RECENT_TEND_WINDOW,
	SCAR_RULES,
	SEVERITY_ADVERBS,
	WOUND_APPLICATION_THRESHOLDS,
)
from domain.wounds.models import normalize_body_part, normalize_injuries


def get_part_trauma(body_part: dict | None) -> int:
	body_part = normalize_body_part(body_part)
	return max(
		int(body_part.get("external", 0) or 0),
		int(body_part.get("internal", 0) or 0),
		int(body_part.get("bruise", 0) or 0),
	)


def get_injury_level(value: int | float) -> str:
	value = int(value or 0)
	if value <= 0:
		return "none"
	if value <= 10:
		return "light"
	if value <= 25:
		return "moderate"
	if value <= 50:
		return "severe"
	return "critical"


def get_bleed_severity(total_bleed: int | float) -> str:
	total_bleed = int(total_bleed or 0)
	if total_bleed <= 0:
		return "none"
	if total_bleed <= 2:
		return "light"
	if total_bleed <= 5:
		return "moderate"
	if total_bleed <= 10:
		return "severe"
	return "critical"


def get_body_part_wound_descriptions(body_part: dict | None) -> list[str]:
	body_part = normalize_body_part(body_part)
	descriptions: list[str] = []

	bruise = int(body_part.get("bruise", 0) or 0)
	if bruise > 0:
		severity = get_injury_level(bruise)
		descriptions.append(f"{SEVERITY_ADVERBS[severity]} bruised")

	external = int(body_part.get("external", 0) or 0)
	if external > 0:
		severity = get_injury_level(external)
		descriptions.append(f"{SEVERITY_ADVERBS[severity]} wounded")

	internal = int(body_part.get("internal", 0) or 0)
	if internal > 0:
		severity = get_injury_level(internal)
		descriptions.append(f"{SEVERITY_ADVERBS[severity]} internally injured")

	scars = int(body_part.get("scar", 0) or 0)
	if scars > 0:
		descriptions.append("marked by old scarring" if scars == 1 else "marked by heavy scarring")

	return descriptions


def apply_scar_progress(body_part: dict | None, before_part: dict | None = None) -> tuple[dict, int]:
	current = normalize_body_part(body_part)
	previous = normalize_body_part(before_part)
	previous_peak = max(int(previous.get("external", 0) or 0), int(previous.get("internal", 0) or 0))
	previous_trauma = int(previous.get("external", 0) or 0) + int(previous.get("internal", 0) or 0)
	current_peak = max(int(current.get("external", 0) or 0), int(current.get("internal", 0) or 0))
	current_trauma = int(current.get("external", 0) or 0) + int(current.get("internal", 0) or 0)
	scar_gain = 0
	if previous_peak < int(SCAR_RULES["severity_threshold"]) <= current_peak:
		scar_gain += 1
	if previous_trauma < int(SCAR_RULES["trauma_threshold"]) <= current_trauma:
		scar_gain += 1
	if previous_trauma >= int(SCAR_RULES["repeat_gate"]) and (current_trauma - previous_trauma) >= int(SCAR_RULES["repeat_threshold"]):
		scar_gain += 1
	if scar_gain > 0:
		current["scar"] = min(int(SCAR_RULES["max_scars"]), int(current.get("scar", 0) or 0) + scar_gain)
	return current, scar_gain


def should_apply_wound(target, body_part: dict | None, damage: int, damage_type: str = "impact", critical: bool = False) -> bool:
	body_part = normalize_body_part(body_part)
	damage = int(damage or 0)
	if damage <= 0:
		return False
	threshold = int(WOUND_APPLICATION_THRESHOLDS.get(str(damage_type or "").lower(), WOUND_APPLICATION_THRESHOLDS["default"]))
	if critical or damage >= threshold:
		return True
	if get_part_trauma(body_part) > 0:
		return True
	max_hp = max(1, int(target.db.max_hp or 1))
	hp = max(0, int(target.db.hp or 0))
	return (hp / max_hp) <= LOW_HP_WOUND_RATIO and damage >= max(3, threshold - 2)


def apply_hit_to_part(target, injuries: dict | None, location: str, damage: int, damage_type: str = "impact", critical: bool = False) -> dict:
	all_injuries = normalize_injuries(injuries)
	if location not in all_injuries:
		return {"applied": False, "injuries": all_injuries, "body_part": {}, "scar_gain": 0, "vital_destroyed": False}

	body_part = normalize_body_part(all_injuries[location])
	if not should_apply_wound(target, body_part, damage, damage_type=damage_type, critical=critical):
		return {
			"applied": False,
			"injuries": all_injuries,
			"body_part": body_part,
			"scar_gain": 0,
			"vital_destroyed": False,
			"severity": get_injury_level(get_part_trauma(body_part)),
		}

	before_part = dict(body_part)
	body_part["tended"] = False
	damage_kind = str(damage_type or "impact").lower()
	amount = max(0, int(damage or 0))

	if damage_kind == "impact":
		previous_bruise = int(body_part.get("bruise", 0) or 0)
		body_part["bruise"] = previous_bruise + amount
		if amount >= 8:
			body_part["internal"] = int(body_part.get("internal", 0) or 0) + max(1, amount // 4)
		if critical:
			body_part["internal"] = int(body_part.get("internal", 0) or 0) + max(1, amount // 3)
		if location == "head":
			head_thresholds = (8, 18, 30)
			bleed_gain = sum(1 for threshold in head_thresholds if previous_bruise < threshold <= body_part["bruise"])
			if critical:
				bleed_gain += 1
			if bleed_gain > 0:
				body_part["bleed"] = int(body_part.get("bleed", 0) or 0) + bleed_gain
				body_part["external"] = int(body_part.get("external", 0) or 0) + bleed_gain
		elif amount >= 10 or critical:
			body_part["bleed"] = int(body_part.get("bleed", 0) or 0) + 1
	else:
		body_part["external"] = int(body_part.get("external", 0) or 0) + amount
		if damage_kind in {"slice", "pierce", "stab"}:
			if amount >= 4:
				body_part["bleed"] = int(body_part.get("bleed", 0) or 0) + 1 + (1 if amount >= 8 else 0)
			if critical:
				body_part["bleed"] = int(body_part.get("bleed", 0) or 0) + 1
		elif amount >= 10 or critical:
			body_part["bleed"] = int(body_part.get("bleed", 0) or 0) + 1

	body_part["external"] = min(int(body_part.get("max", 100) or 100), int(body_part.get("external", 0) or 0))
	body_part["internal"] = min(int(body_part.get("max", 100) or 100), int(body_part.get("internal", 0) or 0))
	body_part, scar_gain = apply_scar_progress(body_part, before_part=before_part)
	all_injuries[location] = body_part
	return {
		"applied": True,
		"injuries": all_injuries,
		"body_part": body_part,
		"scar_gain": scar_gain,
		"vital_destroyed": bool(body_part.get("vital")) and int(body_part.get("external", 0) or 0) >= int(body_part.get("max", 100) or 100),
		"severity": get_injury_level(get_part_trauma(body_part)),
	}


def is_tended(body_part: dict | None, now: float | None = None) -> bool:
	body_part = normalize_body_part(body_part)
	now = float(now or time.time())
	tend_state = body_part.get("tend") or {}
	return int(tend_state.get("duration", 0) or 0) > 0 or now < float(tend_state.get("min_until", 0.0) or 0.0)


def build_tend_state(body_part: dict | None, skill: int = 0, now: float | None = None, strong: bool = False) -> dict:
	body_part = normalize_body_part(body_part)
	now = float(now or time.time())
	current_bleed = max(0, int(body_part.get("bleed", 0) or 0))
	strength = max(3, current_bleed + 1, 2 + (int(skill or 0) // 6))
	duration = 12 + (int(skill or 0) // 2)
	last_applied = float((body_part.get("tend") or {}).get("last_applied", 0.0) or 0.0)
	recently_tended = is_tended(body_part, now=now) or ((now - last_applied) < RECENT_TEND_WINDOW)
	if strong:
		strength += 1
		duration += 4
	if recently_tended:
		strength = max(2, int(strength * 0.6))
		duration = max(6, int(duration * 0.6))
	return {
		"strength": strength,
		"duration": duration,
		"last_applied": now,
		"min_until": now + 120.0,
	}


def heal_part(body_part: dict | None, amount: int) -> dict:
	body_part = normalize_body_part(body_part)
	remaining = max(0, int(amount or 0))
	if remaining <= 0:
		return body_part
	if int(body_part.get("external", 0) or 0) > 0:
		healed = min(int(body_part.get("external", 0) or 0), remaining)
		body_part["external"] = int(body_part.get("external", 0) or 0) - healed
		remaining -= healed
	if remaining > 0 and int(body_part.get("bruise", 0) or 0) > 0:
		body_part["bruise"] = max(0, int(body_part.get("bruise", 0) or 0) - remaining)
	if remaining > 0 and int(body_part.get("internal", 0) or 0) > 0:
		body_part["internal"] = max(0, int(body_part.get("internal", 0) or 0) - remaining)
	if get_part_trauma(body_part) <= 0 and int(body_part.get("bleed", 0) or 0) <= 0:
		body_part["tended"] = False
		body_part["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
	return body_part


def stop_bleeding(body_part: dict | None) -> dict:
	body_part = normalize_body_part(body_part)
	body_part["bleed"] = 0
	body_part["tended"] = True
	body_part["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
	return body_part


def get_total_bleed(injuries: dict | None) -> int:
	normalized = normalize_injuries(injuries)
	return sum(int(body_part.get("bleed", 0) or 0) for body_part in normalized.values())


def get_effective_bleed_total(injuries: dict | None, now: float | None = None) -> int:
	normalized = normalize_injuries(injuries)
	now = float(now or time.time())
	total = 0
	for body_part in normalized.values():
		bleed = int(body_part.get("bleed", 0) or 0)
		tend_state = body_part.get("tend") or {}
		duration = int(tend_state.get("duration", 0) or 0)
		min_until = float(tend_state.get("min_until", 0.0) or 0.0)
		strength = int(tend_state.get("strength", 0) or 0)
		if duration > 0 or now < min_until:
			bleed = max(0, bleed - strength)
		total += bleed
	return total


def has_any_active_wounds(injuries: dict | None) -> bool:
	for body_part in normalize_injuries(injuries).values():
		if get_part_trauma(body_part) > 0 or int(body_part.get("bleed", 0) or 0) > 0:
			return True
	return False


def derive_penalties(injuries: dict | None) -> dict:
	normalized = normalize_injuries(injuries)
	head_trauma = get_part_trauma(normalized.get("head"))
	chest_trauma = get_part_trauma(normalized.get("chest"))
	abdomen_trauma = get_part_trauma(normalized.get("abdomen"))
	left_arm_trauma = get_part_trauma(normalized.get("left_arm"))
	right_arm_trauma = get_part_trauma(normalized.get("right_arm"))
	left_hand_trauma = get_part_trauma(normalized.get("left_hand"))
	right_hand_trauma = get_part_trauma(normalized.get("right_hand"))
	left_leg_trauma = get_part_trauma(normalized.get("left_leg"))
	right_leg_trauma = get_part_trauma(normalized.get("right_leg"))

	arm_penalty = min(25, int(math.sqrt(max(left_arm_trauma, right_arm_trauma))))
	hand_penalty = min(25, int(math.sqrt(max(left_hand_trauma, right_hand_trauma))))
	leg_penalty = min(25, int(math.sqrt(max(left_leg_trauma, right_leg_trauma))))
	head_penalty = min(20, int(math.sqrt(head_trauma)))
	core_penalty = min(18, int(math.sqrt(max(chest_trauma, abdomen_trauma))))
	return {
		"arm_penalty": arm_penalty,
		"hand_penalty": hand_penalty,
		"leg_penalty": leg_penalty,
		"attack_accuracy_penalty": hand_penalty + max(0, head_penalty // 2),
		"attack_control_penalty": arm_penalty + hand_penalty,
		"evasion_penalty": leg_penalty + max(0, core_penalty // 2),
		"balance_penalty": leg_penalty + max(0, core_penalty // 2),
		"movement_cost_mult": 1.0 + (leg_penalty / 40.0),
		"fatigue_recovery_mult": max(0.5, 1.0 - (core_penalty / 40.0)),
	}


def apply_bleed_tick(
	injuries: dict | None,
	*,
	now: float | None = None,
	in_combat: bool = False,
	stabilized_until: float = 0.0,
	stability_strength: float = 0.0,
	resurrection_bleed_multiplier: float = 1.0,
	rng=None,
) -> dict:
	normalized = normalize_injuries(injuries)
	now = float(now or time.time())
	rng = rng or random.random
	is_stabilized = now < float(stabilized_until or 0.0)
	strength = max(0.0, min(1.0, float(stability_strength or 0.0))) if is_stabilized else 0.0
	total_bleed = 0
	resumed_parts: list[str] = []

	for part_name, body_part in normalized.items():
		if int(body_part.get("internal", 0) or 0) > 20:
			worsening_rate = 1.0
			if is_stabilized:
				worsening_rate *= max(0.0, 1.0 - strength)
			bleed_gain = int(worsening_rate)
			fractional = max(0.0, worsening_rate - bleed_gain)
			if fractional > 0.0 and rng() < fractional:
				bleed_gain += 1
			if bleed_gain > 0:
				body_part["bleed"] = int(body_part.get("bleed", 0) or 0) + bleed_gain

		tend_state = dict(body_part.get("tend") or {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0})
		duration = int(tend_state.get("duration", 0) or 0)
		strength_value = int(tend_state.get("strength", 0) or 0)
		min_until = float(tend_state.get("min_until", 0.0) or 0.0)
		was_tended = bool(body_part.get("tended", False))

		effective_bleed = int(body_part.get("bleed", 0) or 0)
		if duration > 0 or now < min_until:
			effective_bleed = max(0, effective_bleed - strength_value)
			if now >= min_until and duration > 0:
				duration -= 1
				if int(body_part.get("external", 0) or 0) > 45:
					duration -= 1
				if in_combat:
					duration -= 1
			tend_state["duration"] = max(0, duration)
			body_part["tend"] = tend_state
			body_part["tended"] = tend_state["duration"] > 0 or now < min_until
			if was_tended and not body_part["tended"] and int(body_part.get("bleed", 0) or 0) > 0:
				resumed_parts.append(part_name)

		total_bleed += max(0, effective_bleed)

	hp_loss = 0
	if total_bleed > 0:
		hp_loss = total_bleed + int(total_bleed * 0.3)
		if total_bleed > 10:
			hp_loss -= (total_bleed - 10)
		hp_loss = max(1, hp_loss)
		hp_loss = max(1, int(round(hp_loss * float(resurrection_bleed_multiplier or 1.0))))

	return {
		"injuries": normalized,
		"total_bleed": total_bleed,
		"hp_loss": hp_loss,
		"resumed_parts": resumed_parts,
		"tick_seconds": BLEED_TICK_SECONDS,
	}


def apply_natural_recovery(injuries: dict | None, *, stabilized: bool = False, in_combat: bool = False) -> dict:
	normalized = normalize_injuries(injuries)
	if in_combat:
		return {"injuries": normalized, "changed": False, "remaining": has_any_active_wounds(normalized)}

	changed = False
	for body_part in normalized.values():
		before = dict(body_part)
		if int(body_part.get("bruise", 0) or 0) > 0:
			body_part["bruise"] = max(0, int(body_part.get("bruise", 0) or 0) - 1)
		if int(body_part.get("bleed", 0) or 0) <= 0:
			if int(body_part.get("external", 0) or 0) > 0 and (stabilized or bool(body_part.get("tended", False))):
				body_part["external"] = max(0, int(body_part.get("external", 0) or 0) - 1)
			if int(body_part.get("internal", 0) or 0) > 0 and stabilized:
				body_part["internal"] = max(0, int(body_part.get("internal", 0) or 0) - 1)
		if get_part_trauma(body_part) <= 0 and int(body_part.get("bleed", 0) or 0) <= 0:
			body_part["tended"] = False
			body_part["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
		if body_part != before:
			changed = True

	return {"injuries": normalized, "changed": changed, "remaining": has_any_active_wounds(normalized)}
