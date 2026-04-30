# MT-510 Zone Atmosphere Survey

## Scope

- Surveyed every zone under `worlddata/zones/*.yaml`.
- Examined room `environment`, `name`, `short_desc`, `desc`, existing structured tags, and any `manual_desc` values.
- Compared recurring concepts against:
  - `world/builder/vocab/room_vocab.yaml`
  - `world/builder/vocab/atmosphere_vocab.yaml`
- Excluded `tags.custom` from proposal analysis by design.

## Corpus Summary

- Zones scanned: 12
- Rooms scanned: 1,761
- Non-empty text fields:
  - `name`: 1,761
  - `desc`: 213
  - `short_desc`: 3
  - `manual_desc`: 0
- Current structured tagging coverage is still sparse. Most meaningful prose signal comes from `worlddata/zones/new_landing.yaml`.
- Several other zone families are builder scaffolds, smoke-test fixtures, or cloned maps (`builder2`, `spawn_smoke*`, `crossingv2*`, `test_crossing`, `tester`). They were included in the scan per dispatch, but they do not materially contribute new atmosphere concepts.

## High-Level Assessment

No missing concept met the dispatch's formal promotion rule of **3+ rooms across 2+ zones** after filtering out obvious clone/test noise. In practice, the survey found a small set of **single-zone, high-signal urban concepts** in `new_landing` that are worth human review, but they should be treated as **consider only if builder requests** rather than automatic canonical additions.

The strongest candidate is `stoops` as a `named_feature`. Several atmosphere refinements also recur inside `new_landing`, but they either overlap existing vocab or are too specific to canonize without broader zone adoption.

## Existing Coverage Snapshot

These concepts already exist in the vocabulary and are either explicitly tagged today or clearly map to present zone content.

### atmosphere.materials

- Already covered in current vocab or existing tags:
  - `stone-walls`
  - `plaster-walls`
  - `timber-walls`
  - `cobbled-floor`
  - `planked-floor`
  - `flagstone-floor`
  - `timber-beams`

### atmosphere.sensory

- Already covered in current vocab or existing tags:
  - `sounds-of-traffic`
  - `sounds-of-commerce`
  - `sounds-of-bells`
  - `sounds-of-water`
  - `cooking-smell`
  - `rain-smell`
  - `dust-smell`
  - `quiet-ambient`

### atmosphere.social_character

- Already covered in current vocab or existing tags:
  - `commercial`
  - `working-class`
  - `mixed-class`
  - `residential`
  - `civic`
  - `religious`
  - `genteel`

### atmosphere.surroundings

- Already covered in current vocab or existing tags:
  - `shops-nearby`
  - `housing-nearby`
  - `market-nearby`
  - `taverns-nearby`
  - `water-nearby`
  - `quiet-area`
  - `city-wall-nearby`

### atmosphere.upkeep

- Already covered in current vocab or existing tags:
  - `well-maintained`
  - `lived-in`
  - `shabby`
  - `pristine-upkeep`
  - `neglected`
  - `abandoned`

### specific_function

- Already covered in current vocab or existing tags:
  - `market-stall`
  - `tavern`
  - `temple`
  - `warehouse`
  - `guild-hall`
  - `forge`

### structure

- Already covered in current vocab or existing tags:
  - `street`
  - `alley`
  - `intersection`
  - `dock`
  - `bridge`
  - `building-interior`
  - `hallway`
  - `threshold`
  - `entrance`
  - `square`

### named_feature

- Already covered in current vocab or existing tags:
  - `signpost`
  - `hearth`
  - `shrine`
  - `workbench`
  - `well`
  - `altar`

## Recommendation Gate

### Additions meeting the formal 3+ rooms / 2+ zones rule

None.

### Single-zone candidates worth human triage

These concepts recur enough within `new_landing` to be interesting, but they do **not** meet the cross-zone rule. Treat them as **consider only if builder requests** unless the reviewer wants to proactively expand the urban vocabulary.

## Survey by Category

### atmosphere.materials

- Missing recurring concepts in zone content:
  - `dressed-stone`
    Frequency: 7 rooms across 1 zone (`new_landing`)
    Examples: `amberwick-lane-eastern-run-4215-4215`, `saltward-street-midway-4219-4219-4219`, `cinder-alley-east-reach-4240-4240`
    Overlap: close to existing `stone-walls`; this is greater material specificity rather than a clearly new surface class
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

- Lower-confidence / consider-only-if-builder-requests:
  - `iron-hardware`
    Frequency: low, single-zone
    Examples: `amberwick-lane-eastern-run-4215-4215`, `saltward-street-south-reach-4223-4223`
    Overlap: could already be represented indirectly via `named_feature` or prose detail
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

### atmosphere.sensory

- Missing recurring concepts in zone content:
  - `horses-ambient`
    Frequency: 10 rooms across 1 zone (`new_landing`)
    Examples: `amberwick-lane-western-run-4213-4213-4213`, `saltward-street-and-amberwick-lane-4217-4217`, `lanternrest-street-2-south-reach-4260-4260`
    Overlap: adjacent to `sounds-of-traffic`, but more specific to animal presence and street life
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

  - `greenery-fragrance`
    Frequency: 10 rooms across 1 zone (`new_landing`)
    Examples: `amberwick-lane-western-run-4213-4213-4213`, `kingshade-street-south-reach-4222`, `brinehook-alley-south-reach-4252-4252`
    Overlap: near `flowers-smell`, but prose points more at trimmed greenery and private-court plantings than flower scent specifically
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

- Lower-confidence / consider-only-if-builder-requests:
  - `street-footfall-ambient`
    Frequency: low-to-medium, single-zone
    Examples: `kingshade-street-midway-4218-4218-4218`, `saltward-street-midway-4219-4219-4219`
    Overlap: likely already close enough to `sounds-of-traffic`
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

### atmosphere.social_character

- Missing recurring concepts in zone content:
  - None strong enough to propose.

- Notes:
  - The recurring social signals in survey prose largely map onto existing terms such as `residential`, `civic`, `commercial`, `working-class`, and `genteel`.

### atmosphere.surroundings

- Missing recurring concepts in zone content:
  - `district-edge`
    Frequency: 6 rooms across 1 zone (`new_landing`)
    Examples: `amberwick-lane-western-run-4213-4213-4213`, `saltward-street-and-amberwick-lane-4217-4217`, `mallow-lane-2-west-reach-4397`
    Overlap: related to `city-wall-nearby`, but the prose is specifically about boundary stones, enclave edges, and transitional margins rather than generic wall proximity
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

- Lower-confidence / consider-only-if-builder-requests:
  - `private-courts-nearby`
    Frequency: low, single-zone
    Examples: `amberwick-lane-western-run-4213-4213-4213`, `kingshade-street-south-reach-4222`
    Overlap: likely already covered well enough by `housing-nearby`
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

### atmosphere.upkeep

- Missing recurring concepts in zone content:
  - `swept-civic-detail`
    Frequency: 10 rooms across 1 zone (`new_landing`)
    Examples: `amberwick-lane-eastern-run-4215-4215`, `brinehook-alley-west-reach-4220`, `harrowgate-street-2-north-reach-4225-4225`
    Overlap: related to existing `well-maintained` and `pristine-upkeep`; this proposal would add a more specific "actively swept and tended" urban maintenance signal
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

- Lower-confidence / consider-only-if-builder-requests:
  - `fastidious-maintenance`
    Frequency: conceptual overlap only
    Examples: same room family as `swept-civic-detail`
    Overlap: probably too synonymous with `well-maintained` / `pristine-upkeep`
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

### specific_function

- Missing recurring concepts in zone content:
  - None strong enough to propose.

- Notes:
  - The prose survey did not surface a reusable cross-room function concept beyond what is already covered by the existing `specific_function` vocabulary.

### structure

- Missing recurring concepts in zone content:
  - None strong enough to propose.

- Notes:
  - Structure concepts in surveyed names and tags mostly fit the existing vocabulary (`street`, `alley`, `intersection`, `dock`, `bridge`, `entrance`, `threshold`, `building-interior`).

### named_feature

- Missing recurring concepts in zone content:
  - `stoops`
    Frequency: 4 rooms across 1 zone (`new_landing`)
    Examples: `kingshade-street-midway-4218-4218-4218`, `brinehook-alley-west-reach-4220`, `harrowgate-street-2-north-reach-4225-4225`
    Overlap: no close existing named-feature equivalent; this is the strongest concrete urban fixture missing from the current vocabulary
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

  - `boundary-stone`
    Frequency: 6 rooms across 1 zone (`new_landing`)
    Examples: `amberwick-lane-western-run-4213-4213-4213`, `dregs-alley-outer-bend-4375-4375`, `mallow-lane-2-west-reach-4397`
    Overlap: overlaps conceptually with `district-edge`; reviewer should choose one framing if either is accepted
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

- Lower-confidence / consider-only-if-builder-requests:
  - `painted-crest`
    Frequency: low, single-zone
    Examples: `amberwick-lane-eastern-run-4215-4215`, `amberwick-lane-east-reach-4216-4216-4216`
    Overlap: could be handled as prose-only specificity rather than canonical vocab
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

  - `iron-lamp`
    Frequency: low, single-zone
    Examples: `saltward-street-south-reach-4223-4223`
    Overlap: likely too specific for canonical named-feature vocab
    Decision: [ ] accept  [ ] reject  [ ] rename: ____  [ ] defer

## Reviewer Guidance

- Strict reading of the dispatch: **do not canonize any of these yet**, because none clear the 2+ zone threshold.
- Practical reading: if the project wants to proactively enrich the urban vocabulary before more zones are tagged, the strongest first-pass review targets are:
  - `stoops`
  - `horses-ambient`
  - `greenery-fragrance`
  - `district-edge`
  - `swept-civic-detail`
- If the reviewer accepts any addition later, prefer the most general reusable slug rather than a `new_landing`-specific phrase.

## Stop Gate

Per dispatch, this phase stops here.

- No YAML vocab files were modified.
- No schema code was changed.
- No AI generation regression was run.
- No DireBuilder UI changes were made.