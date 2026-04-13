from domain.spells.spell_definitions import Spell
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
    def _apply_augmentation_spell(caster, spell, final_spell_power, quality="normal", target=None):
        recipient = target or caster
        strength = 1 + int(float(final_spell_power or 0.0) / 10.0)
        duration = 10 + int(float(final_spell_power or 0.0) / 2.0)
        modifiers = {
            str(key): float(value or 0.0)
            for key, value in dict(getattr(spell, "effect_profile", {}) or {}).get("contest_modifiers", {}).items()
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

        target_type = str(getattr(spell, "target_type", "self") or "self").strip().lower()
        if target_type == "group":
            recipients = SpellEffectService.get_valid_group_targets(getattr(caster, "location", None), caster)
            if not recipients:
                return ActionResult.fail(errors=["There is no one here to protect."], data={"reason": "no_group_targets"})
            payload_targets = []
            for recipient in recipients:
                barrier_result = StateService.apply_warding_effect(recipient, spell.id, strength, duration)
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

        barrier_result = StateService.apply_warding_effect(recipient, spell.id, strength, duration)
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
        recipient = target or caster
        effect_profile = dict(getattr(spell, "effect_profile", {}) or {})
        effect_type = str(effect_profile.get("effect_type", spell.id) or spell.id).strip().lower()

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

        return ActionResult.fail(
            errors=[f"No structured utility behavior exists for {spell.id}."],
            data={"spell_id": spell.id, "spell_type": str(spell.spell_type or "").strip().lower(), "reason": "unknown_utility_effect"},
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
            },
        )
        if not start_result.success:
            return ActionResult.fail(errors=list(start_result.errors or []), data={"reason": "already_active", "effect_family": "cyclic"})

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