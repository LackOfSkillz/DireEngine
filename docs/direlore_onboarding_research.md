# Direlore Onboarding Research

This report is a read-only extraction from the local `direlore` PostgreSQL database on port `5432`.

## Scope

Goal: find Direlore / DragonRealms source material that can inform a production onboarding pipeline for Dragonsire.

Important constraint:

- Direlore contains useful in-world onboarding material for character creation, tutorial commands, newcomer guidance, mentor routing, and safe-failure messaging.
- It does **not** meaningfully cover modern website landing-page UX or account-form UX. Those parts of the new Dragonsire pipeline will need product design rather than canon extraction.

## DB Surfaces Used

The useful onboarding data was found in:

- `public.raw_pages`
- `public.sections`
- `public.page_metadata`
- `public.entities`

Relevant page families discovered:

- `General_new_player_guide`
- `Commoner_new_player_guide`
- `Asemath_Academy`
- `Asemath_Academy_Library`
- `Academy_of_Learning`
- `Lorethew_Mentor_Society`
- `Direction_command`
- `Look_command`
- `Get_command`
- `Inventory_command`
- `Attack_command`
- `Health_command`
- `Experience_command`
- `Depart_command`
- `Death`
- `Language_command`
- `Ozursus`
- `Polyglot_Yulna`

## High-Signal Findings

### 1. DragonRealms already framed onboarding as staged basics

From `General new player guide`:

- The guide explicitly presents an ordered beginner path rather than dumping all systems at once.
- Character creation is broken into digestible steps:
  - name
  - gender
  - race
  - features
  - starting location
  - approval
- After creation, the guide moves into a second phase:
  - joining a guild
  - gear
  - preparation
  - skills
  - experience
  - inventory
  - health
  - money
  - first combat
  - death/favors

Implementation implication:

- Your locked Dragonsire pipeline is directionally correct. Direlore source material also teaches in phases and introduces systems only after identity and immediate survival are handled.

### 2. Character creation source material supports a low-friction identity flow

From `General new player guide` sections:

- `Name Yourself`
  - name is treated as the first important identity choice
  - names should be unique and readable
  - names should avoid obvious joke/profanity/reference failures
- `Genders`
  - gender is lightly handled, not mechanically overloaded
- `Races`
  - race is presented as a major identity choice
  - the guide advises choosing race for culture and character feel, not just min-maxing
- `Features`
  - appearance is lightweight and presented as what others will see on `LOOK`
- `Starting Location`
  - starting location is a separate post-identity choice
- `Approval`
  - there is precedent for a temporary holding room before full release into the world

Implementation implication:

- For Dragonsire, keep chargen short and identity-first:
  - name
  - race
  - light appearance
  - confirm
- Do not front-load profession/stats/lore walls into the first 5 minutes.

### 3. There is strong canon precedent for a newcomer hub with trainers, help, and free utility items

From `Asemath Academy`:

- It is described as a major academic center.
- It has clear points of interest rather than vague flavor only.
- It includes free or useful starter resources in a freshman classroom.
- It includes named trainers on-site:
  - `Ozursus` for magical feats
  - `Yulna` for languages

From `Asemath Academy Library` and `Academy of Learning`:

- both are organized around instructional/reference content
- the academy/library model is explicitly tied to teaching and learning, not just lore storage

Implementation implication:

- Your onboarding first room should behave like a compressed academy/intake hybrid:
  - one guide NPC
  - one visible object
  - one clear route forward
  - obvious training/help affordances
- This supports the `Intake Chamber` concept directly.

### 4. DragonRealms used helper NPCs that are discoverable by `STUDY` and `ASK`

From `Ozursus`:

- players are told they can `STUDY` the NPC to learn what they do
- then `ASK` the NPC about a topic to learn more

From `Yulna`:

- same pattern: discoverability first, then topic-driven teaching

Implementation implication:

- A guide NPC in Dragonsire should not be passive flavor text.
- Strong pattern to borrow:
  - `study guide`
  - `ask guide about movement`
  - `ask guide about combat`
- Even if the first onboarding path is scripted, this gives you a scalable post-tutorial help interface.

### 5. `DIRECTION` is a canon answer to "where do I go next?"

From `Directions command`:

- it exists specifically to route players to important locations
- it groups destinations into meaningful buckets:
  - guilds
  - training
  - gates
  - hunting
  - shops
  - other
- notable beginner-facing entries include:
  - `Combat Training - Tutorial for Newcomers`
  - `Asemath Academy - We teach you how to learn`
  - `Mentors - The people with the answers to your questions`

Implementation implication:

- Your onboarding must always answer the navigation question explicitly.
- After release, Dragonsire should have a lightweight equivalent to `DIR` or a guide-driven directional command so players do not stall out after the tutorial.

### 6. The core tutorial action loop maps directly to real DR command surfaces

From command pages:

- `Get command`
  - explicit simple syntax for taking an item
- `Inventory command`
  - explicit simple syntax for checking carried and worn items
- `Attack command`
  - explicit syntax for attacking a target
  - note: DR `ATTACK` auto-faces and auto-advances if needed
- `Look command`
  - used to refresh room description and inspect players/items
- `Health command`
  - returns readable state rather than just numeric HP
- `Experience command`
  - explains skill-based learning and feedback

Implementation implication:

- Your planned onboarding loop is strongly supported by source material:
  - move
  - look
  - get item
  - inventory check
  - attack target
  - see health / experience response
- This is better aligned with DR canon than starting with stat explanations or lore exposition.

### 7. Direlore reinforces action-first teaching over lecture-first teaching

From `General new player guide`:

- the guide repeatedly explains the game in terms of commands the player should type
- commands are introduced as practical verbs inside context
- combat is framed through immediate actions:
  - set defenses
  - find a target
  - attack
  - react to death/failure

Implementation implication:

- Your requirement of one concept per step is correct.
- Onboarding copy should be imperative and concrete:
  - go east
  - get weapon
  - attack dummy
- Avoid abstract system essays during the first session.

### 8. Direlore supports a safety-net for early failure and death

From `Depart command` and `Death`:

- death is recoverable, not permanent
- new adventurers receive special early protection:
  - favor-free departs while still under beginner protections
  - first-circle death leniency
- death messaging is framed as inconvenience and recovery, not hard failure

Implementation implication:

- onboarding should explicitly normalize failure and recovery.
- If a player fails the combat step, the system should recover cleanly and keep them moving instead of creating a dead end.
- Early-game messaging should make it clear they are not ruined by a mistake.

### 9. Mentor infrastructure is canonically important

From `Lorethew Mentor Society`:

- mentors are an official player-help structure
- they exist to help new players get started and understand the game
- they have known locations and are reachable by `DIR MENTORS`

Implementation implication:

- After release from the scripted intake, there should be a clearly exposed help handoff:
  - guide NPC points players to mentors/help
  - world contains a discoverable help location or command

### 10. Language training already intersects with newcomer-friendly spaces

From `Language command`:

- language switching is a first-class social command
- `Learning New Languages` points directly to Yulna in Asemath Academy

Implementation implication:

- this supports placing optional social-system follow-up inside or just after onboarding
- but it should remain optional and post-foundation, not part of the core first 10 minutes

## Mapping To Dragonsire Pipeline

### Phase 1 - Website Entry

Useful Direlore support:

- almost none directly
- the `General new player guide` supports short plain-language framing of what a text MUD is and how commands work

Best takeaway:

- keep website copy short and clarity-first

### Phase 2 - Account Creation

Useful Direlore support:

- almost none directly in the DB

Best takeaway:

- do not try to derive web-form UX from wiki/game canon

### Phase 3 - Character Creation

Useful Direlore support:

- `General new player guide` directly supports:
  - name
  - gender
  - race
  - features
  - starting location / approval

Best takeaway:

- minimal, step-based identity creation is source-aligned

### Phase 4 - First Room / Intake Chamber

Useful Direlore support:

- `Asemath Academy`
- `Academy of Learning`
- `Asemath Academy Library`

Best takeaway:

- a newcomer hub should feel like a teaching institution with visible help points and concrete resources

### Phase 5 - Guided Loop

Useful Direlore support:

- `Look command`
- `Get command`
- `Inventory command`
- `Attack command`
- `Health command`
- `Experience command`
- `Directions command`

Best takeaway:

- tutorial steps should use real world verbs and immediately visible feedback

### Phase 6 - First Success Moment

Useful Direlore support:

- `General new player guide` combat and progression sections frame advancement as "do the action, learn from it"

Best takeaway:

- first success should be tied to visible consequence and skill gain, not just completion text

### Phase 7 - Minimal System Intro

Useful Direlore support:

- `Health command`
- `Experience command`
- `Inventory command`

Best takeaway:

- health, inventory, and experience are the right first systems to expose after the player has acted

### Phase 8 - Release

Useful Direlore support:

- `Directions command`
- `Lorethew Mentor Society`

Best takeaway:

- release should include an explicit pointer to where help, training, or mentors live next

## Recommended Canon-Derived Requirements For Dragonsire

These are the clearest things Direlore supports for implementation:

1. Character creation should be identity-first and short.
2. The first live area should be a teaching hub, not open-world chaos.
3. A guide NPC should be discoverable and queryable, not just decorative.
4. Tutorial steps should be verb-driven and singular.
5. Navigation after release must be explicit.
6. Early failure should be recoverable and low-punishment.
7. Mentor/help handoff should exist after the scripted sequence.
8. Optional deeper systems like languages should sit just after onboarding, not inside the first mandatory loop.

## Strongest Source Pages To Reuse During Implementation

If you only keep a short source list for the onboarding microtasks, use these:

- `General_new_player_guide`
- `Asemath_Academy`
- `Direction_command`
- `Look_command`
- `Get_command`
- `Inventory_command`
- `Attack_command`
- `Health_command`
- `Experience_command`
- `Depart_command`
- `Death`
- `Lorethew_Mentor_Society`
