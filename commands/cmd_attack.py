import random
import time
from collections.abc import Mapping

from commands.command import Command
from world.systems.ranger import RANGER_SNIPE_CONFIG
from world.systems.skills import award_exp_skill
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

        hit_roll = random.randint(1, 100)
        attacker_reflex = self.caller.get_stat("reflex")
        attacker_agility = self.caller.get_stat("agility")
        skill_rank = self.caller.get_skill(skill_name)
        accuracy = 50 + attacker_reflex + attacker_agility + skill_rank
        stance = self.caller.db.stance or {"offense": 50, "defense": 50}
        accuracy += stance.get("offense", 50) * 0.2
        attacker_position_mods = self.caller.get_position_modifiers()
        accuracy += attacker_position_mods["offense"]
        maneuver_hindrance, _ = self.caller.get_total_hindrance()
        attack_penalty = min(25, int(round(maneuver_hindrance * 0.2)) + self.caller.get_arm_penalty())
        accuracy -= attack_penalty
        accuracy += suitability
        accuracy += (weapon_balance - 50) * 0.1
        accuracy += weapon_effects.get("accuracy", 0)
        accuracy += int(self.caller.get_skill("tactics") / 10)
        if hasattr(self.caller, "is_staggered") and self.caller.is_staggered():
            accuracy -= 10
        if hasattr(self.caller, "get_pressure_accuracy_penalty"):
            accuracy -= self.caller.get_pressure_accuracy_penalty()
        if hasattr(self.caller, "get_exhaustion_accuracy_penalty"):
            accuracy -= self.caller.get_exhaustion_accuracy_penalty()
        debilitation = self.caller.get_state("debilitated") if hasattr(self.caller, "get_state") else None
        if debilitation:
            accuracy -= int(debilitation.get("penalty", 0) or 0)
        nearby_engaged = 0
        if self.caller.location:
            for obj in self.caller.location.contents:
                if obj in {self.caller, target} or not hasattr(obj, "get_target"):
                    continue
                if obj.get_target() == self.caller:
                    nearby_engaged += 1
        if nearby_engaged > 0:
            accuracy += int(self.caller.get_skill("tactics") / 5)
        if skill_rank < 10:
            accuracy -= 10
        att_awareness = self.caller.get_awareness() if hasattr(self.caller, "get_awareness") else "normal"
        if att_awareness == "alert":
            accuracy += 5
        elif att_awareness == "unaware":
            accuracy -= 10
        if self.caller.db.aiming == target.id:
            accuracy += 15 if not is_ranged_weapon else 10 + (ranger_aim_stacks * 5)
        if is_ranged_weapon:
            if current_range == "melee":
                accuracy -= 35
            elif current_range == "near":
                accuracy += 5
            elif current_range == "far":
                accuracy += 10
        if ambush:
            accuracy += ambush_accuracy_bonus
        if attacker_tempo_state == "surging":
            accuracy += 3
        elif attacker_tempo_state == "frenzied":
            accuracy += 5
        if hasattr(self.caller, "get_rhythm_accuracy_bonus"):
            accuracy += self.caller.get_rhythm_accuracy_bonus()
        if isinstance(surge_state, dict):
            accuracy += int(surge_state.get("bonus", 0) or 0)
        if isinstance(press_state, dict):
            accuracy += int(press_state.get("accuracy", 0) or 0)
        if isinstance(frenzy_state, dict):
            accuracy += int(frenzy_state.get("accuracy", 0) or 0)
        if attacker_berserk:
            accuracy += int(attacker_berserk.get("accuracy_bonus", 0) or 0)
        for effect in [attacker_disrupt, attacker_unnerving, attacker_intimidate]:
            if isinstance(effect, dict):
                accuracy -= int(effect.get("accuracy_penalty", 0) or 0)
        tactics_prep = self.caller.get_state("tactics_prep") if hasattr(self.caller, "get_state") else None
        ranger_pounce = self.caller.get_state("ranger_pounce") if hasattr(self.caller, "get_state") else None
        if tactics_prep and tactics_prep.get("target") == target.id:
            accuracy += int(tactics_prep.get("bonus", 0) or 0)
            if hasattr(self.caller, "clear_state"):
                self.caller.clear_state("tactics_prep")
        if isinstance(ranger_pounce, Mapping) and ranger_pounce.get("target_id") == target.id:
            accuracy += int(ranger_pounce.get("accuracy_bonus", 0) or 0)
        if snipe_active:
            accuracy += int(ranger_snipe.get("accuracy_bonus", 0) or 0)
        if isinstance(ranger_mark, Mapping):
            accuracy += int(ranger_mark.get("accuracy_bonus", 0) or 0)
        if bool(getattr(self.caller.db, "is_npc", False)):
            npc_max_hp = self.caller.db.max_hp or 0
            npc_hp_ratio = (self.caller.db.hp or 0) / npc_max_hp if npc_max_hp else 1
            if npc_hp_ratio > 0.7:
                accuracy += 5

        target.incoming_attackers = getattr(target, "incoming_attackers", 0) + 1

        defender_reflex = target.get_stat("reflex")
        defender_agility = target.get_stat("agility")
        evasion = defender_reflex + defender_agility
        target_stance = target.db.stance or {"offense": 50, "defense": 50}
        evasion += target_stance.get("defense", 50) * 0.2
        target_position_mods = target.get_position_modifiers()
        evasion += target_position_mods["defense"]
        target_maneuver_hindrance, _ = target.get_total_hindrance()
        evasion -= target_maneuver_hindrance * 2
        target_awareness = target.get_awareness() if hasattr(target, "get_awareness") else "normal"
        if target_awareness == "alert":
            evasion += 10
        elif target_awareness == "unaware":
            evasion -= 10
        if hasattr(target, "is_surprised") and target.is_surprised():
            evasion -= 20
        target_debilitation = target.get_state("debilitated") if hasattr(target, "get_state") else None
        if target_debilitation and target_debilitation.get("type") == "evasion":
            evasion -= int(target_debilitation.get("penalty", 0) or 0)
        if isinstance(hold_state, dict):
            evasion += int(hold_state.get("defense", 0) or 0)
        if hasattr(target, "has_warrior_passive") and target.has_warrior_passive("multitarget_defense_1") and target.incoming_attackers > 1:
            evasion += 3
        if defender_tempo_state == "frenzied":
            evasion -= 8
        if hasattr(target, "get_exhaustion_defense_penalty"):
            evasion -= target.get_exhaustion_defense_penalty()
        if defender_berserk:
            evasion += int(defender_berserk.get("defense_bonus", 0) or 0)
        defensive_roar = defender_roars.get("defensive") if isinstance(defender_roars, dict) else None
        if isinstance(defensive_roar, dict):
            evasion += int(defensive_roar.get("defense_bonus", 0) or 0)
        if strong_ambush:
            evasion = 0

        if hasattr(self.caller, "apply_death_sting_to_contest_value"):
            accuracy = self.caller.apply_death_sting_to_contest_value(accuracy)
        if hasattr(target, "apply_death_sting_to_contest_value"):
            evasion = target.apply_death_sting_to_contest_value(evasion)

        aimed_location, aimed_part = self.caller.resolve_targeted_body_part()
        if aimed_part == "head":
            accuracy -= 20
        elif aimed_part in ["arm", "leg"]:
            accuracy -= 10

        final_chance = max(10, accuracy - evasion)
        final_chance = min(95, final_chance)
        if final_chance < 95:
            award_exp_skill(target, "evasion", max(10, int(accuracy)), success=hit_roll > final_chance)
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
            self.caller.set_fatigue(self.caller.db.fatigue + fatigue_cost)
            if hasattr(self.caller, "gain_war_tempo"):
                self.caller.gain_war_tempo(5)
            if hasattr(self.caller, "advance_combat_rhythm"):
                self.caller.advance_combat_rhythm(hit=False)
            for state_key in ["warrior_surge", "warrior_crush", "warrior_press", "warrior_sweep", "warrior_whirl", "ranger_pounce"]:
                if hasattr(self.caller, "clear_state"):
                    self.caller.clear_state(state_key)
            miss_roundtime = profile.get("speed", profile.get("roundtime", 3.0))
            if attacker_berserk:
                miss_roundtime = max(1.0, miss_roundtime + float(attacker_berserk.get("roundtime_modifier", 0.0) or 0.0))
            if hasattr(self.caller, "is_warrior_overextended") and self.caller.is_warrior_overextended():
                miss_roundtime += 1
            if ambush:
                if getattr(self.caller.db, "position_state", "neutral") == "advantaged":
                    miss_roundtime -= 1
                miss_roundtime = max(1, min(miss_roundtime + 1, 5))
                self.caller.apply_thief_roundtime(miss_roundtime)
            else:
                self.caller.set_roundtime(miss_roundtime)
            if is_ranged_weapon:
                if hasattr(self.caller, "consume_loaded_ammo"):
                    self.caller.consume_loaded_ammo()
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

        base = max(1, int(profile.get("damage") or 1)) if weapon else 1
        if weapon:
            damage_min = max(1, int(profile.get("damage_min") or base))
            damage_max = max(damage_min, int(profile.get("damage_max") or damage_min))
            base = max(base, random.randint(damage_min, damage_max))
        damage = base + int(skill_rank * 0.2) + int(suitability * 0.3)
        if skill_rank > 30:
            damage += 2
        damage += int(weapon_effects.get("damage_bonus", 0))
        damage -= min(25, self.caller.get_hand_penalty())
        diff = final_chance - hit_roll
        quality = "good"
        if diff > 40:
            quality = "devastating"
            damage = int(round(damage * 1.8))
        elif diff > 25:
            quality = "solid"
            damage = int(round(damage * 1.4))
        elif diff > 10:
            quality = "good"
            damage = int(round(damage * 1.1))
        elif diff > 0:
            quality = "glancing"
            damage = max(1, int(round(damage * 0.7)))

        critical = random.randint(1, 100) < 5
        if snipe_active and hasattr(self.caller, "get_wilderness_bond") and hasattr(self.caller, "get_nature_focus"):
            if self.caller.get_wilderness_bond() >= int(RANGER_SNIPE_CONFIG.get("mastery_bond_threshold", 80) or 80) and self.caller.get_nature_focus() >= int(RANGER_SNIPE_CONFIG.get("mastery_focus_threshold", 60) or 60):
                critical = critical or random.randint(1, 100) <= int(RANGER_SNIPE_CONFIG.get("mastery_crit_bonus", 8) or 8)
        if critical:
            damage *= 2

        if is_ranged_weapon:
            if current_range == "melee":
                damage = int(round(damage * 0.75))
            elif current_range == "near":
                damage = int(round(damage * 1.05))
            elif current_range == "far":
                damage = int(round(damage * 1.10))
            if ranger_aim_stacks:
                damage = int(round(damage * (1 + (ranger_aim_stacks * float(RANGER_SNIPE_CONFIG.get("aim_damage_per_stack", 0.05) or 0.05)))))

        if ambush:
            damage = int(round(damage * ambush_damage_multiplier))
        if attacker_tempo_state == "surging":
            damage = int(round(damage * 1.10))
        elif attacker_tempo_state == "frenzied":
            damage = int(round(damage * 1.20))
        if isinstance(surge_state, dict):
            damage += int(surge_state.get("damage", 0) or 0)
        if isinstance(crush_state, dict):
            damage = int(round(damage * float(crush_state.get("damage_multiplier", 1.0) or 1.0)))
        if isinstance(frenzy_state, dict):
            damage = int(round(damage * float(frenzy_state.get("damage_multiplier", 1.0) or 1.0)))
        if attacker_berserk:
            damage = int(round(damage * float(attacker_berserk.get("damage_multiplier", 1.0) or 1.0)))
        offensive_roar = attacker_roars.get("offensive") if isinstance(attacker_roars, dict) else None
        if isinstance(offensive_roar, dict):
            damage = int(round(damage * 1.05))
        if isinstance(ranger_pounce, Mapping) and ranger_pounce.get("target_id") == target.id:
            damage = int(round(damage * (1 + float(ranger_pounce.get("damage_bonus", 0) or 0.0))))
        if snipe_active:
            damage = int(round(damage * float(ranger_snipe.get("damage_multiplier", 1.0) or 1.0)))

        if getattr(target.db, "roughed", False):
            damage = int(round(damage * 1.1))

        if aimed_part == "head":
            damage += 2
        elif aimed_part == "arm":
            damage += 1

        if aimed_location:
            hit_location = aimed_location
            location_name = aimed_part
        else:
            hit_location = random.choice(list(target.db.injuries.keys()))
            location_name = target.format_body_part_name(hit_location)

        attack_context = {"damage_type": damage_type}

        armor_list = target.get_armor_for_bodypart(hit_location) if hasattr(target, "get_armor_for_bodypart") else target.get_armor_covering(hit_location)
        protection = target.get_total_armor_protection(hit_location) if hasattr(target, "get_total_armor_protection") else sum(target.get_armor_protection_value(armor) for armor in armor_list)
        if protection:
            damage = max(1, damage - int(round(protection)))
            target.msg("Your armor absorbs part of the blow.")

        if hasattr(self.caller, "apply_death_sting_to_damage"):
            damage = self.caller.apply_death_sting_to_damage(damage)
        damage = max(0, int(damage))
        if final_chance < 95:
            difficulty = target.get_stat("reflex") + target.get_stat("agility")
            if skill_name == "brawling":
                brawling_difficulty = max(10, int(target.get_skill("evasion") + difficulty))
                award_exp_skill(self.caller, "brawling", brawling_difficulty, success=True)
            elif skill_name == "light_edge":
                light_edge_difficulty = max(10, int(target.get_skill("evasion") + difficulty))
                award_exp_skill(self.caller, "light_edge", light_edge_difficulty, success=True)
            else:
                _, band = self.caller.get_learning_amount(skill_name, difficulty)
                if band != "trivial":
                    self.caller.use_skill(
                        skill_name,
                        apply_roundtime=False,
                        emit_placeholder=False,
                        require_known=False,
                        difficulty=difficulty,
                        return_learning=True,
                    )
        target_was_dead = bool(getattr(target.db, "is_dead", False))
        if hasattr(target, "apply_incoming_damage"):
            target.apply_incoming_damage(hit_location, damage, attack_context["damage_type"])
        else:
            target.set_hp(target.db.hp - damage)
            target.apply_damage(hit_location, damage, attack_context["damage_type"])
        if not target_was_dead and bool(getattr(target.db, "is_dead", False)) and hasattr(self.caller, "register_empath_offensive_action"):
            self.caller.register_empath_offensive_action(target=target, context="kill", amount=30)
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
            if hasattr(self.caller, "consume_loaded_ammo"):
                self.caller.consume_loaded_ammo()
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

        self.caller.set_balance(self.caller.db.balance - profile["balance_cost"])
        self.caller.set_fatigue(self.caller.db.fatigue + fatigue_cost)
        if hasattr(self.caller, "gain_war_tempo"):
            self.caller.gain_war_tempo(8)
        if hasattr(self.caller, "advance_combat_rhythm"):
            self.caller.advance_combat_rhythm(hit=True)
        for state_key in ["warrior_surge", "warrior_crush", "warrior_press", "warrior_sweep", "warrior_whirl", "ranger_pounce"]:
            if hasattr(self.caller, "clear_state"):
                self.caller.clear_state(state_key)
        self.caller.db.recent_action = True
        self.caller.db.recent_action_timer = time.time()
        action_roundtime = profile.get("speed", profile.get("roundtime", 3.0))
        if attacker_berserk:
            action_roundtime = max(1.0, action_roundtime + float(attacker_berserk.get("roundtime_modifier", 0.0) or 0.0))
        if hasattr(self.caller, "is_warrior_overextended") and self.caller.is_warrior_overextended():
            action_roundtime += 1
        if ambush:
            action_roundtime = max(action_roundtime, 3.0)
            if getattr(self.caller.db, "position_state", "neutral") == "advantaged":
                action_roundtime -= 1
            if partial_ambush:
                action_roundtime += 1
            action_roundtime = max(1, min(action_roundtime, 5))
            if hasattr(self.caller, "record_stealth_contest"):
                self.caller.record_stealth_contest(
                    "ambush",
                    max(10, int(target.get_perception_total() or 0)),
                    result=ambush_result,
                    target=target,
                    roundtime=action_roundtime,
                    event_key="stealth",
                    require_hidden=False,
                )
            self.caller.apply_thief_roundtime(action_roundtime)
        else:
            self.caller.set_roundtime(action_roundtime)

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