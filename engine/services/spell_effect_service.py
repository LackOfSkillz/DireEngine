import time

from domain.spells.spell_definitions import Spell
from domain.wounds import rules as wound_rules
from domain.wounds.models import copy_default_injuries, normalize_injuries
from engine.services.empath_saf_service import EmpathSafService
from engine.services.mana_service import ManaService
from engine.services.result import ActionResult
from engine.services.spell_contest_service import SpellContestService
from engine.services.state_service import StateService


class SpellEffectService:
    EFFECT_FAMILY_HANDLERS = {
        "aoe": "_apply_aoe_spell",
        "augmentation": "_apply_augmentation_spell",
        "cyclic": "_apply_cyclic_spell",
        "debilitation": "_apply_debilitation_spell",
        "healing": "_apply_healing_spell",
        "resurrection": "_apply_resurrection_spell",
        "targeted_magic": "_apply_targeted_magic_spell",
        "utility": "_apply_utility_spell",
        "warding": "_apply_warding_spell",
    }

    @staticmethod
    def apply_spell(caster, spell: Spell, final_spell_power, quality="normal", target=None):
        if caster is None:
            return ActionResult.fail(errors=["Missing caster."])
        if spell is None:
            return ActionResult.fail(errors=["Missing spell definition."])

        spell_type = str(spell.spell_type or "").strip().lower()
        handler_name = SpellEffectService.EFFECT_FAMILY_HANDLERS.get(spell_type)
        if not handler_name:
            return ActionResult.fail(
                errors=[f"No structured effect handler exists for spell family {spell_type}."],
                data={"spell_id": spell.id, "spell_type": spell_type, "reason": "unknown_effect_family"},
            )

        handler = getattr(SpellEffectService, handler_name)
        result = handler(caster, spell, final_spell_power, quality=quality, target=target)
        if getattr(result, "success", False):
            payload = dict((result.data or {}).get("effect_payload") or {})
            if payload:
                payload.setdefault("caster_key", getattr(caster, "key", "someone"))
                result.data["effect_payload"] = payload
        SpellEffectService._attach_structured_effect_trace(caster, spell, handler_name, result)
        return result

    # RULE:
    # Hit or miss is owned by the contest and combat layer.
    # SpellEffectService routes only; it does not decide contested outcomes itself.

    @staticmethod
    def _apply_aoe_spell(caster, spell, final_spell_power, quality="normal", target=None):
        room = target if hasattr(target, "contents") else getattr(caster, "location", None)
        targets = SpellEffectService.get_valid_aoe_targets(room, caster, spell)
        if not targets:
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": {
                        "effect_family": "aoe",
                        "target_count": 0,
                        "targets": [],
                        "source_mana_type": str(spell.mana_type or "").strip().lower(),
                    },
                }
            )

        scaled_power = SpellEffectService._scale_aoe_power(final_spell_power, len(targets), spell)
        target_payloads = []
        for victim in targets:
            # PERFORMANCE:
            # AoE loops must remain O(n).
            # Never add nested target scans inside this loop.
            contest_result = SpellContestService.resolve_targeted_magic(
                caster,
                victim,
                scaled_power,
                spell_id=getattr(spell, "id", None),
                quality=quality,
                wild_modifier=1.0,
            )
            if not contest_result.success:
                target_payloads.append(
                    {
                        "target_id": getattr(victim, "id", None),
                        "target_key": getattr(victim, "key", "someone"),
                        "hit": False,
                        "error": list(contest_result.errors or []),
                    }
                )
                continue

            per_target = dict(contest_result.data or {})
            target_payloads.append(
                {
                    "target_id": getattr(victim, "id", None),
                    "target_key": getattr(victim, "key", "someone"),
                    "hit": bool(per_target.get("hit", False)),
                    "hit_quality": str(per_target.get("hit_quality", "miss") or "miss"),
                    "damage": float(per_target.get("final_damage", 0.0) or 0.0),
                    "absorbed": float(per_target.get("absorbed_by_ward", 0.0) or 0.0),
                    "base_damage": float(per_target.get("base_damage", 0.0) or 0.0),
                    "contest_margin": float(per_target.get("contest_margin", 0.0) or 0.0),
                }
            )

        effect_payload = {
            "effect_family": "aoe",
            "target_count": len(target_payloads),
            "targets": target_payloads,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "scaled_power": float(scaled_power),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_healing_spell(caster, spell, final_spell_power, quality="normal", target=None):
        target_type = str(getattr(spell, "target_type", "self") or "self").strip().lower()
        if target_type == "self" and target is not None and target is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )

        effect_profile = dict(getattr(spell, "effect_profile", {}) or {})
        healing_mode = str(effect_profile.get("healing_mode", "hp") or "hp").strip().lower()
        if healing_mode == "empath_wounds":
            return SpellEffectService._apply_empath_wound_healing(caster, spell, final_spell_power, quality=quality)
        if healing_mode == "external_wounds":
            return SpellEffectService._apply_injury_healing(caster, spell, final_spell_power, quality=quality, heal_external=True)
        if healing_mode == "internal_wounds":
            return SpellEffectService._apply_injury_healing(caster, spell, final_spell_power, quality=quality, heal_internal=True)
        if healing_mode == "scars":
            return SpellEffectService._apply_empath_scar_healing(caster, spell, final_spell_power, quality=quality)
        if healing_mode == "combined_heal":
            return SpellEffectService._apply_combined_empath_heal(caster, spell, final_spell_power, quality=quality)

        recipient = target or caster
        current_hp = int(getattr(getattr(recipient, "db", None), "hp", 0) or 0)
        max_hp = int(getattr(getattr(recipient, "db", None), "max_hp", 0) or 0)
        if max_hp <= 0:
            return ActionResult.fail(
                errors=["Target cannot be healed."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower()},
            )

        quality_bonus = {
            "weak": 0,
            "poor": 0,
            "normal": 1,
            "solid": 1,
            "strong": 2,
            "excellent": 2,
        }.get(str(quality or "normal").strip().lower(), 1)
        effective_power = float(final_spell_power or 0.0)
        if SpellEffectService._is_profession(caster, "empath") and hasattr(caster, "get_empath_healing_modifier"):
            effective_power *= max(0.0, float(caster.get_empath_healing_modifier() or 0.0))

        base_restore = max(1, int(effective_power / 8.0))
        heal_amount = min(max(0, max_hp - current_hp), base_restore + quality_bonus)

        heal_result = StateService.apply_healing(recipient, heal_amount)
        heal_amount = int((heal_result.data or {}).get("amount", 0) or 0)

        effect_payload = {
            "effect_family": "healing",
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "heal_amount": heal_amount,
            "self_target": recipient is caster,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _get_healing_quality_bonus(quality):
        return {
            "weak": 0,
            "poor": 0,
            "normal": 1,
            "solid": 1,
            "strong": 2,
            "excellent": 2,
        }.get(str(quality or "normal").strip().lower(), 1)

    @staticmethod
    def _get_effective_healing_power(caster, final_spell_power):
        effective_power = float(final_spell_power or 0.0)
        if SpellEffectService._is_profession(caster, "empath") and hasattr(caster, "get_empath_healing_modifier"):
            effective_power *= max(0.0, float(caster.get_empath_healing_modifier() or 0.0))
        return effective_power

    @staticmethod
    def _apply_empath_wound_healing(caster, spell, final_spell_power, quality="normal"):
        if not hasattr(caster, "get_empath_wound") or not hasattr(caster, "set_empath_wound"):
            return ActionResult.fail(
                errors=["Caster cannot heal empath wounds."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "missing_empath_wound_hooks"},
            )

        before_vitality = int(caster.get_empath_wound("vitality") or 0)
        before_bleeding = int(caster.get_empath_wound("bleeding") or 0)
        quality_bonus = SpellEffectService._get_healing_quality_bonus(quality)
        effective_power = SpellEffectService._get_effective_healing_power(caster, final_spell_power)
        total_restore = max(0, int(effective_power / 2.0) + quality_bonus)
        heal_vitality = min(before_vitality, max(0, int(round(total_restore * 0.65))))
        heal_bleeding = min(before_bleeding, max(0, total_restore - heal_vitality))
        if heal_bleeding <= 0 and before_bleeding > 0 and total_restore > 0:
            heal_bleeding = 1
            heal_vitality = min(before_vitality, max(0, total_restore - heal_bleeding))

        after_vitality = caster.set_empath_wound("vitality", before_vitality - heal_vitality)
        after_bleeding = caster.set_empath_wound("bleeding", before_bleeding - heal_bleeding)
        healed_vitality = max(0, before_vitality - int(after_vitality or 0))
        healed_bleeding = max(0, before_bleeding - int(after_bleeding or 0))
        heal_amount = healed_vitality + healed_bleeding

        effect_payload = {
            "effect_family": "healing",
            "target_id": getattr(caster, "id", None),
            "target_key": getattr(caster, "key", "someone"),
            "heal_amount": heal_amount,
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "healing_mode": "empath_wounds",
            "healed_vitality": healed_vitality,
            "healed_bleeding": healed_bleeding,
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _clear_tend_state_when_stable(body_part):
        if wound_rules.get_part_trauma(body_part) <= 0 and int(body_part.get("bleed", 0) or 0) <= 0:
            body_part["tended"] = False
            body_part["tend"] = {"strength": 0, "duration": 0, "last_applied": 0.0, "min_until": 0.0}
        return body_part

    @staticmethod
    def _sync_empath_summary_from_injuries(caster, injuries):
        vitality = 0
        bleeding = 0
        for body_part in injuries.values():
            vitality += max(0, int(body_part.get("external", 0) or 0))
            vitality += max(0, int(body_part.get("internal", 0) or 0))
            bleeding += max(0, int(body_part.get("bleed", 0) or 0))
        if hasattr(caster, "set_empath_wound"):
            caster.set_empath_wound("vitality", vitality)
            caster.set_empath_wound("bleeding", bleeding)
        if hasattr(caster, "update_bleed_state"):
            caster.update_bleed_state()
        if hasattr(caster, "sync_client_state"):
            caster.sync_client_state()

    @staticmethod
    def _apply_injury_healing(caster, spell, final_spell_power, quality="normal", *, heal_external=False, heal_internal=False):
        injuries = normalize_injuries(getattr(getattr(caster, "db", None), "injuries", None) or copy_default_injuries())
        quality_bonus = SpellEffectService._get_healing_quality_bonus(quality)
        effective_power = SpellEffectService._get_effective_healing_power(caster, final_spell_power)
        remaining = max(0, int(effective_power / 2.0) + quality_bonus)
        healed_external = 0
        healed_internal = 0

        for body_part in injuries.values():
            if remaining <= 0:
                break
            if heal_external and int(body_part.get("external", 0) or 0) > 0:
                healed = min(int(body_part.get("external", 0) or 0), remaining)
                body_part["external"] = int(body_part.get("external", 0) or 0) - healed
                remaining -= healed
                healed_external += healed
            if remaining <= 0:
                SpellEffectService._clear_tend_state_when_stable(body_part)
                break
            if heal_internal and int(body_part.get("internal", 0) or 0) > 0:
                healed = min(int(body_part.get("internal", 0) or 0), remaining)
                body_part["internal"] = int(body_part.get("internal", 0) or 0) - healed
                remaining -= healed
                healed_internal += healed
            SpellEffectService._clear_tend_state_when_stable(body_part)

        caster.db.injuries = injuries
        SpellEffectService._sync_empath_summary_from_injuries(caster, injuries)

        healing_mode = "external_wounds" if heal_external and not heal_internal else "internal_wounds"
        effect_payload = {
            "effect_family": "healing",
            "target_id": getattr(caster, "id", None),
            "target_key": getattr(caster, "key", "someone"),
            "heal_amount": healed_external + healed_internal,
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "healing_mode": healing_mode,
            "healed_external": healed_external,
            "healed_internal": healed_internal,
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_combined_empath_heal(caster, spell, final_spell_power, quality="normal"):
        injuries = normalize_injuries(getattr(getattr(caster, "db", None), "injuries", None) or copy_default_injuries())
        quality_bonus = SpellEffectService._get_healing_quality_bonus(quality)
        effective_power = SpellEffectService._get_effective_healing_power(caster, final_spell_power)
        remaining_wounds = max(0, int(effective_power / 3.0) + quality_bonus)
        remaining_scars = max(0, int(effective_power / 8.0) + quality_bonus)
        healed_external = 0
        healed_internal = 0
        healed_scars = 0

        for body_part in injuries.values():
            if remaining_wounds <= 0:
                break
            if int(body_part.get("external", 0) or 0) > 0:
                healed = min(int(body_part.get("external", 0) or 0), remaining_wounds)
                body_part["external"] = int(body_part.get("external", 0) or 0) - healed
                remaining_wounds -= healed
                healed_external += healed
            if remaining_wounds > 0 and int(body_part.get("internal", 0) or 0) > 0:
                healed = min(int(body_part.get("internal", 0) or 0), remaining_wounds)
                body_part["internal"] = int(body_part.get("internal", 0) or 0) - healed
                remaining_wounds -= healed
                healed_internal += healed
            SpellEffectService._clear_tend_state_when_stable(body_part)

        if remaining_scars > 0:
            for body_part in injuries.values():
                if remaining_scars <= 0:
                    break
                current = int(body_part.get("scar", 0) or 0)
                if current <= 0:
                    continue
                healed = min(current, remaining_scars)
                body_part["scar"] = current - healed
                remaining_scars -= healed
                healed_scars += healed

        caster.db.injuries = injuries
        SpellEffectService._sync_empath_summary_from_injuries(caster, injuries)

        effect_payload = {
            "effect_family": "healing",
            "target_id": getattr(caster, "id", None),
            "target_key": getattr(caster, "key", "someone"),
            "heal_amount": healed_external + healed_internal + healed_scars,
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "healing_mode": "combined_heal",
            "healed_external": healed_external,
            "healed_internal": healed_internal,
            "healed_scars": healed_scars,
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_empath_scar_healing(caster, spell, final_spell_power, quality="normal"):
        injuries = normalize_injuries(getattr(getattr(caster, "db", None), "injuries", None) or copy_default_injuries())
        quality_bonus = SpellEffectService._get_healing_quality_bonus(quality)
        effective_power = SpellEffectService._get_effective_healing_power(caster, final_spell_power)
        remaining = max(0, int(effective_power / 4.0) + quality_bonus)
        if remaining > 0:
            for part_name, body_part in injuries.items():
                current = int(body_part.get("scar", 0) or 0)
                if current <= 0:
                    continue
                healed = min(current, remaining)
                body_part["scar"] = current - healed
                remaining -= healed
                if remaining <= 0:
                    break

        before_scars = sum(int(part.get("scar", 0) or 0) for part in normalize_injuries(getattr(getattr(caster, "db", None), "injuries", None) or copy_default_injuries()).values())
        after_scars = sum(int(part.get("scar", 0) or 0) for part in injuries.values())
        healed_scars = max(0, before_scars - after_scars)
        caster.db.injuries = injuries
        if hasattr(caster, "sync_client_state"):
            caster.sync_client_state()

        effect_payload = {
            "effect_family": "healing",
            "target_id": getattr(caster, "id", None),
            "target_key": getattr(caster, "key", "someone"),
            "heal_amount": healed_scars,
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "healing_mode": "scars",
            "healed_scars": healed_scars,
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_resurrection_spell(caster, spell, final_spell_power, quality="normal", target=None):
        _quality = quality
        _final_spell_power = final_spell_power
        effect_profile = dict(getattr(spell, "effect_profile", {}) or {})
        behavior = str(effect_profile.get("resurrection_behavior", "single_target_revive") or "single_target_revive").strip().lower()

        if behavior == "deferred_held_mana_ritual_placeholder":
            return ActionResult.fail(
                errors=["Mass Rejuvenation's held-mana ritual is not yet implemented."],
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "reason": "deferred_held_mana_ritual",
                },
            )

        corpse = target
        if not corpse or not bool(getattr(getattr(corpse, "db", None), "is_corpse", False)):
            return ActionResult.fail(
                errors=["You can only cast that spell on a corpse."],
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "reason": "invalid_resurrection_target",
                },
            )

        revive = getattr(caster, "perform_cleric_revive", None)
        if not callable(revive):
            return ActionResult.fail(
                errors=["Caster cannot perform resurrection rites."],
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "reason": "missing_resurrection_hook",
                },
            )

        ok, message = revive(corpse)
        if not ok:
            return ActionResult.fail(
                errors=[str(message or "The resurrection rite fails.")],
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "reason": "resurrection_failed",
                },
            )

        owner = corpse.get_owner() if hasattr(corpse, "get_owner") else None
        target_key = getattr(owner, "key", None) or getattr(corpse, "key", "someone")
        effect_payload = {
            "effect_family": "resurrection",
            "target_id": getattr(owner, "id", None),
            "target_key": target_key,
            "corpse_key": getattr(corpse, "key", "corpse"),
            "self_target": False,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_augmentation_spell(caster, spell, final_spell_power, quality="normal", target=None):
        target_type = str(getattr(spell, "target_type", "self") or "self").strip().lower()
        effect_profile = dict(getattr(spell, "effect_profile", {}) or {})
        if target_type == "self" and target is not None and target is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )
        recipient = target or caster
        if bool(effect_profile.get("disallow_self_target", False)) and recipient is caster:
            return ActionResult.fail(
                errors=["You need a valid target for that spell."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "other_target_only"},
            )
        strength = 1 + int(float(final_spell_power or 0.0) / 10.0)
        duration = 10 + int(float(final_spell_power or 0.0) / 2.0)
        modifiers = {
            str(key): float(value or 0.0)
            for key, value in effect_profile.get("contest_modifiers", {}).items()
        }
        if str(quality or "normal").strip().lower() == "weak":
            strength = max(1, strength - 1)
        elif str(quality or "normal").strip().lower() == "strong":
            strength += 1

        augmentation_result = StateService.apply_augmentation_effect(
            recipient,
            spell.id,
            strength,
            duration,
            modifiers=dict(modifiers),
        )
        applied = dict((augmentation_result.data or {}).get("effect", {}) or {})

        effect_payload = {
            "effect_family": "augmentation",
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "buff_name": spell.id,
            "strength": int(applied.get("strength", strength) or strength),
            "duration": int(applied.get("duration", duration) or duration),
            "self_target": recipient is caster,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_warding_spell(caster, spell, final_spell_power, quality="normal", target=None):
        strength = 1 + int(float(final_spell_power or 0.0) / 10.0)
        duration = 10 + int(float(final_spell_power or 0.0) / 2.0)
        if str(quality or "normal").strip().lower() == "weak":
            strength = max(1, strength - 1)
        elif str(quality or "normal").strip().lower() == "strong":
            strength += 1

        effect_profile = dict(getattr(spell, "effect_profile", {}) or {})
        strength = max(1, int(round(strength * float(effect_profile.get("strength_multiplier", 1.0) or 1.0))))
        modifiers = {
            str(key): float(value or 0.0)
            for key, value in dict(effect_profile.get("contest_modifiers", {}) or {}).items()
        }
        if spell.id == "manifest_force":
            mana_min = int(getattr(spell, "mana_min", 1) or 1)
            mana_max = max(mana_min, int(getattr(spell, "mana_max", mana_min) or mana_min))
            intended_mana = min(mana_max, max(mana_min, int(round(float(final_spell_power or 0.0)))))
            strength = int(effect_profile.get("min_capacity", 30) or 30)
            strength += int(max(0, intended_mana - mana_min) * float(effect_profile.get("capacity_per_mana", 0.5) or 0.5))
            min_duration = int(effect_profile.get("base_duration", 600) or 600)
            max_duration = int(effect_profile.get("max_duration", 2400) or 2400)
            mana_span = max(1, mana_max - mana_min)
            duration = min_duration + int((max(0, intended_mana - mana_min) / float(mana_span)) * max(0, max_duration - min_duration))

        target_type = str(getattr(spell, "target_type", "self") or "self").strip().lower()
        if target_type == "group" or bool(effect_profile.get("group_from_caster", False)):
            recipients = SpellEffectService.get_valid_group_targets(getattr(caster, "location", None), caster)
            if not recipients:
                return ActionResult.fail(errors=["There is no one here to protect."], data={"reason": "no_group_targets"})
            payload_targets = []
            for recipient in recipients:
                extra_data = {}
                if effect_profile.get("undead_evasion_bonus_scale"):
                    extra_data["undead_evasion_bonus"] = int(round(float(effect_profile.get("undead_evasion_bonus_scale", 0.0) or 0.0) * strength))
                barrier_result = StateService.apply_warding_effect(
                    recipient,
                    spell.id,
                    strength,
                    duration,
                    absorbs_physical=bool(effect_profile.get("absorbs_physical", False)),
                    extra_data=extra_data,
                )
                if modifiers:
                    StateService.apply_augmentation_effect(recipient, spell.id, strength, duration, modifiers=dict(modifiers))
                barrier = dict((barrier_result.data or {}).get("effect", {}) or {})
                payload_targets.append(
                    {
                        "target_id": getattr(recipient, "id", None),
                        "target_key": getattr(recipient, "key", "someone"),
                        "barrier_strength": int(barrier.get("strength", strength) or strength),
                        "duration": int(barrier.get("duration", duration) or duration),
                    }
                )
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": {
                        "effect_family": "warding",
                        "target_count": len(payload_targets),
                        "targets": payload_targets,
                        "group_target": True,
                        "target_key": getattr(caster, "key", "group"),
                        "source_spell": spell.id,
                        "source_mana_type": str(spell.mana_type or "").strip().lower(),
                    },
                }
            )

        recipient = target or caster
        if spell.id == "manifest_force":
            StateService.remove_effect(recipient, "warding", spell.id)

        extra_data = {}
        if effect_profile.get("undead_evasion_bonus_scale"):
            extra_data["undead_evasion_bonus"] = int(round(float(effect_profile.get("undead_evasion_bonus_scale", 0.0) or 0.0) * strength))
        if effect_profile.get("emits_light"):
            extra_data["emits_light"] = True

        barrier_result = StateService.apply_warding_effect(
            recipient,
            spell.id,
            strength,
            duration,
            absorbs_physical=bool(effect_profile.get("absorbs_physical", False)),
            extra_data=extra_data,
        )
        if modifiers:
            StateService.apply_augmentation_effect(recipient, spell.id, strength, duration, modifiers=dict(modifiers))
        barrier = dict((barrier_result.data or {}).get("effect", {}) or {})

        effect_payload = {
            "effect_family": "warding",
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "barrier_strength": int(barrier.get("strength", strength) or strength),
            "duration": int(barrier.get("duration", duration) or duration),
            "source_spell": str(barrier.get("name", spell.id) or spell.id),
            "self_target": recipient is caster,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "absorbs_physical": bool(barrier.get("absorbs_physical", False)),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_utility_spell(caster, spell, final_spell_power, quality="normal", target=None):
        _quality = quality
        target_type = str(getattr(spell, "target_type", "self") or "self").strip().lower()
        recipient = target or caster
        effect_profile = dict(getattr(spell, "effect_profile", {}) or {})
        if target_type == "self" and recipient is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )
        if bool(effect_profile.get("disallow_self_target", False)) and recipient is caster:
            return ActionResult.fail(
                errors=["You need a valid target for that spell."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "other_target_only"},
            )
        effect_type = str(effect_profile.get("effect_type", spell.id) or spell.id).strip().lower()
        utility_behavior = str(effect_profile.get("utility_behavior", effect_type) or effect_type).strip().lower()

        if utility_behavior in {"flush_poisons", "cure_disease"}:
            return SpellEffectService._apply_empath_condition_cleanse(caster, recipient, spell, utility_behavior)

        if utility_behavior == "refresh":
            return SpellEffectService._apply_refresh(caster, recipient, spell, final_spell_power)

        if utility_behavior == "raise_power":
            return SpellEffectService._apply_raise_power(caster, recipient, spell, final_spell_power)

        if utility_behavior == "gift_of_life":
            return SpellEffectService._apply_gift_of_life(caster, recipient, spell, final_spell_power)

        if utility_behavior == "innocence":
            return SpellEffectService._apply_innocence(caster, recipient, spell, final_spell_power)

        if utility_behavior == "spirit_beacon":
            favor_getter = getattr(recipient, "get_favor", None)
            available_favor = int(favor_getter() or 0) if callable(favor_getter) else 0
            if available_favor > 0:
                return ActionResult.fail(
                    errors=["Your favor still carries you. Spirit Beacon will not anchor while departure remains open to you."],
                    data={
                        "spell_id": spell.id,
                        "spell_type": str(spell.spell_type or "").strip().lower(),
                        "reason": "favor_available",
                    },
                )
            source_room = getattr(recipient, "location", None)
            recovery_getter = getattr(recipient, "get_nearest_recovery_point", None)
            recovery_point = recovery_getter(room=source_room) if callable(recovery_getter) else None
            if recovery_point is None:
                recovery_point = getattr(recipient, "home", None) or source_room
            duration = int(effect_profile.get("base_duration", 3600) or 3600) + int(
                round(float(final_spell_power or 0.0) * float(effect_profile.get("duration_scale", 0.0) or 0.0))
            )
            utility_result = StateService.apply_utility_effect(
                recipient,
                "spirit_beacon",
                duration,
                source_spell=spell.id,
                extra_data={
                    "capability_flag": str(effect_profile.get("capability_flag", "spirit_beacon_active") or "spirit_beacon_active"),
                    "beacon_room_id": getattr(source_room, "id", None),
                    "beacon_room_key": getattr(source_room, "key", None),
                    "recovery_point_id": getattr(recovery_point, "id", None),
                    "recovery_point_key": getattr(recovery_point, "key", None),
                    "favor_at_cast": available_favor,
                },
            )
            effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
            recipient.db.spirit_beacon = {
                "room_id": effect_data.get("beacon_room_id"),
                "room_key": effect_data.get("beacon_room_key"),
                "recovery_point_id": effect_data.get("recovery_point_id"),
                "recovery_point_key": effect_data.get("recovery_point_key"),
                "favor_at_cast": available_favor,
            }
            effect_payload = {
                "effect_family": "utility",
                "utility_effect": "spirit_beacon",
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", "someone"),
                "duration": int(effect_data.get("duration", duration) or duration),
                "beacon_room_key": str(effect_data.get("beacon_room_key", getattr(source_room, "key", "here")) or "here"),
                "recovery_point_key": str(effect_data.get("recovery_point_key", getattr(recovery_point, "key", "your refuge")) or "your refuge"),
                "self_target": recipient is caster,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
            }
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": effect_payload,
                }
            )

        if utility_behavior == "uncurse":
            uncurse_power = int(effect_profile.get("base_curse_power", 10) or 10) + int(
                round(float(final_spell_power or 0.0) * float(effect_profile.get("curse_power_scale", 0.0) or 0.0))
            )
            uncurse_result = StateService.apply_uncurse(recipient, power=uncurse_power)
            uncurse_data = dict(uncurse_result.data or {})
            effect_payload = {
                "effect_family": "utility",
                "utility_effect": "uncurse",
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", "someone"),
                "removed": bool(uncurse_data.get("removed", False)),
                "death_sting_relieved": bool(uncurse_data.get("death_sting_relieved", False)),
                "self_target": recipient is caster,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
            }
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": effect_payload,
                }
            )

        if effect_type == "cleanse":
            cleanse_result = StateService.apply_cleanse(recipient)
            removed = bool((cleanse_result.data or {}).get("removed", False))
            effect_payload = {
                "effect_family": "utility",
                "utility_effect": "cleanse",
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", "someone"),
                "removed": removed,
                "self_target": recipient is caster,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
            }
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": effect_payload,
                }
            )

        if effect_type == "bless":
            strength = 1 + int(float(final_spell_power or 0.0) / 10.0)
            duration = int(effect_profile.get("base_duration", 600) or 600) + int(
                round(float(final_spell_power or 0.0) * float(effect_profile.get("duration_scale", 0.0) or 0.0))
            )
            if str(quality or "normal").strip().lower() == "weak":
                strength = max(1, strength - 1)
            elif str(quality or "normal").strip().lower() == "strong":
                strength += 1
            utility_result = StateService.apply_utility_effect(
                recipient,
                "bless",
                duration,
                source_spell=spell.id,
                extra_data={
                    "capability_flag": str(effect_profile.get("capability_flag", "bless_active") or "bless_active"),
                    "strength": strength,
                    "undead_accuracy_bonus": int(round(float(effect_profile.get("undead_accuracy_bonus_scale", 0.0) or 0.0) * strength)),
                    "undead_damage_bonus": int(round(float(effect_profile.get("undead_damage_bonus_scale", 0.0) or 0.0) * strength)),
                    "incorporeal_contact": True,
                },
            )
            effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
            effect_payload = {
                "effect_family": "utility",
                "utility_effect": "bless",
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", "someone"),
                "duration": int(effect_data.get("duration", duration) or duration),
                "strength": int(effect_data.get("strength", strength) or strength),
                "self_target": recipient is caster,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
            }
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": effect_payload,
                }
            )

        if effect_type == "light":
            duration = int(effect_profile.get("base_duration", 20) or 20) + int(
                round(float(final_spell_power or 0.0) * float(effect_profile.get("duration_scale", 1.0) or 1.0))
            )
            utility_result = StateService.apply_utility_effect(recipient, "light", duration, source_spell=spell.id)
            effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
            effect_payload = {
                "effect_family": "utility",
                "utility_effect": "light",
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", "someone"),
                "duration": int(effect_data.get("duration", duration) or duration),
                "self_target": recipient is caster,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
            }
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": effect_payload,
                }
            )

        if utility_behavior == "gauge_flow":
            duration = int(effect_profile.get("base_duration", 1800) or 1800) + int(
                round(float(final_spell_power or 0.0) * float(effect_profile.get("duration_scale", 0.0) or 0.0))
            )
            utility_result = StateService.apply_utility_effect(
                recipient,
                "gauge_flow",
                duration,
                source_spell=spell.id,
                extra_data={
                    "capability_flag": str(effect_profile.get("capability_flag", "gauge_flow_active") or "gauge_flow_active"),
                    "potency_scaling": str(effect_profile.get("potency_scaling", "research_time_reduction") or "research_time_reduction"),
                },
            )
            effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
            effect_payload = {
                "effect_family": "utility",
                "utility_effect": "gauge_flow",
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", "someone"),
                "duration": int(effect_data.get("duration", duration) or duration),
                "capability_flag": str(effect_data.get("capability_flag", "gauge_flow_active") or "gauge_flow_active"),
                "self_target": recipient is caster,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
            }
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": effect_payload,
                }
            )

        if utility_behavior == "water_purification":
            return SpellEffectService._apply_water_purification(caster, recipient, spell, final_spell_power)

        if utility_behavior == "ranger_room_effect":
            return SpellEffectService._apply_ranger_room_effect(caster, recipient, spell, final_spell_power)

        if utility_behavior == "ranger_boon":
            return SpellEffectService._apply_ranger_boon(caster, recipient, spell, final_spell_power, quality=quality)

        if utility_behavior == "revelation":
            if target is None or target == caster:
                return ActionResult.fail(
                    errors=["You need a valid target for Revelation."],
                    data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "invalid_target"},
                )
            revealer = getattr(target, "reveal", None)
            hidden_getter = getattr(target, "is_hidden", None)
            was_hidden = bool(hidden_getter()) if callable(hidden_getter) else bool(getattr(getattr(target, "db", None), "stealthed", False))
            if callable(revealer):
                revealer()
            else:
                if hasattr(getattr(target, "db", None), "stealthed"):
                    target.db.stealthed = False
                clearer = getattr(target, "clear_state", None)
                if callable(clearer):
                    clearer("hidden")
            effect_payload = {
                "effect_family": "utility",
                "utility_effect": "revelation",
                "target_id": getattr(target, "id", None),
                "target_key": getattr(target, "key", "someone"),
                "revealed": bool(was_hidden),
                "self_target": False,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
            }
            return ActionResult.ok(
                data={
                    "spell_id": spell.id,
                    "spell_name": spell.name,
                    "spell_type": str(spell.spell_type or "").strip().lower(),
                    "effect_payload": effect_payload,
                }
            )

        return ActionResult.fail(
            errors=[f"No structured utility behavior exists for {spell.id}."],
            data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "unknown_utility_effect"},
        )

    @staticmethod
    def _apply_empath_condition_cleanse(caster, recipient, spell, utility_behavior):
        if recipient is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )

        condition_key = "poison" if utility_behavior == "flush_poisons" else "disease"
        get_wound = getattr(caster, "get_empath_wound", None)
        set_wound = getattr(caster, "set_empath_wound", None)

        def read_wound():
            if callable(get_wound):
                return max(0, int(get_wound(condition_key) or 0))
            wounds = dict(getattr(getattr(caster, "db", None), "wounds", {}) or {})
            return max(0, int(wounds.get(condition_key, 0) or 0))

        def write_wound(value):
            if callable(set_wound):
                set_wound(condition_key, value)
                return
            wounds = dict(getattr(getattr(caster, "db", None), "wounds", {}) or {})
            wounds[condition_key] = max(0, int(value or 0))
            caster.db.wounds = wounds
            sync_client_state = getattr(caster, "sync_client_state", None)
            if callable(sync_client_state):
                sync_client_state()

        before = read_wound()
        if before > 0:
            write_wound(0)
        removed_amount = before - read_wound()
        effect_payload = {
            "effect_family": "utility",
            "utility_effect": utility_behavior,
            "target_id": getattr(caster, "id", None),
            "target_key": getattr(caster, "key", "someone"),
            "removed": bool(removed_amount > 0),
            "removed_amount": removed_amount,
            "condition_key": condition_key,
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _read_fatigue(target):
        get_fatigue = getattr(target, "get_fatigue", None)
        if callable(get_fatigue):
            current, maximum = get_fatigue()
            return max(0, int(current or 0)), max(1, int(maximum or 100))
        db_holder = getattr(target, "db", None)
        current = getattr(db_holder, "fatigue", 0)
        maximum = getattr(db_holder, "max_fatigue", 100)
        return max(0, int(current or 0)), max(1, int(maximum or 100))

    @staticmethod
    def _write_fatigue(target, value):
        set_fatigue = getattr(target, "set_fatigue", None)
        if callable(set_fatigue):
            set_fatigue(value)
            return SpellEffectService._read_fatigue(target)
        db_holder = getattr(target, "db", None)
        maximum = max(1, int(getattr(db_holder, "max_fatigue", 100) or 100))
        current = max(0, min(int(value or 0), maximum))
        setattr(db_holder, "fatigue", current)
        sync_client_state = getattr(target, "sync_client_state", None)
        if callable(sync_client_state):
            sync_client_state()
        return current, maximum

    @staticmethod
    def _apply_refresh(caster, recipient, spell, final_spell_power):
        before, maximum = SpellEffectService._read_fatigue(recipient)
        reduction = max(8, int(round(float(final_spell_power or 0.0))))
        if recipient is not caster:
            profile = dict(getattr(spell, "effect_profile", {}) or {})
            reduction = max(1, int(round(reduction * float(profile.get("other_target_scale", 0.75) or 0.75))))
        after, _ignored_maximum = SpellEffectService._write_fatigue(recipient, before - reduction)
        reduced = max(0, before - after)
        effect_payload = {
            "effect_family": "utility",
            "utility_effect": "refresh",
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "removed": bool(reduced > 0),
            "fatigue_reduced": reduced,
            "fatigue_before": before,
            "fatigue_after": after,
            "max_fatigue": maximum,
            "self_target": recipient is caster,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_raise_power(caster, recipient, spell, final_spell_power):
        if recipient is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )
        room = getattr(caster, "location", None)
        if room is None:
            return ActionResult.fail(
                errors=["You must be standing in a location to raise its Life mana."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "missing_room"},
            )
        db_holder = getattr(room, "db", None)
        mana_map = ManaService._normalize_room_mana_map(getattr(db_holder, "mana", None))
        group_members = [obj for obj in list(getattr(room, "contents", []) or []) if obj is caster or getattr(obj, "account", None)]
        group_count = max(1, len(group_members))
        profile = dict(getattr(spell, "effect_profile", {}) or {})
        mana_boost = float(profile.get("room_mana_boost_scale", 0.03) or 0.03) * float(final_spell_power or 0.0)
        mana_boost += max(0, group_count - 1) * float(profile.get("group_member_bonus", 0.05) or 0.05)
        mana_boost = max(0.15, round(mana_boost, 2))
        before_mana = float(mana_map.get("life", 1.0) or 1.0)
        mana_map["life"] = before_mana + mana_boost
        setattr(db_holder, "mana", mana_map)

        drained_targets = []
        for member in group_members:
            current, maximum = SpellEffectService._read_fatigue(member)
            after, _ignored_member_maximum = SpellEffectService._write_fatigue(member, maximum)
            drained_targets.append(
                {
                    "target_id": getattr(member, "id", None),
                    "target_key": getattr(member, "key", "someone"),
                    "fatigue_before": current,
                    "fatigue_after": after,
                }
            )

        effect_payload = {
            "effect_family": "utility",
            "utility_effect": "raise_power",
            "target_id": getattr(caster, "id", None),
            "target_key": getattr(caster, "key", "someone"),
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "room_key": getattr(room, "key", "here"),
            "life_mana_before": before_mana,
            "life_mana_after": float(mana_map.get("life", before_mana) or before_mana),
            "life_mana_boost": mana_boost,
            "group_count": group_count,
            "fatigue_drained": drained_targets,
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_gift_of_life(caster, recipient, spell, final_spell_power):
        if recipient is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )
        saf_error = EmpathSafService.get_gift_of_life_block_result(caster)
        if saf_error is not None:
            return saf_error
        profile = dict(getattr(spell, "effect_profile", {}) or {})
        duration = int(profile.get("base_duration", 900) or 900) + int(round(float(final_spell_power or 0.0) * float(profile.get("duration_scale", 0.0) or 0.0)))
        stamina_bonus = int(profile.get("stamina_bonus", 8) or 8)
        link_bonus = int(profile.get("link_bonus", 2) or 2)
        utility_result = StateService.apply_utility_effect(
            recipient,
            "gift_of_life",
            duration,
            source_spell=spell.id,
            extra_data={
                "capability_flag": str(profile.get("capability_flag", "gift_of_life_active") or "gift_of_life_active"),
                "stamina_bonus": stamina_bonus,
                "link_bonus": link_bonus,
            },
        )
        effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
        effect_payload = {
            "effect_family": "utility",
            "utility_effect": "gift_of_life",
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "duration": int(effect_data.get("duration", duration) or duration),
            "stamina_bonus": int(effect_data.get("stamina_bonus", stamina_bonus) or stamina_bonus),
            "link_bonus": int(effect_data.get("link_bonus", link_bonus) or link_bonus),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _is_undead_target(target):
        trait_values = [
            str(getattr(getattr(target, "db", None), key, "") or "").strip().lower()
            for key in ("creature_type", "npc_type", "species", "race")
        ]
        searchable = " ".join(
            [
                str(getattr(target, "key", "") or "").lower(),
                str(getattr(getattr(target, "db", None), "desc", "") or "").lower(),
                *trait_values,
            ]
        )
        return any(keyword in searchable for keyword in ("undead", "zombie", "skeleton", "ghost", "wraith"))

    @staticmethod
    def _apply_innocence(caster, recipient, spell, final_spell_power):
        if recipient is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )

        get_shock = getattr(caster, "get_empath_shock", None)
        shock_value = int(get_shock() or 0) if callable(get_shock) else int(getattr(getattr(caster, "db", None), "empath_shock", 0) or 0)
        if shock_value >= 80:
            return ActionResult.fail(
                errors=["You feel completely cut off from others."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "empath_shock_blocked"},
            )

        profile = dict(getattr(spell, "effect_profile", {}) or {})
        duration = int(profile.get("base_duration", 20) or 20) + int(round(float(final_spell_power or 0.0) * float(profile.get("duration_scale", 0.0) or 0.0)))
        released_targets = []
        enraged_targets = []
        room = getattr(caster, "location", None)

        if room is not None and hasattr(room, "contents"):
            for occupant in list(getattr(room, "contents", []) or []):
                if occupant is None or occupant is caster:
                    continue
                if getattr(occupant, "account", None) is not None or bool(getattr(occupant, "has_account", False)):
                    continue
                if not hasattr(occupant, "set_target"):
                    continue
                if hasattr(occupant, "is_dead") and occupant.is_dead():
                    continue

                if SpellEffectService._is_undead_target(occupant):
                    if hasattr(occupant, "add_threat"):
                        occupant.add_threat(caster, int(profile.get("undead_backfire_threat", 25) or 25))
                    occupant.set_target(caster)
                    if getattr(getattr(occupant, "db", None), "in_combat", None) is not None:
                        occupant.db.in_combat = True
                    enraged_targets.append(getattr(occupant, "key", "undead"))
                    continue

                current_target = occupant.get_target() if hasattr(occupant, "get_target") else None
                threat_on_caster = occupant.get_threat(caster) if hasattr(occupant, "get_threat") else 0
                if current_target is not caster and int(threat_on_caster or 0) <= 0:
                    continue

                if hasattr(occupant, "remove_target"):
                    occupant.remove_target(caster)
                if hasattr(occupant, "set_state"):
                    occupant.set_state(
                        "empath_manipulated",
                        {
                            "source_id": getattr(caster, "id", None),
                            "expires_at": time.time() + max(1, int(duration)),
                            "category": "innocence",
                        },
                    )

                replacement = occupant.get_highest_threat() if hasattr(occupant, "get_highest_threat") else None
                if replacement is not None and replacement is not caster:
                    occupant.set_target(replacement)
                elif hasattr(occupant, "disengage"):
                    occupant.disengage(emit_message=False)
                else:
                    occupant.set_target(None)
                    if getattr(getattr(occupant, "db", None), "in_combat", None) is not None:
                        occupant.db.in_combat = False
                released_targets.append(getattr(occupant, "key", "creature"))

        utility_result = StateService.apply_utility_effect(
            recipient,
            "innocence",
            max(1, int(duration)),
            source_spell=spell.id,
            extra_data={
                "capability_flag": str(profile.get("capability_flag", "innocence_active") or "innocence_active"),
                "released_targets": list(released_targets),
                "released_count": len(released_targets),
                "undead_backfires": list(enraged_targets),
                "undead_backfire_count": len(enraged_targets),
            },
        )
        effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
        effect_payload = {
            "effect_family": "utility",
            "utility_effect": "innocence",
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
            "duration": int(effect_data.get("duration", duration) or duration),
            "released_targets": list(effect_data.get("released_targets", released_targets) or []),
            "released_count": int(effect_data.get("released_count", len(released_targets)) or 0),
            "undead_backfires": list(effect_data.get("undead_backfires", enraged_targets) or []),
            "undead_backfire_count": int(effect_data.get("undead_backfire_count", len(enraged_targets)) or 0),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_ranger_boon(caster, recipient, spell, final_spell_power, quality="normal"):
        profile = dict(getattr(spell, "effect_profile", {}) or {})
        effect_type = str(profile.get("effect_type", spell.id) or spell.id).strip().lower()
        strength = 1 + int(float(final_spell_power or 0.0) / 10.0)
        duration = 10 + int(float(final_spell_power or 0.0) / 2.0)
        quality_key = str(quality or "normal").strip().lower()
        if quality_key == "weak":
            strength = max(1, strength - 1)
        elif quality_key == "strong":
            strength += 1
        utility_result = StateService.apply_utility_effect(
            recipient,
            effect_type,
            duration,
            source_spell=spell.id,
            extra_data={
                "capability_flag": str(profile.get("capability_flag", f"{effect_type}_active") or f"{effect_type}_active"),
                "strength": strength,
                "gsl_spell_id": profile.get("gsl_spell_id"),
                "castmod_a0": profile.get("castmod_a0"),
                "castmod_a1": profile.get("castmod_a1"),
                "castmod_a3": profile.get("castmod_a3"),
            },
        )
        effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
        effect_payload = {
            "effect_family": "utility",
            "utility_effect": effect_type,
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "duration": int(effect_data.get("duration", duration) or duration),
            "strength": int(effect_data.get("strength", strength) or strength),
            "capability_flag": str(effect_data.get("capability_flag", "") or ""),
            "self_target": recipient is caster,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_water_purification(caster, recipient, spell, final_spell_power):
        if recipient is not caster:
            return ActionResult.fail(
                errors=["You can only cast that spell on yourself."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "self_target_only"},
            )
        room = getattr(caster, "location", None)
        if room is None:
            return ActionResult.fail(
                errors=["You must be standing in a location to purify its water."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "missing_room"},
            )

        profile = dict(getattr(spell, "effect_profile", {}) or {})
        duration = int(profile.get("base_duration", 120) or 120) + int(
            round(float(final_spell_power or 0.0) * float(profile.get("duration_scale", 0.0) or 0.0))
        )
        utility_result = StateService.apply_utility_effect(
            recipient,
            "water_purification",
            max(1, duration),
            source_spell=spell.id,
            extra_data={
                "capability_flag": str(profile.get("capability_flag", "water_purification_active") or "water_purification_active"),
                "room_key": getattr(room, "key", "here"),
            },
        )
        effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
        room_db = getattr(room, "db", None)
        if room_db is not None:
            room_db.water_purification = {
                "spell_id": spell.id,
                "duration": int(effect_data.get("duration", duration) or duration),
                "source_id": getattr(caster, "id", None),
                "source_key": getattr(caster, "key", "someone"),
            }

        effect_payload = {
            "effect_family": "utility",
            "utility_effect": "water_purification",
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", "someone"),
            "room_key": getattr(room, "key", "here"),
            "duration": int(effect_data.get("duration", duration) or duration),
            "self_target": True,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_ranger_room_effect(caster, recipient, spell, final_spell_power):
        room = getattr(recipient, "location", None)
        if room is None:
            room = getattr(caster, "location", None)
        if room is None:
            return ActionResult.fail(
                errors=["You must be standing in a location to cast that spell."],
                data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "missing_room"},
            )

        profile = dict(getattr(spell, "effect_profile", {}) or {})
        effect_type = str(profile.get("effect_type", spell.id) or spell.id).strip().lower()
        duration = int(profile.get("base_duration", 60) or 60) + int(
            round(float(final_spell_power or 0.0) * float(profile.get("duration_scale", 0.0) or 0.0))
        )
        utility_result = StateService.apply_utility_effect(
            caster,
            effect_type,
            max(1, duration),
            source_spell=spell.id,
            extra_data={
                "capability_flag": str(profile.get("capability_flag", f"{effect_type}_active") or f"{effect_type}_active"),
                "room_key": getattr(room, "key", "here"),
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", getattr(caster, "key", "someone")),
                "gsl_spell_id": profile.get("gsl_spell_id"),
                "castmod_a0": profile.get("castmod_a0"),
                "castmod_a1": profile.get("castmod_a1"),
                "castmod_a3": profile.get("castmod_a3"),
            },
        )
        effect_data = dict((utility_result.data or {}).get("effect", {}) or {})
        room_state_key = str(profile.get("room_state_key", effect_type) or effect_type)
        room_db = getattr(room, "db", None)
        if room_db is not None:
            setattr(
                room_db,
                room_state_key,
                {
                    "spell_id": spell.id,
                    "effect_type": effect_type,
                    "duration": int(effect_data.get("duration", duration) or duration),
                    "source_id": getattr(caster, "id", None),
                    "source_key": getattr(caster, "key", "someone"),
                    "target_id": getattr(recipient, "id", None),
                    "target_key": getattr(recipient, "key", getattr(caster, "key", "someone")),
                },
            )

        effect_payload = {
            "effect_family": "utility",
            "utility_effect": effect_type,
            "target_id": getattr(recipient, "id", None),
            "target_key": getattr(recipient, "key", getattr(caster, "key", "someone")),
            "room_key": getattr(room, "key", "here"),
            "duration": int(effect_data.get("duration", duration) or duration),
            "self_target": recipient is caster,
            "source_mana_type": str(spell.mana_type or "").strip().lower(),
        }
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_targeted_magic_spell(caster, spell, final_spell_power, quality="normal", target=None):
        contest_result = SpellContestService.resolve_targeted_magic(
            caster,
            target,
            final_spell_power,
            spell_id=getattr(spell, "id", None),
            quality=quality,
            wild_modifier=1.0,
            effect_profile=dict(getattr(spell, "effect_profile", {}) or {}),
        )
        if not contest_result.success:
            return contest_result

        effect_payload = dict(contest_result.data or {})
        effect_payload.setdefault("source_mana_type", str(spell.mana_type or "").strip().lower())
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _apply_cyclic_spell(caster, spell, final_spell_power, quality="normal", target=None):
        profile = dict(getattr(spell, "effect_profile", {}) or {})
        target_mode = str(profile.get("target_mode", "self") or "self")
        recipient = caster if target_mode != "single" else target
        room_ref = getattr(caster, "location", None)

        active_cyclic = StateService.get_active_cyclic_effects(caster)
        if active_cyclic:
            active_id, active_payload = next(iter(active_cyclic.items()))
            active_name = str(dict(active_payload or {}).get("spell_name") or dict(active_payload or {}).get("name") or active_id)
            return ActionResult.fail(
                errors=[f"You already sustain a cyclic spell: {active_name}. Release it first with RELEASE CYCLIC before casting another."],
                data={"reason": "single_cyclic_enforced", "active_spell_id": active_id, "active_spell_name": active_name, "effect_family": "cyclic"},
            )

        sustain_source, sustain_ref, sustain_error = SpellEffectService._select_cyclic_sustain_source(caster, spell)
        if sustain_source is None:
            return ActionResult.fail(errors=[sustain_error], data={"reason": "invalid_sustain_source", "effect_family": "cyclic"})

        contest_payload = None
        if bool(profile.get("contest_required", False)):
            contest_result = SpellContestService.resolve_cyclic_application(
                caster,
                recipient,
                final_spell_power,
                effect_profile=profile,
                spell_id=getattr(spell, "id", None),
                quality=quality,
                wild_modifier=1.0,
            )
            if not contest_result.success:
                return contest_result
            contest_payload = dict(contest_result.data or {})
            if not bool(contest_payload.get("hit", False)):
                contest_payload.setdefault("cyclic_state", {"started": False, "collapsed": False})
                contest_payload.setdefault("source_mana_type", str(spell.mana_type or "").strip().lower())
                return ActionResult.ok(
                    data={
                        "spell_id": spell.id,
                        "spell_name": spell.name,
                        "spell_type": str(spell.spell_type or "").strip().lower(),
                        "effect_payload": contest_payload,
                    }
                )

        mana_per_tick = ManaService.calculate_cyclic_tick_cost(getattr(spell, "safe_mana", 1), final_spell_power, profile)
        start_result = StateService.apply_cyclic_effect(
            caster,
            spell.id,
            {
                "spell_id": spell.id,
                "spell_name": spell.name,
                "power": float(final_spell_power or 0.0),
                "mana_per_tick": int(mana_per_tick),
                "active": True,
                "duration": None,
                "tick_count": 0,
                "tick_effect": str(profile.get("tick_effect", "healing") or "healing"),
                "tick_scale": float(profile.get("tick_scale", 0.1) or 0.1),
                "mana_type": str(spell.mana_type or "").strip().lower(),
                "target_mode": target_mode,
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", getattr(caster, "key", "someone")),
                "target_ref": recipient,
                "room_ref": room_ref,
                "room_key": getattr(room_ref, "key", None),
                "max_targets": int(profile.get("max_targets", 0) or 0),
                "interrupt_on_debilitation": bool(profile.get("interrupt_on_debilitation", False)),
                "sustain_source": sustain_source,
                "sustain_ref": sustain_ref,
            },
        )
        if not start_result.success:
            return ActionResult.fail(
                errors=list(start_result.errors or []),
                data=dict(start_result.data or {}) | {"reason": str((start_result.data or {}).get("reason") or "already_active"), "effect_family": "cyclic"},
            )

        effect_payload = dict(contest_payload or {})
        effect_payload.update(
            {
                "effect_family": "cyclic",
                "target_id": getattr(recipient, "id", None),
                "target_key": getattr(recipient, "key", getattr(caster, "key", "someone")),
                "self_target": recipient is caster,
                "source_mana_type": str(spell.mana_type or "").strip().lower(),
                "target_mode": target_mode,
                "cyclic_state": {
                    "started": True,
                    "mana_per_tick": int(mana_per_tick),
                    "power": float(final_spell_power or 0.0),
                    "active": True,
                    "sustain_source": sustain_source,
                    "sustain_ref": sustain_ref,
                },
            }
        )
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _select_cyclic_sustain_source(caster, spell):
        from engine.services.feat_service import FeatService
        from engine.services.mana_service import ManaService

        required_initial = max(1, int(getattr(spell, "mana_min", 1) or 1))
        held_mana = ManaService._get_harnessed_mana_state(caster)
        if held_mana >= required_initial:
            return "held_mana", None, None

        has_raw_channeling = FeatService.has_feat(caster, "raw_channeling") or FeatService.get_unlock(caster, "cyclic_attunement_sustain")
        if has_raw_channeling:
            attunement = ManaService._get_attunement_state(caster)
            if ManaService._coerce_float(attunement.get("current"), default=0.0) >= float(required_initial):
                return "attunement", None, None
            return None, None, f"Your attunement is too low to sustain {spell.name}. Recover first or harness mana."

        return None, None, f"You have insufficient held mana to sustain {spell.name}. Use HARNESS to gather mana into a held pool first."

    @staticmethod
    def _apply_debilitation_spell(caster, spell, final_spell_power, quality="normal", target=None):
        contest_result = SpellContestService.resolve_debilitation(
            caster,
            target,
            final_spell_power,
            effect_profile=dict(getattr(spell, "effect_profile", {}) or {}),
            spell_id=getattr(spell, "id", None),
            quality=quality,
            wild_modifier=1.0,
        )
        if not contest_result.success:
            return contest_result

        effect_payload = dict(contest_result.data or {})
        if (
            str(effect_payload.get("effect_type", "") or "").strip().lower() == "mesmerize"
            and bool(effect_payload.get("hit", False))
            and not bool(effect_payload.get("ignored", False))
            and target is not None
        ):
            if hasattr(target, "disengage"):
                target.disengage(emit_message=False)
            elif hasattr(target, "set_target"):
                target.set_target(None)
                if getattr(getattr(target, "db", None), "in_combat", None) is not None:
                    target.db.in_combat = False
            if hasattr(getattr(target, "ndb", None), "threat_table"):
                target.ndb.threat_table = {}
            if hasattr(target, "set_state"):
                target.set_state(
                    "mesmerized",
                    {
                        "duration": int(effect_payload.get("duration", 0) or 0),
                        "strength": int(effect_payload.get("strength", 0) or 0),
                        "source_spell": spell.id,
                        "applied_by": getattr(caster, "id", None),
                    },
                )
            effect_payload["pacified"] = True
        if bool(effect_payload.get("hit", False)) and not bool(effect_payload.get("ignored", False)) and target is not None:
            effect_type = str(effect_payload.get("effect_type", "") or "").strip().lower()
            if effect_type == "haraweps_bonds" and hasattr(target, "set_state"):
                target.set_state(
                    "haraweps_bonds",
                    {
                        "duration": int(effect_payload.get("duration", 0) or 0),
                        "strength": int(effect_payload.get("strength", 0) or 0),
                        "source_spell": spell.id,
                    },
                )
                effect_payload["restrained"] = True
            elif effect_type == "hobble" and hasattr(target, "set_state"):
                target.set_state(
                    "hobble",
                    {
                        "duration": int(effect_payload.get("duration", 0) or 0),
                        "strength": int(effect_payload.get("strength", 0) or 0),
                        "source_spell": spell.id,
                    },
                )
                effect_payload["movement_reduced"] = True
            elif effect_type == "branch_break":
                profile = dict(getattr(spell, "effect_profile", {}) or {})
                damage_amount = int(profile.get("damage_base", 1) or 1) + int(
                    round(float(effect_payload.get("strength", 0) or 0) * float(profile.get("damage_scale", 0) or 0))
                )
                damage_result = StateService.apply_damage(target, max(1, damage_amount), location="chest", damage_type="impact", attacker=caster)
                effect_payload["final_damage"] = int((damage_result.data or {}).get("amount", 0) or 0)
        effect_payload.setdefault("source_mana_type", str(spell.mana_type or "").strip().lower())
        return ActionResult.ok(
            data={
                "spell_id": spell.id,
                "spell_name": spell.name,
                "spell_type": str(spell.spell_type or "").strip().lower(),
                "effect_payload": effect_payload,
            }
        )

    @staticmethod
    def _is_profession(character, profession):
        normalized = str(profession or "").strip().lower().replace(" ", "_").replace("-", "_")
        if character is None:
            return False
        checker = getattr(character, "is_profession", None)
        if callable(checker):
            return bool(checker(normalized))
        getter = getattr(character, "get_profession", None)
        if callable(getter):
            current = getter()
        else:
            current = getattr(character, "profession", "")
        return str(current or "").strip().lower().replace(" ", "_").replace("-", "_") == normalized

    @staticmethod
    def get_valid_aoe_targets(room, caster, spell=None):
        if room is None or not hasattr(room, "contents"):
            return []
        profile = dict(getattr(spell, "effect_profile", {}) or {})
        max_targets = int(profile.get("max_targets", 0) or 0)
        valid_targets = []
        for occupant in list(getattr(room, "contents", []) or []):
            if occupant is None or occupant is caster:
                continue
            if not hasattr(occupant, "set_hp") or getattr(getattr(occupant, "db", None), "hp", None) is None:
                continue
            valid_targets.append(occupant)
            if max_targets > 0 and len(valid_targets) >= max_targets:
                break
        return valid_targets

    @staticmethod
    def get_valid_group_targets(room, caster):
        recipients = [caster]
        if room is None or not hasattr(room, "contents"):
            return recipients
        for occupant in list(getattr(room, "contents", []) or []):
            if occupant is None or occupant is caster:
                continue
            if getattr(occupant, "account", None) is None or not hasattr(occupant, "get_state"):
                continue
            recipients.append(occupant)
        return recipients

    @staticmethod
    def _scale_aoe_power(final_spell_power, target_count, spell=None):
        _spell = spell
        if int(target_count or 0) <= 1:
            return float(final_spell_power or 0.0)
        return float(final_spell_power or 0.0) / (float(target_count) ** 0.5)

    @staticmethod
    def _attach_structured_effect_trace(caster, spell, handler_name, result):
        ndb = getattr(caster, "ndb", None)
        if ndb is None or not bool(getattr(ndb, "spell_debug", False)) or not getattr(result, "success", False):
            return

        payload = dict((result.data or {}).get("effect_payload") or {})
        effect_family = str(payload.get("effect_family") or str(getattr(spell, "spell_type", "") or "").strip().lower())
        debug_trace = dict(payload.get("debug_trace") or {})
        environment_context = dict(getattr(ndb, "spell_environment_context", None) or {})
        debug_trace.update(
            {
                "spell_id": getattr(spell, "id", None),
                "effect_family": effect_family,
                "handler": str(handler_name or ""),
                "contest_used": effect_family in {"targeted_magic", "debilitation", "aoe"} or (effect_family == "cyclic" and str(payload.get("target_mode", "") or "") == "room"),
                "state_mutation_owner": {
                    "aoe": "StateService",
                    "augmentation": "StateService",
                    "cyclic": "StateService",
                    "targeted_magic": "StateService",
                    "debilitation": "StateService",
                    "healing": "StateService",
                    "utility": "StateService",
                    "warding": "StateService",
                }.get(effect_family, "SpellEffectService"),
                "legacy_fallback": False,
                "effective_env_mana": float(environment_context.get("effective_env_mana", 1.0) or 1.0),
                "environmental_mana_modifier": float(environment_context.get("environmental_mana_modifier", 1.0) or 1.0),
            }
        )
        payload["debug_trace"] = debug_trace
        data = dict(result.data or {})
        data["effect_payload"] = payload
        result.data = data

        entries = list(getattr(ndb, "spell_debug_trace", []) or [])
        if not entries or entries[-1] != debug_trace:
            entries.append(dict(debug_trace))
            ndb.spell_debug_trace = entries[-100:]