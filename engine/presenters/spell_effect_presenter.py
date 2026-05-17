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
            if utility_effect == "hands_of_lirisa":
                if self_target:
                    return ["A warm confidence settles into your hands, sharpening your feel for skinning work ahead."]
                return [f"A warm confidence settles into {target_key}'s hands, readying them for cleaner skinning work."]
            if utility_effect == "earth_meld":
                if self_target:
                    return ["Your awareness sinks into the land around you, revealing nearby concealment in every fold of terrain."]
                return [f"{target_key}'s awareness sinks into the land around them, alert to nearby concealment."]
            if utility_effect == "wolf_scent":
                if self_target:
                    return ["Your awareness blossoms outward as every nearby scent sharpens into vivid detail."]
                return [f"A keen predatory awareness settles over {target_key}, sharpening every scent around them."]
            if utility_effect == "spider_climb":
                if self_target:
                    return ["Your hands and feet seem to find purchase where none should exist."]
                return [f"{target_key} suddenly looks certain-footed enough to climb nearly anything."]
            if utility_effect == "eagle_vision":
                return ["Your sight stretches outward until distant details snap into perfect focus."]
            if utility_effect == "blend":
                return ["You blur into the surrounding terrain until you are all but impossible to pick out."]
            if utility_effect == "breathe_water":
                return ["Your chest tightens, then relaxes as your body adapts to draw breath from the water itself."]
            if utility_effect == "caiman_swim":
                if self_target:
                    return ["Your body settles into the water's rhythm, ready to cut through it with easy power."]
                return [f"{target_key} seems to settle into the water's rhythm, ready to swim with uncanny ease."]
            if utility_effect == "wisdom_of_the_pack":
                return ["A calm pack-instinct settles into you, sharpening your discipline through shared purpose."]
            if utility_effect == "refresh":
                if self_target:
                    if int(payload.get("fatigue_reduced", 0) or 0) <= 0:
                        return ["A bright wave of life passes through you, but there is little fatigue left for it to lift."]
                    return ["A bright wave of life passes through you, easing away weariness."]
                return [f"A bright wave of life passes through {target_key}, easing away their weariness."]
            if utility_effect == "raise_power":
                return ["You drive the Life mana around you into a higher pulse, leaving your whole group spent."]
            if utility_effect == "gift_of_life":
                return ["You draw Gift of Life inward, strengthening your empathic poise and hardening your reserves."]
            if utility_effect == "innocence":
                if int(payload.get("undead_backfire_count", 0) or 0) > 0:
                    return ["A quiet stillness settles around you, but the dead recoil from it with sudden malice."]
                return ["A quiet stillness settles around you, signaling to nearby threats that you are no danger."]
            if utility_effect == "flush_poisons":
                if int(payload.get("removed_amount", 0) or 0) <= 0:
                    return ["A purifying warmth courses through you, but there is no venom left for it to drive out."]
                return ["A purifying warmth courses through you, driving venom out of your blood."]
            if utility_effect == "cure_disease":
                if int(payload.get("removed_amount", 0) or 0) <= 0:
                    return ["Your body warms with renewed vitality, but there is no illness left for the spell to break."]
                return ["Your body warms with renewed vitality as illness gives way before the spell's working."]
            if utility_effect == "bless":
                if self_target:
                    return ["A pure holy radiance settles over you, readying your hands and weapon against the unclean."]
                return [f"A pure holy radiance settles over {target_key}, readying them against the unclean."]
            if utility_effect == "spirit_beacon":
                return [f"You anchor a spirit beacon here, fixing your departing soul toward {payload.get('recovery_point_key', 'your refuge')}."]
            if utility_effect == "uncurse":
                if bool(payload.get("death_sting_relieved", False)):
                    return [f"You invoke Uncurse upon {target_key}, easing Death's Sting and washing hostile magic away."]
                return [f"You invoke Uncurse upon {target_key}, washing hostile magic away."]
            if utility_effect == "revelation":
                if bool(payload.get("revealed", False)):
                    return [f"You invoke Revelation upon {target_key}, wrenching them into plain sight."]
                return [f"You invoke Revelation upon {target_key}, but they are already plainly visible."]
            if utility_effect == "water_purification":
                return [f"You cast powdered charcoal into the water around {payload.get('room_key', 'you')}, and the currents clear under a soft blue glow."]
            if utility_effect == "compost":
                return [f"You call rich Life mana into {payload.get('room_key', 'the ground')}, quickening decay and the churn of rot."]
            if utility_effect == "swarm":
                return [f"You call a stinging swarm onto {target_key}, and the air around them erupts with angry motion."]
            if utility_effect == "awaken_forest":
                return ["The trees around you shudder awake, their branches bending as though listening for your enemies."]
            if utility_effect == "plague_of_scavengers":
                return [f"You seed {target_key} with a droning plague, and hungry scavengers answer the call around them."]
            if utility_effect == "light":
                if spell_id == "holy_light":
                    return ["Holy light blossoms around you, casting back the gloom."]
                return ["A soft light forms around you."]
            if utility_effect == "gauge_flow":
                return ["You complete the cast. Your senses extend outward, perceiving the flow of magical energies around you."]
            if bool(payload.get("removed", False)):
                return ["You feel lingering effects wash away."]
            return ["You feel momentarily refreshed."]

        if effect_family == "healing":
            healing_mode = str(payload.get("healing_mode", "hp") or "hp")
            if amount <= 0:
                if spell_id == "heal" or healing_mode == "combined_heal":
                    return ["Your spell reaches through wounds and scars alike, but there is nothing left for it to restore."]
                if spell_id == "external_wound_healing" or healing_mode == "external_wounds":
                    return ["A focused warmth passes over your skin, but there are no fresh external wounds to close."]
                if spell_id == "internal_wound_healing" or healing_mode == "internal_wounds":
                    return ["A focused warmth settles beneath your skin, but there are no internal wounds to mend."]
                if spell_id == "heal_scars":
                    return ["Your spell passes over you, but there are no scars for it to ease."]
                if spell_id == "heal_wounds" or healing_mode == "empath_wounds":
                    return ["Your spell settles into your carried wounds, but there is nothing for it to mend."]
                return ["Your spell settles over you, but there is nothing for it to mend."] if self_target else [f"Your spell settles over {target_key}, but there is nothing for it to mend."]
            if self_target:
                if spell_id == "heal" or healing_mode == "combined_heal":
                    return ["A deep, encompassing warmth knits wounds and scars together at once, though the broad effort lacks the precision of a narrower working."]
                if spell_id == "external_wound_healing" or healing_mode == "external_wounds":
                    return ["A focused warmth gathers across your skin, knitting fresh external injuries closed."]
                if spell_id == "internal_wound_healing" or healing_mode == "internal_wounds":
                    return ["A focused warmth gathers deep beneath your skin, knitting fresh internal injuries closed."]
                if spell_id == "vitality_healing":
                    return ["Life floods back through you, restoring strength spent in service to others."]
                if spell_id == "heal_wounds" or healing_mode == "empath_wounds":
                    return ["A steady wash of life knits your carried wounds back toward wholeness."]
                if spell_id == "heal_scars" or healing_mode == "scars":
                    return ["A slow warmth works through old scar tissue, easing what once seemed permanent."]
                if mana_type == "holy":
                    return ["A warm pulse of holy radiance closes some of your wounds."]
                return ["A gentle surge of life closes some of your wounds."]
            if mana_type == "holy":
                return [f"A warm pulse of holy radiance closes some of {target_key}'s wounds."]
            return [f"A gentle surge of life closes some of {target_key}'s wounds."]

        if effect_family == "resurrection":
            if spell_id == "rejuvenation":
                return [f"You cast Rejuvenation over {target_key}, calling them back from death through a surge of holy will."]
            if spell_id == "mass_rejuvenation":
                return ["A broad resurrection rite stirs, but the held-mana ritual does not yet answer your call."]
            return [f"You call {target_key} back from death."]

        if effect_family == "augmentation":
            buff_name = str(payload.get("buff_name", "spell") or "spell")
            strength = int(payload.get("strength", 0) or 0)
            if spell_id == "see_the_wind":
                if self_target:
                    return ["You sense every shift in motion around you, as though the wind itself were guiding your aim."]
                return [f"{target_key}'s movements sharpen with a sudden awareness of every shift in the air."]
            if spell_id == "cheetah_swiftness":
                if self_target:
                    return ["A taut, restless speed coils through your limbs, urging you into sudden motion."]
                return [f"A taut, restless speed coils through {target_key}'s limbs."]
            if spell_id == "bear_strength":
                if self_target:
                    return ["A dense surge of power settles into your frame, heavy and unyielding as a bear's strength."]
                return [f"A dense surge of power settles into {target_key}'s frame."]
            if spell_id == "grizzly_claw":
                if self_target:
                    return ["Your hands ache with phantom claws, but the spell refuses to settle on you."]
                return [f"A fierce predatory edge settles over {target_key}'s hands, as if invisible claws had unsheathed."]
            if spell_id == "senses_of_the_tiger":
                if self_target:
                    return ["Your senses tighten into a hunter's focus, every opening suddenly easier to read."]
                return [f"{target_key}'s gaze hardens with a hunter's focus."]
            if self_target:
                return [f"You feel {buff_name} settle into place around you at strength {strength}."]
            return [f"You feel {buff_name} settle into place around {target_key} at strength {strength}."]

        if effect_family == "warding":
            if bool(payload.get("group_target", False)):
                target_count = int(payload.get("target_count", 0) or 0)
                if spell_id == "zone_of_protection":
                    if target_count <= 1:
                        return ["A large translucent sphere forms around you, warding against hostile Life magic."]
                    return ["A large translucent sphere forms around you and your group, warding against hostile Life magic."]
                return [f"You extend a protective field over {target_count} allies."]
            strength = int(payload.get("barrier_strength", 0) or 0)
            if spell_id == "major_physical_protection":
                if self_target:
                    return ["A broad silver ward settles over you, hardening into a stronger bulwark against physical blows."]
                return [f"A broad silver ward settles over {target_key}, hardening into a stronger bulwark against physical blows."]
            if spell_id == "halo":
                if self_target:
                    return ["Pinpoints of intense white light erupt around you, gathering into a dormant halo of force."]
                return [f"Pinpoints of intense white light erupt around {target_key}, gathering into a dormant halo of force."]
            if spell_id == "protection_from_evil":
                if self_target:
                    return ["A soft white glow settles over you, turning aside unholy menace."]
                return [f"A soft white glow settles over {target_key}, turning aside unholy menace."]
            if spell_id == "divine_radiance":
                if self_target:
                    return ["A radiant holy aura surrounds you, spilling light and sheltering you from the unclean."]
                return [f"A radiant holy aura surrounds {target_key}, spilling light and sheltering them from the unclean."]
            if spell_id == "minor_physical_protection":
                if self_target:
                    return ["A soft silver ward settles over you, ready to blunt incoming strikes."]
                return [f"A soft silver ward settles over {target_key}, ready to blunt incoming strikes."]
            if spell_id == "manifest_force":
                return ["You complete the cast. A faintly shimmering barrier of pure force coalesces around you, ready to absorb incoming blows."]
            if self_target:
                return [f"A faint barrier surrounds you with strength {strength}."]
            return [f"A faint barrier surrounds {target_key} with strength {strength}."]

        if effect_family == "cyclic":
            if bool(dict(payload.get("cyclic_state") or {}).get("started", False)):
                spell_name = str(result.data.get("spell_name", payload.get("spell_name", "the spell")) or "the spell")
                sustain_source = str(dict(payload.get("cyclic_state") or {}).get("sustain_source", payload.get("sustain_source", "held_mana")) or "held_mana")
                if spell_name == "the spell":
                    return ["You begin sustaining the spell."]
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
            if effect_type == "haraweps_bonds":
                return [f"Your spell lashes {target_key} in sticky webbing, binding their movement."]
            if effect_type == "slow":
                return [f"Your spell drags at {target_key}'s movements."]
            if effect_type == "hobble":
                return [f"Your spell tangles around {target_key}'s legs, hobbling their movement."]
            if effect_type == "branch_break":
                damage = int(payload.get("final_damage", 0) or 0)
                if damage > 0:
                    return [f"You wrench a snapping branch down onto {target_key}, striking them for {damage} damage."]
                return [f"You wrench a snapping branch down onto {target_key}."]
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
                if spell_id == "aesrela_everild":
                    return [f"You invoke Aesrela Everild at {target_key}, but the silver flames fail to find their mark."]
                if spell_id == "hand_of_tenemlor":
                    return [f"You invoke Hand of Tenemlor at {target_key}, but the divine fire misses them."]
                if spell_id == "strange_arrow":
                    return [f"Your spell completes at {target_key}, but the arrow goes wide, dissipating in a shower of sparks."]
                return [f"Your spell misses {target_key}."]
            if spell_id == "aesrela_everild":
                if absorbed > 0 and final_damage <= 0:
                    return [f"You invoke Aesrela Everild at {target_key}. Silver flame crashes against a barrier and gutters out."]
                if bool(payload.get("stunned", False)):
                    return [f"You invoke Aesrela Everild at {target_key}. Bolts of silver flame hammer into them, leaving them stunned."]
                return [f"You invoke Aesrela Everild at {target_key}. Bolts of silver flame hammer into them."]
            if spell_id == "hand_of_tenemlor":
                if absorbed > 0 and final_damage <= 0:
                    return [f"You invoke Hand of Tenemlor at {target_key}. The burning divine hand splashes harmlessly across a barrier."]
                return [f"You invoke Hand of Tenemlor at {target_key}. A cauterizing hand of holy fire sears their left hand for {int(final_damage)} damage!"]
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
            if utility_effect == "hands_of_lirisa":
                return ["A warm confidence settles into your hands, making skinning work feel suddenly surer."]
            if utility_effect == "earth_meld":
                return ["Your awareness spreads into the ground around you, making concealed things feel easier to notice."]
            if utility_effect == "wolf_scent":
                return ["Your awareness suddenly sharpens as every nearby scent becomes easy to separate."]
            if utility_effect == "spider_climb":
                return ["The world suddenly seems full of handholds and footholds that should not exist."]
            if utility_effect == "eagle_vision":
                return ["Your sight sharpens until even distant detail feels close at hand."]
            if utility_effect == "blend":
                return []
            if utility_effect == "breathe_water":
                return []
            if utility_effect == "caiman_swim":
                return ["The water around you suddenly feels easy to master."]
            if utility_effect == "wisdom_of_the_pack":
                return []
            if utility_effect == "refresh":
                if int(payload.get("fatigue_reduced", 0) or 0) <= 0:
                    return ["A bright wave of life washes through you, but there is little fatigue left for it to lift."]
                return ["A bright wave of life washes through you, easing away some of your weariness."]
            if utility_effect == "bless":
                return ["Holy radiance settles over you, leaving you ready against the unclean."]
            if utility_effect == "uncurse":
                if bool(payload.get("death_sting_relieved", False)):
                    return ["A merciful cleansing eases Death's Sting and strips hostile magic away."]
                return ["A merciful cleansing strips hostile magic away."]
            if utility_effect == "revelation":
                if bool(payload.get("revealed", False)):
                    return ["A divine flash strips away your concealment and leaves you exposed."]
                return ["A divine scrutiny passes over you."]
            if utility_effect == "swarm":
                return ["A furious cloud of biting insects converges around you."]
            if utility_effect == "plague_of_scavengers":
                return ["A droning mass of scavengers fixes on you, surging in with hungry intent."]
            if utility_effect == "light":
                if spell_id == "holy_light":
                    return ["Holy light blossoms around you, driving back the gloom."]
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
            if spell_id == "see_the_wind":
                return ["A preternatural awareness of movement settles over you."]
            if spell_id == "cheetah_swiftness":
                return ["A taut, restless speed settles into your limbs."]
            if spell_id == "bear_strength":
                return ["A dense, heavy strength settles into your frame."]
            if spell_id == "grizzly_claw":
                return ["A fierce predatory edge settles over your hands, as if invisible claws had unsheathed."]
            if spell_id == "senses_of_the_tiger":
                return ["Your senses sharpen into a hunter's focus."]
            return [f"You feel {buff_name} settle around you."]

        if effect_family == "resurrection":
            if spell_id == "rejuvenation":
                return ["A surge of holy will catches you and drags you back from death."]
            return []

        if effect_family == "warding":
            if bool(payload.get("group_target", False)) and spell_id == "zone_of_protection":
                return ["A large translucent sphere forms around you, shimmering with protective Life resonance."]
            if bool(payload.get("group_target", False)):
                return ["A protective field settles over you."]
            if bool(payload.get("self_target", False)):
                return []
            if spell_id == "major_physical_protection":
                return ["A broad silver ward settles around you, hardening against physical blows."]
            if spell_id == "halo":
                return ["Pinpoints of intense white light gather around you in a dormant halo."]
            if spell_id == "protection_from_evil":
                return ["A soft white glow settles around you, warding off unholy force."]
            if spell_id == "divine_radiance":
                return ["A radiant holy aura settles around you, casting back the gloom."]
            if spell_id == "minor_physical_protection":
                return ["A soft silver ward settles around you, ready to blunt incoming blows."]
            if spell_id == "manifest_force":
                return ["A faintly shimmering barrier of pure force coalesces around you."]
            return ["A faint barrier settles around you."]

        if effect_family == "debilitation":
            if not bool(payload.get("hit", False)) or bool(payload.get("ignored", False)):
                if str(payload.get("effect_type", "") or "") == "burden":
                    caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                    return [f"{caster_key}'s spell completes at you, but you shake off its weight."]
                if str(payload.get("effect_type", "") or "") == "mesmerize":
                    return ["The spell brushes your thoughts, but you shake it off."]
                return []
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if effect_type == "burden":
                caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                return [f"{caster_key} completes a spell at you. A sudden weight settles onto your shoulders, dragging at you. You feel weaker and burdened."]
            if effect_type == "daze":
                return ["You feel your thoughts blur."]
            if effect_type == "mesmerize":
                return ["A pacifying haze settles over your thoughts, draining away any urge to attack."]
            if effect_type == "haraweps_bonds":
                return ["Sticky bindings cinch around you, making every step a struggle."]
            if effect_type == "slow":
                return ["Your limbs grow heavy and sluggish."]
            if effect_type == "hobble":
                return ["Your legs tangle under sudden restraining magic."]
            if effect_type == "branch_break":
                damage = int(payload.get("final_damage", 0) or 0)
                if damage > 0:
                    return [f"A breaking branch slams into you for {damage} damage!"]
                return ["A breaking branch crashes into you."]
            return ["A hostile spell takes hold of you."]

        if effect_family == "targeted_magic":
            if not bool(payload.get("hit", False)):
                if spell_id == "aesrela_everild":
                    caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                    return [f"{caster_key}'s silver flame bolts streak past you and fade."]
                if spell_id == "hand_of_tenemlor":
                    return ["A blazing hand of divine fire lashes out, but misses you."]
                if spell_id == "strange_arrow":
                    caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                    return [f"{caster_key}'s spell completes at you, but the arrow misses, sparks scattering past you."]
                return ["A spell flashes past you without landing."]
            if spell_id == "aesrela_everild":
                if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                    return ["Your barrier catches the silver flame and smothers it."]
                if bool(payload.get("stunned", False)):
                    return ["Silver flame bolts hammer into you and leave you reeling, stunned."]
                return ["Silver flame bolts hammer into you."]
            if spell_id == "hand_of_tenemlor":
                if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                    return ["Your barrier catches the burning hand before it can sear you."]
                caster_key = str(payload.get("caster_key", "Someone") or "Someone")
                return [f"{caster_key}'s spell sears your left hand with holy fire, dealing {int(float(payload.get('final_damage', 0.0) or 0.0))} damage!"]
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
        healing_mode = str(payload.get("healing_mode", "hp") or "hp")

        amount = int(payload.get("heal_amount", 0) or 0)
        mana_type = str(payload.get("source_mana_type", "") or "").strip().lower()
        if amount <= 0:
            if spell_id == "vitality_healing":
                return f"{caster_key} draws life back into themselves, looking visibly steadier."
            if spell_id == "heal_wounds" or healing_mode == "empath_wounds":
                return f"A patient wash of life settles over {caster_key}, knitting their carried wounds toward wholeness."
            if spell_id == "heal_scars" or healing_mode == "scars":
                return f"A slow restorative warmth passes over {caster_key}'s old scars."
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
            if utility_effect == "hands_of_lirisa":
                target_key = str(payload.get("target_key", caster_key) or caster_key)
                if bool(payload.get("self_target", False)):
                    return f"{caster_key}'s hands steady with a hunter's confidence."
                return f"{caster_key} settles a hunter's confidence over {target_key}."
            if utility_effect == "earth_meld":
                target_key = str(payload.get("target_key", caster_key) or caster_key)
                if bool(payload.get("self_target", False)):
                    return f"{caster_key} stills as their awareness sinks into the surrounding land."
                return f"{caster_key} settles a land-bonded awareness over {target_key}."
            if utility_effect == "wolf_scent":
                target_key = str(payload.get("target_key", caster_key) or caster_key)
                if bool(payload.get("self_target", False)):
                    return f"{caster_key} lifts their head slightly as a feral keenness comes into their senses."
                return f"{caster_key} sharpens {target_key}'s senses with a feral surge of scent-awareness."
            if utility_effect == "spider_climb":
                target_key = str(payload.get("target_key", caster_key) or caster_key)
                if bool(payload.get("self_target", False)):
                    return f"{caster_key} steadies as though every surface around them had become climbable."
                return f"{caster_key} settles uncanny climbing ease over {target_key}."
            if utility_effect == "eagle_vision":
                return f"{caster_key}'s gaze sharpens, fixing on details far beyond ordinary sight."
            if utility_effect == "blend":
                return f"{caster_key} blurs smoothly into the surrounding terrain until they are hard to follow."
            if utility_effect == "breathe_water":
                return f"{caster_key} convulses for a moment as their breathing changes to suit the water."
            if utility_effect == "caiman_swim":
                target_key = str(payload.get("target_key", caster_key) or caster_key)
                if bool(payload.get("self_target", False)):
                    return f"{caster_key} rolls their shoulders as though the pull of water has suddenly become familiar."
                return f"{caster_key} settles a smooth swimmer's poise over {target_key}."
            if utility_effect == "wisdom_of_the_pack":
                return f"{caster_key} stills for a moment as a deeper pack-instinct settles into place."
            if utility_effect == "refresh":
                target_key = str(payload.get("target_key", caster_key) or caster_key)
                if bool(payload.get("self_target", False)):
                    return f"A bright restorative pulse passes through {caster_key}."
                return f"{caster_key} calls a bright restorative pulse over {target_key}."
            if utility_effect == "raise_power":
                return f"{caster_key} draws on Life mana so hard that the air itself seems to thrum, while the group sags with sudden weariness."
            if utility_effect == "gift_of_life":
                return f"{caster_key} draws Gift of Life inward, settling into a steadier empathic focus."
            if utility_effect == "innocence":
                if int(payload.get("undead_backfire_count", 0) or 0) > 0:
                    return f"{caster_key}'s empathic calm washes outward, but nearby undead twist toward them in sudden hostility."
                return f"{caster_key}'s presence softens with empathic calm, drawing the attention of nearby threats elsewhere."
            if utility_effect == "flush_poisons":
                return f"A purifying warmth passes through {caster_key}, flushing corruption from their body."
            if utility_effect == "cure_disease":
                return f"A steady restorative warmth settles over {caster_key} as illness loosens its hold."
            if utility_effect == "bless":
                target_key = str(payload.get("target_key", "someone") or "someone")
                if bool(payload.get("self_target", False)):
                    return f"{caster_key} draws a mantle of holy radiance around themselves."
                return f"{caster_key} lays a mantle of holy radiance over {target_key}."
            if utility_effect == "spirit_beacon":
                return f"{caster_key} fixes a pale spirit beacon around themselves."
            if utility_effect == "uncurse":
                target_key = str(payload.get("target_key", "someone") or "someone")
                if bool(payload.get("death_sting_relieved", False)):
                    return f"{caster_key} invokes Uncurse over {target_key}, easing Death's Sting and hostile magic alike."
                return f"{caster_key} invokes Uncurse over {target_key}, washing hostile magic away."
            if utility_effect == "revelation":
                target_key = str(payload.get("target_key", "someone") or "someone")
                if bool(payload.get("revealed", False)):
                    return f"{caster_key} invokes Revelation upon {target_key}, forcing them into plain sight."
                return f"{caster_key} invokes Revelation upon {target_key}, but little changes."
            if utility_effect == "water_purification":
                return f"{caster_key} scatters dark powder into the water, and the currents clear under a pale blue glow."
            if utility_effect == "compost":
                return f"{caster_key} calls rich Life mana into the ground, and decay quickens around them."
            if utility_effect == "swarm":
                return f"{caster_key} calls a furious swarm down around {payload.get('target_key', 'someone')}."
            if utility_effect == "awaken_forest":
                return f"{caster_key} rouses the forest itself, and the branches around the area begin to stir."
            if utility_effect == "plague_of_scavengers":
                return f"{caster_key} seeds a droning plague around {payload.get('target_key', 'someone')}, and scavengers answer from every crack and hollow."
            if utility_effect == "light":
                if spell_id == "holy_light":
                    return f"Holy light blossoms around {caster_key}, pushing back the gloom."
                return f"A soft light gathers around {caster_key}."
            if utility_effect == "gauge_flow":
                return f"{caster_key} completes a spell. Their gaze becomes distant, attuned to something beyond the visible."
            if bool(payload.get("removed", False)):
                return f"A cleansing wash passes over {caster_key}."
            return f"A brief shimmer passes over {caster_key}."
        if effect_family == "augmentation":
            target_key = str(payload.get("target_key", "someone") or "someone")
            buff_name = str(payload.get("buff_name", "spell") or "spell")
            if spell_id == "see_the_wind":
                if bool(payload.get("self_target", False)):
                    return f"{caster_key}'s attention sharpens with every whisper of motion in the air."
                return f"{caster_key} sharpens {target_key}'s awareness of every shift in the wind."
            if spell_id == "cheetah_swiftness":
                if bool(payload.get("self_target", False)):
                    return f"A taut, predatory quickness settles through {caster_key}'s limbs."
                return f"A taut, predatory quickness settles through {target_key}'s limbs at {caster_key}'s invocation."
            if spell_id == "bear_strength":
                if bool(payload.get("self_target", False)):
                    return f"A heavy, ursine strength settles into {caster_key}'s frame."
                return f"A heavy, ursine strength settles into {target_key}'s frame at {caster_key}'s invocation."
            if spell_id == "grizzly_claw":
                return f"{caster_key} settles a fierce clawing edge over {target_key}."
            if spell_id == "senses_of_the_tiger":
                if bool(payload.get("self_target", False)):
                    return f"{caster_key}'s expression tightens into a hunter's focus."
                return f"{caster_key} sharpens {target_key}'s senses into a hunter's focus."
            if bool(payload.get("self_target", False)):
                return f"{caster_key} gathers {buff_name} inward."
            return f"{caster_key} settles {buff_name} over {target_key}."

        if effect_family == "resurrection":
            target_key = str(payload.get("target_key", "someone") or "someone")
            corpse_key = str(payload.get("corpse_key", "a corpse") or "a corpse")
            if spell_id == "rejuvenation":
                return f"{caster_key} invokes Rejuvenation over {corpse_key}, and {target_key} jolts back to life."
            if spell_id == "mass_rejuvenation":
                return f"{caster_key} begins invoking a broad resurrection rite, but the magic fails to stabilize."
            return f"{caster_key} calls {target_key} back from death."

        if effect_family == "warding":
            if bool(payload.get("group_target", False)):
                if spell_id == "zone_of_protection":
                    if int(payload.get("target_count", 0) or 0) <= 1:
                        return f"A large translucent sphere forms around {caster_key}, shimmering with protective Life resonance."
                    return f"A large translucent sphere forms around {caster_key} and companions, shimmering with protective Life resonance."
                return f"{caster_key} extends a protective field over the group."
            target_key = str(payload.get("target_key", "someone") or "someone")
            if spell_id == "major_physical_protection":
                return f"A broad silver ward settles over {caster_key if bool(payload.get('self_target', False)) else target_key}."
            if spell_id == "halo":
                return f"Pinpoints of intense white light whirl around {caster_key if bool(payload.get('self_target', False)) else target_key}, gathering into a dormant halo."
            if spell_id == "protection_from_evil":
                if bool(payload.get("self_target", False)):
                    return f"A soft white glow gathers around {caster_key}, warding off unholy force."
                return f"A soft white glow gathers around {target_key} at {caster_key}'s invocation."
            if spell_id == "divine_radiance":
                return f"A radiant holy aura blazes around {caster_key if bool(payload.get('self_target', False)) else target_key}."
            if spell_id == "minor_physical_protection":
                return f"A soft silver ward settles over {caster_key if bool(payload.get('self_target', False)) else target_key}."
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
                if str(payload.get("effect_type", "") or "") == "mesmerize":
                    return f"{caster_key}'s spell brushes over {target_key}, but the creature resists the pacifying magic."
                return f"{caster_key}'s spell fails to take hold on {target_key}."
            effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
            if effect_type == "burden":
                return f"{caster_key}'s spell completes at {target_key}. {target_key} sags visibly, looking suddenly burdened."
            if effect_type == "daze":
                return f"{caster_key}'s spell leaves {target_key} looking dazed."
            if effect_type == "mesmerize":
                return f"{caster_key}'s spell settles over {target_key}, leaving the creature strangely calm and pacified."
            if effect_type == "haraweps_bonds":
                return f"{caster_key}'s spell lashes {target_key} in sticky webbing."
            if effect_type == "slow":
                return f"{caster_key}'s spell drags at {target_key}'s movement."
            if effect_type == "hobble":
                return f"{caster_key}'s spell tangles around {target_key}'s legs, hobbling them."
            if effect_type == "branch_break":
                damage = int(payload.get("final_damage", 0) or 0)
                if damage > 0:
                    return f"{caster_key}'s spell rips a heavy branch free and smashes it into {target_key} for {damage} damage."
                return f"{caster_key}'s spell rips a heavy branch free and smashes it into {target_key}."
            return f"{caster_key}'s spell hinders {target_key}."

        if effect_family == "targeted_magic":
            target_key = str(payload.get("target_key", "someone") or "someone")
            if not bool(payload.get("hit", False)):
                if spell_id == "aesrela_everild":
                    return f"{caster_key} invokes Aesrela Everild, but the silver flames miss {target_key}."
                if spell_id == "hand_of_tenemlor":
                    return f"{caster_key} invokes Hand of Tenemlor, but the burning hand misses {target_key}."
                if spell_id == "strange_arrow":
                    return f"{caster_key}'s spell completes at {target_key}, the arrow missing and dissipating in scattered sparks."
                return f"{caster_key}'s spell misses {target_key}."
            if spell_id == "aesrela_everild":
                if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                    return f"{caster_key} invokes Aesrela Everild at {target_key}, but silver flame splashes uselessly across a barrier."
                if bool(payload.get("stunned", False)):
                    return f"{caster_key} invokes Aesrela Everild. Bolts of silver flame crash into {target_key}, leaving them visibly stunned."
                return f"{caster_key} invokes Aesrela Everild. Bolts of silver flame crash into {target_key}."
            if spell_id == "hand_of_tenemlor":
                if float(payload.get("absorbed_by_ward", 0.0) or 0.0) > 0 and float(payload.get("final_damage", 0.0) or 0.0) <= 0:
                    return f"{caster_key} invokes Hand of Tenemlor at {target_key}, but the burning hand splashes across a barrier."
                return f"{caster_key} invokes Hand of Tenemlor. A blazing hand of holy fire sears {target_key}'s left hand."
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
                spell_name = str(payload.get("spell_name") or "").strip()
                if not spell_name:
                    return f"{caster_key} begins sustaining a spell."
                sustain_source = str(dict(payload.get("cyclic_state") or {}).get("sustain_source", payload.get("sustain_source", "held_mana")) or "held_mana")
                if sustain_source == "attunement":
                    return f"{caster_key} draws raw mana from their essence into a sustained spell pattern."
                return f"{caster_key} completes a complex spell weaving; tendrils of mana flow from their held mana into a sustained pattern."
            return None

        if effect_family != "healing":
            return None

        target_key = str(payload.get("target_key", "someone") or "someone")
        mana_type = str(payload.get("source_mana_type", "") or "").strip().lower()
        healing_mode = str(payload.get("healing_mode", "hp") or "hp")
        if bool(payload.get("self_target", False)):
            if spell_id == "heal" or healing_mode == "combined_heal":
                return f"A broad restorative warmth settles over {caster_key}, easing wounds and scars together."
            if spell_id == "external_wound_healing" or healing_mode == "external_wounds":
                return f"A focused warmth gathers across {caster_key}'s skin, sealing fresh external injuries."
            if spell_id == "internal_wound_healing" or healing_mode == "internal_wounds":
                return f"A focused warmth sinks beneath {caster_key}'s skin, mending internal hurts."
            if spell_id == "vitality_healing":
                return f"{caster_key} draws life back into themselves, looking visibly steadier."
            if spell_id == "heal_wounds" or healing_mode == "empath_wounds":
                return f"A patient wash of life settles over {caster_key}, knitting their carried wounds toward wholeness."
            if spell_id == "heal_scars" or healing_mode == "scars":
                return f"A slow restorative warmth passes over {caster_key}'s old scars."
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
            if spell_name == "the spell" and reason == "insufficient_mana":
                return ["You lose control of the spell."]
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
            if str(payload.get("effect_type", "") or "") == "hands_of_lirisa":
                return ["The warmth in your hands fades, and your skinning confidence ebbs away."]
            if str(payload.get("effect_type", "") or "") == "earth_meld":
                return ["Your awareness of the land recedes, and nearby concealment grows uncertain again."]
            if str(payload.get("effect_type", "") or "") == "blend":
                return ["Your outline slips back into plain sight as the terrain releases you."]
            if str(payload.get("effect_type", "") or "") == "breathe_water":
                return ["Your body forgets the water's rhythm, and breathing underwater is no longer possible."]
            if str(payload.get("effect_type", "") or "") == "water_purification":
                return ["The pale blue clarity fades from the water as the spell's protection ends."]
            if str(payload.get("effect_type", "") or "") == "compost":
                return ["The rich churn of decay settles back into ordinary stillness."]
            if str(payload.get("effect_type", "") or "") == "swarm":
                return ["The angry swarm scatters, its droning fury fading into the distance."]
            if str(payload.get("effect_type", "") or "") == "awaken_forest":
                return ["The stirred branches quiet, and the forest settles back into stillness."]
            if str(payload.get("effect_type", "") or "") == "plague_of_scavengers":
                return ["The droning plague thins out as the scavengers lose interest and disperse."]
            if str(payload.get("effect_type", "") or "") == "bless":
                return ["The holy radiance around you gutters out, leaving your hands ordinary once more."]
            if str(payload.get("effect_type", "") or "") == "light":
                if str(payload.get("spell_id", "") or "") == "holy_light":
                    return ["The holy light around you fades, and the shadows return."]
                return ["The soft light around you fades."]
            if str(payload.get("effect_type", "") or "") == "gauge_flow":
                return ["Your extended awareness of magical flows fades. You return to ordinary perception."]
            return []
        if str(payload.get("effect_family", "") or "") == "warding":
            effect_name = str(payload.get("effect_type", payload.get("spell_id", "")) or "")
            if effect_name == "manifest_force":
                return ["The shimmering barrier of force around you fades and dissipates as its spell ends."]
            if effect_name == "major_physical_protection":
                return ["The broad silver ward around you thins and vanishes."]
            if effect_name == "halo":
                return ["The whirling halo of white light around you dissolves into drifting motes."]
            if effect_name == "protection_from_evil":
                return ["The soft white glow around you fades away."]
            if effect_name == "divine_radiance":
                return ["The radiant holy aura around you dims, and the shadows begin to creep back in."]
            if effect_name == "minor_physical_protection":
                return ["The silver ward around you thins and vanishes."]
            return []
        if str(payload.get("effect_family", "") or "") != "debilitation":
            return []
        effect_type = str(payload.get("effect_type", "debilitation") or "debilitation")
        if effect_type == "burden":
            return ["The weight burdening you lifts. You feel your strength returning."]
        if effect_type == "daze":
            return ["You shake off the daze."]
        if effect_type == "mesmerize":
            return ["The pacifying haze lifts, and your instincts sharpen again."]
        if effect_type == "haraweps_bonds":
            return ["The sticky bindings loosen and fall away."]
        if effect_type == "slow":
            return ["Your movement quickens as the slowing magic fades."]
        if effect_type == "hobble":
            return ["Your legs free themselves as the hobbling magic fades."]
        if effect_type == "branch_break":
            return ["The violent aftershock of the breaking branch finally eases."]
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
        if effect_family == "warding" and effect_name == "major_physical_protection":
            return f"The broad silver ward around {subject_key} thins and vanishes."
        if effect_family == "warding" and effect_name == "halo":
            return f"The whirling halo of white light around {subject_key} dissolves into drifting motes."
        if effect_family == "warding" and effect_name == "protection_from_evil":
            return f"The soft white glow around {subject_key} fades away."
        if effect_family == "warding" and effect_name == "divine_radiance":
            return f"The radiant holy aura around {subject_key} dims back into shadow."
        if effect_family == "warding" and effect_name == "minor_physical_protection":
            return f"The silver ward around {subject_key} thins and vanishes."
        if effect_family == "utility" and effect_name == "bless":
            return f"The holy radiance around {subject_key} gutters out."
        if effect_family == "utility" and effect_name == "compost":
            return f"The rich churn of decay around {subject_key} subsides."
        if effect_family == "utility" and effect_name == "swarm":
            return f"The furious swarm around {subject_key} scatters away."
        if effect_family == "utility" and effect_name == "awaken_forest":
            return f"The stirred branches around {subject_key} settle back into stillness."
        if effect_family == "utility" and effect_name == "plague_of_scavengers":
            return f"The droning plague around {subject_key} thins out and disperses."
        if effect_family == "utility" and effect_name == "light" and str(payload.get("spell_id", "") or "") == "holy_light":
            return f"The holy light around {subject_key} fades back into shadow."
        if effect_family == "utility" and str(payload.get("effect_type", "") or "") == "gauge_flow":
            return f"{subject_key}'s distant gaze refocuses on the present."
        if effect_family == "debilitation" and str(payload.get("effect_type", "") or "") == "burden":
            return f"{subject_key} straightens up, looking less burdened."
        return None