import random

from evennia import Command

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
    aliases = ["att", "slice", "bash", "jab"]
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
            target = self.caller.search(target_name)

            if not target:
                return

        if target == self.caller:
            self.caller.msg("Attacking yourself would accomplish very little.")
            return

        if not hasattr(target, "set_hp") or target.db.hp is None:
            self.caller.msg(f"You cannot fight {target.key}.")
            return

        if not target.is_alive():
            self.caller.msg(f"{target.key} is already down.")
            return

        if is_player_character(self.caller) and is_gm_character(target):
            target_target = target.get_target() if hasattr(target, "get_target") else None
            if target_target != self.caller:
                self.caller.msg(
                    "If you had to make one final mistake in life, attacking Jekar would be as good as any you might choose."
                )
                return

        self.caller.set_target(target)
        target.set_target(self.caller)
        weapon = self.caller.get_wielded_weapon() if hasattr(self.caller, "get_wielded_weapon") else self.caller.get_weapon()
        profile = self.caller.get_weapon_profile()
        current_range = self.caller.get_range(target)
        is_ranged_weapon = bool(weapon and getattr(weapon.db, "is_ranged", False))
        if not is_ranged_weapon and current_range != "melee":
            self.caller.msg("You are too far away to attack in melee.")
            return
        if hasattr(target, "check_room_traps_for_enemy"):
            target.check_room_traps_for_enemy(self.caller)

        ambush = False
        strong_ambush = False
        ambush_accuracy_bonus = 0
        ambush_damage_multiplier = 1.0
        if self.caller.is_hidden() and self.caller.is_ambushing():
            ambush_target_id = self.caller.get_ambush_target_id()
            if target.id == ambush_target_id:
                ambush = True
                ambush_accuracy_bonus += 30
                ambush_damage_multiplier = 1.5
                if self.caller.is_stalking() and self.caller.get_stalk_target_id() == target.id:
                    ambush_accuracy_bonus += 15
                    ambush_damage_multiplier += 0.25
                target_awareness = target.get_awareness() if hasattr(target, "get_awareness") else "normal"
                strong_ambush = target_awareness == "unaware"
                if hasattr(target, "apply_surprise") and target_awareness in {"unaware", "normal"}:
                    target.apply_surprise()
                    react_or_message_target(target, player_text="You are caught completely off guard!", awareness="alert")

        if self.caller.is_hidden():
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
        weapon_effects = weapon.get_weapon_effects(self.caller) if weapon and hasattr(weapon, "get_weapon_effects") else {}
        weapon_balance = profile.get("balance", 50) + weapon_effects.get("balance", 0)
        suitability = weapon.get_weapon_suitability(self.caller) if weapon and hasattr(weapon, "get_weapon_suitability") else 0

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
            accuracy += 15
        if is_ranged_weapon and current_range == "melee":
            accuracy -= 20
        if ambush:
            accuracy += ambush_accuracy_bonus
        tactics_prep = self.caller.get_state("tactics_prep") if hasattr(self.caller, "get_state") else None
        if tactics_prep and tactics_prep.get("target") == target.id:
            accuracy += int(tactics_prep.get("bonus", 0) or 0)
            if hasattr(self.caller, "clear_state"):
                self.caller.clear_state("tactics_prep")
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
        if strong_ambush:
            evasion = 0

        aimed_location, aimed_part = self.caller.resolve_targeted_body_part()
        if aimed_part == "head":
            accuracy -= 20
        elif aimed_part in ["arm", "leg"]:
            accuracy -= 10

        final_chance = max(10, accuracy - evasion)
        final_chance = min(95, final_chance)
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

        if current_range == "melee":
            range_phrase = "at close range"
        elif current_range == "missile":
            range_phrase = "from a distance"
        else:
            range_phrase = "from reach"

        if hit_roll > final_chance:
            self.caller.set_fatigue(self.caller.db.fatigue + profile["fatigue_cost"])
            self.caller.set_roundtime(profile.get("roundtime", 3.0))
            if is_ranged_weapon:
                self.caller.msg(f"You fire at {target.key} {range_phrase} but miss.")
                target.msg(f"{self.caller.key} fires at you {range_phrase} but misses.")
                if self.caller.location:
                    self.caller.location.msg_contents(
                        f"{self.caller.key} fires at {target.key} {range_phrase} but misses.",
                        exclude=[self.caller, target],
                    )
                return
            self.caller.msg(f"You {verb_player} at {target.key} with {weapon_phrase} but miss.")
            target.msg(f"{self.caller.key} {verb_target} at you with {weapon.key if weapon else 'their fists'} but misses.")
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"{self.caller.key} {verb_target} at {target.key} with {weapon.key if weapon else 'their fists'} but misses.",
                    exclude=[self.caller, target],
                )
            return

        base = profile.get("damage") if weapon else 1
        if weapon:
            base = max(base, random.randint(profile["damage_min"], profile["damage_max"]))
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
        if critical:
            damage *= 2

        if ambush:
            damage = int(round(damage * ambush_damage_multiplier))

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

        damage = max(0, int(damage))
        if final_chance < 95:
            difficulty = target.get_stat("reflex") + target.get_stat("agility")
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
        target.set_hp(target.db.hp - damage)
        target.apply_damage(hit_location, damage, attack_context["damage_type"])
        if hasattr(target, "set_awareness"):
            prior_awareness = target.get_awareness()
            target.set_awareness("alert")
            if prior_awareness != "alert":
                target.msg("You become more alert!")
        if hasattr(target, "is_surprised") and target.is_surprised():
            target.clear_surprise()
            target.msg("You regain your bearings!")

        quality_phrase = f"critical {quality}" if critical else quality
        if is_ranged_weapon:
            self.caller.msg(
                f"You fire at {target.key}'s {location_name} {range_phrase} with a {quality_phrase} hit."
            )
            target.msg(
                f"{self.caller.key} fires at your {location_name} {range_phrase} with a {quality_phrase} hit."
            )
            if self.caller.location:
                self.caller.location.msg_contents(
                    f"{self.caller.key} fires at {target.key}'s {location_name} {range_phrase} with a {quality_phrase} hit.",
                    exclude=[self.caller, target],
                )
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
        self.caller.set_fatigue(self.caller.db.fatigue + profile["fatigue_cost"])
        self.caller.set_roundtime(profile.get("speed", profile.get("roundtime", 3.0)))

        if target.db.hp == 0:
            self.caller.msg(f"You bring down {target.key}.")
            target.msg("You collapse from the blow.")
            self.caller.set_target(None)
            target.set_target(None)