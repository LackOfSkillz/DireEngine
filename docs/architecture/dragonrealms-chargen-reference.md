# DragonRealms Chargen Reference

## Scope

This document summarizes what the local Direlore research says about DragonRealms-style player creation and player-facing appearance.

It is intended as an implementation reference for Dragonsire.

Important constraint:

- The workspace does not contain a raw Direlore database dump or direct SQL query scripts for this topic.
- The verified local sources are the extracted research documents:
  - `docs/direlore_onboarding_research.md`
  - `docs/direlore_race_research.md`
- `docs/direlore_race_research.md` explicitly states it was extracted read-only from the local `direlore` PostgreSQL database.

This means the findings below are only as exact as the extracted crawl snapshot.

## Verified DragonRealms Creation Flow

From the Direlore onboarding research, DragonRealms newcomer guidance presented character creation in this order:

1. name
2. gender
3. race
4. features
5. starting location
6. approval

The important design implication is that creation was identity-first and lightweight.

Verified behavioral notes:

- name is a primary identity decision, not a throwaway form field
- gender is present but not mechanically overloaded in the onboarding guidance
- race is a major identity and culture decision
- features are lightweight rather than a massive mechanical configuration layer
- starting location is a separate choice after identity fields
- approval / holding-room release existed as a distinct step

## What "Features" Meant

The strongest verified statement in the extracted Direlore notes is:

- appearance is lightweight and presented as what others will see on `LOOK`

This matters more than it looks.

DragonRealms-style chargen was not primarily about building a hidden stats object. It was about constructing the visible social presentation of the character.

Implementation consequences:

- appearance should produce look-facing output
- appearance should be quick to choose
- appearance should not bury the player in lore walls or deep mechanical setup
- feature selection belongs before release into the world, not as an afterthought after onboarding begins

## Verified Race-Facing Appearance Inputs

The extracted race research verifies several appearance-adjacent categories that matter during or immediately after chargen.

### Race-level creation look

Each race page carries a character-creation look blurb describing the default visual impression of a newly created member of that race.

Examples from the extracted source:

- Dwarves: short, wide, heavily bearded, physically solid, unflinching, powerful
- Elotheans: tall, thin, large-eyed, composed, controlled, observant
- Elves: slightly taller than humans, willowy, graceful, bright-eyed, refined
- Gor'Togs: tall, dark green, hairless, massively built, steady, solid
- Halflings: short, merry, sharp-eyed, confident, bright
- Humans: moderate height, visually central, few extremes
- Prydaen: human-sized, short-furred, tuft-eared, tailed, clawed, visually predatory
- Rakash: moderate height, human-like mixed with wolf-human traits, tail and ears visible in the half-human description
- S'Kra Mur: tall, lithe, scaled, slit-pupiled, tailed

These blurbs are important because they show that race contributes default visual identity before any player-selected micro-features are layered on top.

### Height data

The race research includes explicit height ranges for some races, often split by male and female.

Examples confirmed in the extracted notes:

- Dwarves: male `4.5` to `5.5` feet, female `4.0` to `5.0` feet
- Elves: male `6.0` to `7.0` feet, female `5.5` to `6.5` feet
- Humans: male `5.5` to `6.0` feet, female `5.0` to `5.75` feet
- Halflings: rough range about `3` to `4` feet

This strongly suggests a familiar DR-style implementation should not treat height as a generic global short/average/tall choice only. It should at least be race-aware, and ideally sex-aware if Dragonsire keeps sex/gender-separated body ranges.

### Distinct physical race traits

The extracted research also confirms that some races carry always-visible physical identifiers that should feed look text automatically.

Examples confirmed in the local Direlore extraction:

- Dwarves: beard identity is culturally important
- Halflings: furry feet
- Prydaen: fur, ears, tail, claws
- Rakash: ears and tail, plus human-form versus moonskin interpretation
- S'Kra Mur: scales and tail

These are not optional cosmetic toggles in the source summary. They are race identity anchors.

## Verified LOOK Behavior

The extracted onboarding research confirms that features are what other players will see on `LOOK`.

The extracted race research adds a second critical rule:

- some races have different visible-age or identity labels depending on who is looking

That means DragonRealms look behavior is not strictly a single static description string.

It contains observer-sensitive presentation.

### What self-look versus other-look changes

The strongest verified differences in the local Direlore extraction are age labels and outsider interpretation.

Confirmed patterns:

- some races mostly use generic "people see" age bands
- some races use race-specific self labels but generic outsider labels
- Rakash is a special case with self-view plus outsider-in-human-form plus outsider-in-moonskin distinctions

### Confirmed self versus outsider cases

Halflings:

- self labels include race-flavored terms such as `kneebiter`, `tartsnatcher`, `hairyfoot`, `grayroot`, `talespinner`
- outsiders see generic labels such as `child`, `young`, `adult`, `mature`, `elderly`, `aged`

Prydaen:

- self labels include race-flavored terms such as `tail-chaser`, `mouse-catcher`, `bird-hunter`, `shadow-prowler`, `scar-bearer`
- outsiders compress their appearance much more crudely and less accurately

Elves:

- self labels extend through their own longer-lived race perspective
- outsider labels lag behind and make elves appear younger for longer

Rakash:

- age visibility splits three ways:
  - what Rakash see
  - what outsiders see in human form
  - what outsiders see in moonskin

S'Kra Mur:

- self labels follow a normal DragonRealms sequence
- outsiders are worse at judging age and often keep reading them as younger, then much older, for longer spans

## What This Means For Dragonsire LOOK

If the goal is familiarity rather than exact cloning, Dragonsire should still preserve the core DragonRealms presentation rules:

1. `look self` should not always be identical to what others see.
2. Race should affect baseline body presentation even before clothing and flavor text.
3. Appearance choices should feed directly into visible look output.
4. Some races should support observer-sensitive phrasing rather than one universal label.
5. Race-specific body traits should be automatically visible in look text.

## Verified High-Level Data We Can Implement Now

The extracted Direlore materials are already sufficient to implement these parts with confidence:

- chargen step order centered on name, gender, race, features, release
- lightweight appearance rather than long mechanical setup
- race-specific creation blurbs
- race-specific body defaults
- race-aware height handling
- race-specific physical traits in appearance output
- split self-look versus outsider-look age labeling for the races that clearly need it
- outsider distortion for special races such as Halflings, Prydaen, Rakash, and S'Kra Mur

## What The Current Snapshot Does Not Fully Recover

The extracted Direlore research does not appear to fully expose every exact feature-choice menu from live DragonRealms character creation.

Unresolved from the local snapshot:

- exact canonical feature option lists for hair style
- exact canonical feature option lists for hair color
- exact canonical feature option lists for eye color or eye shape
- exact canonical feature option lists for body build descriptors
- exact canonical self-look string templates as emitted by the game client
- exact outsider-look string templates as emitted by the game client
- exact approval-room copy and exact starting-location prompt wording

This is an extraction limit, not evidence that those things did not exist.

## Recommended Dragonsire Implementation Model

To feel familiar while staying maintainable, split the implementation into four layers.

### 1. Canonical race appearance profile

Each race should define:

- creation blurb
- core body markers
- height range
- optional sex-specific body range if retained
- self age labels
- outsider age labels
- special observer rules

### 2. Player-selected feature profile

Store structured feature fields rather than only a generated description string.

Suggested minimum fields:

- body build
- height value or height band
- hair style
- hair color
- eye color
- skin tone or scale tone

Suggested race-conditional fields:

- beard style for dwarves and other beard-capable races
- fur color and tail presentation for Felari-style races
- ear and tail descriptors for Lunari-style races
- scale tone and eye shape for Saurathi-style races

### 3. Observer-aware look renderer

Build look output from structured data, not from one frozen description blob.

Renderer responsibilities:

- self-view age label selection
- outsider-view age label selection
- race-specific physical trait injection
- worn equipment rendering
- description assembly from structured feature values

### 4. Race-aware chargen constraints

Feature selection should be filtered by race where needed.

Examples:

- beard presentation should not be a hidden universal field
- fur-specific descriptors should not appear for non-furred races
- tail wording should not be optional for tailed races whose baseline identity includes it
- height choices should be generated from race body ranges

## Familiarity Targets For Dragonsire

If the goal is "feels like DragonRealms" rather than "rebuild every menu exactly," the highest-value fidelity targets are:

- short identity-first chargen
- race matters visually, not just statistically
- appearance exists primarily to drive look text
- self look and outsider look are not always identical
- race-specific age language exists where DR used it
- race-specific body traits are always visible in a character's presentation

## Immediate Build Checklist

The next implementation pass should aim to deliver these concrete outcomes:

1. Replace the single generated appearance sentence with structured appearance fields on the character.
2. Add canonical race appearance data for all playable Dragonsire race analogues.
3. Add observer-aware look rendering for self versus others.
4. Add race-specific visible traits to appearance assembly.
5. Upgrade height from generic short/average/tall to race-aware ranges or race-aware bands.
6. Restore or redesign the mirror-style appearance review so players can verify their visible presentation before release.
7. Keep appearance lightweight and fast, matching the verified DragonRealms guidance.

## Open Research Follow-Up

If exact DragonRealms feature menus are required rather than familiar behavior, the next research pass should query or crawl for:

- exact feature-selection help text
- exact look-command examples for self and others
- exact character-creation screen prompts
- exact starting-location and approval step text

Those details are not fully recoverable from the current extracted snapshot alone.