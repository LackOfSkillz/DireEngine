from collections.abc import Mapping
import random
import time

from engine.services.combat_xp import CombatXP
from engine.services.result import ActionResult
from engine.services.state_service import StateService
from engine.services.stealth_service import StealthService
from domain.combat.resolution import resolve_attack
from world.systems.ranger import RANGER_SNIPE_CONFIG


class CombatService:

    @staticmethod
    def attack(attacker, target):
        validation = CombatService._validate_attack(attacker, target)
        if validation is not None:
            return validation

        preflight = CombatService._prepare_attack(attacker, target)
        if not preflight.success:
            return preflight

        context = CombatService._build_context(attacker, target)
        resolution = resolve_attack(attacker, target, context=context)
        details = dict(resolution.details or {})

        damage_result = ActionResult.ok(data={"amount": 0})
        if resolution.hit:
            attack_context = dict(details.get("attack_context", {}) or {})
            damage_result = StateService.apply_damage(
                target,
                resolution.damage,
                location=details.get("hit_location"),
                damage_type=attack_context.get("damage_type", "impact"),
                critical=bool(details.get("critical", False)),
            )

        CombatService._apply_post_resolution_state(attacker, target, details, resolution.hit)
        CombatXP.award(attacker, target, details, resolution.hit)
        StateService.apply_fatigue(attacker, int(details.get("fatigue_cost", 0) or 0))
        StateService.apply_roundtime(attacker, resolution.roundtime, ambush=bool(details.get("ambush")))

        payload = CombatService._build_result_payload(attacker, target, details, resolution, damage_result)
        return ActionResult.ok(data=payload)

    @staticmethod
    def _validate_attack(attacker, target):
        if attacker.is_stunned():
            attacker.consume_stun()
            return ActionResult.fail(data={"error_code": "stunned", "outcome": "blocked"})

        if attacker.is_in_roundtime():
            return ActionResult.fail(data={"error_code": "roundtime", "outcome": "blocked"})

        balance, _ = attacker.get_balance()
        if balance <= 0:
            return ActionResult.fail(data={"error_code": "off_balance", "outcome": "blocked"})

        if not attacker.is_alive():
            return ActionResult.fail(data={"error_code": "attacker_dead", "outcome": "blocked"})

        if target is None:
            return ActionResult.fail(data={"error_code": "no_target", "outcome": "blocked"})

        if target == attacker:
            return ActionResult.fail(data={"error_code": "self_attack", "outcome": "blocked"})

        if getattr(getattr(target, "db", None), "is_corpse", False):
            return ActionResult.fail(data={"error_code": "corpse_target", "outcome": "blocked", "target_name": getattr(target, "key", "someone")})

        if not hasattr(target, "set_hp") or getattr(target.db, "hp", None) is None:
            return ActionResult.fail(data={"error_code": "invalid_target", "outcome": "blocked", "target_name": getattr(target, "key", "someone")})

        if not target.is_alive():
            return ActionResult.fail(data={"error_code": "target_dead", "outcome": "blocked", "target_name": getattr(target, "key", "someone")})

        if CombatService._is_player_character(attacker) and CombatService._is_gm_character(target):
            target_target = target.get_target() if hasattr(target, "get_target") else None
            if target_target != attacker:
                return ActionResult.fail(data={"error_code": "gm_protected", "outcome": "blocked"})

        try:
            from systems import onboarding

            block_message = onboarding.get_attack_block(attacker, target)
            if block_message:
                return ActionResult.fail(data={"error_code": "blocked", "block_message": block_message, "outcome": "blocked"})
            if onboarding.resolve_training_attack(attacker, target):
                return ActionResult.ok(data={"outcome": "handled"})
        except Exception:
            pass

        return None

    @staticmethod
    def _prepare_attack(attacker, target):
        if hasattr(attacker, "maybe_msg_death_sting_combat_feedback"):
            attacker.maybe_msg_death_sting_combat_feedback()

        if getattr(attacker.db, "disguised", False) and hasattr(attacker, "clear_disguise"):
            attacker.clear_disguise()

        if hasattr(attacker, "get_collapse_chance") and random.random() < attacker.get_collapse_chance():
            attacker.db.position = "kneeling"
            if hasattr(attacker, "break_combat_rhythm"):
                attacker.break_combat_rhythm(show_message=False)
            StateService.apply_roundtime(attacker, 3)
            return ActionResult.fail(
                data={
                    "error_code": "collapse",
                    "outcome": "blocked",
                    "target_name": getattr(target, "key", "someone"),
                    "attacker_name": getattr(attacker, "key", "Someone"),
                }
            )

        if hasattr(attacker, "get_pressure_hesitation_chance") and random.random() < attacker.get_pressure_hesitation_chance():
            StateService.apply_roundtime(attacker, 1.5)
            return ActionResult.fail(data={"error_code": "hesitation", "outcome": "blocked"})

        if hasattr(attacker, "get_overextended_action_delay_chance") and random.random() < attacker.get_overextended_action_delay_chance():
            StateService.apply_roundtime(attacker, 2)
            return ActionResult.fail(data={"error_code": "overextended", "outcome": "blocked"})

        attacker.set_target(target)
        target.set_target(attacker)

        weapon = attacker.get_wielded_weapon() if hasattr(attacker, "get_wielded_weapon") else attacker.get_weapon()
        profile = attacker.get_weapon_profile()
        current_range = attacker.get_range(target)
        weapon_range_type = str(profile.get("weapon_range_type") or "").strip().lower()
        is_ranged_weapon = bool(weapon and (getattr(weapon.db, "is_ranged", False) or weapon_range_type))
        ammo_state = attacker.get_equipped_ammo_state() if hasattr(attacker, "get_equipped_ammo_state") else None
        if is_ranged_weapon and (not ammo_state or not ammo_state.get("loaded")):
            return ActionResult.fail(data={"error_code": "needs_ammo", "outcome": "blocked"})
        if not is_ranged_weapon and current_range != "melee":
            return ActionResult.fail(data={"error_code": "too_far_melee", "outcome": "blocked"})

        if hasattr(attacker, "register_empath_offensive_action"):
            attacker.register_empath_offensive_action(target=target, context="attack", amount=15)
        if hasattr(target, "check_room_traps_for_enemy"):
            target.check_room_traps_for_enemy(attacker)

        try:
            from systems import onboarding

            onboarding.note_combat_start(attacker, target)
            if str(getattr(getattr(target, "db", None), "onboarding_enemy_role", "") or "").lower() == "breach":
                onboarding.note_breach_progress(attacker, "start")
        except Exception:
            pass

        return ActionResult.ok(data={"outcome": "ready"})

    @staticmethod
    def _build_context(attacker, target):
        weapon = attacker.get_wielded_weapon() if hasattr(attacker, "get_wielded_weapon") else attacker.get_weapon()
        profile = attacker.get_weapon_profile()
        current_range = attacker.get_range(target)
        weapon_range_type = str(profile.get("weapon_range_type") or "").strip().lower()
        is_ranged_weapon = bool(weapon and (getattr(weapon.db, "is_ranged", False) or weapon_range_type))
        ranger_snipe = attacker.get_state("ranger_snipe") if hasattr(attacker, "get_state") else None
        ranger_aim_stacks = attacker.get_ranger_aim_stacks(target) if hasattr(attacker, "get_ranger_aim_stacks") else 0
        ranger_mark = target.get_ranger_mark_effect_on() if hasattr(target, "get_ranger_mark_effect_on") else None
        snipe_active = isinstance(ranger_snipe, Mapping) and ranger_snipe.get("target_id") == target.id

        ambush_context = CombatService._resolve_ambush(attacker, target)
        if ambush_context.get("failed"):
            return ambush_context

        skill_name = profile.get("skill", "brawling")
        surge_state = attacker.get_state("warrior_surge") if hasattr(attacker, "get_state") else None
        crush_state = attacker.get_state("warrior_crush") if hasattr(attacker, "get_state") else None
        press_state = attacker.get_state("warrior_press") if hasattr(attacker, "get_state") else None
        sweep_state = attacker.get_state("warrior_sweep") if hasattr(attacker, "get_state") else None
        whirl_state = attacker.get_state("warrior_whirl") if hasattr(attacker, "get_state") else None
        frenzy_state = attacker.get_state("warrior_frenzy") if hasattr(attacker, "get_state") else None
        hold_state = target.get_state("warrior_hold") if hasattr(target, "get_state") else None
        attacker_tempo_state = attacker.get_war_tempo_state() if hasattr(attacker, "get_war_tempo_state") else "calm"
        defender_tempo_state = target.get_war_tempo_state() if hasattr(target, "get_war_tempo_state") else "calm"
        attacker_berserk = attacker.get_active_warrior_berserk() if hasattr(attacker, "get_active_warrior_berserk") else None
        defender_berserk = target.get_active_warrior_berserk() if hasattr(target, "get_active_warrior_berserk") else None
        attacker_roars = attacker.get_active_warrior_roars() if hasattr(attacker, "get_active_warrior_roars") else {}
        defender_roars = target.get_active_warrior_roars() if hasattr(target, "get_active_warrior_roars") else {}
        attacker_disrupt = attacker.get_warrior_roar_effect("disrupt") if hasattr(attacker, "get_warrior_roar_effect") else None
        attacker_unnerving = attacker.get_warrior_roar_effect("unnerving") if hasattr(attacker, "get_warrior_roar_effect") else None
        attacker_intimidate = attacker.get_warrior_roar_effect("intimidate") if hasattr(attacker, "get_warrior_roar_effect") else None
        weapon_effects = weapon.get_weapon_effects(attacker) if weapon and hasattr(weapon, "get_weapon_effects") else {}
        suitability = weapon.get_weapon_suitability(attacker) if weapon and hasattr(weapon, "get_weapon_suitability") else 0
        fatigue_cost = int(profile["fatigue_cost"])
        if hasattr(attacker, "has_warrior_passive") and attacker.has_warrior_passive("fatigue_reduction_1"):
            fatigue_cost = max(0, int(round(fatigue_cost * 0.9)))
        if frenzy_state:
            fatigue_cost += 1
        if attacker_berserk:
            fatigue_cost += int(attacker_berserk.get("fatigue_cost_bonus", 0) or 0)
        if hasattr(attacker, "get_rhythm_fatigue_discount"):
            fatigue_cost = max(0, fatigue_cost - attacker.get_rhythm_fatigue_discount())
        if hasattr(attacker, "get_exhaustion_fatigue_multiplier"):
            fatigue_cost = max(0, int(round(fatigue_cost * attacker.get_exhaustion_fatigue_multiplier())))

        target.incoming_attackers = getattr(target, "incoming_attackers", 0) + 1
        aimed_location, aimed_part = attacker.resolve_targeted_body_part()
        damage_profile = dict(profile.get("damage_types") or {})
        if not damage_profile:
            fallback_damage_type = (profile.get("damage_type") or "impact").lower()
            damage_profile = {"slice": 0, "impact": 0, "puncture": 0, fallback_damage_type: 1}
        damage_type = max(damage_profile, key=damage_profile.get)
        offensive_roar = attacker_roars.get("offensive") if isinstance(attacker_roars, dict) else None
        weapon_name = getattr(weapon, "key", "") if weapon else ""

        if attacker.is_hidden() and not snipe_active:
            StealthService.break_stealth(attacker)

        attacker.clear_aim()
        return {
            "aimed_location": aimed_location,
            "aimed_part": aimed_part,
            "ambush": bool(ambush_context.get("ambush")),
            "ambush_accuracy_bonus": int(ambush_context.get("ambush_accuracy_bonus", 0) or 0),
            "ambush_announced": bool(ambush_context.get("ambush_announced", False)),
            "ambush_damage_multiplier": float(ambush_context.get("ambush_damage_multiplier", 1.0) or 1.0),
            "ambush_result": ambush_context.get("ambush_result"),
            "attacker_berserk": attacker_berserk,
            "attacker_disrupt": attacker_disrupt,
            "attacker_intimidate": attacker_intimidate,
            "attacker_name": getattr(attacker, "key", "Someone"),
            "attacker_tempo_state": attacker_tempo_state,
            "attacker_unnerving": attacker_unnerving,
            "crush_state": crush_state,
            "current_range": current_range,
            "damage_type": damage_type,
            "defender_berserk": defender_berserk,
            "defender_roars": defender_roars,
            "defender_tempo_state": defender_tempo_state,
            "fatigue_cost": fatigue_cost,
            "frenzy_state": frenzy_state,
            "hold_state": hold_state,
            "is_ranged_weapon": is_ranged_weapon,
            "offensive_roar": offensive_roar,
            "partial_ambush": bool(ambush_context.get("partial_ambush", False)),
            "press_state": press_state,
            "profile": profile,
            "ranger_aim_stacks": ranger_aim_stacks,
            "ranger_mark": ranger_mark,
            "ranger_snipe": ranger_snipe,
            "skill_name": skill_name,
            "snipe_active": snipe_active,
            "snipe_config": dict(RANGER_SNIPE_CONFIG or {}),
            "strong_ambush": bool(ambush_context.get("strong_ambush", False)),
            "suitability": suitability,
            "surge_state": surge_state,
            "sweep_state": sweep_state,
            "target_name": getattr(target, "key", "someone"),
            "weapon": weapon,
            "weapon_effects": weapon_effects,
            "weapon_name": weapon_name,
            "whirl_state": whirl_state,
        }

    @staticmethod
    def _resolve_ambush(attacker, target):
        context = {
            "ambush": False,
            "ambush_accuracy_bonus": 0,
            "ambush_damage_multiplier": 1.0,
            "ambush_announced": False,
            "partial_ambush": False,
            "strong_ambush": False,
            "surprise_reaction": False,
        }
        if not attacker.is_hidden() or not attacker.is_ambushing():
            return context
        if target.id != attacker.get_ambush_target_id():
            return context

        from utils.contests import run_contest

        stealth_total = attacker.get_stealth_total()
        if getattr(attacker.db, "marked_target", None) == target.id:
            stealth_total += 10
        if getattr(attacker.db, "position_state", "neutral") == "advantaged":
            stealth_total += 10
        if "cunning" in (getattr(attacker.db, "khri_active", None) or {}):
            stealth_total += 5
        if attacker.is_stalking() and attacker.get_stalk_target_id() == target.id:
            stealth_total += 10

        ambush_result = run_contest(stealth_total, target.get_perception_total(), attacker=attacker, defender=target)
        if ambush_result["outcome"] == "fail":
            if hasattr(attacker, "set_position_state"):
                attacker.set_position_state("exposed")
            attacker.db.recent_action = True
            attacker.db.recent_action_timer = time.time()
            StealthService.break_stealth(attacker)
            ambush_rt = 3
            if getattr(attacker.db, "position_state", "neutral") == "advantaged":
                ambush_rt -= 1
            ambush_rt = max(1, min(ambush_rt + 1, 5))
            if hasattr(attacker, "record_stealth_contest"):
                attacker.record_stealth_contest(
                    "ambush",
                    max(10, int(target.get_perception_total() or 0)),
                    result=ambush_result,
                    target=target,
                    roundtime=ambush_rt,
                    event_key="stealth",
                    require_hidden=False,
                )
            StateService.apply_roundtime(attacker, ambush_rt, ambush=True)
            return {
                "failed": True,
                "result": ActionResult.fail(data={"error_code": "ambush_no_opening", "outcome": "blocked"}),
            }

        partial_ambush = ambush_result["outcome"] == "partial"
        ambush_accuracy_bonus = 25
        ambush_damage_multiplier = 0.75 if partial_ambush else 1.25
        if attacker.is_stalking() and attacker.get_stalk_target_id() == target.id:
            ambush_accuracy_bonus += 15
            if not partial_ambush:
                ambush_damage_multiplier += 0.15
        if getattr(attacker.db, "marked_target", None) == target.id:
            ambush_damage_multiplier += 0.1
        if "cunning" in (getattr(attacker.db, "khri_active", None) or {}):
            ambush_damage_multiplier += 0.05
        target_awareness = target.get_awareness() if hasattr(target, "get_awareness") else "normal"
        strong_ambush = (not partial_ambush) and target_awareness == "unaware"
        if hasattr(target, "apply_surprise") and target_awareness in {"unaware", "normal"}:
            target.apply_surprise()
        return {
            "ambush": True,
            "ambush_accuracy_bonus": ambush_accuracy_bonus,
            "ambush_announced": True,
            "ambush_damage_multiplier": ambush_damage_multiplier,
            "ambush_result": ambush_result,
            "partial_ambush": partial_ambush,
            "strong_ambush": strong_ambush,
            "surprise_reaction": bool(target_awareness in {"unaware", "normal"}),
        }

    @staticmethod
    def _apply_post_resolution_state(attacker, target, details, hit):
        if not hit:
            CombatService._resolve_snipe_concealment(attacker, target, details, hit=False)
            return

        if details.get("ambush") and not details.get("partial_ambush"):
            target.db.staggered = True
            target.db.stagger_timer = time.time()
            attacker.db.post_ambush_grace = True
            attacker.db.post_ambush_grace_until = time.time() + 2

        if isinstance(details.get("sweep_state"), dict):
            balance_resist = 0
            defender_berserk = details.get("defender_berserk")
            if hasattr(target, "has_warrior_passive") and target.has_warrior_passive("balance_resist_1"):
                balance_resist += 15
            if defender_berserk:
                balance_resist += int(defender_berserk.get("balance_resist_bonus", 0) or 0)
            if balance_resist and random.randint(1, 100) <= min(85, balance_resist):
                details["sweep_resisted"] = True
            else:
                target.db.position = "prone"
                details["sweep_knockdown"] = True

        if isinstance(details.get("whirl_state"), dict):
            details["whirl_momentum"] = True

        if hasattr(target, "set_awareness"):
            prior_awareness = target.get_awareness()
            target.set_awareness("alert")
            details["target_alerted"] = prior_awareness != "alert"

        pressure_gain = 0
        attacker_tempo_state = details.get("attacker_tempo_state")
        if attacker_tempo_state == "building":
            pressure_gain += 2
        elif attacker_tempo_state == "surging":
            pressure_gain += 4
        elif attacker_tempo_state == "frenzied":
            pressure_gain += 6
        if hasattr(attacker, "get_combat_streak") and attacker.get_combat_streak() >= 5:
            pressure_gain += 2
        if isinstance(details.get("offensive_roar"), dict):
            pressure_gain += 2
        if int(details.get("hit_roll", 101) or 101) <= int(details.get("final_chance", 0) or 0):
            pressure_gain += 3
        if pressure_gain and hasattr(target, "add_pressure"):
            target.add_pressure(pressure_gain)

        if hasattr(target, "is_surprised") and target.is_surprised():
            target.clear_surprise()
            details["target_regained_bearings"] = True

        if details.get("weapon_effects", {}).get("flavor"):
            details["weapon_flavor"] = True

        if details.get("aimed_part") == "head" and random.randint(1, 100) < 10:
            target.db.stunned = True
            details["head_stun"] = True

        if details.get("ambush") and hasattr(attacker, "record_stealth_contest") and details.get("ambush_result"):
            attacker.record_stealth_contest(
                "ambush",
                max(10, int(target.get_perception_total() or 0)),
                result=details.get("ambush_result"),
                target=target,
                roundtime=float(details.get("roundtime", 0.0) or 0.0),
                event_key="stealth",
                require_hidden=False,
            )

        if attacker.is_hidden() or bool(getattr(attacker.db, "stealthed", False)):
            StealthService.break_stealth(attacker)

        CombatService._resolve_snipe_concealment(attacker, target, details, hit=True)

        if int(getattr(target.db, "hp", 0) or 0) == 0:
            attacker.set_target(None)
            target.set_target(None)
            details["outcome"] = "kill"
            try:
                from systems import onboarding

                completed, awarded = onboarding.note_combat_win(attacker, target)
                details["onboarding_completed"] = bool(completed)
                details["onboarding_awarded"] = bool(awarded)
                if completed and awarded:
                    details["onboarding_feedback"] = onboarding.format_token_feedback(onboarding.ensure_onboarding_state(attacker))
            except Exception:
                pass

    @staticmethod
    def _resolve_snipe_concealment(attacker, target, details, hit=False):
        if not details.get("snipe_active"):
            return
        bond_bonus = attacker.get_ranger_snipe_retention_bonus() if hasattr(attacker, "get_ranger_snipe_retention_bonus") else 0
        target_awareness = target.get_awareness() if hasattr(target, "get_awareness") else "normal"
        awareness_penalty = {"alert": 20, "normal": 10, "unaware": 0}.get(target_awareness, 10)
        ranger_aim_stacks = int(details.get("ranger_aim_stacks", 0) or 0)
        ranger_snipe = dict(details.get("ranger_snipe") or {})
        chance = 25 + bond_bonus + (ranger_aim_stacks * 8) - awareness_penalty
        chance += int(ranger_snipe.get("stealth_bonus", 0) or 0)
        if hit:
            chance -= 5
        chance = max(5, min(90, chance))
        details["remained_concealed"] = random.randint(1, 100) <= chance
        details["revealed_position"] = not details["remained_concealed"]
        if not details["remained_concealed"]:
            StealthService.break_stealth(attacker)
        if hasattr(attacker, "clear_state"):
            attacker.clear_state("ranger_snipe")

    @staticmethod
    def _build_result_payload(attacker, target, details, resolution, damage_result):
        current_range = str(details.get("current_range", "near") or "near")
        if current_range == "melee":
            range_phrase = "at close range"
        elif current_range == "far":
            range_phrase = "from a distance"
        else:
            range_phrase = "from nearby cover"

        outcome = str(details.get("outcome", "hit" if resolution.hit else "miss") or ("hit" if resolution.hit else "miss"))
        payload = {
            "ambush_announced": bool(details.get("ambush_announced", False)),
            "armor_absorbed": bool(details.get("armor_absorbed", False)),
            "attacker_name": getattr(attacker, "key", "Someone"),
            "critical": bool(details.get("critical", False)),
            "damage": int(damage_result.amount if resolution.hit else 0),
            "damage_type": str(details.get("damage_type", "impact") or "impact"),
            "details": details,
            "error_code": str(details.get("error_code", "") or ""),
            "head_stun": bool(details.get("head_stun", False)),
            "hit": bool(resolution.hit),
            "injury_events": list((damage_result.data or {}).get("injury_events", []) or []),
            "is_ranged_weapon": bool(details.get("is_ranged_weapon", False)),
            "location_name": str(details.get("location_name", "body") or "body"),
            "onboarding_feedback": str(details.get("onboarding_feedback", "") or ""),
            "outcome": outcome,
            "quality": str(details.get("quality", "good") or "good"),
            "range_phrase": range_phrase,
            "remained_concealed": bool(details.get("remained_concealed", False)),
            "revealed_position": bool(details.get("revealed_position", False)),
            "roundtime": float(resolution.roundtime or 0.0),
            "snipe_active": bool(details.get("snipe_active", False)),
            "surprise_reaction": bool(details.get("surprise_reaction", False)),
            "sweep_knockdown": bool(details.get("sweep_knockdown", False)),
            "sweep_resisted": bool(details.get("sweep_resisted", False)),
            "target_alerted": bool(details.get("target_alerted", False)),
            "target_name": getattr(target, "key", "someone"),
            "target_regained_bearings": bool(details.get("target_regained_bearings", False)),
            "weapon_flavor": bool(details.get("weapon_flavor", False)),
            "weapon_name": str(details.get("weapon_name", "") or ""),
            "whirl_momentum": bool(details.get("whirl_momentum", False)),
        }
        return payload

    @staticmethod
    def _is_player_character(obj):
        return bool(obj) and not bool(getattr(obj.db, "is_npc", False))

    @staticmethod
    def _is_gm_character(obj):
        if not obj:
            return False
        if bool(getattr(obj, "is_superuser", False)):
            return True
        if hasattr(obj, "check_permstring") and obj.check_permstring("developer"):
            return True
        account = getattr(obj, "account", None)
        if account and getattr(account, "is_superuser", False):
            return True
        if account and hasattr(account, "check_permstring") and account.check_permstring("developer"):
            return True
        return False