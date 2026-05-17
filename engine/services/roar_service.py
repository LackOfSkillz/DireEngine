import time
from collections.abc import Mapping

from domain.abilities.roars.registry import ROAR_REGISTRY, get_roar_definition, get_roar_definition_by_bit
from engine.services.result import ActionResult
from engine.services.vocal_damage_service import VocalDamageService


class RoarService:
    ACTIVE_STATE_KEY = "barbarian_active_roars"
    NPC_ALLY_EFFECT_CODE = 360001
    KUNIYO_BIT = 0
    HONOR_STATE_KEY = "barbarian_roar_honor"
    VENGEANCE_STATE_KEY = "barbarian_roar_vengeance"
    STEADFASTNESS_STATE_KEY = "barbarian_roar_steadfastness"
    PRIDE_STATE_KEY = "barbarian_roar_pride"
    NOBILITY_STATE_KEY = "barbarian_roar_nobility"
    BRAVERY_STATE_KEY = "barbarian_roar_bravery"
    BLOODTHIRST_STATE_KEY = "barbarian_roar_bloodthirst"
    SUPERIORITY_STATE_KEY = "barbarian_roar_superiority"
    TROTHFANG_STATE_KEY = "barbarian_roar_trothfang"
    TEMPESTUOUS_STATE_KEY = "barbarian_roar_tempestuous"
    EMBRACE_STATE_KEY = "barbarian_roar_deaths_embrace"
    MAGICS_BANE_STATE_KEY = "barbarian_roar_magics_bane"
    MAGES_LAMENT_STATE_KEY = "barbarian_roar_mages_lament"
    SCREECH_STATE_KEY = "barbarian_roar_screech_of_madness"
    BANSHEE_STATE_KEY = "barbarian_roar_banshees_wail"
    INSANE_LAUGHTER_STATE_KEY = "barbarian_roar_insane_laughter"
    ANGER_EARTH_STATE_KEY = "barbarian_roar_anger_the_earth"
    SERPENT_HISS_STATE_KEY = "barbarian_roar_serpent_hiss"
    SLASH_SHADOWS_STATE_KEY = "barbarian_roar_slash_the_shadows"

    @classmethod
    def now(cls):
        return time.time()

    @classmethod
    def _get_circle(cls, actor) -> int:
        getter = getattr(actor, "get_circle", None)
        if callable(getter):
            return max(1, int(getter() or 1))
        return max(1, int(getattr(getattr(actor, "db", None), "circle", 1) or 1))

    @classmethod
    def get_roar_power_modifier(cls, actor, category: str) -> int:
        try:
            from engine.services.dance_service import DanceService

            return int(DanceService.get_roar_power_modifier(actor, category) or 100)
        except Exception:
            return 100

    @classmethod
    def get_total_slots_for_circle(cls, circle: int) -> int:
        return max(0, int((int(circle or 0) + 5) / 10))

    @classmethod
    def get_total_slots(cls, actor) -> int:
        return cls.get_total_slots_for_circle(cls._get_circle(actor))

    @classmethod
    def _is_barbarian(cls, actor) -> bool:
        checker = getattr(actor, "is_profession", None)
        return bool(callable(checker) and checker("barbarian"))

    @classmethod
    def _get_spellbook1(cls, actor) -> int:
        getter = getattr(actor, "get_spellbook1", None)
        if callable(getter):
            return max(0, int(getter() or 0))
        return max(0, int(getattr(getattr(actor, "db", None), "spellbook1", 0) or 0))

    @classmethod
    def _set_spellbook1(cls, actor, value):
        setter = getattr(actor, "set_spellbook1", None)
        if callable(setter):
            return setter(value)
        actor.db.spellbook1 = max(0, int(value or 0))
        return actor.db.spellbook1

    @classmethod
    def has_known_roar_bit(cls, actor, bit_index: int) -> bool:
        value = cls._get_spellbook1(actor)
        return bool(value & (1 << int(bit_index)))

    @classmethod
    def get_known_roars(cls, actor):
        known = []
        for bit_index in sorted(getattr(__import__("domain.abilities.roars.registry", fromlist=["ROAR_BY_BIT"]), "ROAR_BY_BIT", {}).keys()):
            if cls.has_known_roar_bit(actor, bit_index):
                definition = get_roar_definition_by_bit(bit_index)
                if definition:
                    known.append(definition)
        return known

    @classmethod
    def get_known_roar_names(cls, actor):
        return [definition.name for definition in cls.get_known_roars(actor)]

    @classmethod
    def get_remaining_slots(cls, actor) -> int:
        return max(0, cls.get_total_slots(actor) - len(cls.get_known_roars(actor)))

    @classmethod
    def ensure_kuniyo_auto_learned(cls, actor) -> bool:
        if not cls._is_barbarian(actor):
            return False
        if cls._get_circle(actor) < 5:
            return False
        if cls.has_known_roar_bit(actor, cls.KUNIYO_BIT):
            return False
        if cls.get_known_roars(actor):
            return False
        return cls.set_known_roar(actor, cls.KUNIYO_BIT, enforce_slots=False).success

    @classmethod
    def set_known_roar(cls, actor, bit_index: int, *, enforce_slots: bool = True):
        if not cls._is_barbarian(actor):
            return ActionResult.fail(errors=["Only Barbarians may learn roars."])
        definition = get_roar_definition_by_bit(bit_index)
        if definition is None:
            return ActionResult.fail(errors=["Unknown roar."])
        if cls.has_known_roar_bit(actor, bit_index):
            return ActionResult.ok(data={"bit_index": bit_index, "spellbook1": cls._get_spellbook1(actor)})
        if enforce_slots and cls.get_remaining_slots(actor) < 1:
            return ActionResult.fail(errors=["You have no free roar slots available."])
        missing_prerequisites = [
            required_bit
            for required_bit in tuple(getattr(definition, "prerequisite_bits", ()) or ())
            if not cls.has_known_roar_bit(actor, required_bit)
        ]
        if missing_prerequisites:
            return ActionResult.fail(errors=["You have not received the proper instruction in that technique."])
        new_value = cls._get_spellbook1(actor) | (1 << int(bit_index))
        cls._set_spellbook1(actor, new_value)
        return ActionResult.ok(data={"bit_index": bit_index, "spellbook1": new_value})

    @classmethod
    def clear_known_roar(cls, actor, bit_index: int):
        new_value = cls._get_spellbook1(actor) & ~(1 << int(bit_index))
        cls._set_spellbook1(actor, new_value)
        return ActionResult.ok(data={"bit_index": bit_index, "spellbook1": new_value})

    @classmethod
    def _room_has_flag(cls, room, flag_name: str) -> bool:
        if room is None:
            return False
        normalized = str(flag_name or "").strip().lower()
        if not normalized:
            return False
        db_holder = getattr(room, "db", None)
        if db_holder is not None and bool(getattr(db_holder, normalized, False)):
            return True
        tags = getattr(room, "tags", None)
        if tags is not None:
            try:
                if bool(tags.has(normalized)):
                    return True
            except Exception:
                pass
        return False

    @classmethod
    def _is_droughtmans_maze(cls, room) -> bool:
        room_id = int(getattr(room, "id", getattr(room, "dbid", 0)) or 0)
        return 1051000 <= room_id <= 1053999

    @classmethod
    def _has_effect_code(cls, actor, code: int) -> bool:
        state_key = f"effect_{int(code)}"
        getter = getattr(actor, "get_state", None)
        if callable(getter) and getter(state_key):
            return True
        active_effects = getter("active_effects") if callable(getter) else {}
        if isinstance(active_effects, dict):
            for effect_map in active_effects.values():
                if isinstance(effect_map, dict) and str(code) in effect_map:
                    return True
        return False

    @classmethod
    def _get_group_marker(cls, actor):
        db_holder = getattr(actor, "db", None)
        for attr_name in ("group_id", "group"):
            value = str(getattr(db_holder, attr_name, "") or "").strip().lower()
            if value:
                return value
        ndb_holder = getattr(actor, "ndb", None)
        for attr_name in ("group_id", "group"):
            value = str(getattr(ndb_holder, attr_name, "") or "").strip().lower()
            if value:
                return value
        return None

    @classmethod
    def _is_living(cls, actor) -> bool:
        if actor is None:
            return False
        is_dead = getattr(actor, "is_dead", None)
        return not bool(callable(is_dead) and is_dead())

    @classmethod
    def _get_ally_targets(cls, actor):
        room = getattr(actor, "location", None)
        if room is None:
            return [actor]

        actor_group = cls._get_group_marker(actor)
        recipients = [actor]
        seen_ids = {int(getattr(actor, "id", 0) or 0)}
        for occupant in list(getattr(room, "contents", []) or []):
            if occupant is None or occupant is actor or getattr(occupant, "location", None) != room:
                continue
            occupant_id = int(getattr(occupant, "id", 0) or 0)
            if occupant_id > 0 and occupant_id in seen_ids:
                continue
            if not cls._is_living(occupant):
                continue

            include = False
            occupant_group = cls._get_group_marker(occupant)
            if actor_group:
                include = occupant_group == actor_group
            else:
                include = getattr(occupant, "account", None) is not None and hasattr(occupant, "get_state")

            if not include and cls._has_effect_code(occupant, cls.NPC_ALLY_EFFECT_CODE):
                include = True

            if not include:
                continue

            recipients.append(occupant)
            if occupant_id > 0:
                seen_ids.add(occupant_id)
        return recipients

    @classmethod
    def _resolve_recipients(cls, actor, definition):
        if str(getattr(definition, "category", "") or "").strip().lower() == "inspiration":
            return cls._get_ally_targets(actor)
        return cls._resolve_targets(actor)

    @classmethod
    def _clean_active_roars(cls, actor):
        getter = getattr(actor, "get_state", None)
        setter = getattr(actor, "set_state", None)
        clearer = getattr(actor, "clear_state", None)
        if not callable(getter):
            return {}
        raw = getter(cls.ACTIVE_STATE_KEY)
        if not isinstance(raw, Mapping):
            return {}
        active = {}
        now = cls.now()
        for key, payload in dict(raw or {}).items():
            if not isinstance(payload, Mapping):
                continue
            if float(payload.get("expires_at", 0.0) or 0.0) <= now:
                continue
            active[str(key)] = dict(payload)
        if active != dict(raw or {}):
            if active and callable(setter):
                setter(cls.ACTIVE_STATE_KEY, active)
            elif not active and callable(clearer):
                clearer(cls.ACTIVE_STATE_KEY)
        return active

    @classmethod
    def get_active_roars(cls, actor):
        return cls._clean_active_roars(actor)

    @classmethod
    def _update_active_roar(cls, actor, definition, payload):
        getter = getattr(actor, "get_state", None)
        setter = getattr(actor, "set_state", None)
        if not callable(setter):
            return
        active = dict(getter(cls.ACTIVE_STATE_KEY) or {}) if callable(getter) else {}
        active[str(definition.name)] = dict(payload)
        setter(cls.ACTIVE_STATE_KEY, active)

    @classmethod
    def set_target_effect(cls, target, state_key: str, payload: dict):
        setter = getattr(target, "set_state", None)
        if callable(setter):
            setter(state_key, dict(payload or {}))

    @classmethod
    def _clean_target_effect(cls, actor, state_key: str):
        getter = getattr(actor, "get_state", None)
        clearer = getattr(actor, "clear_state", None)
        if not callable(getter):
            return None
        payload = getter(state_key)
        if not isinstance(payload, Mapping):
            return None
        if float(payload.get("expires_at", 0.0) or 0.0) > cls.now():
            return dict(payload)
        if state_key == cls.STEADFASTNESS_STATE_KEY:
            hp_bonus = max(0, int(payload.get("hp_bonus", 0) or 0))
            if hp_bonus > 0 and hasattr(actor, "db"):
                current_hp = int(getattr(actor.db, "hp", 0) or 0)
                base_max_hp = int(getattr(actor.db, "max_hp", 0) or 0)
                berserk_bonus = int(getattr(actor, "get_barbarian_berserk_hp_bonus", lambda: 0)() or 0)
                actor.db.hp = max(0, min(base_max_hp + berserk_bonus, current_hp - hp_bonus))
        if state_key == cls.BLOODTHIRST_STATE_KEY:
            fatigue_cost = max(0, int(payload.get("fatigue_cost", 0) or 0))
            if fatigue_cost > 0 and hasattr(actor, "db"):
                current = int(getattr(actor.db, "fatigue", 0) or 0)
                maximum = int(getattr(actor.db, "max_fatigue", current) or current)
                actor.db.fatigue = max(0, min(maximum, current + fatigue_cost))
        if callable(clearer):
            clearer(state_key)
        return None

    @classmethod
    def get_defense_penalty(cls, actor, defense_name: str) -> int:
        normalized = str(defense_name or "").strip().lower()
        total = 0
        for state_key in ("barbarian_roar_everild", cls.SUPERIORITY_STATE_KEY):
            payload = cls._clean_target_effect(actor, state_key)
            if not isinstance(payload, Mapping):
                continue
            penalties = dict(payload.get("penalties") or {})
            total += int(penalties.get(normalized, 0) or 0)
        return total

    @classmethod
    def get_stun_susceptibility(cls, actor) -> int:
        payload = cls._clean_target_effect(actor, "barbarian_roar_kuniyo")
        if not isinstance(payload, Mapping):
            return 0
        return max(0, int(payload.get("stun_vulnerability_pct", 0) or 0))

    @classmethod
    def get_stun_resistance_bonus(cls, actor) -> int:
        payload = cls._get_penalty_payload(actor, cls.VENGEANCE_STATE_KEY)
        return max(0, int(payload.get("stun_resistance_pct", 0) or 0))

    @classmethod
    def get_temp_hp_bonus(cls, actor) -> int:
        payload = cls._get_penalty_payload(actor, cls.STEADFASTNESS_STATE_KEY)
        return max(0, int(payload.get("hp_bonus", 0) or 0))

    @classmethod
    def _get_penalty_payload(cls, actor, state_key: str):
        payload = cls._clean_target_effect(actor, state_key)
        if not isinstance(payload, Mapping):
            return {}
        return dict(payload)

    @classmethod
    def get_stat_modifier(cls, actor, stat_name: str) -> int:
        normalized = str(stat_name or "").strip().lower()
        total = 0
        for state_key in (cls.TROTHFANG_STATE_KEY, cls.HONOR_STATE_KEY, cls.PRIDE_STATE_KEY, cls.BLOODTHIRST_STATE_KEY):
            payload = cls._get_penalty_payload(actor, state_key)
            modifiers = dict(payload.get("stat_modifiers") or {})
            total += int(modifiers.get(normalized, 0) or 0)
        return total

    @classmethod
    def get_offense_penalty(cls, actor, penalty_name: str) -> int:
        normalized = str(penalty_name or "").strip().lower()
        total = 0
        for state_key in (cls.TEMPESTUOUS_STATE_KEY, cls.EMBRACE_STATE_KEY, cls.BLOODTHIRST_STATE_KEY):
            payload = cls._get_penalty_payload(actor, state_key)
            penalties = dict(payload.get("penalties") or {})
            total += int(penalties.get(normalized, 0) or 0)
        return total

    @classmethod
    def get_skill_modifier(cls, actor, skill_name: str) -> int:
        normalized = str(skill_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        total = 0
        for state_key in (cls.MAGICS_BANE_STATE_KEY, cls.SLASH_SHADOWS_STATE_KEY, cls.NOBILITY_STATE_KEY, cls.BLOODTHIRST_STATE_KEY):
            payload = cls._get_penalty_payload(actor, state_key)
            modifiers = dict(payload.get("skill_modifiers") or {})
            total += int(modifiers.get(normalized, 0) or 0)
        return total

    @classmethod
    def get_magic_penalty(cls, actor, modifier_name: str) -> int:
        normalized = str(modifier_name or "").strip().lower().replace("-", "_").replace(" ", "_")
        total = 0
        for state_key in (cls.MAGICS_BANE_STATE_KEY, cls.MAGES_LAMENT_STATE_KEY):
            payload = cls._get_penalty_payload(actor, state_key)
            penalties = dict(payload.get("modifiers") or {})
            total += int(penalties.get(normalized, 0) or 0)
        return max(0, total)

    @classmethod
    def get_fear_amplification(cls, actor) -> int:
        payload = cls._get_penalty_payload(actor, cls.SCREECH_STATE_KEY)
        return max(0, int(payload.get("fear_amplification_pct", 0) or 0))

    @classmethod
    def get_fear_resistance(cls, actor) -> int:
        payload = cls._get_penalty_payload(actor, cls.BRAVERY_STATE_KEY)
        return max(0, int(payload.get("fear_resistance_pct", 0) or 0))

    @classmethod
    def is_immobilized(cls, actor) -> bool:
        return bool(cls._get_penalty_payload(actor, cls.BANSHEE_STATE_KEY))

    @classmethod
    def get_attack_roundtime_penalty(cls, actor) -> float:
        total = 0.0
        for state_key in (cls.INSANE_LAUGHTER_STATE_KEY, cls.PRIDE_STATE_KEY):
            payload = cls._get_penalty_payload(actor, state_key)
            total += float(payload.get("attack_roundtime_penalty", 0.0) or 0.0)
        return total

    @classmethod
    def get_balance_recovery_penalty(cls, actor) -> int:
        payload = cls._get_penalty_payload(actor, cls.ANGER_EARTH_STATE_KEY)
        return max(0, int(payload.get("balance_recovery_penalty", 0) or 0))

    @classmethod
    def get_forced_return_block(cls, actor):
        payload = cls._get_penalty_payload(actor, cls.SERPENT_HISS_STATE_KEY)
        return payload if payload else {}

    @classmethod
    def get_stat(cls, actor, name):
        get_stat = getattr(actor, "get_stat", None)
        if callable(get_stat):
            return int(get_stat(name) or 0)
        stats = dict(getattr(getattr(actor, "db", None), "stats", {}) or {})
        return int(stats.get(str(name or "").strip().lower(), 0) or 0)

    @classmethod
    def calculate_margin(cls, actor, target, *, style: str, modifier: int, randomizer=None) -> int:
        rng = randomizer or (lambda low, high: 0)
        modifier = int((int(modifier or 100) * cls.get_roar_power_modifier(actor, "intimidation")) / 100)
        attacker_power = int((cls.get_stat(actor, "discipline") + cls.get_stat(actor, "charisma")) / 2)
        attacker_power += int(cls.get_stat(actor, "strength") / 3)
        attacker_power += int(cls._get_circle(actor) / 2)
        target_resist = int((cls.get_stat(target, "discipline") + cls.get_stat(target, "reflex")) / 2)
        target_resist += int(getattr(getattr(target, "db", None), "mm", 0) or 0)
        if style == "everild":
            target_resist += int((cls.get_stat(target, "agility") + cls.get_stat(target, "strength")) / 5)
        margin = int((attacker_power * int(modifier or 100)) / 100) - target_resist + int(rng(-5, 10))
        return margin

    @classmethod
    def _resolve_targets(cls, actor):
        targets = []
        target = actor.get_target() if hasattr(actor, "get_target") else None
        if target is not None and getattr(target, "location", None) == getattr(actor, "location", None):
            targets.append(target)
        elif getattr(actor, "location", None) is not None:
            for obj in list(getattr(actor.location, "contents", []) or []):
                if obj == actor or getattr(obj, "location", None) != actor.location:
                    continue
                if bool(getattr(getattr(obj, "db", None), "is_npc", False)):
                    targets.append(obj)
        seen = set()
        unique = []
        for obj in targets:
            obj_id = getattr(obj, "id", id(obj))
            if obj_id in seen:
                continue
            seen.add(obj_id)
            unique.append(obj)
        return unique

    @classmethod
    def can_roar(cls, actor, roar_name: str | None = None):
        cls.ensure_kuniyo_auto_learned(actor)
        if not cls._is_barbarian(actor):
            return ActionResult.fail(errors=["You are not following the Barbarian path."])
        room = getattr(actor, "location", None)
        if cls._room_has_flag(room, "silenced"):
            return ActionResult.fail(errors=["Disturbing the silence of this area would be both foolish and rude."])
        if cls._room_has_flag(room, "safehaven"):
            return ActionResult.fail(errors=["Disturbing the peace of this area would be both foolish and rude."])
        position = str(getattr(getattr(actor, "db", None), "position", "standing") or "standing").strip().lower()
        if position in {"sitting", "prone", "kneeling"}:
            actor.db.position = "standing"
            return ActionResult.fail(messages=["You release a roar of frustration as you attempt to regain your footing."])
        if bool(getattr(getattr(actor, "db", None), "nonexist", False)) or bool(getattr(getattr(actor, "db", None), "invisible", False)):
            return ActionResult.fail(errors=["The metaphysical conundrum your current state of existence presents makes roaring impossible.  It's just not natural!"])
        if cls._is_droughtmans_maze(room):
            return ActionResult.fail(errors=["Something prevents you from doing that."])
        if not roar_name:
            return ActionResult.ok(data=VocalDamageService.get_exhaustion_tier(actor))
        definition = get_roar_definition(roar_name)
        if definition is None:
            return ActionResult.fail(errors=["Have patience.  The preview will include all roars and battle cries, but not all right away."])
        if not cls.has_known_roar_bit(actor, definition.bit_index):
            return ActionResult.fail(errors=["You have not received the proper instruction in that technique."])
        return ActionResult.ok(data={"definition": definition})

    @classmethod
    def invoke(cls, actor, roar_name: str | None = None, *, randomizer=None):
        check = cls.can_roar(actor, roar_name)
        if not check.success:
            return check
        if not roar_name:
            return ActionResult.ok(messages=[check.data.get("message", "You feel ready to defeat an army!")], data=check.data)

        definition = check.data["definition"]
        vocal_profile = VocalDamageService.get_total_vocal_damage(actor)
        vocal_gate = definition.vocal_damage_check(actor, vocal_profile)
        if not vocal_gate.success:
            return vocal_gate
        definition.add_vocal_damage(actor, VocalDamageService)
        targets = cls._resolve_recipients(actor, definition)
        result = definition.begin_roar(actor, targets, cls, vocal_profile=vocal_profile, randomizer=randomizer)
        if result.success:
            duration = 0
            target_names = list(result.data.get("targets", []) or [])
            if target_names:
                duration = max(duration, 15)
            cls._update_active_roar(
                actor,
                definition,
                {
                    "display_name": definition.canonical_display_name,
                    "expires_at": cls.now() + duration if duration else cls.now() + 15,
                    "targets": target_names,
                },
            )
        return result