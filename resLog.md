=== RUN 01 ===
Favor: 0
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 0
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_01 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_01 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_01 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_01 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_01 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_01 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_01 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_01 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_01 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_01 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[CLERIC]: There is not enough lingering favor to revive them.
[TRACE]: > observe tick 1
[TRACE]: > observe tick 2
[TRACE]: > observe tick 3
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: NO
Revive failed; no post-revive survival window occurred.
POST-REVIVE OBSERVATION
Tick 1: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 1
Tick 2: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 2
Tick 3: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 3
Tick 4: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: NO
Survival Duration: not revived
Second Death: NO
Observed Issue: revive failed due to insufficient lingering favor
Player Feel: gated

=== RUN 02 ===
Favor: 0
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 0
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_02 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_02 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_02 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_02 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_02 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_02 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_02 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_02 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_02 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_02 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[CLERIC]: There is not enough lingering favor to revive them.
[TRACE]: > observe tick 1
[TRACE]: > observe tick 2
[TRACE]: > observe tick 3
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: NO
Revive failed; no post-revive survival window occurred.
POST-REVIVE OBSERVATION
Tick 1: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 1
Tick 2: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 2
Tick 3: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 3
Tick 4: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: NO
Survival Duration: not revived
Second Death: NO
Observed Issue: revive failed due to insufficient lingering favor
Player Feel: gated

=== RUN 03 ===
Favor: 0
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 0
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_03 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_03 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_03 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_03 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_03 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_03 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_03 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_03 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_03 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_03 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[CLERIC]: There is not enough lingering favor to revive them.
[TRACE]: > observe tick 1
[TRACE]: > observe tick 2
[TRACE]: > observe tick 3
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: NO
Revive failed; no post-revive survival window occurred.
POST-REVIVE OBSERVATION
Tick 1: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 1
Tick 2: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 2
Tick 3: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 3
Tick 4: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: NO
Survival Duration: not revived
Second Death: NO
Observed Issue: revive failed due to insufficient lingering favor
Player Feel: gated

=== RUN 04 ===
Favor: 0
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 0
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_04 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_04 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_04 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_04 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_04 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_04 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_04 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_04 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_04 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_04 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[CLERIC]: There is not enough lingering favor to revive them.
[TRACE]: > observe tick 1
[TRACE]: > observe tick 2
[TRACE]: > observe tick 3
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: NO
Revive failed; no post-revive survival window occurred.
POST-REVIVE OBSERVATION
Tick 1: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 1
Tick 2: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 2
Tick 3: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 3
Tick 4: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: NO
Survival Duration: not revived
Second Death: NO
Observed Issue: revive failed due to insufficient lingering favor
Player Feel: gated

=== RUN 05 ===
Favor: 0
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 0
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_05 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_05 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_05 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_05 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_05 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_05 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_05 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_05 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_05 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_05 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[CLERIC]: There is not enough lingering favor to revive them.
[TRACE]: > observe tick 1
[TRACE]: > observe tick 2
[TRACE]: > observe tick 3
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: NO
Revive failed; no post-revive survival window occurred.
POST-REVIVE OBSERVATION
Tick 1: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 1
Tick 2: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 2
Tick 3: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 3
Tick 4: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 38 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: NO
Survival Duration: not revived
Second Death: NO
Observed Issue: revive failed due to insufficient lingering favor
Player Feel: gated

=== RUN 06 ===
Favor: 1
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 1
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: Your favor feels thin as death takes hold.
[ROOM]: SIM_RES_TARGET_06 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_06 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_06 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_06 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_06 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_06 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_06 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_06 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_06 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_06 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_06. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_06 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_06 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_06 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_06 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_06 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [TARGET]: You have no favor left to call upon. You must depart. || [ROOM]: SIM_RES_TARGET_06 crumples to the ground. || [CLERIC]: SIM_RES_TARGET_06 crumples to the ground. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 07 ===
Favor: 1
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 1
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: Your favor feels thin as death takes hold.
[ROOM]: SIM_RES_TARGET_07 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_07 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_07 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_07 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_07 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_07 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_07 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_07 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_07 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_07 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_07. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_07 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_07 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_07 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_07 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_07 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [TARGET]: You have no favor left to call upon. You must depart. || [ROOM]: SIM_RES_TARGET_07 collapses suddenly, life leaving their body. || [CLERIC]: SIM_RES_TARGET_07 collapses suddenly, life leaving their body. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 08 ===
Favor: 1
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 1
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: Your favor feels thin as death takes hold.
[ROOM]: SIM_RES_TARGET_08 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_08 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_08 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_08 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_08 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_08 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_08 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_08 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_08 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_08 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_08. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_08 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_08 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_08 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_08 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_08 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [TARGET]: You have no favor left to call upon. You must depart. || [ROOM]: SIM_RES_TARGET_08 crumples to the ground. || [CLERIC]: SIM_RES_TARGET_08 crumples to the ground. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 09 ===
Favor: 1
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 1
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: Your favor feels thin as death takes hold.
[ROOM]: SIM_RES_TARGET_09 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_09 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_09 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_09 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_09 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_09 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_09 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_09 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_09 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_09 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_09. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_09 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_09 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_09 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_09 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_09 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [TARGET]: You have no favor left to call upon. You must depart. || [ROOM]: SIM_RES_TARGET_09 staggers, then falls motionless. || [CLERIC]: SIM_RES_TARGET_09 staggers, then falls motionless. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 10 ===
Favor: 1
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 1
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[TARGET]: Your favor feels thin as death takes hold.
[ROOM]: SIM_RES_TARGET_10 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_10 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_10 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_10 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_10 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_10 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_10 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_10 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_10 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_10 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_10. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_10 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_10 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_10 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[TARGET]: You have no favor left to call upon. You must depart.
[ROOM]: SIM_RES_TARGET_10 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_10 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [TARGET]: You have no favor left to call upon. You must depart. || [ROOM]: SIM_RES_TARGET_10 collapses suddenly, life leaving their body. || [CLERIC]: SIM_RES_TARGET_10 collapses suddenly, life leaving their body. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 11 ===
Favor: 5
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 5
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_11 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_11 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_11 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_11 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_11 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_11 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_11 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_11 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_11 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_11 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_11. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_11 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_11 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_11 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_11 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_11 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_11 staggers, then falls motionless. || [CLERIC]: SIM_RES_TARGET_11 staggers, then falls motionless. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 12 ===
Favor: 5
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 5
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_12 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_12 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_12 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_12 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_12 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_12 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_12 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_12 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_12 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_12 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_12. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_12 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_12 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_12 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_12 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_12 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_12 collapses suddenly, life leaving their body. || [CLERIC]: SIM_RES_TARGET_12 collapses suddenly, life leaving their body. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 13 ===
Favor: 5
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 5
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_13 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_13 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_13 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_13 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_13 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_13 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_13 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_13 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_13 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_13 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_13. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_13 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_13 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_13 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_13 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_13 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_13 collapses suddenly, life leaving their body. || [CLERIC]: SIM_RES_TARGET_13 collapses suddenly, life leaving their body. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 14 ===
Favor: 5
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 5
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_14 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_14 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_14 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_14 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_14 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_14 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_14 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_14 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_14 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_14 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_14. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_14 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_14 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_14 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_14 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_14 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_14 collapses suddenly, life leaving their body. || [CLERIC]: SIM_RES_TARGET_14 collapses suddenly, life leaving their body. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 15 ===
Favor: 5
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 5
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_15 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_15 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_15 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_15 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_15 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_15 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_15 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_15 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_15 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_15 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_15. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_15 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_15 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_15 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_15 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_15 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_15 crumples to the ground. || [CLERIC]: SIM_RES_TARGET_15 crumples to the ground. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 16 ===
Favor: 15
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 15
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_16 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_16 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_16 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_16 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_16 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_16 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_16 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_16 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_16 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_16 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_16. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_16 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_16 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_16 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_16 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_16 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_16 staggers, then falls motionless. || [CLERIC]: SIM_RES_TARGET_16 staggers, then falls motionless. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 17 ===
Favor: 15
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 15
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_17 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_17 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_17 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_17 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_17 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_17 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_17 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_17 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_17 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_17 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_17. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_17 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_17 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_17 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_17 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_17 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_17 staggers, then falls motionless. || [CLERIC]: SIM_RES_TARGET_17 staggers, then falls motionless. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 18 ===
Favor: 15
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 15
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_18 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_18 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_18 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_18 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_18 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_18 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_18 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_18 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_18 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_18 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_18. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_18 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_18 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_18 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_18 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_18 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_18 collapses suddenly, life leaving their body. || [CLERIC]: SIM_RES_TARGET_18 collapses suddenly, life leaving their body. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 19 ===
Favor: 15
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 15
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_19 collapses suddenly, life leaving their body.
[CLERIC]: SIM_RES_TARGET_19 collapses suddenly, life leaving their body.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_19 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_19 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_19 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_19 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_19 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_19 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_19 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_19 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_19. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_19 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_19 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_19 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_19 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_19 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_19 staggers, then falls motionless. || [CLERIC]: SIM_RES_TARGET_19 staggers, then falls motionless. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== RUN 20 ===
Favor: 15
Death Type: Wounds
Empath Healing: NONE
Scenario: Base Resurrection + Wound Recursion Observation
COMMAND TRACE
> reset favor 15
> reset death_sting 0
> reset debuffs and wound state
> apply heavy wound profile
> confirm NO empath healing
> prepare corpse
> stabilize corpse
> restore corpse
> bind corpse
> revive corpse
SYSTEM OUTPUT
[TRACE]: > wound tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 3
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: You are slipping away.
[TRACE]: > wound tick 4
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > wound tick 5
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > wound tick 6
[ROOM]: SIM_RES_TARGET_20 crumples to the ground.
[CLERIC]: SIM_RES_TARGET_20 crumples to the ground.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > prepare corpse
[ROOM]: SIM_RES_CLERIC_20 begins preparing the body.
[TARGET]: SIM_RES_CLERIC_20 begins preparing the body.
[CLERIC]: You begin preparing the body for the rites.
[ROOM]: The body settles into ritual readiness.
[TARGET]: The body settles into ritual readiness.
[ROOM]: The rite is ready for stabilization.
[CLERIC]: The rite is ready for stabilization.
[TARGET]: The rite is ready for stabilization.
[TARGET]: You feel distant hands preparing your body.
[CLERIC]: You finish preparing the body for the rites.
[TRACE]: > stabilize corpse
[ROOM]: SIM_RES_CLERIC_20 begins a stabilization vigil.
[TARGET]: SIM_RES_CLERIC_20 begins a stabilization vigil.
[CLERIC]: You begin stabilizing the body's fading pattern.
[ROOM]: The fading pattern steadies.
[TARGET]: The fading pattern steadies.
[ROOM]: The rite is ready for restoration.
[CLERIC]: The rite is ready for restoration.
[TARGET]: The rite is ready for restoration.
[TARGET]: You feel your fading self steady slightly.
[CLERIC]: You stabilize the body's fading pattern and hold its memories in place.
[TRACE]: > restore corpse
[ROOM]: SIM_RES_CLERIC_20 begins restoring the corpse's fading pattern.
[TARGET]: SIM_RES_CLERIC_20 begins restoring the corpse's fading pattern.
[CLERIC]: You begin restoring the body's fragile memories.
[ROOM]: The corpse's memory coheres once more.
[TARGET]: The corpse's memory coheres once more.
[ROOM]: The rite is ready for binding.
[CLERIC]: The rite is ready for binding.
[TARGET]: The rite is ready for binding.
[TARGET]: Something of you is being restored.
[CLERIC]: You restore coherence to the corpse's lingering memories.
[TRACE]: > bind corpse
[ROOM]: SIM_RES_CLERIC_20 begins binding the wandering soul.
[TARGET]: SIM_RES_CLERIC_20 begins binding the wandering soul.
[CLERIC]: You begin binding the soul securely to the body.
[ROOM]: The soul's tether tightens and holds.
[TARGET]: The soul's tether tightens and holds.
[ROOM]: The final rite may now be attempted.
[CLERIC]: The final rite may now be attempted.
[TARGET]: The final rite may now be attempted.
[TARGET]: A firm pull anchors you back toward your body.
[CLERIC]: You secure the soul to the body and make the final rite possible.
[TRACE]: > revive corpse
[TARGET]: A distant rite tugs at the edge of your spirit.
[CLERIC]: You begin the final rite over corpse of SIM_RES_TARGET_20. Remain still and unhurt until it is complete.
[TARGET]: Your remaining favor softens the blow of death.
[TARGET]: You feel the weight of death cling to you.
[TARGET]: SIM_RES_CLERIC_20 calls you back from death. The soul returns cleanly, guided by a flawless rite.
[TARGET]: A portion of your favor is spent to complete the return.
[ROOM]: SIM_RES_TARGET_20 jolts back to life. The soul returns cleanly, guided by a flawless rite.
[CLERIC]: You complete the final rite and call SIM_RES_TARGET_20 back to life. The soul returns cleanly, guided by a flawless rite.
[TRACE]: > observe tick 1
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TARGET]: Your condition is worsening.
[TRACE]: > observe tick 2
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 3
[ROOM]: SIM_RES_TARGET_20 staggers, then falls motionless.
[CLERIC]: SIM_RES_TARGET_20 staggers, then falls motionless.
[TARGET]: You have died.
[TARGET]: You feel yourself slipping free from your body.
[TARGET]: You bleed from your wounds.
[TARGET]: You are bleeding heavily!
[TRACE]: > observe tick 4
[TRACE]: > observe tick 5
[TRACE]: > observe tick 6
[TRACE]: > observe tick 7
[TRACE]: > observe tick 8
[TRACE]: > observe tick 9
[TRACE]: > observe tick 10
[TRACE]: > observe tick 11
[TRACE]: > observe tick 12
[TRACE]: > observe tick 13
[TRACE]: > observe tick 14
[TRACE]: > observe tick 15
[TRACE]: > observe tick 16
[TRACE]: > observe tick 17
[TRACE]: > observe tick 18
[TRACE]: > observe tick 19
[TRACE]: > observe tick 20
STATE TRANSITIONS
Pre-Death Tick 1: alive | HP 82 | Bleed 28 | Medical badly_injured
Pre-Death Tick 2: alive | HP 63 | Bleed 30 | Medical badly_injured
Pre-Death Tick 3: alive | HP 44 | Bleed 32 | Medical critical
Pre-Death Tick 4: alive | HP 24 | Bleed 34 | Medical critical
Pre-Death Tick 5: alive | HP 4 | Bleed 36 | Medical critical
Pre-Death Tick 6: dead | HP 0 | Bleed 38 | Medical critical
Corpse created from wound death.
Ritual stages executed: prepare -> stabilize -> restore -> bind -> revive.
Revived: YES
Second death triggered during post-revive observation at tick 3.
POST-REVIVE OBSERVATION
Tick 1: alive | HP 38 | Bleed 40 | Medical critical | Messages: [TRACE]: > observe tick 1 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily! || [TARGET]: Your condition is worsening.
Tick 2: alive | HP 16 | Bleed 42 | Medical critical | Messages: [TRACE]: > observe tick 2 || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 3: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 3 || [ROOM]: SIM_RES_TARGET_20 staggers, then falls motionless. || [CLERIC]: SIM_RES_TARGET_20 staggers, then falls motionless. || [TARGET]: You have died. || [TARGET]: You feel yourself slipping free from your body. || [TARGET]: You bleed from your wounds. || [TARGET]: You are bleeding heavily!
Tick 4: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 4
Tick 5: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 5
Tick 6: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 6
Tick 7: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 7
Tick 8: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 8
Tick 9: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 9
Tick 10: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 10
Tick 11: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 11
Tick 12: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 12
Tick 13: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 13
Tick 14: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 14
Tick 15: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 15
Tick 16: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 16
Tick 17: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 17
Tick 18: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 18
Tick 19: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 19
Tick 20: dead | HP 0 | Bleed 44 | Medical critical | Messages: [TRACE]: > observe tick 20
RESULT SUMMARY
Revive Success: YES
Survival Duration: 3 ticks
Second Death: YES
Observed Issue: wounds persisted and caused a second death
Player Feel: abrupt

=== VALIDATION CHECKS ===
1. Favor Scaling
Hold TRUE? YES | avg survival ticks -> 0:0.0, 1:3.0, 5:3.0, 15:3.0
2. Wound Persistence
Persisted after revive? YES
3. Double Death Behavior
Revive -> die again observed in 15/20 runs
4. Messaging Quality
Observed messaging quality: clear enough
5. System Feel
Dominant feel across runs: abrupt
