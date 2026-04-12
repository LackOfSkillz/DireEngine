from __future__ import annotations

from collections.abc import Mapping
import time

from domain.wounds import rules as wound_rules
from domain.wounds.constants import BLEED_TICK_SECONDS, BODY_PART_ORDER, RECOVERY_TICK_SECONDS
from domain.wounds.models import copy_default_injuries, normalize_injuries
from engine.services.result import ActionResult


_SCHEDULER_CALLBACKS_REGISTERED = False


def _get_scheduler_api():
	from world.systems.scheduler import cancel_event, register_event_callback, schedule_event

	return cancel_event, register_event_callback, schedule_event


def _ensure_scheduler_callbacks_registered() -> bool:
	global _SCHEDULER_CALLBACKS_REGISTERED
	if _SCHEDULER_CALLBACKS_REGISTERED:
		return True
	try:
		_, register_event_callback, _ = _get_scheduler_api()
	except Exception:
		return False
	register_event_callback("injury:process_bleed", _callback_process_bleed)
	register_event_callback("injury:process_recovery", _callback_process_recovery)
	_SCHEDULER_CALLBACKS_REGISTERED = True
	return True


class InjuryService:

	@staticmethod
	def _ensure_wound_state(target) -> dict:
		if hasattr(target, "ensure_core_defaults"):
			target.ensure_core_defaults()
		injuries = getattr(getattr(target, "db", None), "injuries", None)
		if not isinstance(injuries, Mapping):
			injuries = copy_default_injuries()
			target.db.injuries = injuries
		else:
			injuries = normalize_injuries(injuries)
			target.db.injuries = injuries
		return injuries

	@staticmethod
	def _set_injuries(target, injuries: dict) -> dict:
		normalized = normalize_injuries(injuries)
		target.db.injuries = normalized
		return normalized

	@staticmethod
	def _format_part(target, part_name: str) -> str:
		if hasattr(target, "format_body_part_name"):
			return target.format_body_part_name(part_name)
		return str(part_name or "part").replace("_", " ")

	@staticmethod
	def _get_total_bleed(target) -> int:
		return wound_rules.get_total_bleed(InjuryService._ensure_wound_state(target))

	@staticmethod
	def _has_active_wounds(target) -> bool:
		return wound_rules.has_any_active_wounds(InjuryService._ensure_wound_state(target))

	@staticmethod
	def _schedule_bleed_tick(target) -> None:
		if target is None or not getattr(target, "pk", None):
			return
		if not _ensure_scheduler_callbacks_registered():
			return
		_, _, schedule_event = _get_scheduler_api()
		schedule_event(
			"bleed",
			target,
			BLEED_TICK_SECONDS,
			"injury:process_bleed",
			metadata={"system": "injury", "type": "bleed", "timing_mode": "scheduled-expiry"},
		)

	@staticmethod
	def _cancel_bleed_tick(target) -> None:
		if target is None:
			return
		try:
			cancel_event, _, _ = _get_scheduler_api()
		except Exception:
			return
		cancel_event("bleed", target)

	@staticmethod
	def _schedule_recovery_tick(target) -> None:
		if target is None or not getattr(target, "pk", None):
			return
		if not _ensure_scheduler_callbacks_registered():
			return
		_, _, schedule_event = _get_scheduler_api()
		schedule_event(
			"recover",
			target,
			RECOVERY_TICK_SECONDS,
			"injury:process_recovery",
			metadata={"system": "injury", "type": "recover", "timing_mode": "scheduled-expiry"},
		)

	@staticmethod
	def _cancel_recovery_tick(target) -> None:
		if target is None:
			return
		try:
			cancel_event, _, _ = _get_scheduler_api()
		except Exception:
			return
		cancel_event("recover", target)

	@staticmethod
	def sync_scheduled_effects(target) -> None:
		if InjuryService._get_total_bleed(target) > 0:
			InjuryService._schedule_bleed_tick(target)
		else:
			InjuryService._cancel_bleed_tick(target)

		if InjuryService._has_active_wounds(target):
			InjuryService._schedule_recovery_tick(target)
		else:
			InjuryService._cancel_recovery_tick(target)

	@staticmethod
	def bootstrap_scheduled_effects(target) -> None:
		if target is None or not getattr(target, "pk", None):
			return
		InjuryService.sync_scheduled_effects(target)

	@staticmethod
	def get_active_penalties(target) -> dict:
		injuries = InjuryService._ensure_wound_state(target)
		return wound_rules.derive_penalties(injuries)

	@staticmethod
	def get_injury_level(value) -> str:
		return wound_rules.get_injury_level(value)

	@staticmethod
	def get_bleed_severity(total_bleed) -> str:
		return wound_rules.get_bleed_severity(total_bleed)

	@staticmethod
	def get_body_part_wound_descriptions(body_part: dict | None) -> list[str]:
		return wound_rules.get_body_part_wound_descriptions(body_part)

	@staticmethod
	def get_injury_display_lines(target, looker=None) -> list[str]:
		injuries = InjuryService._ensure_wound_state(target)
		lines: list[str] = []
		for part_name in BODY_PART_ORDER:
			body_part = injuries.get(part_name)
			if not body_part:
				continue
			trauma = wound_rules.get_part_trauma(body_part)
			bleed = int(body_part.get("bleed", 0) or 0)
			tended = bool(body_part.get("tended", False))
			if trauma <= 0 and bleed <= 0:
				continue
			part_display = InjuryService._format_part(target, part_name)
			wound_text = ", ".join(wound_rules.get_body_part_wound_descriptions(body_part)) or "uninjured"
			tended_text = " (tended)" if tended else ""
			if looker == target:
				if bleed > 0:
					lines.append(f"You are bleeding from your {part_display}{tended_text}.")
				else:
					lines.append(f"Your {part_display} is {wound_text}{tended_text}.")
				continue
			owner_name = target.get_possessive_name(looker=looker) if hasattr(target, "get_possessive_name") else f"{getattr(target, 'key', 'Their')}'s"
			if bleed > 0:
				lines.append(f"{owner_name.capitalize()} {part_display} is bleeding{tended_text}.")
			else:
				lines.append(f"{owner_name.capitalize()} {part_display} is {wound_text}{tended_text}.")
		return lines

	@staticmethod
	def update_bleed_state(target, emit_messages: bool = True) -> ActionResult:
		injuries = InjuryService._ensure_wound_state(target)
		total_bleed = wound_rules.get_total_bleed(injuries)
		new_state = wound_rules.get_bleed_severity(total_bleed)
		old_state = str(getattr(target.db, "bleed_state", "none") or "none")
		target.db.bleed_state = new_state
		if emit_messages and new_state != old_state:
			if hasattr(target, "on_bleed_state_change"):
				target.on_bleed_state_change(old_state, new_state)
			else:
				if new_state == "none":
					target.msg("Your bleeding has stopped.")
				elif new_state == "light":
					target.msg("You are bleeding.")
				elif new_state == "moderate":
					target.msg("Your wounds are bleeding steadily.")
				elif new_state == "severe":
					target.msg("Your wounds are bleeding heavily.")
				else:
					target.msg("Blood is pouring from your wounds!")
		InjuryService.sync_scheduled_effects(target)
		return ActionResult.ok(data={"bleed_state": new_state, "total_bleed": total_bleed})

	@staticmethod
	def apply_hit_wound(target, location, damage, damage_type="impact", critical: bool = False):
		injuries = InjuryService._ensure_wound_state(target)
		if not location or location not in injuries:
			return ActionResult.ok(data={"amount": int(damage or 0), "location": location, "severity": "none", "bleed": 0, "applied": False})

		amount = max(0, int(damage or 0))
		if amount <= 0:
			return ActionResult.ok(data={"amount": 0, "location": location, "severity": "none", "bleed": 0, "applied": False})

		if hasattr(target, "maybe_break_ranger_aim_on_hit"):
			target.maybe_break_ranger_aim_on_hit(amount)
		if getattr(target.db, "disguised", False) and hasattr(target, "clear_disguise"):
			target.clear_disguise()
		if getattr(target.db, "post_ambush_grace", False) and time.time() < float(getattr(target.db, "post_ambush_grace_until", 0) or 0):
			amount = max(0, int(round(amount * 0.8)))
		if bool(getattr(target.db, "is_npc", False)) and hasattr(target, "is_surprised") and target.is_surprised() and hasattr(target, "set_awareness"):
			target.set_awareness("alert")

		apply_result = wound_rules.apply_hit_to_part(target, injuries, location, amount, damage_type=damage_type, critical=critical)
		injuries = InjuryService._set_injuries(target, apply_result["injuries"])
		body_part = apply_result.get("body_part") or {}
		severity = str(apply_result.get("severity") or "none")
		if apply_result.get("applied"):
			if severity in {"severe", "critical"}:
				target.msg(f"Your {InjuryService._format_part(target, location)} is badly damaged!")
			if int(apply_result.get("scar_gain", 0) or 0) > 0:
				target.msg(f"The hurt leaves lasting damage in your {InjuryService._format_part(target, location)}.")
			if location == "chest" and int(body_part.get("internal", 0) or 0) > 50:
				target.msg("You are in critical condition!")

		if apply_result.get("vital_destroyed"):
			target.db.is_dead = True

		penalties = wound_rules.derive_penalties(injuries)
		bleed_result = InjuryService.update_bleed_state(target)
		return ActionResult.ok(
			data={
				"amount": amount,
				"location": location,
				"severity": severity,
				"bleed": int(body_part.get("bleed", 0) or 0),
				"applied": bool(apply_result.get("applied")),
				"total_bleed": int(bleed_result.data.get("total_bleed", 0) or 0),
				"penalties": penalties,
			},
		)

	@staticmethod
	def heal_wound(target, location, amount):
		injuries = InjuryService._ensure_wound_state(target)
		if not location or location not in injuries:
			return ActionResult.fail(errors=[f"Unknown wound location: {location}"])
		injuries[location] = wound_rules.heal_part(injuries.get(location), amount)
		InjuryService._set_injuries(target, injuries)
		InjuryService.update_bleed_state(target, emit_messages=False)
		return ActionResult.ok(data={"location": location, "amount": int(amount or 0)})

	@staticmethod
	def stop_bleeding(target, location):
		injuries = InjuryService._ensure_wound_state(target)
		if not location or location not in injuries:
			return ActionResult.fail(errors=[f"Unknown wound location: {location}"])
		injuries[location] = wound_rules.stop_bleeding(injuries.get(location))
		InjuryService._set_injuries(target, injuries)
		InjuryService.update_bleed_state(target)
		return ActionResult.ok(data={"location": location})

	@staticmethod
	def stabilize_wound(target, location, skill_result=None, tender=None, heal_amount: int = 0, strong: bool = False):
		injuries = InjuryService._ensure_wound_state(target)
		if not location or location not in injuries:
			return ActionResult.fail(errors=[f"Unknown wound location: {location}"])
		healer = tender or target
		skill_rank = int(skill_result or 0)
		if skill_rank <= 0 and hasattr(healer, "get_skill"):
			skill_rank = int(healer.get_skill("first_aid") or 0)
		body_part = dict(injuries.get(location) or {})
		if int(body_part.get("bleed", 0) or 0) <= 0 and wound_rules.get_part_trauma(body_part) <= 0:
			return ActionResult.fail(errors=[f"{location} does not need treatment"])
		body_part["tend"] = wound_rules.build_tend_state(body_part, skill=skill_rank, strong=strong)
		body_part["tended"] = True
		injuries[location] = body_part
		InjuryService._set_injuries(target, injuries)
		if hasattr(target, "start_first_aid_training_window"):
			target.start_first_aid_training_window(location, tender=healer)
		if heal_amount > 0:
			InjuryService.heal_wound(target, location, heal_amount)
		InjuryService.update_bleed_state(target, emit_messages=False)
		return ActionResult.ok(data={"location": location, "strength": int(body_part["tend"].get("strength", 0) or 0), "duration": int(body_part["tend"].get("duration", 0) or 0)})

	@staticmethod
	def process_bleed_tick(target, payload=None):
		if target is None or not getattr(target, "pk", None):
			return ActionResult.fail(errors=["Missing target"])
		injuries = InjuryService._ensure_wound_state(target)
		if wound_rules.get_total_bleed(injuries) <= 0:
			InjuryService._cancel_bleed_tick(target)
			InjuryService.sync_scheduled_effects(target)
			return ActionResult.ok(data={"hp_loss": 0, "total_bleed": 0})

		bleed_result = wound_rules.apply_bleed_tick(
			injuries,
			now=time.time(),
			in_combat=bool(getattr(target.db, "in_combat", False)),
			stabilized_until=float(getattr(target.db, "stabilized_until", 0.0) or 0.0),
			stability_strength=float(getattr(target.db, "stability_strength", 0.0) or 0.0),
			resurrection_bleed_multiplier=float(target.get_resurrection_bleed_multiplier() if hasattr(target, "get_resurrection_bleed_multiplier") else 1.0),
		)
		injuries = InjuryService._set_injuries(target, bleed_result["injuries"])
		for part_name in bleed_result.get("resumed_parts", []):
			target.msg(f"Your {InjuryService._format_part(target, part_name)} begins bleeding again!")
		hp_loss = int(bleed_result.get("hp_loss", 0) or 0)
		if hp_loss > 0:
			target.set_hp((target.db.hp or 0) - hp_loss)
			target.msg("You bleed from your wounds.")
			if int(bleed_result.get("total_bleed", 0) or 0) > 5:
				target.msg("You are bleeding heavily!")
			if (target.db.hp or 0) <= 0:
				if hasattr(target, "consume_resurrection_death_guard") and target.consume_resurrection_death_guard():
					target.db.hp = 1
					target.msg("Your returning life falters, but the rite holds for one heartbeat.")
				else:
					target.db.is_dead = True
		InjuryService.update_bleed_state(target)
		return ActionResult.ok(data={"hp_loss": hp_loss, "total_bleed": wound_rules.get_total_bleed(injuries)})

	@staticmethod
	def process_recovery_tick(target, payload=None):
		if target is None or not getattr(target, "pk", None):
			return ActionResult.fail(errors=["Missing target"])
		injuries = InjuryService._ensure_wound_state(target)
		recovery_result = wound_rules.apply_natural_recovery(
			injuries,
			stabilized=bool(time.time() < float(getattr(target.db, "stabilized_until", 0.0) or 0.0)),
			in_combat=bool(getattr(target.db, "in_combat", False)),
		)
		InjuryService._set_injuries(target, recovery_result["injuries"])
		InjuryService.update_bleed_state(target, emit_messages=False)
		return ActionResult.ok(data={"changed": bool(recovery_result.get("changed")), "remaining": bool(recovery_result.get("remaining"))})


def _callback_process_bleed(owner, payload=None):
	return InjuryService.process_bleed_tick(owner, payload)


def _callback_process_recovery(owner, payload=None):
	return InjuryService.process_recovery_tick(owner, payload)