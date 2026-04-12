# ARCHITECTURE RULE:
# Do NOT add new combat logic here.
# All new logic must go through CombatService.

import random
import time
from collections.abc import Mapping

from commands.command import Command
from engine.services.combat_service import CombatService
from world.systems.ranger import RANGER_SNIPE_CONFIG
from world.systems.stealth import break_stealth

from utils.contests import run_contest
from utils.survival_messaging import msg_room, react_or_message_target


VERBS = {
    "slice": ["slash", "cut", "carve"],
    "impact": ["smash", "crush", "slam"],
    "puncture": ["stab", "pierce", "thrust"],
}


def conjugate(verb, is_player):
    if is_player:
        return verb
    if verb.endswith(("s", "sh", "ch", "x", "z")):
        return f"{verb}es"
    if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
        return f"{verb[:-1]}ies"
    return f"{verb}s"


def get_weapon_phrase(weapon):
    if not weapon:
        return "your fists"
    return f"your {weapon.key}"


def is_player_character(obj):
    return bool(obj) and not bool(getattr(obj.db, "is_npc", False))


def is_gm_character(obj):
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


class CmdAttack(Command):
    """
    Attack someone in the room.

    Examples:
      attack goblin
      att corl
    """

    key = "attack"
    aliases = ["att", "hit", "kill", "slice", "bash", "jab"]
    help_category = "Combat"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to attack.")
            self.caller.consume_stun()
            return

        if self.caller.is_in_roundtime():
            self.caller.msg_roundtime_block()
            return

        balance, _ = self.caller.get_balance()
        if balance <= 0:
            self.caller.msg("You are too off balance to make a good attack.")
            return

        if not self.caller.is_alive():
            self.caller.msg("You cannot attack while defeated.")
            return

        if not self.args:
            target = self.caller.get_target() if hasattr(self.caller, "get_target") else None
            if not target:
                self.caller.msg("Who do you want to attack?")
                return
        else:
            target_name = self.args.strip()
            room = self.caller.location
            if not room:
                self.caller.msg("There is no one here to attack.")
                return
            candidates = [obj for obj in room.contents if obj != self.caller]
            target, matches, base_query, index = self.caller.resolve_numbered_candidate(
                target_name,
                candidates,
                default_first=True,
            )
            if not target:
                if matches and index is not None:
                    self.caller.msg_numbered_matches(base_query, matches)
                else:
                    self.caller.msg("You do not see that target here.")
                return

        if target == self.caller:
            self.caller.msg("Attacking yourself would accomplish very little.")
            return

        attacker = self.caller

        try:
            from systems import onboarding

            block_message = onboarding.get_attack_block(self.caller, target)
            if block_message:
                self.caller.msg(block_message)
                return
            if onboarding.resolve_training_attack(self.caller, target):
                return
        except Exception:
            pass

        if getattr(getattr(target, "db", None), "is_corpse", False):
            self.caller.msg("There is no life left there to fight.")
            return

        if not hasattr(target, "set_hp") or target.db.hp is None:
            self.caller.msg(f"You cannot fight {target.key}.")
            return

        if not target.is_alive():
            self.caller.msg(f"{target.key} is already down.")
            return

        if hasattr(self.caller, "maybe_msg_death_sting_combat_feedback"):
            self.caller.maybe_msg_death_sting_combat_feedback()

        if is_player_character(self.caller) and is_gm_character(target):
            target_target = target.get_target() if hasattr(target, "get_target") else None
            if target_target != self.caller:
                self.caller.msg(
                    "If you had to make one final mistake in life, attacking Jekar would be as good as any you might choose."
                )
                return

        if getattr(self.caller.db, "disguised", False) and hasattr(self.caller, "clear_disguise"):
            self.caller.clear_disguise()

        if hasattr(self.caller, "get_collapse_chance") and random.random() < self.caller.get_collapse_chance():
            self.caller.db.position = "kneeling"
            self.caller.set_roundtime(3)
            if hasattr(self.caller, "break_combat_rhythm"):
                self.caller.break_combat_rhythm(show_message=False)
            self.caller.msg("Your exhausted body buckles before you can attack.")
            target_name = getattr(target, "key", "your attacker")
            if getattr(self.caller, "location", None):
                self.caller.location.msg_contents(
                    f"{self.caller.key} buckles from exhaustion before attacking {target_name}.",
                    exclude=[self.caller],
                )
            return

        if hasattr(self.caller, "get_pressure_hesitation_chance") and random.random() < self.caller.get_pressure_hesitation_chance():
            self.caller.msg("You hesitate under the assault.")
            self.caller.set_roundtime(1.5)
            return

        if hasattr(self.caller, "get_overextended_action_delay_chance") and random.random() < self.caller.get_overextended_action_delay_chance():
            self.caller.msg("Your overextended limbs lag behind your intent.")
            self.caller.set_roundtime(2)
            return

        self.caller.set_target(target)
        target.set_target(self.caller)
        weapon = self.caller.get_wielded_weapon() if hasattr(self.caller, "get_wielded_weapon") else self.caller.get_weapon()
        profile = self.caller.get_weapon_profile()
        current_range = self.caller.get_range(target)
        weapon_range_type = str(profile.get("weapon_range_type") or "").strip().lower()
        is_ranged_weapon = bool(weapon and (getattr(weapon.db, "is_ranged", False) or weapon_range_type))
        ranger_snipe = self.caller.get_state("ranger_snipe") if hasattr(self.caller, "get_state") else None
        ranger_aim_stacks = self.caller.get_ranger_aim_stacks(target) if hasattr(self.caller, "get_ranger_aim_stacks") else 0
        ranger_mark = target.get_ranger_mark_effect_on() if hasattr(target, "get_ranger_mark_effect_on") else None
        snipe_active = isinstance(ranger_snipe, Mapping) and ranger_snipe.get("target_id") == target.id
        ammo_state = self.caller.get_equipped_ammo_state() if hasattr(self.caller, "get_equipped_ammo_state") else None
        if is_ranged_weapon and (not ammo_state or not ammo_state.get("loaded")):
            self.caller.msg("You need to load your ranged weapon first.")
            return
        if not is_ranged_weapon and current_range != "melee":
            self.caller.msg("You are too far away to attack in melee.")
            return
        if hasattr(self.caller, "register_empath_offensive_action"):
            self.caller.register_empath_offensive_action(target=target, context="attack", amount=15)
        if hasattr(target, "check_room_traps_for_enemy"):
            target.check_room_traps_for_enemy(self.caller)
        try:
            from systems import onboarding

            onboarding.note_combat_start(self.caller, target)
            if str(getattr(getattr(target, "db", None), "onboarding_enemy_role", "") or "").lower() == "breach":
                onboarding.note_breach_progress(self.caller, "start")
        except Exception:
            pass

        ambush = False
        strong_ambush = False
        partial_ambush = False
        ambush_result = None
        ambush_accuracy_bonus = 0
        ambush_damage_multiplier = 1.0
        if self.caller.is_hidden() and self.caller.is_ambushing():
            ambush_target_id = self.caller.get_ambush_target_id()
            if target.id == ambush_target_id:
                stealth_total = self.caller.get_stealth_total()
                if getattr(self.caller.db, "marked_target", None) == target.id:
                    stealth_total += 10
                if getattr(self.caller.db, "position_state", "neutral") == "advantaged":
                    stealth_total += 10
                if "cunning" in (getattr(self.caller.db, "khri_active", None) or {}):
                    stealth_total += 5
                if self.caller.is_stalking() and self.caller.get_stalk_target_id() == target.id:
                    stealth_total += 10
                ambush_result = run_contest(stealth_total, target.get_perception_total(), attacker=self.caller, defender=target)
                if ambush_result["outcome"] == "fail":
                    self.caller.msg("You fail to find the opening!")
                    if hasattr(self.caller, "set_position_state"):
                        self.caller.set_position_state("exposed")
                    self.caller.db.recent_action = True
                    self.caller.db.recent_action_timer = time.time()
                    self.caller.break_stealth()
                    ambush_rt = 3
                    if getattr(self.caller.db, "position_state", "neutral") == "advantaged":
                        ambush_rt -= 1
                    ambush_rt = max(1, min(ambush_rt + 1, 5))
                    if hasattr(self.caller, "record_stealth_contest"):
                        self.caller.record_stealth_contest(
                            "ambush",
                            max(10, int(target.get_perception_total() or 0)),
                            result=ambush_result,
                            target=target,
                            roundtime=ambush_rt,
                            event_key="stealth",
                            require_hidden=False,
                        )
                    self.caller.apply_thief_roundtime(ambush_rt)
                    return
                ambush = True
                partial_ambush = ambush_result["outcome"] == "partial"
                ambush_accuracy_bonus += 25
                ambush_damage_multiplier = 0.75 if partial_ambush else 1.25
                if self.caller.is_stalking() and self.caller.get_stalk_target_id() == target.id:
                    ambush_accuracy_bonus += 15
                    if not partial_ambush:
                        ambush_damage_multiplier += 0.15
                if getattr(self.caller.db, "marked_target", None) == target.id:
                    ambush_damage_multiplier += 0.1
                if "cunning" in (getattr(self.caller.db, "khri_active", None) or {}):
                    ambush_damage_multiplier += 0.05
                target_awareness = target.get_awareness() if hasattr(target, "get_awareness") else "normal"
                strong_ambush = (not partial_ambush) and target_awareness == "unaware"
                if hasattr(target, "apply_surprise") and target_awareness in {"unaware", "normal"}:
                    target.apply_surprise()
                    react_or_message_target(target, player_text="You are caught completely off guard!", awareness="alert")

        if self.caller.is_hidden() and not snipe_active:
            self.caller.break_stealth()

        if ambush:
            self.caller.msg(f"You ambush {target.key}!")
            react_or_message_target(target, player_text=f"{self.caller.key} ambushes you!", awareness="alert")
            msg_room(
                self.caller,
                f"{self.caller.key} bursts from hiding and ambushes {target.key}!",
                exclude=[self.caller, target],
            )

        skill_name = profile.get("skill", "brawling")
        surge_state = self.caller.get_state("warrior_surge") if hasattr(self.caller, "get_state") else None
        crush_state = self.caller.get_state("warrior_crush") if hasattr(self.caller, "get_state") else None
        press_state = self.caller.get_state("warrior_press") if hasattr(self.caller, "get_state") else None
        sweep_state = self.caller.get_state("warrior_sweep") if hasattr(self.caller, "get_state") else None
        whirl_state = self.caller.get_state("warrior_whirl") if hasattr(self.caller, "get_state") else None
        frenzy_state = self.caller.get_state("warrior_frenzy") if hasattr(self.caller, "get_state") else None
        hold_state = target.get_state("warrior_hold") if hasattr(target, "get_state") else None
        attacker_tempo_state = self.caller.get_war_tempo_state() if hasattr(self.caller, "get_war_tempo_state") else "calm"
        defender_tempo_state = target.get_war_tempo_state() if hasattr(target, "get_war_tempo_state") else "calm"
        attacker_berserk = self.caller.get_active_warrior_berserk() if hasattr(self.caller, "get_active_warrior_berserk") else None
        defender_berserk = target.get_active_warrior_berserk() if hasattr(target, "get_active_warrior_berserk") else None
        attacker_roars = self.caller.get_active_warrior_roars() if hasattr(self.caller, "get_active_warrior_roars") else {}
        defender_roars = target.get_active_warrior_roars() if hasattr(target, "get_active_warrior_roars") else {}
        attacker_disrupt = self.caller.get_warrior_roar_effect("disrupt") if hasattr(self.caller, "get_warrior_roar_effect") else None
        attacker_unnerving = self.caller.get_warrior_roar_effect("unnerving") if hasattr(self.caller, "get_warrior_roar_effect") else None
        attacker_intimidate = self.caller.get_warrior_roar_effect("intimidate") if hasattr(self.caller, "get_warrior_roar_effect") else None
        weapon_effects = weapon.get_weapon_effects(self.caller) if weapon and hasattr(weapon, "get_weapon_effects") else {}
        weapon_balance = profile.get("balance", 50) + weapon_effects.get("balance", 0)
        suitability = weapon.get_weapon_suitability(self.caller) if weapon and hasattr(weapon, "get_weapon_suitability") else 0
        fatigue_cost = int(profile["fatigue_cost"])
        if hasattr(self.caller, "has_warrior_passive") and self.caller.has_warrior_passive("fatigue_reduction_1"):
            fatigue_cost = max(0, int(round(fatigue_cost * 0.9)))
        if frenzy_state:
            fatigue_cost += 1
        if attacker_berserk:
            fatigue_cost += int(attacker_berserk.get("fatigue_cost_bonus", 0) or 0)
        if hasattr(self.caller, "get_rhythm_fatigue_discount"):
            fatigue_cost = max(0, fatigue_cost - self.caller.get_rhythm_fatigue_discount())
        if hasattr(self.caller, "get_exhaustion_fatigue_multiplier"):
            fatigue_cost = max(0, int(round(fatigue_cost * self.caller.get_exhaustion_fatigue_multiplier())))

        target.incoming_attackers = getattr(target, "incoming_attackers", 0) + 1
        aimed_location, aimed_part = self.caller.resolve_targeted_body_part()

        combat_context = {
            "aimed_part": aimed_part,
            "ambush": ambush,
            "ambush_accuracy_bonus": ambush_accuracy_bonus,
            "ambush_damage_multiplier": ambush_damage_multiplier,
            "attacker_berserk": attacker_berserk,
            "attacker_disrupt": attacker_disrupt,
            "attacker_intimidate": attacker_intimidate,
            "attacker_tempo_state": attacker_tempo_state,
            "attacker_unnerving": attacker_unnerving,
            "crush_state": crush_state,
            "current_range": current_range,
            "defender_berserk": defender_berserk,
            "defender_roars": defender_roars,
            "defender_tempo_state": defender_tempo_state,
            "fatigue_cost": fatigue_cost,
            "frenzy_state": frenzy_state,
            "hold_state": hold_state,
            "is_ranged_weapon": is_ranged_weapon,
            "partial_ambush": partial_ambush,
            "press_state": press_state,
            "profile": profile,
            "ranger_aim_stacks": ranger_aim_stacks,
            "ranger_mark": ranger_mark,
            "ranger_snipe": ranger_snipe,
            "skill_name": skill_name,
            "snipe_active": snipe_active,
            "strong_ambush": strong_ambush,
            "suitability": suitability,
            "surge_state": surge_state,
            "weapon_effects": weapon_effects,
        }

        damage_profile = dict(profile.get("damage_types") or {})
        if not damage_profile:
            fallback_damage_type = (profile.get("damage_type") or "impact").lower()
            damage_profile = {"slice": 0, "impact": 0, "puncture": 0, fallback_damage_type: 1}
        damage_type = max(damage_profile, key=damage_profile.get)
        verb = random.choice(VERBS.get(damage_type, ["strike"]))
        verb_player = conjugate(verb, True)
        verb_target = conjugate(verb, False)
        weapon_phrase = get_weapon_phrase(weapon)
        self.caller.clear_aim()

        offensive_roar = attacker_roars.get("offensive") if isinstance(attacker_roars, dict) else None
        combat_context.update(
            {
                "aimed_location": aimed_location,
                "damage_type": damage_type,
                "offensive_roar": offensive_roar,
                "weapon": weapon,
            }
        )
        result = CombatService.attack(attacker, target, context=combat_context)
        combat_context = result.details
        hit = result.hit
        damage = result.damage
        hit_roll = combat_context["hit_roll"]
        final_chance = combat_context["final_chance"]
        ranger_pounce = combat_context.get("ranger_pounce")

        def resolve_snipe_concealment(hit=False):
            if not snipe_active:
                return
            bond_bonus = self.caller.get_ranger_snipe_retention_bonus() if hasattr(self.caller, "get_ranger_snipe_retention_bonus") else 0
            awareness_penalty = {"alert": 20, "normal": 10, "unaware": 0}.get(target_awareness, 10)
            chance = 25 + bond_bonus + (ranger_aim_stacks * 8) - awareness_penalty
            chance += int(ranger_snipe.get("stealth_bonus", 0) or 0)
            if hit:
                chance -= 5
            chance = max(5, min(90, chance))
            if random.randint(1, 100) <= chance:
                self.caller.msg("You remain concealed after the shot.")
            else:
                self.caller.break_stealth()
                self.caller.msg("Your shot gives away your position!")
                if self.caller.location:
                    self.caller.location.msg_contents(
                        f"{self.caller.key}'s hidden position is revealed.",
                        exclude=[self.caller],
                    )
            if hasattr(self.caller, "clear_state"):
                self.caller.clear_state("ranger_snipe")

        if current_range == "melee":
            range_phrase = "at close range"
        elif current_range == "far":
            range_phrase = "from a distance"
        else:
            range_phrase = "from nearby cover"

        if hit_roll > final_chance:
            if is_ranged_weapon:
                if snipe_active:
                    self.caller.msg("Your concealed shot misses its mark.")
                    target.msg("An arrow flies from nowhere and misses you.")
                else:
                    self.caller.msg(f"You fire at {target.key} {range_phrase} but miss.")
                    target.msg(f"{self.caller.key} fires at you {range_phrase} but misses.")
                if self.caller.location:
                    self.caller.location.msg_contents(
                        f"An arrow flies from nowhere toward {target.key}." if snipe_active else f"{self.caller.key} fires at {target.key} {range_phrase} but misses.",
                        exclude=[self.caller, target],
                    )
                resolve_snipe_concealment(hit=False)
                return
            self.caller.msg(f"You {verb_player} at {target.key} with {weapon_phrase} but miss.")
            target.msg(f"{self.caller.key} {verb_target} at you with {weapon.key if weapon else 'their fists'} but misses.")
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"{self.caller.key} {verb_target} at {target.key} with {weapon.key if weapon else 'their fists'} but misses.",
                    exclude=[self.caller, target],
                )
            return

        attack_context = combat_context["attack_context"]
        critical = combat_context["critical"]
        hit_location = combat_context["hit_location"]
        location_name = combat_context["location_name"]
        quality = combat_context["quality"]
        if combat_context.get("armor_absorbed"):
            target.msg("Your armor absorbs part of the blow.")
        if isinstance(sweep_state, dict):
            balance_resist = 0
            if hasattr(target, "has_warrior_passive") and target.has_warrior_passive("balance_resist_1"):
                balance_resist += 15
            if defender_berserk:
                balance_resist += int(defender_berserk.get("balance_resist_bonus", 0) or 0)
            if balance_resist and random.randint(1, 100) <= min(85, balance_resist):
                self.caller.msg(f"{target.key} resists your sweep and keeps their footing.")
                target.msg("You absorb the sweep and keep your footing.")
            else:
                target.db.position = "prone"
                self.caller.msg(f"You sweep {target.key} off their feet.")
                target.msg("You are driven off your feet!")
        if isinstance(whirl_state, dict):
            self.caller.msg("Your momentum carries through the melee.")
        if ambush and not partial_ambush:
            target.db.staggered = True
            target.db.stagger_timer = time.time()
            self.caller.db.post_ambush_grace = True
            self.caller.db.post_ambush_grace_until = time.time() + 2
        if hasattr(target, "set_awareness"):
            prior_awareness = target.get_awareness()
            target.set_awareness("alert")
            if prior_awareness != "alert":
                target.msg("You become more alert!")
        pressure_gain = 0
        if attacker_tempo_state == "building":
            pressure_gain += 2
        elif attacker_tempo_state == "surging":
            pressure_gain += 4
        elif attacker_tempo_state == "frenzied":
            pressure_gain += 6
        if hasattr(self.caller, "get_combat_streak") and self.caller.get_combat_streak() >= 5:
            pressure_gain += 2
        if isinstance(offensive_roar, dict):
            pressure_gain += 2
        if hit_roll <= final_chance:
            pressure_gain += 3
        if pressure_gain and hasattr(target, "add_pressure"):
            target.add_pressure(pressure_gain)
        if hasattr(target, "is_surprised") and target.is_surprised():
            target.clear_surprise()
            target.msg("You regain your bearings!")

        quality_phrase = f"critical {quality}" if critical else quality
        if is_ranged_weapon:
            if snipe_active:
                self.caller.msg(f"You release a carefully placed shot from concealment and strike {target.key}'s {location_name}.")
                target.msg(f"An arrow flies from nowhere and strikes your {location_name}.")
            else:
                self.caller.msg(
                    f"You fire at {target.key}'s {location_name} {range_phrase} with a {quality_phrase} hit."
                )
                target.msg(
                    f"{self.caller.key} fires at your {location_name} {range_phrase} with a {quality_phrase} hit."
                )
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"An arrow flies from nowhere toward {target.key}." if snipe_active else f"{self.caller.key} fires at {target.key}'s {location_name} {range_phrase} with a {quality_phrase} hit.",
                    exclude=[self.caller, target],
                )
            resolve_snipe_concealment(hit=True)
        else:
            self.caller.msg(
                f"You {verb_player} {target.key}'s {location_name} with a {quality_phrase} hit."
            )
            target.msg(
                f"{self.caller.key} {verb_target} your {location_name} with a {quality_phrase} hit."
            )
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"{self.caller.key} {verb_target} {target.key}'s {location_name} with a {quality_phrase} hit.",
                    exclude=[self.caller, target],
                )

        if weapon_effects.get("flavor"):
            self.caller.msg("Your weapon moves like an extension of your will.")

        if aimed_part == "head" and random.randint(1, 100) < 10:
            target.db.stunned = True
            target.msg("The blow leaves you stunned.")

        if ambush and hasattr(self.caller, "record_stealth_contest"):
            self.caller.record_stealth_contest(
                "ambush",
                max(10, int(target.get_perception_total() or 0)),
                result=ambush_result,
                target=target,
                roundtime=result.roundtime,
                event_key="stealth",
                require_hidden=False,
            )

        if self.caller.is_hidden() or bool(getattr(self.caller.db, "stealthed", False)):
            break_stealth(self.caller)

        if target.db.hp == 0:
            self.caller.msg(f"You bring down {target.key}.")
            target.msg("You collapse from the blow.")
            self.caller.set_target(None)
            target.set_target(None)
            try:
                from systems import onboarding

                completed, awarded = onboarding.note_combat_win(self.caller, target)
                if completed and awarded:
                    self.caller.msg(onboarding.format_token_feedback(onboarding.ensure_onboarding_state(self.caller)))
            except Exception:
                pass