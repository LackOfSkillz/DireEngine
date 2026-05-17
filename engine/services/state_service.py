from engine.services.injury_service import InjuryService
from engine.services.result import ActionResult


class StateService:

    @staticmethod
    def _pick_primary_effect(effect_map):
        if not effect_map:
            return None
        ranked = sorted(
            ((str(name), dict(data or {})) for name, data in dict(effect_map).items() if data),
            key=lambda item: (
                int(item[1].get("strength", 0) or 0),
                int(item[1].get("duration", 0) or 0),
                item[0],
            ),
            reverse=True,
        )
        return ranked[0][1] if ranked else None

    @staticmethod
    def _pick_primary_effect_by(effect_map, predicate):
        filtered = {}
        for name, data in dict(effect_map or {}).items():
            payload = dict(data or {})
            if predicate(payload):
                filtered[str(name)] = payload
        return StateService._pick_primary_effect(filtered)

    @staticmethod
    def _sync_legacy_state_views(target, active_effects, previous_active_effects=None):
        setter = getattr(target, "set_state", None)
        clearer = getattr(target, "clear_state", None)
        if not callable(setter) and not callable(clearer):
            return

        previous_active_effects = dict(previous_active_effects or {})

        augmentation = StateService._pick_primary_effect(dict(active_effects.get("augmentation") or {}))
        if augmentation and callable(setter):
            setter("augmentation_buff", dict(augmentation))
        elif callable(clearer) and "augmentation" in previous_active_effects:
            clearer("augmentation_buff")

        ward = StateService._pick_primary_effect(dict(active_effects.get("warding") or {}))
        if ward and callable(setter):
            setter("warding_barrier", dict(ward))
        elif callable(clearer) and "warding" in previous_active_effects:
            clearer("warding_barrier")

        physical_ward = StateService._pick_primary_effect_by(
            dict(active_effects.get("warding") or {}),
            lambda payload: bool(payload.get("absorbs_physical", False)),
        )
        if physical_ward and callable(setter):
            setter("physical_barrier", dict(physical_ward))
        elif callable(clearer) and "warding" in previous_active_effects:
            clearer("physical_barrier")

        utility_effects = dict(active_effects.get("utility") or {})
        utility_light = None
        for effect_data in utility_effects.values():
            effect_payload = dict(effect_data or {})
            if str(effect_payload.get("effect_type", "") or "") == "light":
                utility_light = effect_payload
                break
        if utility_light is None:
            luminous_ward = StateService._pick_primary_effect_by(
                dict(active_effects.get("warding") or {}),
                lambda payload: bool(payload.get("emits_light", False)),
            )
            if luminous_ward:
                utility_light = dict(luminous_ward)
                utility_light.setdefault("effect_type", "light")
        if utility_light and callable(setter):
            setter("utility_light", utility_light)
        elif callable(clearer) and ("utility" in previous_active_effects or "warding" in previous_active_effects):
            clearer("utility_light")

    @staticmethod
    def _get_active_effects(target):
        getter = getattr(target, "get_state", None)
        if not callable(getter):
            return {}
        active_effects = getter("active_effects") or {}
        if not isinstance(active_effects, dict):
            active_effects = dict(active_effects)
        normalized = {}
        for category, effect_map in active_effects.items():
            if not isinstance(effect_map, dict):
                effect_map = dict(effect_map)
            normalized[str(category)] = {str(effect_name): dict(effect_data or {}) for effect_name, effect_data in effect_map.items()}
        return normalized

    @staticmethod
    def _set_active_effects(target, active_effects):
        setter = getattr(target, "set_state", None)
        clearer = getattr(target, "clear_state", None)
        previous_active_effects = StateService._get_active_effects(target)
        normalized = {}
        for category, effect_map in dict(active_effects or {}).items():
            if not effect_map:
                continue
            normalized[str(category)] = {str(effect_name): dict(effect_data or {}) for effect_name, effect_data in dict(effect_map).items() if effect_data}
        if not normalized:
            StateService._sync_legacy_state_views(target, {}, previous_active_effects=previous_active_effects)
            if callable(clearer):
                clearer("active_effects")
            return {}
        if callable(setter):
            setter("active_effects", normalized)
        if hasattr(getattr(target, "db", None), "encumbrance_dirty"):
            target.db.encumbrance_dirty = True
        StateService._sync_legacy_state_views(target, normalized, previous_active_effects=previous_active_effects)
        return normalized

    @staticmethod
    def apply_augmentation_effect(target, buff_name, strength, duration, modifiers=None):
        active_effects = StateService._get_active_effects(target)
        augmentation_effects = dict(active_effects.get("augmentation") or {})
        effect_key = str(buff_name or "augmentation").strip().lower().replace(" ", "_")
        incoming_strength = max(1, int(strength or 0))
        incoming_duration = max(1, int(duration or 0))
        normalized_modifiers = {str(key): float(value or 0.0) for key, value in dict(modifiers or {}).items()}
        existing = dict(augmentation_effects.get(effect_key) or {})
        if existing and int(existing.get("strength", 0) or 0) > incoming_strength:
            refreshed = dict(existing)
            refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), incoming_duration)
            if normalized_modifiers:
                refreshed["modifiers"] = dict(normalized_modifiers)
            augmentation_effects[effect_key] = refreshed
            active_effects["augmentation"] = augmentation_effects
            StateService._set_active_effects(target, active_effects)
            return ActionResult.ok(data={"effect": refreshed, "ignored": True})

        effect_data = {
            "name": effect_key,
            "strength": incoming_strength,
            "duration": incoming_duration,
            "modifiers": dict(normalized_modifiers),
        }
        if existing:
            effect_data["strength"] = max(int(existing.get("strength", 0) or 0), incoming_strength)
            effect_data["duration"] = max(int(existing.get("duration", 0) or 0), incoming_duration)
        augmentation_effects[effect_key] = effect_data
        active_effects["augmentation"] = augmentation_effects
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(data={"effect": effect_data, "ignored": False})

    @staticmethod
    def apply_warding_effect(target, source_spell, strength, duration, absorbs_physical=False, extra_data=None):
        active_effects = StateService._get_active_effects(target)
        warding_effects = dict(active_effects.get("warding") or {})
        effect_key = str(source_spell or "warding").strip().lower().replace(" ", "_")
        incoming_strength = max(1, int(strength or 0))
        incoming_duration = max(1, int(duration or 0))
        normalized_extra = {str(key): value for key, value in dict(extra_data or {}).items()}
        existing = dict(warding_effects.get(effect_key) or {})
        if existing:
            existing["strength"] = max(int(existing.get("strength", 0) or 0), incoming_strength)
            existing["duration"] = max(int(existing.get("duration", 0) or 0), incoming_duration)
            existing["absorbs_physical"] = bool(existing.get("absorbs_physical", False) or absorbs_physical)
            existing.update(normalized_extra)
            warding_effects[effect_key] = existing
            active_effects["warding"] = warding_effects
            StateService._set_active_effects(target, active_effects)
            return ActionResult.ok(data={"effect": existing, "refreshed": True})

        effect_data = {
            "name": effect_key,
            "spell_id": effect_key,
            "strength": incoming_strength,
            "duration": incoming_duration,
            "absorbs_physical": bool(absorbs_physical),
        }
        effect_data.update(normalized_extra)
        warding_effects[effect_key] = effect_data
        active_effects["warding"] = warding_effects
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(data={"effect": effect_data, "refreshed": False})

    @staticmethod
    def get_strongest_physical_ward(target):
        getter = getattr(target, "get_state", None)
        if callable(getter):
            mirrored = getter("physical_barrier")
            if isinstance(mirrored, dict) and mirrored:
                return dict(mirrored)
        return StateService._pick_primary_effect_by(
            dict(StateService._get_active_effects(target).get("warding") or {}),
            lambda payload: bool(payload.get("absorbs_physical", False)),
        )

    @staticmethod
    def get_strongest_magic_ward(target):
        warding_effects = dict(StateService._get_active_effects(target).get("warding") or {})
        strongest = StateService._pick_primary_effect_by(
            warding_effects,
            lambda payload: not bool(payload.get("absorbs_physical", False)),
        )
        if strongest:
            return strongest
        if warding_effects:
            return None
        getter = getattr(target, "get_state", None)
        if callable(getter):
            mirrored = getter("warding_barrier")
            if isinstance(mirrored, dict) and mirrored:
                return dict(mirrored)
        return None

    @staticmethod
    def consume_ward(target, spell_id, absorbed):
        active_effects = StateService._get_active_effects(target)
        warding_effects = dict(active_effects.get("warding") or {})
        effect_key = str(spell_id or "").strip().lower().replace(" ", "_")
        ward = dict(warding_effects.get(effect_key) or {})
        if not ward:
            return ActionResult.fail(data={"reason": "missing_ward", "spell_id": effect_key})

        absorbed_amount = max(0, int(absorbed or 0))
        ward["strength"] = max(0, int(ward.get("strength", 0) or 0) - absorbed_amount)
        depleted = int(ward.get("strength", 0) or 0) <= 0
        if depleted:
            warding_effects.pop(effect_key, None)
        else:
            warding_effects[effect_key] = ward

        if warding_effects:
            active_effects["warding"] = warding_effects
        else:
            active_effects.pop("warding", None)
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(data={"effect": ward, "depleted": depleted, "absorbed": absorbed_amount})

    @staticmethod
    def apply_utility_effect(target, effect_name, duration, source_spell=None, extra_data=None):
        active_effects = StateService._get_active_effects(target)
        utility_effects = dict(active_effects.get("utility") or {})
        effect_key = str(source_spell or effect_name or "utility").strip().lower().replace(" ", "_")
        effect_data = {
            "name": effect_key,
            "effect_type": str(effect_name or "utility").strip().lower().replace(" ", "_"),
            "duration": max(1, int(duration or 0)),
        }
        effect_data.update({str(key): value for key, value in dict(extra_data or {}).items()})
        existing = dict(utility_effects.get(effect_key) or {})
        if existing:
            effect_data["duration"] = max(int(existing.get("duration", 0) or 0), int(effect_data["duration"] or 0))
        utility_effects[effect_key] = effect_data
        active_effects["utility"] = utility_effects
        StateService._set_active_effects(target, active_effects)
        StateService._sync_utility_capability_flags(target, effect_data)
        return ActionResult.ok(data={"effect": effect_data})

    @staticmethod
    def apply_uncurse(target, power=0):
        cleanse_result = StateService.apply_cleanse(target)
        cleanse_data = dict(cleanse_result.data or {})
        removed = bool(cleanse_data.get("removed", False))
        legacy_states = []
        clearer = getattr(target, "clear_state", None)
        getter = getattr(target, "get_state", None)
        if callable(clearer) and callable(getter):
            for state_name in ("cursed", "hexed", "jinxed"):
                if getter(state_name):
                    clearer(state_name)
                    removed = True
                    legacy_states.append(state_name)

        death_sting_relieved = False
        death_sting_message = None
        reducer = getattr(target, "reduce_death_sting", None)
        if callable(reducer):
            sting_ok, sting_message = reducer(max(10, int(power or 0)))
            death_sting_relieved = bool(sting_ok)
            death_sting_message = sting_message if sting_ok else None
            removed = removed or death_sting_relieved

        return ActionResult.ok(
            data={
                "removed": removed,
                "removed_effects": dict(cleanse_data.get("removed_effects", {}) or {}),
                "removed_legacy_states": legacy_states,
                "death_sting_relieved": death_sting_relieved,
                "death_sting_message": death_sting_message,
            }
        )

    @staticmethod
    def apply_cleanse(target):
        active_effects = StateService._get_active_effects(target)
        removed_effects = dict(active_effects.pop("debilitation", {}) or {})
        removed = bool(removed_effects)
        clearer = getattr(target, "clear_state", None)
        getter = getattr(target, "get_state", None)
        if callable(clearer) and callable(getter):
            if getter("exposed_magic"):
                clearer("exposed_magic")
                removed = True
            if getter("debilitated"):
                clearer("debilitated")
                removed = True
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(data={"removed": removed, "removed_effects": removed_effects})

    @staticmethod
    def apply_debilitation_effect(
        target,
        effect_type,
        strength,
        duration,
        applied_by=None,
        contest_margin=0.0,
        source_spell=None,
        modifiers=None,
        stat_debuffs=None,
        encumbrance_modifier=0,
        stacking="replace_weaker",
    ):
        active_effects = StateService._get_active_effects(target)
        debilitation_effects = dict(active_effects.get("debilitation") or {})
        effect_key = str(effect_type or "debilitation").strip().lower().replace(" ", "_")
        incoming_strength = max(1, int(strength or 0))
        incoming_duration = max(1, int(duration or 0))
        normalized_modifiers = {str(key): float(value or 0.0) for key, value in dict(modifiers or {}).items()}
        normalized_stat_debuffs = {str(key): int(value or 0) for key, value in dict(stat_debuffs or {}).items() if int(value or 0) != 0}
        normalized_encumbrance = int(encumbrance_modifier or 0)
        existing = dict(debilitation_effects.get(effect_key) or {})
        if existing:
            existing_strength = max(1, int(existing.get("strength", 0) or 0))
            if existing_strength > incoming_strength:
                return ActionResult.ok(
                    data={
                        "applied": False,
                        "replaced": False,
                        "ignored": True,
                        "effect": existing,
                    }
                )
            if existing_strength == incoming_strength:
                refreshed = dict(existing)
                refreshed["duration"] = max(int(refreshed.get("duration", 0) or 0), incoming_duration)
                refreshed["contest_margin"] = float(contest_margin)
                refreshed["applied_by"] = applied_by
                refreshed["source_spell"] = source_spell
                refreshed["stacking"] = str(stacking or "replace_weaker")
                if normalized_modifiers:
                    refreshed["modifiers"] = dict(normalized_modifiers)
                if normalized_stat_debuffs:
                    refreshed["stat_debuffs"] = dict(normalized_stat_debuffs)
                if normalized_encumbrance:
                    refreshed["encumbrance_modifier"] = int(normalized_encumbrance)
                debilitation_effects[effect_key] = refreshed
                active_effects["debilitation"] = debilitation_effects
                StateService._set_active_effects(target, active_effects)
                return ActionResult.ok(
                    data={
                        "applied": True,
                        "replaced": False,
                        "ignored": False,
                        "effect": refreshed,
                    }
                )

        effect_data = {
            "effect_type": effect_key,
            "strength": incoming_strength,
            "duration": incoming_duration,
            "applied_by": applied_by,
            "contest_margin": float(contest_margin),
            "source_spell": source_spell,
            "stacking": str(stacking or "replace_weaker"),
            "modifiers": dict(normalized_modifiers),
            "stat_debuffs": dict(normalized_stat_debuffs),
            "encumbrance_modifier": int(normalized_encumbrance),
        }
        debilitation_effects[effect_key] = effect_data
        active_effects["debilitation"] = debilitation_effects
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(
            data={
                "applied": True,
                "replaced": bool(existing),
                "ignored": False,
                "effect": effect_data,
            }
        )

    @staticmethod
    def get_active_cyclic_effects(target):
        return dict(StateService._get_active_effects(target).get("cyclic") or {})

    @staticmethod
    def apply_cyclic_effect(target, spell_id, effect_data):
        active_effects = StateService._get_active_effects(target)
        cyclic_effects = dict(active_effects.get("cyclic") or {})
        effect_key = str(spell_id or "cyclic").strip().lower().replace(" ", "_")
        if cyclic_effects and effect_key not in cyclic_effects:
            active_id, active_payload = next(iter(cyclic_effects.items()))
            active_name = str(dict(active_payload or {}).get("spell_name") or dict(active_payload or {}).get("name") or active_id)
            return ActionResult.fail(
                errors=[f"You already sustain a cyclic spell: {active_name}. Release it first with RELEASE CYCLIC before casting another."],
                data={"started": False, "reason": "single_cyclic_enforced", "active_spell_id": active_id, "active_spell_name": active_name},
            )
        if cyclic_effects.get(effect_key):
            return ActionResult.fail(
                errors=["That cyclic spell is already active."],
                data={"started": False, "reason": "already_active", "effect": dict(cyclic_effects.get(effect_key) or {})},
            )

        effect_payload = dict(effect_data or {})
        effect_payload.setdefault("active", True)
        effect_payload.setdefault("duration", None)
        effect_payload.setdefault("tick_count", 0)
        effect_payload.setdefault("sustain_source", "held_mana")
        effect_payload.setdefault("sustain_ref", None)
        cyclic_effects[effect_key] = effect_payload
        active_effects["cyclic"] = cyclic_effects
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(data={"started": True, "effect": dict(effect_payload)})

    @staticmethod
    def remove_effect(target, category, effect_name=None):
        active_effects = StateService._get_active_effects(target)
        category_key = str(category or "").strip().lower().replace(" ", "_")
        effect_map = dict(active_effects.get(category_key) or {})
        if not effect_map:
            return ActionResult.ok(data={"removed": False, "effects": {}})

        if effect_name is None:
            if category_key == "utility":
                for removed_effect in effect_map.values():
                    StateService._clear_utility_capability_flags(target, removed_effect)
            active_effects.pop(category_key, None)
            StateService._set_active_effects(target, active_effects)
            return ActionResult.ok(data={"removed": True, "effects": {}})

        effect_key = str(effect_name or "").strip().lower().replace(" ", "_")
        removed = effect_key in effect_map
        removed_effect = dict(effect_map.get(effect_key) or {})
        effect_map.pop(effect_key, None)
        if removed and category_key == "utility":
            StateService._clear_utility_capability_flags(target, removed_effect)
        if effect_map:
            active_effects[category_key] = effect_map
        else:
            active_effects.pop(category_key, None)
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(data={"removed": removed, "effects": dict(effect_map)})

    @staticmethod
    def tick_active_effects(target):
        # PERFORMANCE RULE:
        # This path may run for many characters per tick.
        # Avoid per-effect expensive lookups or new nested scans unless justified.
        active_effects = StateService._get_active_effects(target)
        if not active_effects:
            return ActionResult.ok(data={"expired_effects": [], "active_effects": {}})

        expired_effects = []
        updated_effects = {}
        for category, effect_map in active_effects.items():
            category_updates = {}
            for effect_name, effect_data in dict(effect_map or {}).items():
                updated = dict(effect_data or {})
                if updated.get("duration") is None:
                    category_updates[str(effect_name)] = updated
                    continue
                updated["duration"] = int(updated.get("duration", 0) or 0) - 1
                if int(updated.get("duration", 0) or 0) <= 0:
                    expired_payload = dict(effect_data or {})
                    expired_payload["effect_family"] = str(category)
                    expired_payload["effect_type"] = str(effect_name)
                    StateService._expire_effect_side_effects(target, str(category), expired_payload)
                    expired_effects.append(expired_payload)
                    continue
                category_updates[str(effect_name)] = updated
            if category_updates:
                updated_effects[str(category)] = category_updates

        StateService._set_active_effects(target, updated_effects)
        return ActionResult.ok(data={"expired_effects": expired_effects, "active_effects": updated_effects})

    @staticmethod
    def _sync_utility_capability_flags(target, effect_data):
        capability_flag = str(dict(effect_data or {}).get("capability_flag", "") or "").strip()
        if not capability_flag:
            return
        setattr(target.db, capability_flag, True)
        setattr(target.db, f"{capability_flag}_expires_in", int(dict(effect_data or {}).get("duration", 0) or 0))

    @staticmethod
    def _clear_utility_capability_flags(target, effect_data):
        capability_flag = str(dict(effect_data or {}).get("capability_flag", "") or "").strip()
        if not capability_flag:
            return
        setattr(target.db, capability_flag, False)
        setattr(target.db, f"{capability_flag}_expires_in", 0)

    @staticmethod
    def _expire_effect_side_effects(target, category, effect_data):
        if str(category or "") == "utility":
            StateService._clear_utility_capability_flags(target, effect_data)
            return
        if str(category or "") == "debilitation" and hasattr(getattr(target, "db", None), "encumbrance_dirty"):
            target.db.encumbrance_dirty = True

    @staticmethod
    def apply_healing(target, amount):
        heal_amount = max(0, int(amount or 0))
        if heal_amount <= 0:
            return ActionResult.ok(data={"amount": 0})
        current_hp = int(getattr(getattr(target, "db", None), "hp", 0) or 0)
        max_hp = int(getattr(getattr(target, "db", None), "max_hp", 0) or 0)
        if max_hp <= 0:
            return ActionResult.ok(data={"amount": 0})
        applied = min(heal_amount, max(0, max_hp - current_hp))
        if applied > 0 and hasattr(target, "set_hp"):
            target.set_hp(current_hp + applied)
        return ActionResult.ok(data={"amount": applied})

    @staticmethod
    def process_cyclic_effects(target):
        from engine.services.mana_service import ManaService
        from engine.services.feat_service import FeatService
        from engine.services.spell_contest_service import SpellContestService

        active_effects = StateService._get_active_effects(target)
        cyclic_effects = dict(active_effects.get("cyclic") or {})
        if not cyclic_effects:
            return ActionResult.ok(data={"processed_effects": [], "collapsed_effects": [], "active_effects": dict(active_effects)})

        processed_effects = []
        collapsed_effects = []
        updated_effects = dict(cyclic_effects)
        for effect_name, effect_data in cyclic_effects.items():
            updated = dict(effect_data or {})
            if not bool(updated.get("active", True)):
                updated_effects.pop(effect_name, None)
                continue

            collapse_reason = None
            current_hp = int(getattr(getattr(target, "db", None), "hp", 0) or 0)
            if current_hp <= 0:
                collapse_reason = "caster_dead"
            elif bool(updated.get("interrupt_on_debilitation", False)) and dict(active_effects.get("debilitation") or {}):
                collapse_reason = "interrupted"
            elif str(updated.get("target_mode", "") or "") == "room" and updated.get("room_ref") is not None and getattr(target, "location", None) is not updated.get("room_ref"):
                collapse_reason = "left_room"

            if collapse_reason is not None:
                collapsed = dict(updated)
                collapsed["effect_family"] = "cyclic"
                collapsed["effect_type"] = str(effect_name)
                collapsed["collapse_reason"] = collapse_reason
                collapsed_effects.append(collapsed)
                updated_effects.pop(effect_name, None)
                continue

            mana_per_tick = max(0, ManaService._coerce_int(updated.get("mana_per_tick"), default=0))
            mana_result = ManaService.consume_mana_for_cyclic(
                target,
                mana_per_tick,
                updated.get("sustain_source", "held_mana"),
                sustain_ref=updated.get("sustain_ref"),
            )
            if not mana_result.success:
                collapsed = dict(updated)
                collapsed["effect_family"] = "cyclic"
                collapsed["effect_type"] = str(effect_name)
                collapsed["collapse_reason"] = str((mana_result.data or {}).get("reason") or "insufficient_mana")
                collapsed["remaining_mana"] = float((mana_result.data or {}).get("remaining_mana", 0.0) or 0.0)
                collapsed_effects.append(collapsed)
                updated_effects.pop(effect_name, None)
                continue

            effective_power = float(updated.get("power", 0.0) or 0.0)
            room = getattr(target, "location", None)
            mana_type = str(updated.get("mana_type", "") or "").strip().lower()
            environmental_modifier = ManaService.get_environmental_modifier(room, mana_type)
            effective_power *= environmental_modifier
            effective_power += float(StateService._get_augmentation_modifier(target, "magic_attack"))
            effective_power = max(0.0, effective_power - float(StateService._get_debilitation_modifier(target, "magic_attack")))
            tick_scale = max(0.01, float(updated.get("tick_scale", 0.1) or 0.1))
            tick_count = int(updated.get("tick_count", 0) or 0) + 1
            payload = {
                "effect_family": "cyclic",
                "effect_type": str(effect_name),
                "tick_count": tick_count,
                "mana_per_tick": float((mana_result.data or {}).get("consumed", mana_per_tick) or 0.0),
                "requested_base_cost": float((mana_result.data or {}).get("requested_base_cost", mana_per_tick) or 0.0),
                "remaining_mana": float((mana_result.data or {}).get("remaining_mana", 0.0) or 0.0),
                "target_id": updated.get("target_id"),
                "target_key": updated.get("target_key"),
                "environmental_mana_modifier": float(environmental_modifier),
                "sustain_source": str(updated.get("sustain_source", "held_mana") or "held_mana"),
                "sustain_ref": updated.get("sustain_ref"),
            }

            tick_effect = str(updated.get("tick_effect", "healing") or "healing")
            if tick_effect == "healing":
                heal_amount = max(0, int(round(effective_power * tick_scale)))
                heal_result = StateService.apply_healing(target, heal_amount)
                payload["heal_amount"] = int((heal_result.data or {}).get("amount", 0) or 0)
            elif tick_effect == "aoe_damage_over_time":
                room = updated.get("room_ref") if updated.get("room_ref") is not None else getattr(target, "location", None)
                victims = StateService._get_room_targets(room, target, max_targets=updated.get("max_targets", 0))
                scaled_power = float(effective_power)
                if len(victims) > 1:
                    scaled_power = float(effective_power) / (float(len(victims)) ** 0.5)
                payload["target_count"] = len(victims)
                payload["targets"] = []
                for victim in victims:
                    contest_result = SpellContestService.resolve_targeted_magic(
                        target,
                        victim,
                        scaled_power,
                        spell_id=updated.get("spell_id"),
                        quality="normal",
                        wild_modifier=1.0,
                    )
                    contest_payload = dict(contest_result.data or {}) if contest_result.success else {}
                    payload["targets"].append(
                        {
                            "target_id": getattr(victim, "id", None),
                            "target_key": getattr(victim, "key", "someone"),
                            "hit": bool(contest_payload.get("hit", False)),
                            "final_damage": float(contest_payload.get("final_damage", 0.0) or 0.0),
                            "absorbed_by_ward": float(contest_payload.get("absorbed_by_ward", 0.0) or 0.0),
                        }
                    )
            elif tick_effect == "damage_over_time":
                victim = updated.get("target_ref")
                if victim is None or int(getattr(getattr(victim, "db", None), "hp", 0) or 0) <= 0:
                    collapsed = dict(updated)
                    collapsed["effect_family"] = "cyclic"
                    collapsed["effect_type"] = str(effect_name)
                    collapsed["collapse_reason"] = "invalid_target"
                    collapsed_effects.append(collapsed)
                    updated_effects.pop(effect_name, None)
                    continue
                base_damage = max(1, int(round(effective_power * tick_scale)))
                resisted_damage = max(0, int(getattr(victim, "apply_magic_resistance", lambda value: value)(base_damage) or 0))
                remaining_damage = max(0, int(getattr(target, "apply_ward_absorption", lambda victim_obj, value: value)(victim, resisted_damage) or 0))
                absorbed = max(0, int(resisted_damage) - int(remaining_damage))
                damage_result = ActionResult.ok(data={"amount": 0})
                if remaining_damage > 0:
                    damage_result = StateService.apply_damage(victim, remaining_damage, location="chest", damage_type="impact")
                payload["base_damage"] = float(int(resisted_damage or 0))
                payload["absorbed_by_ward"] = float(absorbed)
                payload["final_damage"] = float(int((damage_result.data or {}).get("amount", 0) or 0))

            updated["tick_count"] = tick_count
            updated_effects[str(effect_name)] = updated
            processed_effects.append(payload)
            StateService._record_cyclic_trace(target, effect_name, payload)

        if updated_effects:
            active_effects["cyclic"] = updated_effects
        else:
            active_effects.pop("cyclic", None)
        StateService._set_active_effects(target, active_effects)
        return ActionResult.ok(data={"processed_effects": processed_effects, "collapsed_effects": collapsed_effects, "active_effects": dict(active_effects)})

    @staticmethod
    def _get_augmentation_modifier(target, modifier_key):
        buff = getattr(target, "get_state", lambda key: None)("augmentation_buff")
        if not isinstance(buff, dict):
            return 0
        modifiers = dict(buff.get("modifiers") or {})
        scale = float(modifiers.get(str(modifier_key or "").strip().lower().replace(" ", "_"), 0.0) or 0.0)
        return max(0, int(round(float(buff.get("strength", 0) or 0) * scale)))

    @staticmethod
    def _get_debilitation_modifier(target, modifier_key):
        getter = getattr(target, "get_effect_modifier", None)
        if callable(getter):
            return max(0, int(getter(modifier_key) or 0))
        return 0

    @staticmethod
    def _record_cyclic_trace(target, effect_name, payload):
        ndb = getattr(target, "ndb", None)
        if ndb is None or not bool(getattr(ndb, "spell_debug", False)):
            return
        trace_payload = {
            "spell_id": str(effect_name),
            "effect_family": "cyclic",
            "tick_count": int(payload.get("tick_count", 0) or 0),
            "mana_per_tick": float(payload.get("mana_per_tick", 0.0) or 0.0),
            "remaining_mana": float(payload.get("remaining_mana", 0.0) or 0.0),
            "legacy_fallback": False,
        }
        entries = list(getattr(ndb, "spell_debug_trace", []) or [])
        entries.append(trace_payload)
        ndb.spell_debug_trace = entries[-100:]

    @staticmethod
    def _get_room_targets(room, caster, max_targets=0):
        if room is None or not hasattr(room, "contents"):
            return []
        victims = []
        limit = int(max_targets or 0)
        for occupant in list(getattr(room, "contents", []) or []):
            if occupant is None or occupant is caster:
                continue
            if not hasattr(occupant, "set_hp") or getattr(getattr(occupant, "db", None), "hp", None) is None:
                continue
            victims.append(occupant)
            if limit > 0 and len(victims) >= limit:
                break
        return victims

    @staticmethod
    def apply_damage(target, damage, location=None, damage_type="impact", critical=False, attacker=None):
        damage = int(damage or 0)
        if damage <= 0:
            return ActionResult.ok(data={"amount": 0, "location": location, "damage_type": damage_type, "critical": bool(critical)})

        final_damage = damage
        if location is not None and hasattr(target, "apply_empath_unity_share"):
            final_damage = int(target.apply_empath_unity_share(location, damage, damage_type=damage_type) or 0)
        if final_damage <= 0:
            return ActionResult.ok(data={"amount": 0, "location": location, "damage_type": damage_type, "critical": bool(critical)})

        target.set_hp((target.db.hp or 0) - final_damage)
        wound_result = ActionResult.ok(data={})
        if location is not None:
            wound_result = InjuryService.apply_hit_wound(target, location, final_damage, damage_type=damage_type, critical=critical)

        if getattr(target, "is_empath", lambda: False)() and target.get_empath_link_state(require_local=False, emit_break_messages=False):
            target.decay_empath_link_stability(amount=None, reason="damage", emit_message=True)
        if getattr(target, "is_empath", lambda: False)() and target.get_empath_unity_state():
            target.decay_empath_unity_stability(event_key="damage", emit_message=True)

        if attacker is not None and attacker != target and bool(getattr(attacker, "has_account", False)):
            if hasattr(target, "add_threat"):
                target.add_threat(attacker, max(10, final_damage))
            if hasattr(target, "at_attacked"):
                target.at_attacked(attacker)

        data = {"amount": final_damage, "location": location, "damage_type": damage_type, "critical": bool(critical)}
        data.update(dict(wound_result.data or {}))
        data.setdefault("injury_events", list((wound_result.data or {}).get("injury_events", []) or []))
        return ActionResult.ok(data=data)

    @staticmethod
    def apply_roundtime(character, duration, ambush=False):
        if ambush:
            character.apply_thief_roundtime(duration)
            return ActionResult.ok(data={"roundtime": float(duration or 0.0), "ambush": True})
        character.set_roundtime(duration)
        return ActionResult.ok(data={"roundtime": float(duration or 0.0), "ambush": False})

    @staticmethod
    def apply_balance(character, amount):
        character.set_balance(amount)
        return ActionResult.ok(data={"balance": amount})

    @staticmethod
    def apply_fatigue(character, amount):
        character.set_fatigue(amount)
        return ActionResult.ok(data={"fatigue": amount})