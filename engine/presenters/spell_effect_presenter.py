class SpellEffectPresenter:
    @staticmethod
    def render_self(result):
        if not getattr(result, "success", False):
            return list(getattr(result, "errors", []) or [])

        payload = dict(result.data.get("effect_payload") or {})
        effect_family = str(payload.get("effect_family", "") or "")
        amount = int(payload.get("heal_amount", 0) or 0)
        self_target = bool(payload.get("self_target", False))
        target_key = str(payload.get("target_key", "someone") or "someone")
        mana_type = str(payload.get("source_mana_type", "") or "").strip().lower()

        if effect_family == "aoe":
            return ["You unleash a burst of energy!"]

        if effect_family == "utility":
            utility_effect = str(payload.get("utility_effect", "utility") or "utility")
            if utility_effect == "light":
                return ["A soft light forms around you."]
            if bool(payload.get("removed", False)):
                return ["You feel lingering effects wash away."]
            return ["You feel momentarily refreshed."]

        if effect_family == "healing":
            if amount <= 0:
                return ["Your spell settles over you, but there is nothing for it to mend."] if self_target else [f"Your spell settles over {target_key}, but there is nothing for it to mend."]
            if self_target:
                if mana_type == "holy":
                    return ["A warm pulse of holy radiance closes some of your wounds."]
                return ["A gentle surge of life closes some of your wounds."]
            if mana_type == "holy":
                return [f"A warm pulse of holy radiance closes some of {target_key}'s wounds."]
            return [f"A gentle surge of life closes some of {target_key}'s wounds."]

        if effect_family == "augmentation":
            buff_name = str(payload.get("buff_name", "spell") or "spell")
            strength = int(payload.get("strength", 0) or 0)
            if self_target:
                return [f"You feel {buff_name} settle into place around you at strength {strength}."]
            return [f"You feel {buff_name} settle into place around {target_key} at strength {strength}."]

        if effect_family == "warding":
            if bool(payload.get("group_target", False)):
                target_count = int(payload.get("target_count", 0) or 0)
                return [f"You extend a protective field over {target_count} allies."]
            strength = int(payload.get("barrier_strength", 0) or 0)
            if self_target:
                return [f"A faint barrier surrounds you with strength {strength}."]
            return [f"A faint barrier surrounds {target_key} with strength {strength}."]

        if effect_family == "cyclic":
            if bool(dict(payload.get("cyclic_state") or {}).get("started", False)):
                return ["You begin sustaining the spell."]
            if not bool(payload.get("hit", True)):
                return [f"Your spell fails to take hold on {target_key}."]
            return []

        if effect_family == "debilitation":
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if not bool(payload.get("hit", False)) or bool(payload.get("ignored", False)):
                return ["The spell fails to take hold."]
            if effect_type == "daze":
                return [f"Your spell leaves {target_key} reeling in a haze."]
            if effect_type == "slow":
                return [f"Your spell drags at {target_key}'s movements."]
            return [f"Your spell hinders {target_key}."]

        if effect_family == "targeted_magic":
            hit = bool(payload.get("hit", False))
            absorbed = float(payload.get("absorbed_by_ward", 0.0) or 0.0)
            final_damage = float(payload.get("final_damage", 0.0) or 0.0)
            hit_quality = str(payload.get("hit_quality", "hit") or "hit")
            hit_verb = {
                "graze": "grazes",
                "hit": "hits",
                "strong": "strikes",
            }.get(hit_quality, "hits")
            if not hit:
                return [f"Your spell misses {target_key}."]
            if absorbed > 0 and final_damage <= 0:
                return [f"Your spell strikes {target_key}, but the barrier absorbs it completely."]
            if absorbed > 0:
                return [f"Your spell {hit_verb} {target_key}, but part of the impact is absorbed by a barrier."]
            return [f"Your spell {hit_verb} {target_key}."]

        return []

    @staticmethod
    def render_target(result):
        if not getattr(result, "success", False):
            return []

        payload = dict(result.data.get("effect_payload") or {})
        effect_family = str(payload.get("effect_family", "") or "")
        if effect_family == "aoe":
            return []
        if effect_family == "utility":
            if bool(payload.get("self_target", False)):
                return []
            utility_effect = str(payload.get("utility_effect", "utility") or "utility")
            if utility_effect == "light":
                return ["A soft light gathers around you."]
            if bool(payload.get("removed", False)):
                return ["The lingering hostile magic around you washes away."]
            return []
        if effect_family == "augmentation":
            if bool(payload.get("self_target", False)):
                return []
            buff_name = str(payload.get("buff_name", "spell") or "spell")
            return [f"You feel {buff_name} settle around you."]

        if effect_family == "warding":
            if bool(payload.get("group_target", False)):
                return ["A protective field settles over you."]
            if bool(payload.get("self_target", False)):
                return []
            return ["A faint barrier settles around you."]

        if effect_family == "debilitation":
            if not bool(payload.get("hit", False)) or bool(payload.get("ignored", False)):
                return []
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if effect_type == "daze":
                return ["You feel your thoughts blur."]
            if effect_type == "slow":
                return ["Your limbs grow heavy and sluggish."]
            return ["A hostile spell takes hold of you."]

        if effect_family == "targeted_magic":
            if not bool(payload.get("hit", False)):
                return ["A spell flashes past you without landing."]
            if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                return ["Your barrier catches the spell completely."]
            if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0:
                return ["A barrier around you blunts part of the spell's force."]
            return ["The spell slams into you."]

        if effect_family == "cyclic":
            if not bool(payload.get("hit", True)):
                return ["A sustained spell fails to take hold on you."]
            return []

        if effect_family != "healing":
            return []
        if bool(payload.get("self_target", False)):
            return []

        amount = int(payload.get("heal_amount", 0) or 0)
        mana_type = str(payload.get("source_mana_type", "") or "").strip().lower()
        if amount <= 0:
            return ["A soft restorative warmth passes over you, but nothing changes."]
        if mana_type == "holy":
            return ["A warm pulse of holy radiance passes over you, easing some of your pain."]
        return ["A soft restorative warmth passes over you, easing some of your pain."]

    @staticmethod
    def render_room(result, caster_key):
        if not getattr(result, "success", False):
            return None

        payload = dict(result.data.get("effect_payload") or {})
        effect_family = str(payload.get("effect_family", "") or "")
        if effect_family == "aoe":
            return f"{caster_key} unleashes a burst of energy!"
        if effect_family == "utility":
            utility_effect = str(payload.get("utility_effect", "utility") or "utility")
            if utility_effect == "light":
                return f"A soft light gathers around {caster_key}."
            if bool(payload.get("removed", False)):
                return f"A cleansing wash passes over {caster_key}."
            return f"A brief shimmer passes over {caster_key}."
        if effect_family == "augmentation":
            target_key = str(payload.get("target_key", "someone") or "someone")
            buff_name = str(payload.get("buff_name", "spell") or "spell")
            if bool(payload.get("self_target", False)):
                return f"{caster_key} gathers {buff_name} inward."
            return f"{caster_key} settles {buff_name} over {target_key}."

        if effect_family == "warding":
            if bool(payload.get("group_target", False)):
                return f"{caster_key} extends a protective field over the group."
            target_key = str(payload.get("target_key", "someone") or "someone")
            if bool(payload.get("self_target", False)):
                return f"{caster_key} draws a barrier tight around themselves."
            return f"{caster_key} settles a barrier around {target_key}."

        if effect_family == "debilitation":
            target_key = str(payload.get("target_key", "someone") or "someone")
            if not bool(payload.get("hit", False)) or bool(payload.get("ignored", False)):
                return f"{caster_key}'s spell fails to take hold on {target_key}."
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if effect_type == "daze":
                return f"{caster_key}'s spell leaves {target_key} looking dazed."
            if effect_type == "slow":
                return f"{caster_key}'s spell drags at {target_key}'s movement."
            return f"{caster_key}'s spell hinders {target_key}."

        if effect_family == "targeted_magic":
            target_key = str(payload.get("target_key", "someone") or "someone")
            if not bool(payload.get("hit", False)):
                return f"{caster_key}'s spell misses {target_key}."
            if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                return f"{caster_key}'s spell crashes harmlessly against {target_key}'s barrier."
            if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0:
                return f"{caster_key}'s spell strikes {target_key}, but a barrier catches part of it."
            return f"{caster_key}'s spell strikes {target_key}."

        if effect_family == "cyclic":
            if not bool(payload.get("hit", True)):
                return f"{caster_key}'s sustained spell fails to take hold on {str(payload.get('target_key', 'someone') or 'someone')}."
            if bool(dict(payload.get("cyclic_state") or {}).get("started", False)):
                return f"{caster_key} begins sustaining a spell."
            return None

        if effect_family != "healing":
            return None

        target_key = str(payload.get("target_key", "someone") or "someone")
        mana_type = str(payload.get("source_mana_type", "") or "").strip().lower()
        if bool(payload.get("self_target", False)):
            if mana_type == "holy":
                return f"{caster_key} draws a warm pulse of holy radiance inward."
            return f"{caster_key} draws a gentle wash of life inward."
        if mana_type == "holy":
            return f"{caster_key} lays a warm pulse of holy radiance over {target_key}."
        return f"{caster_key} lays a gentle wash of life over {target_key}."

    @staticmethod
    def render_expiration(effect_payload):
        payload = dict(effect_payload or {})
        if str(payload.get("effect_family", "") or "") == "cyclic":
            reason = str(payload.get("collapse_reason", "") or "")
            if reason == "insufficient_mana":
                return ["You lose control of the spell."]
            if reason == "interrupted":
                return ["The sustained spell breaks under interference."]
            if reason == "caster_dead":
                return ["Your sustained spell dies with you."]
            if reason == "invalid_target":
                return ["Your sustained spell unravels as its target slips away."]
            return ["Your sustained spell ends."]
        if str(payload.get("effect_family", "") or "") == "utility":
            if str(payload.get("effect_type", "") or "") == "light":
                return ["The soft light around you fades."]
            return []
        if str(payload.get("effect_family", "") or "") != "debilitation":
            return []
        effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
        if effect_type == "daze":
            return ["You shake off the daze."]
        if effect_type == "slow":
            return ["Your movement quickens as the slowing magic fades."]
        return ["The hostile magic loses its hold on you."]