# MT-417 Comparison

## Phase A Finding

- Request payload sent exactly one `user` message and no `system` message.
- The codebase prompt text was embedded inside that `user` message.
- The response still emitted `**Room Description:**`, matching MT-415-style wrapper leakage.
- Practical finding: the LM Studio UI override is not winning in behavior, so the Phase B batch below reflects current effective behavior rather than a verified layered override.

## Evidence Files

- tmp/mt417_prompt_layering_test.txt
- exports/sample_descriptions_mt417_run1.txt

## Metric Comparison

| Metric | MT-415 | MT-417 | Delta |
| --- | ---: | ---: | ---: |
| Generated samples | 17 | 17 | 0 |
| Safe samples | 0 | 0 | 0 |
| Useful samples | 0 | 0 | 0 |
| Useful acceptance rate | 0.0 | 0.0 | 0.0 |
| Wrapper leakage total | 55 | 71 | 16 |
| Wrapper-affected samples | 17 | 17 | 0 |
| Average words | 67.35 | 71.24 | 3.8900000000000006 |
| 45-90 word band | 17 | 17 | 0 |
| 3-5 sentence band | 17 | 17 | 0 |
| Poetic filler total | 9 | 9 | 0 |
| Fabrication watchlist total | 2 | 1 | -1 |
| Stub phrase total | 1 | 0 | -1 |
| Second-person violations | 5 | 7 | 2 |
| Geometry violations | 3 | 6 | 3 |
| Structural-fabrication flag count | 16 | 17 | 1 |

## Distribution Comparison

- MT-415 word buckets: under_45=0, 45_to_90=17, over_90=0
- MT-417 word buckets: under_45=0, 45_to_90=17, over_90=0
- MT-415 sentence buckets: under_3=0, 3_to_5=17, over_5=0
- MT-417 sentence buckets: under_3=0, 3_to_5=17, over_5=0

## Five-Room Verdicts

### CRO_500_100

- MT-415 wrapper: partially disappeared
- MT-417 wrapper: persisted
- MT-415 tracked failures: none of the tracked MT-415 failures
- MT-417 tracked failures: second-person
- Body quality verdict relative to MT-415: worse

MT-417 sample:

```text
**Room Data:**

- Structure: cave-passage
- Exits: 2 (north, east)
- Materials: rock-walls

**Atmospheric Tags:**

- Sensory: echoing
- Upkeep: worn

**Description:**

The narrow cave passage stretches out, hewn from the earth's bedrock. Rough, worn stone walls press close on either side, their surfaces damp to the touch and slick with condensation. Each footstep sends a sharp echo bouncing off the hard-packed dirt floor, announcing your presence in this quiet, confined space. The air grows colder as you venture deeper, the chill seeping into the very stones themselves.
```

### crossingV2_192_132

- MT-415 wrapper: persisted
- MT-417 wrapper: partially disappeared
- MT-415 tracked failures: none of the tracked MT-415 failures
- MT-417 tracked failures: none of the tracked MT-415 failures
- Body quality verdict relative to MT-415: same

MT-417 sample:

```text
**Room Description:**

The room is rectangular, with three exits leading north, east, and south. The walls are made of rough-hewn stone, cold to the touch. A faint draft whispers through the northern exit, carrying a hint of damp earth. The floor is bare, worn smooth by time rather than use, reflecting the dim light from an unseen source.
```

### saltward-street-and-amberwick-lane-4217-4217

- MT-415 wrapper: persisted
- MT-417 wrapper: persisted
- MT-415 tracked failures: geometry term, second-person
- MT-417 tracked failures: second-person
- Body quality verdict relative to MT-415: worse

MT-417 sample:

```text
**Room Data:**

- Structure: cave-passage
- Exits: 2 (north, east)
- Atmospheric Tags:
  - Materials: earthen-floor, rocky-walls
  - Sensory: damp-air

**Description:**

The passage narrows as it stretches northward, the earthen floor sloping gently beneath your feet. The walls, rough and damp to the touch, close in on either side, their jagged surfaces glistening with moisture. A chill hangs heavy in the air, carrying a faint, musty scent of wet earth. The passage opens up slightly to the east, revealing a hint of the exit's direction.
```

### amberwick-lane-western-run-4213-4213-4213

- MT-415 wrapper: partially disappeared
- MT-417 wrapper: persisted
- MT-415 tracked failures: geometry term
- MT-417 tracked failures: second-person
- Body quality verdict relative to MT-415: worse

MT-417 sample:

```text
**Room Data:**

- Structure: cave-passage
- Exits: 2 (North, East)
- Materials: stone-walls

**Atmospheric Tags:**

- Sensory: damp-air
- Upkeep: worn

**Description:**

The passage narrows to the North, its rough stone walls glistening with moisture. The air grows heavy and damp as you proceed, each breath drawing in the scent of wet earth. To the East, the tunnel widens slightly, revealing a faint hint of light from an unseen source. The ground beneath is uneven, worn smooth by time rather than feet, leading deeper into the cave system.
```

### CRO_500_150

- MT-415 wrapper: partially disappeared
- MT-417 wrapper: persisted
- MT-415 tracked failures: lantern fabrication
- MT-417 tracked failures: geometry term
- Body quality verdict relative to MT-415: worse

MT-417 sample:

```text
**Room Data:**

- Structure: cave-passage
- Exits: north, south
- Materials: rough-stones
- Atmospheric Tags: sensory: damp-air

**Description:**

The narrow passage curves gently to the north and south, hemmed in by rough stone walls that glisten with moisture. The air is heavy with a cool, earthy dampness, carrying a faint echo of dripping water from unseen depths. The floor slopes slightly downward, worn smooth by countless footsteps, leading deeper into the subterranean labyrinth.
```
