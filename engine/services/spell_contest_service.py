from engine.services.result import ActionResult
from engine.services.state_service import StateService


class SpellContestService:
    @staticmethod
    def _resolve_spell_contest(caster, target, final_spell_power, *, primary_skill, defense_skill, defense_stat, exposed_bonus=0, wild_modifier=1.0):
        factor = SpellContestService._get_multi_skill_factor(caster, primary_skill, "attunement")
        effective_power = float(final_spell_power or 0.0) * (0.5 + factor) * float(wild_modifier or 1.0)
        attack_score = effective_power + SpellContestService._get_skill(caster, primary_skill)

        debuff = SpellContestService._get_state(caster, "debilitated")
        if debuff and str(debuff.get("type", "accuracy") or "accuracy") in {"accuracy", "offense"}:
            attack_score -= int(debuff.get("penalty", 0) or 0)
        attack_score -= SpellContestService._get_effect_modifier(caster, "magic_attack")
        attack_score += SpellContestService._get_augmentation_modifier(caster, "magic_attack")
        if exposed_bonus > 0 and SpellContestService._get_state(target, "exposed_magic"):
            attack_score += int(exposed_bonus)

        defense_score = SpellContestService._get_skill(target, defense_skill) + SpellContestService._get_stat(target, defense_stat, 10)
        target_debuff = SpellContestService._get_state(target, "debilitated")
        if target_debuff and target_debuff.get("type") == defense_skill:
            defense_score -= int(target_debuff.get("penalty", 0) or 0)
        defense_score -= SpellContestService._get_effect_modifier(target, "magic_defense")
        defense_score += SpellContestService._get_augmentation_modifier(target, "magic_defense")

        setattr(target, "incoming_attackers", getattr(target, "incoming_attackers", 0) + 1)
        attackers = getattr(target, "incoming_attackers", 1)
        pressure_penalty = int(attackers ** 0.5)
        defense_score = max(1.0, float(defense_score) - float(pressure_penalty))

        contest_margin = float(attack_score) - float(defense_score)
        hit_quality = SpellContestService._resolve_hit_quality(caster, attack_score, defense_score)
        hit = hit_quality != "miss"
        return {
            "effective_power": float(effective_power),
            "attack_score": float(attack_score),
            "defense_score": float(defense_score),
            "contest_margin": float(contest_margin),
            "hit_quality": hit_quality,
            "hit": bool(hit),
        }

    @staticmethod
    def resolve_targeted_magic(caster, target, final_spell_power, spell_id=None, quality="normal", wild_modifier=1.0):
        if target is None or target == caster:
            return ActionResult.fail(
                errors=["You need a valid target for that spell."],
                data={"reason": "invalid_target", "effect_family": "targeted_magic"},
            )
        if not hasattr(target, "set_hp") or getattr(getattr(target, "db", None), "hp", None) is None:
            return ActionResult.fail(
                errors=["That is not a valid target for this spell."],
                data={"reason": "invalid_target", "effect_family": "targeted_magic"},
            )

        contest = SpellContestService._resolve_spell_contest(
            caster,
            target,
            final_spell_power,
            primary_skill="targeted_magic",
            defense_skill="evasion",
            defense_stat="reflex",
            exposed_bonus=5,
            wild_modifier=wild_modifier,
        )
        attack_score = float(contest["attack_score"])
        defense_score = float(contest["defense_score"])
        contest_margin = float(contest["contest_margin"])
        hit_quality = str(contest["hit_quality"])
        hit = bool(contest["hit"])
        effective_power = float(contest["effective_power"])

        if hasattr(caster, "award_skill_experience"):
            caster.award_skill_experience("targeted_magic", max(10, int(defense_score)), success=hit)
        if hasattr(target, "award_skill_experience"):
            target.award_skill_experience("evasion", max(10, int(attack_score)), success=not hit)

        if not hit:
            trace_payload = SpellContestService._record_targeted_magic_trace(
                caster,
                spell_id=spell_id,
                target=target,
                hit=False,
                contest_margin=float(contest_margin),
                base_damage=0.0,
                absorbed=0.0,
                final_damage=0.0,
            )
            return ActionResult.ok(
                data={
                    "effect_family": "targeted_magic",
                    "hit": False,
                    "hit_quality": "miss",
                    "attack_score": float(attack_score),
                    "defense_score": float(defense_score),
                    "contest_margin": float(contest_margin),
                    "base_damage": 0.0,
                    "final_damage": 0.0,
                    "absorbed_by_ward": 0.0,
                    "target_id": getattr(target, "id", None),
                    "target_key": getattr(target, "key", "someone"),
                    "debug_trace": trace_payload,
                }
            )

        multiplier = {"graze": 0.5, "hit": 1.0, "strong": 1.5}[hit_quality]
        if str(quality or "normal").strip().lower() == "weak":
            multiplier *= 0.75
        elif str(quality or "normal").strip().lower() == "strong":
            multiplier *= 1.25

        raw_damage = max(1, int(effective_power * multiplier / 3.0))
        resisted_damage = SpellContestService._apply_magic_resistance(target, raw_damage)
        warded_damage = SpellContestService._apply_ward_absorption(caster, target, resisted_damage)
        absorbed_by_ward = max(0, int(resisted_damage) - int(warded_damage))

        damage_result = ActionResult.ok(data={"amount": 0})
        if int(warded_damage or 0) > 0:
            # RULE:
            # HP mutation is owned by StateService when damage gets through.
            damage_result = StateService.apply_damage(target, int(warded_damage), location="chest", damage_type="impact")

        trace_payload = SpellContestService._record_targeted_magic_trace(
            caster,
            spell_id=spell_id,
            target=target,
            hit=True,
            contest_margin=float(contest_margin),
            base_damage=float(int(resisted_damage or 0)),
            absorbed=float(absorbed_by_ward),
            final_damage=float(int(warded_damage or 0)),
        )

        return ActionResult.ok(
            data={
                "effect_family": "targeted_magic",
                "hit": True,
                "hit_quality": hit_quality,
                "attack_score": float(attack_score),
                "defense_score": float(defense_score),
                "contest_margin": float(contest_margin),
                "base_damage": float(int(resisted_damage or 0)),
                "final_damage": float(int(warded_damage or 0)),
                "absorbed_by_ward": float(absorbed_by_ward),
                "target_id": getattr(target, "id", None),
                "target_key": getattr(target, "key", "someone"),
                "injury_events": list((damage_result.data or {}).get("injury_events", []) or []),
                "debug_trace": trace_payload,
            }
        )

    @staticmethod
    def resolve_debilitation(caster, target, final_spell_power, *, effect_profile=None, spell_id=None, quality="normal", wild_modifier=1.0):
        if target is None or target == caster:
            return ActionResult.fail(
                errors=["You need a valid target for that spell."],
                data={"reason": "invalid_target", "effect_family": "debilitation"},
            )
        if not hasattr(target, "get_state") or not hasattr(target, "set_state"):
            return ActionResult.fail(
                errors=["That is not a valid target for this spell."],
                data={"reason": "invalid_target", "effect_family": "debilitation"},
            )

        contest = SpellContestService._resolve_spell_contest(
            caster,
            target,
            final_spell_power,
            primary_skill="debilitation",
            defense_skill="warding",
            defense_stat="discipline",
            exposed_bonus=0,
            wild_modifier=wild_modifier,
        )
        attack_score = float(contest["attack_score"])
        defense_score = float(contest["defense_score"]) + float(SpellContestService._get_magic_resistance(target))
        contest_margin = float(attack_score) - float(defense_score)
        hit_quality = SpellContestService._resolve_hit_quality(caster, attack_score, defense_score)
        hit = hit_quality != "miss"

        if hasattr(caster, "award_skill_experience"):
            caster.award_skill_experience("debilitation", max(10, int(defense_score)), success=hit)
        if hasattr(target, "award_skill_experience"):
            target.award_skill_experience("warding", max(10, int(attack_score)), success=not hit)

        if not hit:
            trace_payload = SpellContestService._record_debilitation_trace(
                caster,
                spell_id=spell_id,
                effect_type=str(dict(effect_profile or {}).get("effect_type", "debilitation") or "debilitation"),
                contest_margin=float(contest_margin),
                strength=0.0,
                duration=0.0,
            )
            return ActionResult.ok(
                data={
                    "effect_family": "debilitation",
                    "effect_type": str(dict(effect_profile or {}).get("effect_type", "debilitation") or "debilitation"),
                    "hit": False,
                    "hit_quality": "miss",
                    "attack_score": float(attack_score),
                    "defense_score": float(defense_score),
                    "contest_margin": float(contest_margin),
                    "strength": 0.0,
                    "duration": 0.0,
                    "target_id": getattr(target, "id", None),
                    "target_key": getattr(target, "key", "someone"),
                    "debug_trace": trace_payload,
                }
            )

        profile = dict(effect_profile or {})
        effect_type = str(profile.get("effect_type", "debilitation") or "debilitation").strip().lower().replace(" ", "_")
        base_strength = max(1.0, float(profile.get("base_strength", 1.0) or 1.0))
        strength_scale = max(0.0, float(profile.get("strength_scale", 0.05) or 0.05))
        base_duration = max(1.0, float(profile.get("base_duration", 4.0) or 4.0))
        duration_scale = max(0.0, float(profile.get("duration_scale", 0.5) or 0.5))
        strength = max(1, int(base_strength + max(0.0, contest_margin) * strength_scale))
        if str(quality or "normal").strip().lower() == "strong":
            strength += 1
        elif str(quality or "normal").strip().lower() == "weak":
            strength = max(1, strength - 1)
        duration = max(1, int(round(base_duration + strength * duration_scale)))
        apply_result = StateService.apply_debilitation_effect(
            target,
            effect_type,
            strength,
            duration,
            applied_by=getattr(caster, "id", None),
            contest_margin=float(contest_margin),
            source_spell=spell_id,
            modifiers=dict(profile.get("contest_modifiers") or {}),
        )
        effect_data = dict((apply_result.data or {}).get("effect") or {})
        trace_payload = SpellContestService._record_debilitation_trace(
            caster,
            spell_id=spell_id,
            effect_type=effect_type,
            contest_margin=float(contest_margin),
            strength=float(int(effect_data.get("strength", strength) or strength)),
            duration=float(int(effect_data.get("duration", duration) or duration)),
        )
        return ActionResult.ok(
            data={
                "effect_family": "debilitation",
                "effect_type": effect_type,
                "hit": True,
                "hit_quality": hit_quality,
                "attack_score": float(attack_score),
                "defense_score": float(defense_score),
                "contest_margin": float(contest_margin),
                "strength": float(int(effect_data.get("strength", strength) or strength)),
                "duration": float(int(effect_data.get("duration", duration) or duration)),
                "applied": bool((apply_result.data or {}).get("applied", False)),
                "replaced": bool((apply_result.data or {}).get("replaced", False)),
                "ignored": bool((apply_result.data or {}).get("ignored", False)),
                "target_id": getattr(target, "id", None),
                "target_key": getattr(target, "key", "someone"),
                "debug_trace": trace_payload,
            }
        )

    @staticmethod
    def resolve_cyclic_application(caster, target, final_spell_power, *, effect_profile=None, spell_id=None, quality="normal", wild_modifier=1.0):
        profile = dict(effect_profile or {})
        if target is None or target == caster:
            return ActionResult.fail(
                errors=["You need a valid target for that spell."],
                data={"reason": "invalid_target", "effect_family": "cyclic"},
            )
        if not hasattr(target, "get_state"):
            return ActionResult.fail(
                errors=["That is not a valid target for this spell."],
                data={"reason": "invalid_target", "effect_family": "cyclic"},
            )

        contest = SpellContestService._resolve_spell_contest(
            caster,
            target,
            final_spell_power,
            primary_skill=str(profile.get("contest_primary_skill", "debilitation") or "debilitation"),
            defense_skill=str(profile.get("contest_defense_skill", "warding") or "warding"),
            defense_stat=str(profile.get("contest_defense_stat", "discipline") or "discipline"),
            exposed_bonus=0,
            wild_modifier=wild_modifier,
        )
        attack_score = float(contest["attack_score"])
        defense_score = float(contest["defense_score"])
        if bool(profile.get("include_magic_resistance", False)):
            defense_score += float(SpellContestService._get_magic_resistance(target))
        contest_margin = float(attack_score) - float(defense_score)
        hit_quality = SpellContestService._resolve_hit_quality(caster, attack_score, defense_score)
        hit = hit_quality != "miss"
        return ActionResult.ok(
            data={
                "effect_family": "cyclic",
                "hit": bool(hit),
                "hit_quality": "miss" if not hit else hit_quality,
                "attack_score": float(attack_score),
                "defense_score": float(defense_score),
                "contest_margin": float(contest_margin),
                "target_id": getattr(target, "id", None),
                "target_key": getattr(target, "key", "someone"),
                "spell_id": spell_id,
            }
        )

    @staticmethod
    def _record_targeted_magic_trace(caster, *, spell_id, target, hit, contest_margin, base_damage, absorbed, final_damage):
        if not SpellContestService._targeted_magic_trace_enabled(caster):
            return None
        trace_payload = {
            "spell_id": spell_id,
            "hit": bool(hit),
            "contest_margin": float(contest_margin),
            "base_damage": float(base_damage),
            "absorbed": float(absorbed),
            "final_damage": float(final_damage),
            "target_id": getattr(target, "id", None),
            "target_key": getattr(target, "key", "someone"),
        }
        ndb = getattr(caster, "ndb", None)
        entries = list(getattr(ndb, "spell_debug_trace", []) or [])
        entries.append(trace_payload)
        ndb.spell_debug_trace = entries[-100:]
        return dict(trace_payload)

    @staticmethod
    def _record_debilitation_trace(caster, *, spell_id, effect_type, contest_margin, strength, duration):
        if not SpellContestService._targeted_magic_trace_enabled(caster):
            return None
        trace_payload = {
            "spell_id": spell_id,
            "effect_type": str(effect_type or "debilitation"),
            "contest_margin": float(contest_margin),
            "strength": float(strength),
            "duration": float(duration),
        }
        ndb = getattr(caster, "ndb", None)
        entries = list(getattr(ndb, "spell_debug_trace", []) or [])
        entries.append(trace_payload)
        ndb.spell_debug_trace = entries[-100:]
        return dict(trace_payload)

    @staticmethod
    def _targeted_magic_trace_enabled(caster):
        ndb = getattr(caster, "ndb", None)
        return ndb is not None and bool(getattr(ndb, "spell_debug", False))

    @staticmethod
    def _get_skill(character, skill_name):
        getter = getattr(character, "get_skill", None)
        if callable(getter):
            return max(0, int(getter(skill_name) or 0))
        return 0

    @staticmethod
    def _get_state(character, state_name):
        getter = getattr(character, "get_state", None)
        if callable(getter):
            return getter(state_name)
        return None

    @staticmethod
    def _get_effect_modifier(character, modifier_key):
        getter = getattr(character, "get_effect_modifier", None)
        if callable(getter):
            return max(0, int(getter(modifier_key) or 0))
        return 0

    @staticmethod
    def _get_augmentation_modifier(character, modifier_key):
        buff = SpellContestService._get_state(character, "augmentation_buff")
        if not isinstance(buff, dict):
            return 0
        modifiers = dict(buff.get("modifiers") or {})
        scale = float(modifiers.get(str(modifier_key or "").strip().lower().replace(" ", "_"), 0.0) or 0.0)
        if scale <= 0.0:
            return 0
        return max(0, int(round(float(buff.get("strength", 0) or 0) * scale)))

    @staticmethod
    def _get_stat(character, stat_name, default=10):
        getter = getattr(character, "get_stat", None)
        if callable(getter):
            return int(getter(stat_name) or default)
        stats = getattr(getattr(character, "db", None), "stats", None) or {}
        return int(stats.get(stat_name, default) or default)

    @staticmethod
    def _get_magic_resistance(character):
        getter = getattr(character, "get_magic_resistance", None)
        if callable(getter):
            return int(getter() or 0)
        stats = getattr(getattr(character, "db", None), "stats", None) or {}
        return int(stats.get("magic_resistance", 0) or 0)

    @staticmethod
    def _get_multi_skill_factor(character, primary, secondary):
        getter = getattr(character, "get_multi_skill_factor", None)
        if callable(getter):
            return float(getter(primary, secondary) or 0.0)
        primary_skill = SpellContestService._get_skill(character, primary)
        secondary_skill = SpellContestService._get_skill(character, secondary)
        return min(primary_skill, secondary_skill) / max(1, max(primary_skill, secondary_skill))

    @staticmethod
    def _resolve_hit_quality(caster, offense, defense):
        resolver = getattr(caster, "resolve_hit_quality", None)
        if callable(resolver):
            return resolver(offense, defense)
        ratio = float(offense) / max(1.0, float(defense))
        if ratio < 0.5:
            return "miss"
        if ratio < 0.8:
            return "graze"
        if ratio < 1.2:
            return "hit"
        return "strong"

    @staticmethod
    def _apply_magic_resistance(target, damage):
        applier = getattr(target, "apply_magic_resistance", None)
        if callable(applier):
            return max(0, int(applier(damage)))
        return max(0, int(damage or 0))

    @staticmethod
    def _apply_ward_absorption(caster, target, damage):
        applier = getattr(caster, "apply_ward_absorption", None)
        if callable(applier):
            return max(0, int(applier(target, damage) or 0))
        return max(0, int(damage or 0))