# DRG-MSG-AUDIT - Three-Audience Messaging Coverage Audit

## Summary

This audit cataloged 22 shipped public interaction actions and 6 intentionally private information surfaces. Of the 22 public actions, 12 currently have full audience coverage, 3 have partial coverage, and 7 have no canonical audience split, for a structural coverage rate of 54.5%. The biggest gaps are not the older combat verbs themselves; those mostly reach actor, target, and room already. The main remediation work sits in progression and social-milestone actions shipped in LEARN-002b, where stat training and circle advancement currently emit actor-only text, plus a smaller combat pass to correct semantic fidelity where parry and dodge outcomes are still narrated as generic misses. Recommendation: adopt option B, a thin `send_action_messages(...)` helper, because the Evennia API is already sufficient but the shipped code proves discipline alone is not preventing audience omissions.

## Step 0 - Canonical GSL Pattern

### Canonical vocabulary confirmed from source

Canonical scripts inspected:

- `S00119` - `POKE`, the clearest actor/target/room split example
- `S00153` - will-o-wisp room-only ambient behavior
- `S00159` - parser utility and common `msgp` failure paths
- `S00485` - guildleader interaction and advancement-facing RP messaging
- `S08825` - intelligent attack chooser

Observed message verbs:

| GSL verb | Audience | Observed use |
| --- | --- | --- |
| `msgp` | actor only | First-person messaging such as `You poke...`, parser failures, guildleader speech to the acting player |
| `msg np1` | specific target | Direct second-person target view such as `$P0 pokes you...` |
| `msgr` | whole room | Ambient room broadcasts with no exclusions |
| `msgrxp` | room minus actor | Room message when only the actor has a custom first-person line |
| `msgrx2` | room minus actor and target | Canonical interaction pattern when both actor and target have their own lines |
| `msggm` / `msgrgm` | staff/debug | GM-only instrumentation or debug visibility |

### Canonical pattern example

From `S00119` `POKE`:

```text
msgp    "You frown, giving $P1 a sharp poke in the ribs."
msg np1 "$P0 frowns, giving you a sharp poke in the ribs."
msgrx2  "$P0 frowns, giving $P1 a sharp poke in the ribs."
```

This confirms the user framing: canon expects three-audience handling for targeted public actions.

### Substitution tokens observed in source

The source confirms a rich token vocabulary. The exact declension rules are embedded in the GSL engine, but the observed meanings are clear enough for audit purposes:

| Token | Observed meaning |
| --- | --- |
| `$P0`, `$P1` | actor / target player display name |
| `$P0H`, `$P1H` | possessive form for actor / target |
| `$P0G`, `$P1G` | gender-aware pronoun for actor / target |
| `$P0Iself` | reflexive actor pronoun |
| `$C0N`, `$C1N` | creature name / noun form |
| `$C0S`, `$C1S` | short singular creature reference |
| `$C0D`, `$O1D` | descriptive display form |
| `$O1S` | short singular object name |
| `$S0`, `$S9` | contextual string slot such as room/sky or direction |

### Gender and pronoun handling

Canon is explicitly pronoun-aware. `S00119` uses `$P1G` and `$P1H` inside the same interaction so the actor, target, and room text stay grammatically correct without hardcoding `his/her/their`. That is materially richer than the current repo pattern, which mostly interpolates `attacker.key` and `target.key` into fixed English strings.

### Helper-pattern finding

One part of the request was to verify whether `S08825` is a messaging callback/router. It is not. `S08825` is an intelligent attack-choice routine that selects melee maneuvers based on weapon profile, IQ, and prior maneuver state. It contains GM debug messaging, but it is not a general actor/observer disambiguation helper. The real canon grounding for audience-split messaging is in verb scripts like `S00119`, not in `S08825`.

## Step 1 - Shipped Dispatch Inventory

Confirmed shipped dispatches with player-visible actions:

| Dispatch | Delivered player-visible action surfaces |
| --- | --- |
| `DRG-022.5` | combat scaffold and extension-era combat command structure; visible combat movement/engagement verbs are already live in current commands |
| `DRG-023` | foundational data wiring; not directly a messaging dispatch, but it feeds `experience` and skill identity surfaces |
| `DRG-024` | attack resolution rewrite underlying miss/hit/kill combat narration |
| `DRG-024a` | hit area, damage, armor reduction, wounds, cleanup, and resulting combat narration fields |
| `DRG-024b` | attack verbs `thrust`, `lunge`, `slice`, `chop`, `sweep`, `feint`, `jab` |
| `DRG-024c` | `parry` and `dodge` defense stance commands |
| `DRG-INFRA-001` | `combatreset` and `sync_state_to_client()` dead-state recovery support |
| `DRG-INFRA-002` | reliability/sync work; no new player-visible audience messaging surface found in this audit |
| `LEARN-001` | `tdp`, TDP display in `experience`, passive rank/TDP accrual |
| `LEARN-002a` | stat trainer and guildleader room/NPC infrastructure |
| `LEARN-002b` | `train` and `study` context dispatch, stat-training consult/commit, circle consult/commit, direct stat info commands, `exp <skill>`, `exp circle` |

Notes:

- `DRG-022.5` and `DRG-023` are mostly enabling dispatches. The first strong messaging surfaces start in the combat and learning slices.
- `DRG-INFRA-002` did not present a distinct player-visible text surface in the code inspected; it is better treated as infrastructure than as an audience-messaging dispatch.

## Step 2 - Per-Action Coverage Tables

Coverage legend used for public interaction actions:

- `A` - full audience coverage: actor, target when applicable, and room observers receive intentional messages
- `B` - partial audience coverage: one audience is missing or only receives a fallback/non-specific line
- `N` - no canonical split: actor-only or otherwise missing the expected audience pattern

Private information surfaces are marked `Private-ok` and are not counted against canonical public-action coverage.

### Combat Actions

| Action | Code location | Actor message | Target message | Room message | Coverage | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Target person focus | `commands/cmd_target.py` | `You focus on X.` | none | none | N | Likely an intentionally tactical/private action, but it does not follow a public interaction pattern |
| Target body-part focus | `commands/cmd_target.py` | `You focus your attacks on the head/arm/...` | none | none | N | Pure actor-facing tactical state |
| Advance to melee | `commands/cmd_advance.py` | `You close the distance on X.` | `X closes the distance on you.` | `X closes the distance on Y.` excluding both | A | Clean triple split |
| Advance but target holds near range | `commands/cmd_advance.py` | `You press closer...` | `X closes in, but you keep them at near range.` | `X closes the distance on Y.` excluding both | A | Structurally full, though the room line is less specific than actor/target lines |
| Retreat to far range | `commands/cmd_retreat.py` | `You successfully retreat from X!` | `X retreats out to far range.` | `X retreats from Y.` excluding both | A | Clean triple split |
| Retreat partial | `commands/cmd_retreat.py` | `You manage to pull back slightly...` | `X pulls back slightly from you.` | `X pulls back slightly from Y.` excluding both | A | Clean triple split |
| Retreat fail | `commands/cmd_retreat.py` | `You fail to disengage from X!` | `X tries to retreat from you but cannot break away.` | `X fails to break away from Y.` excluding both | A | Clean triple split |
| Disengage | `commands/cmd_disengage.py` | `You step back and disengage.` | `X breaks away from the fight.` only if mutual target linkage exists | `X steps back from the fight.` excluding actor only | B | Room broadcast excludes actor but not target; target may see both target-specific and room-style text, or no target-specific text at all |
| Generic melee attack miss | `engine/presenters/combat_presenter.py` | `You thrust/swing... but miss.` | `X thrusts/swings at you... but misses.` | `X thrusts/swings at Y... but misses.` excluding both | A | Full triple split |
| Generic melee attack hit with hit area | `engine/presenters/combat_presenter.py` | `You strike X's arm/head...` | `X strikes your arm/head...` | `X strikes Y's arm/head...` excluding both | A | Full triple split |
| Attack kill / defender death | `engine/presenters/combat_presenter.py`, `world/systems/death.py` | Kill message to attacker, death lines to defender | `You collapse from the blow.` plus `You have died.` | combat room line plus separate death emote | A | Full coverage, though death is split across two systems |
| Attack fully parried | `domain/combat/resolution.py`, `engine/presenters/combat_presenter.py` | generic miss text | generic miss text | generic miss text | A | Structural coverage exists, but semantic fidelity is wrong: parry outcome is not narrated as parry |
| Attack evaded / dodged | `domain/combat/resolution.py`, `engine/presenters/combat_presenter.py` | generic miss text | generic miss text | generic miss text | A | Structural coverage exists, but semantic fidelity is wrong: evade/dodge outcome is not narrated as dodge |
| Armor mitigation add-on | `engine/presenters/combat_presenter.py` | none | `Your armor absorbs part of the blow.` | none | B | Supplemental mitigation narration reaches only the defender |
| Force-of-impact messaging | `domain/combat/resolution.py`, `engine/presenters/combat_presenter.py` | generic quality phrase only | generic quality phrase only | generic quality phrase only | N | DRG-024b promised force-of-impact-visible combat feel, but no dedicated FOI audience line exists |
| Parry stance command | `commands/cmd_defense_verbs.py` | `You move into a position to parry.` | N/A | `X moves into a position to parry.` excluding actor | A | Correct for untargeted public action |
| Dodge stance command | `commands/cmd_defense_verbs.py` | `You move into a position to dodge.` | N/A | `X moves into a position to dodge.` excluding actor | A | Correct for untargeted public action |

Combat-specific fidelity findings:

- Structural audience coverage is much better in combat than expected.
- The biggest combat gap is semantic, not plumbing: `CombatPresenter` only branches on `miss`, `hit`, and `kill`. It ignores `combat_outcome` values such as `parried_full`, `parried_partial`, `shielded_full`, `shielded_partial`, and `evaded`, so multiple canon-distinct events collapse into generic miss or generic hit phrasing.

### Infrastructure Actions

| Action | Code location | Actor message | Target message | Room message | Coverage | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `combatreset` admin command | `commands/cmd_combatreset.py` | `You reset X's combat state.` | `A restoring force clears your combat state and lingering wounds.` | none | B | Strong actor/target split, no room/admin-observer broadcast |
| `sync_state_to_client()` | `typeclasses/characters.py` | none | none | none | Silent system surface | Not a player-visible messaging surface; excluded from public-action statistics |

### Progression / Training / Advancement Actions

| Action | Code location | Actor message | Target message | Room message | Coverage | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `tdp` command | `commands/cmd_tdp.py` | private TDP totals | N/A | none | Private-ok | Correctly private |
| `exp` | `commands/cmd_experience.py` | private skill list | N/A | none | Private-ok | Correctly private |
| `exp all` | `commands/cmd_experience.py` | private full skill list | N/A | none | Private-ok | Correctly private |
| `exp <skill>` | `commands/cmd_experience.py` | private skill detail | N/A | none | Private-ok | Correctly private |
| `exp circle` | `commands/cmd_experience.py` | private progression projection | N/A | none | Private-ok | Correctly private |
| Direct stat info commands | `commands/cmd_stat_info.py` | private stat readout | N/A | none | Private-ok | Correctly private |
| Stat training consult | `engine/services/stat_training_service.py`, `commands/cmd_train.py`, `commands/cmd_study.py` | trainer speech returned to actor only | trainer NPC is not a recipient | none | N | No observer-facing message that someone is consulting a trainer |
| Stat training commit | `engine/services/stat_training_service.py`, `commands/cmd_train.py`, `commands/cmd_study.py` | `Trainer nods once. You feel your Strength sharpen...` | trainer NPC is not a recipient | none | N | This is the clearest community-design gap |
| Circle advancement consult | `commands/cmd_train.py`, `commands/cmd_study.py`, `engine/services/circle_service.py` | guildleader progress review to actor only | guildleader NPC is not a recipient | none | N | Social moment is private only |
| Circle advancement commit | `engine/services/circle_service.py`, `commands/cmd_train.py`, `commands/cmd_study.py` | `Leader marks your advancement...` | guildleader NPC is not a recipient | none | N | No guildhall announcement or room celebration line |
| Rank gain from pulse | `world/systems/skills.py`, `typeclasses/characters.py` | none | N/A | none | Silent system | Not a direct player-visible messaging action today |
| Mind lock / mindstate display | `commands/cmd_experience.py` | private informational display | N/A | none | Private-ok | Correctly private |

### Other Relevant Surfaces Found During Audit

These were not part of the requested dispatch list, but they are useful baseline evidence for future remediation discipline:

- Several older or adjacent systems already use room exclusion correctly, for example corpse/ritual room messages in `typeclasses/characters.py` and various recovery verbs outside the audited dispatches.
- This means the repo already has living examples of `room.msg_contents(..., exclude=[...])`; messaging inconsistency is a discipline problem, not a missing-engine-capability problem.

## Step 3 - Coverage Statistics

### Public interaction actions scored

- Total public interaction actions cataloged: `22`
- Full coverage (`A`): `12`
- Partial coverage (`B`): `3`
- No canonical split (`N`): `7`
- Structural canonical coverage rate: `54.5%`

### Private information surfaces audited separately

- Intentionally private actor-only surfaces confirmed: `6`
- Accidental private-data room leakage found: `0`

### Highest-impact gaps ranked

1. **Training and advancement are socially silent.**
   Stat training consult, stat training commit, circle consult, and circle commit are all actor-only today. These are the clearest missed room-presence opportunities.

2. **Combat defense outcomes are semantically flattened.**
   Parry and dodge/evasion outcomes technically reach all three audiences, but the text is generic miss text rather than parry/dodge-specific narration. The audience plumbing exists; the presenter vocabulary is incomplete.

3. **Disengage and supplemental combat messaging are inconsistent.**
   `disengage` does not exclude the target from the room line and only sends a dedicated target line in one branch. Armor mitigation only narrates to the defender.

4. **Force-of-impact feel is under-realized in text.**
   DRG-024b promised a stronger combat-feel layer, but there is no dedicated FOI-specific message vocabulary today, only generic `quality` phrasing.

5. **Tactical target-selection actions are actor-only.**
   These are lower priority than the social/public gaps because they may be intentionally private, but the audit records them so future dispatches can make that choice explicitly.

### Remediation scope estimate

- `DRG-MSG-001` can likely stay a single dispatch if it is explicitly scoped to:
  - combat presenter semantics and a few command-level combat fixes
  - stat training and circle room-announcement coverage
  - a small shared messaging helper
- Estimated implementation weight: moderate, not tiny. Roughly one focused dispatch touching `CombatPresenter`, a handful of combat commands, `cmd_train`, `cmd_study`, `circle_service`, and a new helper module plus tests.
- A split is only needed if the remediation also tries to add full pronoun-aware token rendering across the whole game in the same pass.

## Step 4 - Evennia API Mapping

The codebase and live Evennia API both confirm the standard audience-routing patterns are available directly.

Verified `DefaultRoom.msg_contents` signature in this environment:

```python
(self, text=None, exclude=None, from_obj=None, mapping=None, raise_funcparse_errors=False, **kwargs)
```

Confirmed mapping:

| GSL verb | Evennia equivalent | Notes |
| --- | --- | --- |
| `msgp "text"` | `caller.msg("text")` | direct actor message |
| `msg np1 "text"` | `target.msg("text")` | direct target message |
| `msgr "text"` | `room.msg_contents("text")` | room-wide broadcast |
| `msgrxp "text"` | `room.msg_contents("text", exclude=[caller])` | room minus actor |
| `msgrx2 "text"` | `room.msg_contents("text", exclude=[caller, target])` | room minus actor and target |
| `msggm` / `msgrgm` | permission-gated `caller.msg(...)` or channel/admin helper | no exact stock single-verb equivalent |

Important Evennia-specific finding:

- This build supports `from_obj` and `mapping`, which means the codebase can use Evennia's funcparser-aware `$You()`, `$conj()`, and `$pron()` formatting for perspective and pronoun handling if desired.
- That is the closest modern equivalent to GSL's token-rich audience-aware phrasing.

## Step 5 - Utility Recommendation

### Recommendation: Option B

Adopt a thin `engine/services/messaging.py` helper.

Reasoning:

- The Evennia primitives are already enough.
- The repo already knows how to use them.
- The shipped code still forgot room coverage on multiple recent dispatches.
- That is exactly the kind of recurring omission a tiny helper is meant to prevent.

### Recommended helper shape

```python
from typing import Optional


def send_action_messages(
    actor,
    target=None,
    room=None,
    actor_message: Optional[str] = None,
    target_message: Optional[str] = None,
    room_message: Optional[str] = None,
    room_exclude_actor: bool = True,
    room_exclude_target: bool = True,
    from_obj=None,
    mapping=None,
) -> None:
    """Send actor/target/room messages for one public action.

    Use for public player-visible actions. Do not use for private information
    commands such as EXP, TDP, or direct stat readouts.
    """
    if actor_message:
        actor.msg(actor_message)
    if target and target_message:
        target.msg(target_message)
    elif target and room_message and not target_message:
        target.msg(room_message)
    if room_message:
        location = room or getattr(actor, "location", None)
        if location:
            exclude = []
            if room_exclude_actor:
                exclude.append(actor)
            if target and room_exclude_target:
                exclude.append(target)
            location.msg_contents(
                room_message,
                exclude=exclude or None,
                from_obj=from_obj or actor,
                mapping=mapping,
            )


def send_untargeted_action(
    actor,
    room=None,
    actor_message: Optional[str] = None,
    room_message: Optional[str] = None,
    from_obj=None,
    mapping=None,
) -> None:
    send_action_messages(
        actor=actor,
        target=None,
        room=room,
        actor_message=actor_message,
        room_message=room_message,
        room_exclude_actor=True,
        from_obj=from_obj or actor,
        mapping=mapping,
    )
```

### Utility guidance

- Use the helper for public actions, not private info commands.
- Prefer Evennia funcparser-aware text for room messaging when pronoun handling matters.
- Keep actor text first-person, target text second-person, room text third-person.
- Require new gameplay dispatches to include a `Messaging Triple Specification` section in the dispatch itself.

## Appendix - Suggested Remediation Messages For Highest-Impact Gaps

These are suggested text only. No code changes are proposed here.

### 1. Stat training consult

- Actor: `Master Bron studies you carefully. "To sharpen your Strength will cost 63 Time Development Points. TRAIN COMMIT if you are certain."`
- Room: `Master Bron studies Aedan with a practiced trainer's eye.`

### 2. Stat training commit

- Actor: `Master Bron nods once. You feel your Strength sharpen to 22.`
- Room: `Master Bron nods approvingly as Aedan completes a bout of strength training.`

### 3. Circle advancement consult

- Actor: `Guildleader Kalika reviews your progress toward Circle 3.`
- Room: `Guildleader Kalika quietly reviews Aedan's standing within the guild.`

### 4. Circle advancement commit

- Actor: `Guildleader Kalika marks your advancement. You are now Circle 3.`
- Room: `Guildleader Kalika formally recognizes Aedan's advancement within the guild.`

### 5. Disengage

- Actor: `You step back and disengage from the fight.`
- Target: `Aedan steps back and breaks away from you.`
- Room: `Aedan steps back and disengages from the fight.`

### 6. Fully parried attack

- Actor: `You lunge at the bandit, but your attack rings off their guard.`
- Target: `Aedan lunges at you, but you catch the blow on your defense.`
- Room: `Aedan lunges at the bandit, but the attack is turned aside.`

### 7. Dodged / evaded attack

- Actor: `You thrust at the bandit, but they slip cleanly away from the blow.`
- Target: `Aedan thrusts at you, but you evade the attack.`
- Room: `Aedan thrusts at the bandit, but the bandit evades cleanly.`

### 8. Armor mitigation add-on

- Actor: `Your blow lands, but the armor turns much of the impact.`
- Target: `Your armor absorbs part of the blow.`
- Room: `The blow lands, but armor blunts the force of it.`

### 9. Force-of-impact high result

- Actor: `The impact lands with bone-jarring force.`
- Target: `The blow crashes into you with bone-jarring force.`
- Room: `The impact lands with a bone-jarring crack.`

### 10. `combatreset` admin visibility

- Actor: `You reset Aedan's combat state.`
- Target: `A restoring force clears your combat state and lingering wounds.`
- Room: `A brief restorative surge passes over Aedan.`

## Verification Checklist

- [x] Step 0: GSL canonical pattern documented; vocabulary table built; substitution tokens listed
- [x] Step 1: Shipped dispatches inventoried against changelog and roadmap
- [x] Step 2: Every relevant player-visible action from the audited dispatches has a row or explicit note
- [x] Step 3: Coverage statistics computed; highest-impact gaps ranked
- [x] Step 4: Evennia API mapping confirmed against this codebase's Evennia install
- [x] Step 5: Utility recommendation made with reasoning and signature draft
- [x] Step 6: Report written to `tmp/drg-msg-audit-report.md`
- [x] NO gameplay code changed
- [x] Read-only audit stayed within the requested scope