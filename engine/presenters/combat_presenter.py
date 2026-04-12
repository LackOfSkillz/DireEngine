from engine.presenters.injury_presenter import InjuryPresenter
from utils.survival_messaging import react_or_message_target


VERBS = {
    "slice": ["slash", "cut", "carve"],
    "impact": ["smash", "crush", "slam"],
    "puncture": ["stab", "pierce", "thrust"],
}


class CombatPresenter:

    @staticmethod
    def conjugate(verb, is_player):
        if is_player:
            return verb
        if verb.endswith(("s", "sh", "ch", "x", "z")):
            return f"{verb}es"
        if verb.endswith("y") and len(verb) > 1 and verb[-2] not in "aeiou":
            return f"{verb[:-1]}ies"
        return f"{verb}s"

    @staticmethod
    def _get_weapon_phrase(data):
        weapon_name = str(data.get("weapon_name", "") or "").strip()
        if not weapon_name:
            return "your fists"
        return f"your {weapon_name}"

    @staticmethod
    def _get_weapon_display_name(data):
        return str(data.get("weapon_name", "") or "their fists")

    @staticmethod
    def _choose_verb(data):
        damage_type = str(data.get("damage_type", "impact") or "impact").strip().lower()
        verb = str(data.get("verb", "") or "").strip().lower()
        if verb:
            return verb
        return VERBS.get(damage_type, ["strike"])[0]

    @staticmethod
    def render_attack(result, attacker, target):
        data = dict(getattr(result, "data", {}) or {})
        attacker_lines = []
        target_lines = []
        room_lines = []
        target_reactions = []

        error_code = str(data.get("error_code", "") or "")
        outcome = str(data.get("outcome", "") or "")
        target_name = str(data.get("target_name", "someone") or "someone")
        attacker_name = str(data.get("attacker_name", "Someone") or "Someone")

        if error_code == "no_target":
            attacker_lines.append("Who do you want to attack?")
        elif error_code == "no_room":
            attacker_lines.append("There is no one here to attack.")
        elif error_code == "target_not_found":
            attacker_lines.append("You do not see that target here.")
        elif error_code == "self_attack":
            attacker_lines.append("Attacking yourself would accomplish very little.")
        elif error_code == "stunned":
            attacker_lines.append("You are too stunned to attack.")
        elif error_code == "roundtime":
            attacker_lines.append("You are still recovering from your last action.")
        elif error_code == "off_balance":
            attacker_lines.append("You are too off balance to make a good attack.")
        elif error_code == "attacker_dead":
            attacker_lines.append("You cannot attack while defeated.")
        elif error_code == "blocked":
            attacker_lines.append(str(data.get("block_message", "You cannot do that right now.") or "You cannot do that right now."))
        elif error_code == "corpse_target":
            attacker_lines.append("There is no life left there to fight.")
        elif error_code == "invalid_target":
            attacker_lines.append(f"You cannot fight {target_name}.")
        elif error_code == "target_dead":
            attacker_lines.append(f"{target_name} is already down.")
        elif error_code == "gm_protected":
            attacker_lines.append("If you had to make one final mistake in life, attacking Jekar would be as good as any you might choose.")
        elif error_code == "collapse":
            attacker_lines.append("Your exhausted body buckles before you can attack.")
            room_lines.append(f"{attacker_name} buckles from exhaustion before attacking {target_name}.")
        elif error_code == "hesitation":
            attacker_lines.append("You hesitate under the assault.")
        elif error_code == "overextended":
            attacker_lines.append("Your overextended limbs lag behind your intent.")
        elif error_code == "needs_ammo":
            attacker_lines.append("You need to load your ranged weapon first.")
        elif error_code == "too_far_melee":
            attacker_lines.append("You are too far away to attack in melee.")
        elif error_code == "ambush_no_opening":
            attacker_lines.append("You fail to find the opening!")

        if outcome == "handled":
            return {"attacker": attacker_lines, "target": target_lines, "room": room_lines, "target_reactions": target_reactions}

        if data.get("surprise_reaction"):
            target_reactions.append({"text": "You are caught completely off guard!", "awareness": "alert"})

        if data.get("ambush_announced"):
            attacker_lines.append(f"You ambush {target_name}!")
            target_reactions.append({"text": f"{attacker_name} ambushes you!", "awareness": "alert"})
            room_lines.append(f"{attacker_name} bursts from hiding and ambushes {target_name}!")

        if outcome == "miss":
            verb = CombatPresenter._choose_verb(data)
            verb_player = CombatPresenter.conjugate(verb, True)
            verb_target = CombatPresenter.conjugate(verb, False)
            weapon_phrase = CombatPresenter._get_weapon_phrase(data)
            weapon_name = CombatPresenter._get_weapon_display_name(data)
            range_phrase = str(data.get("range_phrase", "from nearby cover") or "from nearby cover")
            if data.get("is_ranged_weapon"):
                if data.get("snipe_active"):
                    attacker_lines.append("Your concealed shot misses its mark.")
                    target_lines.append("An arrow flies from nowhere and misses you.")
                    room_lines.append(f"An arrow flies from nowhere toward {target_name}.")
                else:
                    attacker_lines.append(f"You fire at {target_name} {range_phrase} but miss.")
                    target_lines.append(f"{attacker_name} fires at you {range_phrase} but misses.")
                    room_lines.append(f"{attacker_name} fires at {target_name} {range_phrase} but misses.")
            else:
                attacker_lines.append(f"You {verb_player} at {target_name} with {weapon_phrase} but miss.")
                target_lines.append(f"{attacker_name} {verb_target} at you with {weapon_name} but misses.")
                room_lines.append(f"{attacker_name} {verb_target} at {target_name} with {weapon_name} but misses.")
            if data.get("remained_concealed"):
                attacker_lines.append("You remain concealed after the shot.")
            if data.get("revealed_position"):
                attacker_lines.append("Your shot gives away your position!")
                room_lines.append(f"{attacker_name}'s hidden position is revealed.")
        elif outcome in {"hit", "kill"}:
            verb = CombatPresenter._choose_verb(data)
            verb_player = CombatPresenter.conjugate(verb, True)
            verb_target = CombatPresenter.conjugate(verb, False)
            range_phrase = str(data.get("range_phrase", "from nearby cover") or "from nearby cover")
            location_name = str(data.get("location_name", "body") or "body")
            quality = str(data.get("quality", "good") or "good")
            quality_phrase = f"critical {quality}" if data.get("critical") else quality
            weapon_phrase = CombatPresenter._get_weapon_phrase(data)
            if data.get("is_ranged_weapon"):
                if data.get("snipe_active"):
                    attacker_lines.append(f"You release a carefully placed shot from concealment and strike {target_name}'s {location_name}.")
                    target_lines.append(f"An arrow flies from nowhere and strikes your {location_name}.")
                    room_lines.append(f"An arrow flies from nowhere toward {target_name}.")
                else:
                    attacker_lines.append(f"You fire at {target_name}'s {location_name} {range_phrase} with a {quality_phrase} hit.")
                    target_lines.append(f"{attacker_name} fires at your {location_name} {range_phrase} with a {quality_phrase} hit.")
                    room_lines.append(f"{attacker_name} fires at {target_name}'s {location_name} {range_phrase} with a {quality_phrase} hit.")
                if data.get("remained_concealed"):
                    attacker_lines.append("You remain concealed after the shot.")
                if data.get("revealed_position"):
                    attacker_lines.append("Your shot gives away your position!")
                    room_lines.append(f"{attacker_name}'s hidden position is revealed.")
            else:
                attacker_lines.append(f"You {verb_player} {target_name}'s {location_name} with {weapon_phrase} in a {quality_phrase} hit.")
                target_lines.append(f"{attacker_name} {verb_target} your {location_name} with a {quality_phrase} hit.")
                room_lines.append(f"{attacker_name} {verb_target} {target_name}'s {location_name} with a {quality_phrase} hit.")

            if data.get("armor_absorbed"):
                target_lines.append("Your armor absorbs part of the blow.")
            if data.get("sweep_resisted"):
                attacker_lines.append(f"{target_name} resists your sweep and keeps their footing.")
                target_lines.append("You absorb the sweep and keep your footing.")
            if data.get("sweep_knockdown"):
                attacker_lines.append(f"You sweep {target_name} off their feet.")
                target_lines.append("You are driven off your feet!")
            if data.get("whirl_momentum"):
                attacker_lines.append("Your momentum carries through the melee.")
            if data.get("target_alerted"):
                target_lines.append("You become more alert!")
            if data.get("target_regained_bearings"):
                target_lines.append("You regain your bearings!")
            if data.get("weapon_flavor"):
                attacker_lines.append("Your weapon moves like an extension of your will.")
            if data.get("head_stun"):
                target_lines.append("The blow leaves you stunned.")
            if outcome == "kill":
                attacker_lines.append(f"You bring down {target_name}.")
                target_lines.append("You collapse from the blow.")

        return {"attacker": attacker_lines, "target": target_lines, "room": room_lines, "target_reactions": target_reactions}

    @staticmethod
    def present_attack(result, attacker, target):
        payload = CombatPresenter.render_attack(result, attacker, target)
        for line in payload.get("attacker", []):
            attacker.msg(line)
        if target:
            for reaction in payload.get("target_reactions", []):
                react_or_message_target(target, player_text=reaction.get("text"), awareness=reaction.get("awareness"))
            for line in payload.get("target", []):
                target.msg(line)
            InjuryPresenter.present_events(target, payload.get("injury_events", []))
        if getattr(attacker, "location", None):
            for line in payload.get("room", []):
                attacker.location.msg_contents(line, exclude=[obj for obj in [attacker, target] if obj is not None])
        onboarding_feedback = str(getattr(result, "data", {}).get("onboarding_feedback", "") or "")
        if onboarding_feedback:
            attacker.msg(onboarding_feedback)