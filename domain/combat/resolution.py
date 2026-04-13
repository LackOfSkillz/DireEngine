from collections.abc import Mapping
import random


EARLY_GAME_DAMAGE_CLAMP_RATIO = 0.15
EARLY_GAME_DAMAGE_CLAMP_RANK = 20


class AttackResolution:
    def __init__(self, hit=False, damage=0, roundtime=0, details=None):
        self.hit = hit
        self.damage = damage
        self.roundtime = roundtime
        self.details = details or {}


def resolve_attack(attacker, target, context=None):
    details = dict(context or {})
    hit = calculate_hit(attacker, target, details)
    details["hit"] = hit
    roundtime = calculate_roundtime(attacker, target, details)
    damage = calculate_damage(attacker, target, details) if hit else 0
    return AttackResolution(hit=hit, damage=damage, roundtime=roundtime, details=details)


def calculate_hit(attacker, target, context=None):
    context = context or {}
    hit_roll = random.randint(1, 100)
    skill_name = context["skill_name"]
    profile = context["profile"]
    weapon_effects = context["weapon_effects"]
    suitability = context["suitability"]
    current_range = context["current_range"]
    is_ranged_weapon = context["is_ranged_weapon"]
    ranger_aim_stacks = context["ranger_aim_stacks"]
    ambush = context["ambush"]
    ambush_accuracy_bonus = context["ambush_accuracy_bonus"]
    attacker_tempo_state = context["attacker_tempo_state"]
    surge_state = context["surge_state"]
    press_state = context["press_state"]
    frenzy_state = context["frenzy_state"]
    attacker_berserk = context["attacker_berserk"]
    attacker_disrupt = context["attacker_disrupt"]
    attacker_unnerving = context["attacker_unnerving"]
    attacker_intimidate = context["attacker_intimidate"]
    snipe_active = context["snipe_active"]
    ranger_snipe = context["ranger_snipe"]
    ranger_mark = context["ranger_mark"]
    hold_state = context["hold_state"]
    defender_tempo_state = context["defender_tempo_state"]
    defender_berserk = context["defender_berserk"]
    defender_roars = context["defender_roars"]
    strong_ambush = context["strong_ambush"]
    aimed_part = context["aimed_part"]

    attacker_reflex = attacker.get_stat("reflex")
    attacker_agility = attacker.get_stat("agility")
    skill_rank = attacker.get_skill(skill_name)
    accuracy = 50 + attacker_reflex + attacker_agility + skill_rank
    stance = attacker.db.stance or {"offense": 50, "defense": 50}
    accuracy += stance.get("offense", 50) * 0.2
    attacker_position_mods = attacker.get_position_modifiers()
    accuracy += attacker_position_mods["offense"]
    maneuver_hindrance, _ = attacker.get_total_hindrance()
    attack_penalty = min(25, int(round(maneuver_hindrance * 0.2)) + attacker.get_arm_penalty())
    accuracy -= attack_penalty
    accuracy += suitability
    accuracy += (profile.get("balance", 50) + weapon_effects.get("balance", 0) - 50) * 0.1
    accuracy += weapon_effects.get("accuracy", 0)
    accuracy += int(attacker.get_skill("tactics") / 10)
    if hasattr(attacker, "is_staggered") and attacker.is_staggered():
        accuracy -= 10
    if hasattr(attacker, "get_pressure_accuracy_penalty"):
        accuracy -= attacker.get_pressure_accuracy_penalty()
    if hasattr(attacker, "get_exhaustion_accuracy_penalty"):
        accuracy -= attacker.get_exhaustion_accuracy_penalty()
    structured_accuracy_penalty = attacker.get_effect_modifier("accuracy") if hasattr(attacker, "get_effect_modifier") else 0
    if structured_accuracy_penalty:
        accuracy -= int(structured_accuracy_penalty or 0)
    else:
        debilitation = attacker.get_state("debilitated") if hasattr(attacker, "get_state") else None
        if debilitation:
            accuracy -= int(debilitation.get("penalty", 0) or 0)
    nearby_engaged = 0
    if attacker.location:
        for obj in attacker.location.contents:
            if obj in {attacker, target} or not hasattr(obj, "get_target"):
                continue
            if obj.get_target() == attacker:
                nearby_engaged += 1
    if nearby_engaged > 0:
        accuracy += int(attacker.get_skill("tactics") / 5)
    if skill_rank < 10:
        accuracy -= 10
    att_awareness = attacker.get_awareness() if hasattr(attacker, "get_awareness") else "normal"
    if att_awareness == "alert":
        accuracy += 5
    elif att_awareness == "unaware":
        accuracy -= 10
    if attacker.db.aiming == target.id:
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
    if hasattr(attacker, "get_rhythm_accuracy_bonus"):
        accuracy += attacker.get_rhythm_accuracy_bonus()
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
    tactics_prep = attacker.get_state("tactics_prep") if hasattr(attacker, "get_state") else None
    ranger_pounce = attacker.get_state("ranger_pounce") if hasattr(attacker, "get_state") else None
    if tactics_prep and tactics_prep.get("target") == target.id:
        accuracy += int(tactics_prep.get("bonus", 0) or 0)
        if hasattr(attacker, "clear_state"):
            attacker.clear_state("tactics_prep")
    if isinstance(ranger_pounce, Mapping) and ranger_pounce.get("target_id") == target.id:
        accuracy += int(ranger_pounce.get("accuracy_bonus", 0) or 0)
    if snipe_active:
        accuracy += int(ranger_snipe.get("accuracy_bonus", 0) or 0)
    if isinstance(ranger_mark, Mapping):
        accuracy += int(ranger_mark.get("accuracy_bonus", 0) or 0)
    if bool(getattr(attacker.db, "is_npc", False)):
        npc_max_hp = attacker.db.max_hp or 0
        npc_hp_ratio = (attacker.db.hp or 0) / npc_max_hp if npc_max_hp else 1
        if npc_hp_ratio > 0.7:
            accuracy += 5

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
    structured_evasion_penalty = target.get_effect_modifier("evasion") if hasattr(target, "get_effect_modifier") else 0
    if structured_evasion_penalty:
        evasion -= int(structured_evasion_penalty or 0)
    else:
        target_debilitation = target.get_state("debilitated") if hasattr(target, "get_state") else None
        if target_debilitation and target_debilitation.get("type") == "evasion":
            evasion -= int(target_debilitation.get("penalty", 0) or 0)
    if isinstance(hold_state, dict):
        evasion += int(hold_state.get("defense", 0) or 0)
    if hasattr(target, "has_warrior_passive") and target.has_warrior_passive("multitarget_defense_1") and getattr(target, "incoming_attackers", 0) > 1:
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

    if hasattr(attacker, "apply_death_sting_to_contest_value"):
        accuracy = attacker.apply_death_sting_to_contest_value(accuracy)
    if hasattr(target, "apply_death_sting_to_contest_value"):
        evasion = target.apply_death_sting_to_contest_value(evasion)

    if aimed_part == "head":
        accuracy -= 20
    elif aimed_part in ["arm", "leg"]:
        accuracy -= 10

    final_chance = max(10, accuracy - evasion)
    final_chance = min(95, final_chance)
    context["hit_roll"] = hit_roll
    context["accuracy"] = accuracy
    context["evasion"] = evasion
    context["final_chance"] = final_chance
    context["ranger_pounce"] = ranger_pounce
    return hit_roll <= final_chance


def calculate_damage(attacker, target, context=None):
    context = context or {}
    profile = context["profile"]
    weapon = context["weapon"]
    skill_name = context["skill_name"]
    skill_rank = attacker.get_skill(skill_name)
    suitability = context["suitability"]
    weapon_effects = context["weapon_effects"]
    final_chance = context["final_chance"]
    hit_roll = context["hit_roll"]
    current_range = context["current_range"]
    is_ranged_weapon = context["is_ranged_weapon"]
    ranger_aim_stacks = context["ranger_aim_stacks"]
    ambush = context["ambush"]
    ambush_damage_multiplier = context["ambush_damage_multiplier"]
    attacker_tempo_state = context["attacker_tempo_state"]
    surge_state = context["surge_state"]
    crush_state = context["crush_state"]
    frenzy_state = context["frenzy_state"]
    attacker_berserk = context["attacker_berserk"]
    offensive_roar = context["offensive_roar"]
    ranger_pounce = context.get("ranger_pounce")
    snipe_active = context["snipe_active"]
    ranger_snipe = context["ranger_snipe"]
    aimed_part = context["aimed_part"]
    aimed_location = context["aimed_location"]
    damage_type = context["damage_type"]
    snipe_config = dict(context.get("snipe_config") or {})

    base = max(1, int(profile.get("damage") or 1)) if weapon else 1
    if weapon:
        damage_min = max(1, int(profile.get("damage_min") or base))
        damage_max = max(damage_min, int(profile.get("damage_max") or damage_min))
        base = max(base, random.randint(damage_min, damage_max))
    damage = base + int(skill_rank * 0.2) + int(suitability * 0.3)
    if skill_rank > 30:
        damage += 2
    damage += int(weapon_effects.get("damage_bonus", 0))
    damage -= min(25, attacker.get_hand_penalty())
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
    if snipe_active and hasattr(attacker, "get_wilderness_bond") and hasattr(attacker, "get_nature_focus"):
        if attacker.get_wilderness_bond() >= int(snipe_config.get("mastery_bond_threshold", 80) or 80) and attacker.get_nature_focus() >= int(snipe_config.get("mastery_focus_threshold", 60) or 60):
            critical = critical or random.randint(1, 100) <= int(snipe_config.get("mastery_crit_bonus", 8) or 8)
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
            damage = int(round(damage * (1 + (ranger_aim_stacks * float(snipe_config.get("aim_damage_per_stack", 0.05) or 0.05)))))

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

    armor_list = target.get_armor_for_bodypart(hit_location) if hasattr(target, "get_armor_for_bodypart") else target.get_armor_covering(hit_location)
    protection = target.get_total_armor_protection(hit_location) if hasattr(target, "get_total_armor_protection") else sum(target.get_armor_protection_value(armor) for armor in armor_list)
    armor_absorbed = False
    if protection:
        damage = max(1, damage - int(round(protection)))
        armor_absorbed = True
    if hasattr(attacker, "apply_death_sting_to_damage"):
        damage = attacker.apply_death_sting_to_damage(damage)

    target_evasion = int(target.get_skill("evasion") or 0) if hasattr(target, "get_skill") else 0
    if skill_rank <= EARLY_GAME_DAMAGE_CLAMP_RANK and target_evasion <= EARLY_GAME_DAMAGE_CLAMP_RANK:
        max_hp = max(1, int(target.db.max_hp or 1))
        damage = min(damage, max(1, int(round(max_hp * EARLY_GAME_DAMAGE_CLAMP_RATIO))))

    damage = max(0, int(damage))
    context["armor_absorbed"] = armor_absorbed
    context["attack_context"] = {"damage_type": damage_type}
    context["critical"] = critical
    context["damage"] = damage
    context["hit_location"] = hit_location
    context["location_name"] = location_name
    context["quality"] = quality
    return damage


def calculate_roundtime(attacker, target, context=None):
    context = context or {}
    profile = context["profile"]
    attacker_berserk = context["attacker_berserk"]
    ambush = context["ambush"]
    partial_ambush = context.get("partial_ambush", False)
    hit = context.get("hit", False)

    action_roundtime = profile.get("speed", profile.get("roundtime", 3.0))
    if attacker_berserk:
        action_roundtime = max(1.0, action_roundtime + float(attacker_berserk.get("roundtime_modifier", 0.0) or 0.0))
    if hasattr(attacker, "is_warrior_overextended") and attacker.is_warrior_overextended():
        action_roundtime += 1
    if ambush:
        if hit:
            action_roundtime = max(action_roundtime, 3.0)
            if getattr(attacker.db, "position_state", "neutral") == "advantaged":
                action_roundtime -= 1
            if partial_ambush:
                action_roundtime += 1
            action_roundtime = max(1, min(action_roundtime, 5))
        else:
            if getattr(attacker.db, "position_state", "neutral") == "advantaged":
                action_roundtime -= 1
            action_roundtime = max(1, min(action_roundtime + 1, 5))

    context["roundtime"] = action_roundtime
    return action_roundtime