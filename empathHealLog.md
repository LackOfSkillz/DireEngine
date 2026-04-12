=== RUN 15 ===
Scenario: C
Scenario Name: Corpse Stabilize + Res + Finish Heal
Iteration: 5 of 5

Initial Setup:
- Patient state: alive=NO, hp=0, vitality=79, bleeding=32, fatigue=0, trauma=0, medical=critical, shock=0
- Empath state: alive=YES, hp=100, vitality=0, bleeding=0, fatigue=0, trauma=0, medical=stable, shock=0
- Cleric state: alive=YES, hp=100, vitality=0, bleeding=0, fatigue=0, trauma=0, medical=stable, shock=0
- Favor: 5
- Devotion: 100
- Room: SIM_EMPATH_ROOM_C_15
- Wounds summary: head: external 8, internal 6, bleed 2; chest: external 42, internal 28, bleed 20; abdomen: external 34, internal 24, bleed 16
- Corpse condition: 70/100

Command Trace:
> stabilize corpse
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
> touch SIM_PATIENT_C_15
> assess
> stabilize SIM_PATIENT_C_15
> take bleeding all
> take vitality 20

System / Game Output:
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You are slipping away.
[EMPATH] Your senses snag on SIM_PATIENT_C_15. They are fading.
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] Your condition is worsening.
[EMPATH] Your senses snag on SIM_PATIENT_C_15. They are fading.
[ROOM] SIM_PATIENT_C_15 crumples to the ground.
[EMPATH] SIM_PATIENT_C_15 crumples to the ground.
[CLERIC] SIM_PATIENT_C_15 crumples to the ground.
[PATIENT] You have died.
[PATIENT] You feel yourself slipping free from your body.
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[EMPATH] You carefully tend to the corpse, slowing its decay.
[ROOM] SIM_CLERIC_C_15 begins preparing the body.
[PATIENT] SIM_CLERIC_C_15 begins preparing the body.
[EMPATH] SIM_CLERIC_C_15 begins preparing the body.
[CLERIC] You begin preparing the body for the rites.
[ROOM] The body settles into ritual readiness.
[PATIENT] The body settles into ritual readiness.
[EMPATH] The body settles into ritual readiness.
[ROOM] The rite is ready for stabilization.
[PATIENT] The rite is ready for stabilization.
[EMPATH] The rite is ready for stabilization.
[CLERIC] The rite is ready for stabilization.
[PATIENT] You feel distant hands preparing your body.
[CLERIC] You finish preparing the body for the rites.
[ROOM] SIM_CLERIC_C_15 begins a stabilization vigil.
[PATIENT] SIM_CLERIC_C_15 begins a stabilization vigil.
[EMPATH] SIM_CLERIC_C_15 begins a stabilization vigil.
[CLERIC] You begin stabilizing the body's fading pattern.
[ROOM] The fading pattern steadies.
[PATIENT] The fading pattern steadies.
[EMPATH] The fading pattern steadies.
[ROOM] The rite is ready for restoration.
[PATIENT] The rite is ready for restoration.
[EMPATH] The rite is ready for restoration.
[CLERIC] The rite is ready for restoration.
[PATIENT] You feel your fading self steady slightly.
[CLERIC] You stabilize the body's fading pattern and hold its memories in place.
[ROOM] SIM_CLERIC_C_15 begins restoring the corpse's fading pattern.
[PATIENT] SIM_CLERIC_C_15 begins restoring the corpse's fading pattern.
[EMPATH] SIM_CLERIC_C_15 begins restoring the corpse's fading pattern.
[CLERIC] You begin restoring the body's fragile memories.
[ROOM] The corpse's memory coheres once more.
[PATIENT] The corpse's memory coheres once more.
[EMPATH] The corpse's memory coheres once more.
[ROOM] The rite is ready for binding.
[PATIENT] The rite is ready for binding.
[EMPATH] The rite is ready for binding.
[CLERIC] The rite is ready for binding.
[PATIENT] Something of you is being restored.
[CLERIC] You restore coherence to the corpse's lingering memories.
[ROOM] SIM_CLERIC_C_15 begins binding the wandering soul.
[PATIENT] SIM_CLERIC_C_15 begins binding the wandering soul.
[EMPATH] SIM_CLERIC_C_15 begins binding the wandering soul.
[CLERIC] You begin binding the soul securely to the body.
[ROOM] The soul's tether tightens and holds.
[PATIENT] The soul's tether tightens and holds.
[EMPATH] The soul's tether tightens and holds.
[ROOM] The final rite may now be attempted.
[PATIENT] The final rite may now be attempted.
[EMPATH] The final rite may now be attempted.
[CLERIC] The final rite may now be attempted.
[PATIENT] A firm pull anchors you back toward your body.
[CLERIC] You secure the soul to the body and make the final rite possible.
[PATIENT] A distant rite tugs at the edge of your spirit.
[CLERIC] You begin the final rite over corpse of SIM_PATIENT_C_15. Remain still and unhurt until it is complete.
[PATIENT] Your remaining favor softens the blow of death.
[PATIENT] You feel the weight of death cling to you.
[PATIENT] SIM_CLERIC_C_15 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[PATIENT] A portion of your favor is spent to complete the return.
[ROOM] SIM_PATIENT_C_15 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[EMPATH] SIM_PATIENT_C_15 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC] You complete the final rite and call SIM_PATIENT_C_15 back to life. The soul returns cleanly, guided by a flawless rite.
[EMPATH] You reach out and sense the condition of your patient.
[EMPATH] Vitality: 79%
[EMPATH] Bleeding: 32%
[EMPATH] Poison: 0%
[EMPATH] Disease: 0%
[EMPATH] You steady their condition, slowing the damage.
[ROOM] SIM_EMPATH_C_15 steadies SIM_PATIENT_C_15's condition with practiced calm.
[CLERIC] SIM_EMPATH_C_15 steadies SIM_PATIENT_C_15's condition with practiced calm.
[PATIENT] Your condition steadies under careful hands.
[EMPATH] You lessen the burden as you take it.
[PATIENT] You feel your pain lessen.
[EMPATH] You draw out living force, lessening the burden even as it tears through you.
[PATIENT] You feel your pain lessen.
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You are slipping away.
[EMPATH] Your senses snag on SIM_PATIENT_C_15. They are fading.
[EMPATH] Your senses are clear.
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[ROOM] SIM_PATIENT_C_15 crumples to the ground.
[EMPATH] SIM_PATIENT_C_15 crumples to the ground.
[CLERIC] SIM_PATIENT_C_15 crumples to the ground.
[PATIENT] You have died.
[PATIENT] You feel yourself slipping free from your body.
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!
[PATIENT] You bleed from your wounds.
[PATIENT] You are bleeding heavily!

Tick Observation:
Death Tick 1: patient=alive | hp 82 | bleed 28 | medical badly_injured | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Death Tick 2: patient=alive | hp 63 | bleed 30 | medical badly_injured | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Death Tick 3: patient=alive | hp 44 | bleed 32 | medical critical | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily! || [PATIENT] You are slipping away. || [EMPATH] Your senses snag on SIM_PATIENT_C_15. They are fading.
Death Tick 4: patient=alive | hp 24 | bleed 34 | medical critical | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Death Tick 5: patient=alive | hp 4 | bleed 36 | medical critical | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily! || [PATIENT] Your condition is worsening. || [EMPATH] Your senses snag on SIM_PATIENT_C_15. They are fading.
Death Tick 6: patient=dead | hp 0 | bleed 38 | medical critical | Messages: [ROOM] SIM_PATIENT_C_15 crumples to the ground. || [EMPATH] SIM_PATIENT_C_15 crumples to the ground. || [CLERIC] SIM_PATIENT_C_15 crumples to the ground. || [PATIENT] You have died. || [PATIENT] You feel yourself slipping free from your body. || [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 1: patient=alive | patient hp 44 | patient bleed 39 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 11 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily! || [PATIENT] You are slipping away. || [EMPATH] Your senses snag on SIM_PATIENT_C_15. They are fading. || [EMPATH] Your senses are clear.
Tick 2: patient=alive | patient hp 28 | patient bleed 40 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 13 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 3: patient=alive | patient hp 12 | patient bleed 40 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 15 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 4: patient=dead | patient hp 0 | patient bleed 41 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 17 | Messages: [ROOM] SIM_PATIENT_C_15 crumples to the ground. || [EMPATH] SIM_PATIENT_C_15 crumples to the ground. || [CLERIC] SIM_PATIENT_C_15 crumples to the ground. || [PATIENT] You have died. || [PATIENT] You feel yourself slipping free from your body. || [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 5: patient=dead | patient hp 0 | patient bleed 42 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 19 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 6: patient=dead | patient hp 0 | patient bleed 43 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 21 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 7: patient=dead | patient hp 0 | patient bleed 43 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 23 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 8: patient=dead | patient hp 0 | patient bleed 44 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 25 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 9: patient=dead | patient hp 0 | patient bleed 44 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 27 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 10: patient=dead | patient hp 0 | patient bleed 44 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 29 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 11: patient=dead | patient hp 0 | patient bleed 45 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 31 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 12: patient=dead | patient hp 0 | patient bleed 46 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 33 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 13: patient=dead | patient hp 0 | patient bleed 46 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 35 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 14: patient=dead | patient hp 0 | patient bleed 47 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 37 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!
Tick 15: patient=dead | patient hp 0 | patient bleed 48 | patient medical critical | empath hp 95 | empath bleed 21 | empath vitality 39 | Messages: [PATIENT] You bleed from your wounds. || [PATIENT] You are bleeding heavily!

Outcome Summary:
- Transfer succeeded: YES
- Patient stabilized: YES
- Corpse res succeeded: YES
- Patient re-died after res: YES
- Final patient condition: alive=NO, hp=0, vitality=70, bleeding=13, fatigue=0, trauma=0, medical=critical, shock=0
- Final empath condition: alive=YES, hp=95, vitality=39, bleeding=21, fatigue=3, trauma=0, medical=injured, shock=4
- Observed issue: none in the resurrection contract itself; the corpse was revived from a still-critical wound state and the follow-up healing sequence was insufficient to prevent re-death
- Player feel: tense but correct; outcome now reflects prep quality and post-res care rather than hidden revive behavior