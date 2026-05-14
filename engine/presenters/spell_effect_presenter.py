class SpellEffectPresenter:
    @staticmethod
    def _get_spell_id(result, payload):
        if result is not None:
            return str(result.data.get("spell_id", payload.get("spell_id", "")) or "").strip().lower()
        return str(payload.get("spell_id", "") or "").strip().lower()

    @staticmethod
    def render_self(result):
        if not getattr(result, "success", False):
            return list(getattr(result, "errors", []) or [])

        payload = dict(result.data.get("effect_payload") or {})
        effect_family = str(payload.get("effect_family", "") or "")
        spell_id = SpellEffectPresenter._get_spell_id(result, payload)
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
            if utility_effect == "gauge_flow":
                return ["You complete the cast. Your senses extend outward, perceiving the flow of magical energies around you."]
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
            if spell_id == "manifest_force":
                return ["You complete the cast. A faintly shimmering barrier of pure force coalesces around you, ready to absorb incoming blows."]
            if self_target:
                return [f"A faint barrier surrounds you with strength {strength}."]
            return [f"A faint barrier surrounds {target_key} with strength {strength}."]

        if effect_family == "cyclic":
            if bool(dict(payload.get("cyclic_state") or {}).get("started", False)):
                spell_name = str(result.data.get("spell_name", payload.get("spell_name", "the spell")) or "the spell")
                sustain_source = str(dict(payload.get("cyclic_state") or {}).get("sustain_source", payload.get("sustain_source", "held_mana")) or "held_mana")
                if sustain_source == "attunement":
                    return [f"You channel the cyclic spell of {spell_name} directly from your attunement. The pattern stabilizes around you, drawing raw mana from your essence."]
                return [f"You channel the cyclic spell of {spell_name} from your held mana. The pattern stabilizes around you."]
            if not bool(payload.get("hit", True)):
                return [f"Your spell fails to take hold on {target_key}."]
            return []

        if effect_family == "debilitation":
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if not bool(payload.get("hit", False)) or bool(payload.get("ignored", False)):
                if effect_type == "burden":
                    return [f"Your spell completes at {target_key}, but the energy slips away without taking hold."]
                return ["The spell fails to take hold."]
            if effect_type == "burden":
                return [f"You complete the cast at {target_key}. A weight settles onto them, dragging at them."]
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
                if spell_id == "strange_arrow":
                    return [f"Your spell completes at {target_key}, but the arrow goes wide, dissipating in a shower of sparks."]
                return [f"Your spell misses {target_key}."]
            if spell_id == "strange_arrow":
                if absorbed > 0 and final_damage <= 0:
                    return [f"You complete the cast at {target_key}. A jagged arrow of crackling energy lances out, but a barrier breaks it apart harmlessly."]
                return [f"You complete the cast at {target_key}. A jagged arrow of crackling energy lances out and strikes them for {int(final_damage)} damage!"]
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
        spell_id = SpellEffectPresenter._get_spell_id(result, payload)
        if effect_family == "aoe":
            return []
        if effect_family == "utility":
            if bool(payload.get("self_target", False)):
                return []
            utility_effect = str(payload.get("utility_effect", "utility") or "utility")
            if utility_effect == "light":
                return ["A soft light gathers around you."]
            if utility_effect == "gauge_flow":
                return []
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
            if spell_id == "manifest_force":
                return ["A faintly shimmering barrier of pure force coalesces around you."]
            return ["A faint barrier settles around you."]

        if effect_family == "debilitation":
            if not bool(payload.get("hit", False)) or bool(payload.get("ignored", False)):
                if str(payload.get("effect_type", "") or "") == "burden":
                    caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                    return [f"{caster_key}'s spell completes at you, but you shake off its weight."]
                return []
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if effect_type == "burden":
                caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                return [f"{caster_key} completes a spell at you. A sudden weight settles onto your shoulders, dragging at you. You feel weaker and burdened."]
            if effect_type == "daze":
                return ["You feel your thoughts blur."]
            if effect_type == "slow":
                return ["Your limbs grow heavy and sluggish."]
            return ["A hostile spell takes hold of you."]

        if effect_family == "targeted_magic":
            if not bool(payload.get("hit", False)):
                if spell_id == "strange_arrow":
                    caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                    return [f"{caster_key}'s spell completes at you, but the arrow misses, sparks scattering past you."]
                return ["A spell flashes past you without landing."]
            if spell_id == "strange_arrow":
                if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                    return ["A barrier around you catches the crackling arrow completely."]
                caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                return [f"{caster_key}'s spell completes at you. A jagged arrow of crackling energy lances into you, dealing {int(float(payload.get('final_damage', 0.0) or 0.0))} damage!"]
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
        spell_id = SpellEffectPresenter._get_spell_id(result, payload)
        if effect_family == "aoe":
            return f"{caster_key} unleashes a burst of energy!"
        if effect_family == "utility":
            utility_effect = str(payload.get("utility_effect", "utility") or "utility")
            if utility_effect == "light":
                return f"A soft light gathers around {caster_key}."
            if utility_effect == "gauge_flow":
                return f"{caster_key} completes a spell. Their gaze becomes distant, attuned to something beyond the visible."
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
            if spell_id == "manifest_force":
                return f"{caster_key} completes a spell. A faintly shimmering barrier of pure force coalesces around them."
            if bool(payload.get("self_target", False)):
                return f"{caster_key} draws a barrier tight around themselves."
            return f"{caster_key} settles a barrier around {target_key}."

        if effect_family == "debilitation":
            target_key = str(payload.get("target_key", "someone") or "someone")
            if not bool(payload.get("hit", False)) or bool(payload.get("ignored", False)):
                if str(payload.get("effect_type", "") or "") == "burden":
                    return f"{caster_key}'s spell completes at {target_key}, but the energy dissipates without effect."
                return f"{caster_key}'s spell fails to take hold on {target_key}."
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if effect_type == "burden":
                return f"{caster_key}'s spell completes at {target_key}. {target_key} sags visibly, looking suddenly burdened."
            if effect_type == "daze":
                return f"{caster_key}'s spell leaves {target_key} looking dazed."
            if effect_type == "slow":
                return f"{caster_key}'s spell drags at {target_key}'s movement."
            return f"{caster_key}'s spell hinders {target_key}."

        if effect_family == "targeted_magic":
            target_key = str(payload.get("target_key", "someone") or "someone")
            if not bool(payload.get("hit", False)):
                if spell_id == "strange_arrow":
                    return f"{caster_key}'s spell completes at {target_key}, the arrow missing and dissipating in scattered sparks."
                return f"{caster_key}'s spell misses {target_key}."
            if spell_id == "strange_arrow":
                if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                    return f"{caster_key}'s spell completes at {target_key}, but the crackling arrow splinters against a barrier."
                return f"{caster_key}'s spell completes at {target_key}. A jagged arrow of crackling energy strikes {target_key} with a sharp crack of thunder."
            if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                return f"{caster_key}'s spell crashes harmlessly against {target_key}'s barrier."
            if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0:
                return f"{caster_key}'s spell strikes {target_key}, but a barrier catches part of it."
            return f"{caster_key}'s spell strikes {target_key}."

        if effect_family == "cyclic":
            if not bool(payload.get("hit", True)):
                return f"{caster_key}'s sustained spell fails to take hold on {str(payload.get('target_key', 'someone') or 'someone')}."
            if bool(dict(payload.get("cyclic_state") or {}).get("started", False)):
                sustain_source = str(dict(payload.get("cyclic_state") or {}).get("sustain_source", payload.get("sustain_source", "held_mana")) or "held_mana")
                if sustain_source == "attunement":
                    return f"{caster_key} draws raw mana from their essence into a sustained spell pattern."
                return f"{caster_key} completes a complex spell weaving; tendrils of mana flow from their held mana into a sustained pattern."
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
            spell_name = str(payload.get("spell_name", payload.get("effect_type", "the spell")) or "the spell").replace("_", " ")
            sustain_source = str(payload.get("sustain_source", "held_mana") or "held_mana")
            if reason == "insufficient_held_mana":
                return [f"Your {spell_name} pattern collapses as your held mana runs dry. You feel the sustained magic dissipate."]
            if reason == "insufficient_attunement":
                return [f"Your {spell_name} pattern collapses as your attunement runs dry. You feel the sustained magic dissipate."]
            if reason == "raw_channeling_lost":
                return [f"Without Raw Channeling, you can no longer sustain {spell_name} from your attunement directly. The pattern collapses."]
            if reason == "cambrinth_subsystem_not_yet_implemented":
                return ["Cambrinth sustain is not yet available. The sustained pattern collapses."]
            if reason == "insufficient_mana":
                if sustain_source == "attunement":
                    return [f"Your {spell_name} pattern collapses as your attunement runs dry. You feel the sustained magic dissipate."]
                return [f"Your {spell_name} pattern collapses as your held mana runs dry. You feel the sustained magic dissipate."]
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
            if str(payload.get("effect_type", "") or "") == "gauge_flow":
                return ["Your extended awareness of magical flows fades. You return to ordinary perception."]
            return []
        if str(payload.get("effect_family", "") or "") == "warding":
            effect_name = str(payload.get("effect_type", payload.get("spell_id", "")) or "")
            if effect_name == "manifest_force":
                return ["The shimmering barrier of force around you fades and dissipates as its spell ends."]
            return []
        if str(payload.get("effect_family", "") or "") != "debilitation":
            return []
        effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
        if effect_type == "burden":
            return ["The weight burdening you lifts. You feel your strength returning."]
        if effect_type == "daze":
            return ["You shake off the daze."]
        if effect_type == "slow":
            return ["Your movement quickens as the slowing magic fades."]
        return ["The hostile magic loses its hold on you."]

    @staticmethod
    def render_expiration_room(effect_payload, subject_key):
        payload = dict(effect_payload or {})
        effect_family = str(payload.get("effect_family", "") or "")
        effect_name = str(payload.get("effect_type", payload.get("spell_id", "")) or "")
        if effect_family == "cyclic":
            return f"{subject_key}'s sustained spell pattern collapses, the magic dissipating into the air."
        if effect_family == "warding" and effect_name == "manifest_force":
            return f"The shimmering barrier of force around {subject_key} fades and dissipates."
        if effect_family == "utility" and str(payload.get("effect_type", "") or "") == "gauge_flow":
            return f"{subject_key}'s distant gaze refocuses on the present."
        if effect_family == "debilitation" and str(payload.get("effect_type", "") or "") == "burden":
            return f"{subject_key} straightens up, looking less burdened."
        return None