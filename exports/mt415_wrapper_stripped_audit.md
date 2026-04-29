# MT-415 Wrapper-Stripped Audit

Shippable: 0/17
Almost-shippable: 0/17
Not shippable: 17/17

Recommendation: Parser-path does not unlock enough quality by itself; continued prompt iteration or a revised diagnosis is justified.

## Sample Table

| Zone | Room | Original words | Stripped words | Original verdict | Stripped verdict | Classification | Sterile flag |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| demo1 | CRO_450_100 | 70 | 50 | safe=False, useful=False | safe=False, useful=False, second_person=0, geometry=0, structural=True | not shippable | no |
| demo1 | CRO_500_100 | 86 | 84 | safe=False, useful=False | safe=True, useful=True, second_person=0, geometry=0, structural=True | not shippable | yes |
| demo1 | CRO_400_150 | 58 | 56 | safe=False, useful=False | safe=True, useful=True, second_person=0, geometry=0, structural=True | not shippable | yes |
| demo1 | CRO_450_150 | 54 | 52 | safe=False, useful=False | safe=True, useful=True, second_person=0, geometry=0, structural=True | not shippable | yes |
| demo1 | CRO_500_150 | 75 | 73 | safe=False, useful=False | safe=False, useful=False, second_person=0, geometry=0, structural=True | not shippable | yes |
| crossingV2 | crossingV2_178_132 | 85 | 64 | safe=False, useful=False | safe=False, useful=False, second_person=0, geometry=0, structural=False | not shippable | yes |
| crossingV2 | crossingV2_192_132 | 58 | 39 | safe=False, useful=False | safe=True, useful=False, second_person=0, geometry=0, structural=True | not shippable | yes |
| crossingV2 | crossingV2_200_132 | 65 | 63 | safe=False, useful=False | safe=True, useful=False, second_person=0, geometry=0, structural=True | not shippable | yes |
| crossingV2 | crossingV2_214_132 | 70 | 45 | safe=False, useful=False | safe=False, useful=False, second_person=1, geometry=0, structural=False | not shippable | no |
| crossingV2 | crossingV2_222_132 | 58 | 56 | safe=False, useful=False | safe=False, useful=False, second_person=0, geometry=0, structural=True | not shippable | yes |
| crossingV2 | crossingV2_236_132 | 72 | 54 | safe=False, useful=False | safe=False, useful=False, second_person=0, geometry=0, structural=True | not shippable | no |
| new_landing | amberwick-lane-western-run-4213-4213-4213 | 63 | 61 | safe=False, useful=False | safe=True, useful=True, second_person=0, geometry=1, structural=True | not shippable | yes |
| new_landing | amberwick-lane-midway-4214-4214 | 69 | 67 | safe=False, useful=False | safe=False, useful=False, second_person=0, geometry=0, structural=True | not shippable | yes |
| new_landing | amberwick-lane-eastern-run-4215-4215 | 65 | 40 | safe=False, useful=False | safe=False, useful=False, second_person=0, geometry=1, structural=True | not shippable | yes |
| new_landing | amberwick-lane-east-reach-4216-4216-4216 | 75 | 63 | safe=False, useful=False | safe=False, useful=False, second_person=1, geometry=0, structural=False | not shippable | no |
| new_landing | saltward-street-and-amberwick-lane-4217-4217 | 58 | 34 | safe=False, useful=False | safe=True, useful=False, second_person=1, geometry=1, structural=True | not shippable | no |
| new_landing | kingshade-street-and-amberwick-lane-4212-4212 | 64 | 62 | safe=False, useful=False | safe=False, useful=False, second_person=2, geometry=0, structural=False | not shippable | yes |

## Sample Details

### demo1 / CRO_450_100

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=0, geometry=0, structural=True
- Stripped items: **Room Data:**, - Structure: cave-passage, - Exits: 2 (north, east), - Atmospheric Tags:, - Materials: earthen-floor, - Sensory: damp-air, - Upkeep: neglected, **Description:**
- Notes: possible unsupported structural detail remains, fails safe rubric after stripping

### demo1 / CRO_500_100

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=True, useful=True, second_person=0, geometry=0, structural=True
- Stripped items: **Room Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile

### demo1 / CRO_400_150

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=True, useful=True, second_person=0, geometry=0, structural=True
- Stripped items: **Room Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile

### demo1 / CRO_450_150

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=True, useful=True, second_person=0, geometry=0, structural=True
- Stripped items: **Room Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile

### demo1 / CRO_500_150

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=0, geometry=0, structural=True
- Stripped items: **Room Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile, fails safe rubric after stripping

### crossingV2 / crossingV2_178_132

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=0, geometry=0, structural=False
- Stripped items: **Room Data:**, - Structure: Cave-Tunnel, - Exits: North, South, **Atmospheric Tags:**, - Materials: Rock-Walls, Dirt-Floor, - Sensory: Echoing-Noises, - Upkeep: Unkempt, **Description:**
- Notes: passes mechanically but reads generic/sterile, fails safe rubric after stripping

### crossingV2 / crossingV2_192_132

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=True, useful=False, second_person=0, geometry=0, structural=True
- Stripped items: **Room Data:**, - Structure: cave-passage, - Exits: north, east, **Atmospheric Tags:**, - Materials: earthen-floor, - Sensory: damp-air, - Upkeep: neglected, **Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile, fails useful rubric beyond minor tolerance

### crossingV2 / crossingV2_200_132

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=True, useful=False, second_person=0, geometry=0, structural=True
- Stripped items: **Room Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile, fails useful rubric beyond minor tolerance

### crossingV2 / crossingV2_214_132

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=1, geometry=0, structural=False
- Stripped items: **Room Data:**, - Structure: cave-passage, - Exit Count: 2, - Exit Directions: north, east, **Atmospheric Tags (present):**, - Materials: earthen-floor, - Sensory: echoing-ambient, - Surroundings: water-nearby, **Description:**
- Notes: second-person remains, fails safe rubric after stripping

### crossingV2 / crossingV2_222_132

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=0, geometry=0, structural=True
- Stripped items: **Room Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile, fails safe rubric after stripping

### crossingV2 / crossingV2_236_132

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=0, geometry=0, structural=True
- Stripped items: **Room Data:**, - Structure: Cavern, - Exits: 3 (North, East, West), - Atmospheric Tags: materials: stone-walls, sensory: echoing, upkeep: neglected
- Notes: possible unsupported structural detail remains, fails safe rubric after stripping

### new_landing / amberwick-lane-western-run-4213-4213-4213

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=True, useful=True, second_person=0, geometry=1, structural=True
- Stripped items: **Room Description:**
- Notes: unsupported geometry remains, possible unsupported structural detail remains, passes mechanically but reads generic/sterile

### new_landing / amberwick-lane-midway-4214-4214

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=0, geometry=0, structural=True
- Stripped items: **Room Description:**
- Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile, fails safe rubric after stripping

### new_landing / amberwick-lane-eastern-run-4215-4215

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=0, geometry=1, structural=True
- Stripped items: **Room Data:**, - Structure: cave-passage, - Exits: north, south, - Materials: rocky-walls, uneven-floor, **Atmospheric Tags (present):**, - Sensory: damp-air, dripping-water, - Upkeep: worn-out, **Description:**
- Notes: unsupported geometry remains, possible unsupported structural detail remains, passes mechanically but reads generic/sterile, fails safe rubric after stripping

### new_landing / amberwick-lane-east-reach-4216-4216-4216

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=1, geometry=0, structural=False
- Stripped items: **Room Data:**, - Structure: cave-passage, - Exits: 2 (north, east), - Upkeep: neglected, **Description:**
- Notes: second-person remains, fails safe rubric after stripping

### new_landing / saltward-street-and-amberwick-lane-4217-4217

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=True, useful=False, second_person=1, geometry=1, structural=True
- Stripped items: **Room Data:**, - Structural Tags: structure: cave-passage, shape: curved, - Exit Data: exits: 2 (north, east), - Atmospheric Tags: materials: rocky-walls, sensory: echoing-sound, **Description:**
- Notes: second-person remains, unsupported geometry remains, possible unsupported structural detail remains, fails useful rubric beyond minor tolerance

### new_landing / kingshade-street-and-amberwick-lane-4212-4212

- Classification: not shippable
- Original verdict: safe=False, useful=False
- Stripped verdict: safe=False, useful=False, second_person=2, geometry=0, structural=False
- Stripped items: **Room Description:**
- Notes: second-person remains, passes mechanically but reads generic/sterile, fails safe rubric after stripping

## Examples: shippable

No samples in this classification.

## Examples: almost-shippable

No samples in this classification.

## Examples: not shippable

### demo1 / CRO_450_100

Original:

```text
**Room Data:**
- Structure: cave-passage
- Exits: 2 (north, east)
- Atmospheric Tags:
  - Materials: earthen-floor
  - Sensory: damp-air
  - Upkeep: neglected

**Description:**
The passage narrows to the north, its earthen floor uneven and slick with moisture. Water drips rhythmically from above, echoing off the low ceiling. The air is heavy with a musty dampness that clings to the skin. To the east, the tunnel opens slightly, hinting at a wider space beyond.
```

Stripped:

```text
The passage narrows to the north, its earthen floor uneven and slick with moisture. Water drips rhythmically from above, echoing off the low ceiling. The air is heavy with a musty dampness that clings to the skin. To the east, the tunnel opens slightly, hinting at a wider space beyond.
```

Notes: possible unsupported structural detail remains, fails safe rubric after stripping

### demo1 / CRO_500_100

Original:

```text
**Room Description:**

The room is a compact square, its four walls close enough to reach out and touch from the center. The ceiling, barely visible above, presses down slightly, creating an intimate atmosphere. Two exits lead off to the north and east, their dark openings stark against the rough stone surfaces. The air here is damp and heavy with a faint metallic tang, hinting at the mining activity nearby. The floor, worn smooth by years of passage, bears deep grooves from countless carts laden with ore.
```

Stripped:

```text
The room is a compact square, its four walls close enough to reach out and touch from the center. The ceiling, barely visible above, presses down slightly, creating an intimate atmosphere. Two exits lead off to the north and east, their dark openings stark against the rough stone surfaces. The air here is damp and heavy with a faint metallic tang, hinting at the mining activity nearby. The floor, worn smooth by years of passage, bears deep grooves from countless carts laden with ore.
```

Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile

### demo1 / CRO_400_150

Original:

```text
**Room Description:**

The room is a square, roughly four paces across each side. Three exits lead out: north, east, and south. The floor is smooth, worn stone, cool to the touch. A faint, musty smell lingers, hinting at long-forgotten dampness. The walls are bare, their surfaces chilled by the drafts that whisper through the unseen corridors beyond.
```

Stripped:

```text
The room is a square, roughly four paces across each side. Three exits lead out: north, east, and south. The floor is smooth, worn stone, cool to the touch. A faint, musty smell lingers, hinting at long-forgotten dampness. The walls are bare, their surfaces chilled by the drafts that whisper through the unseen corridors beyond.
```

Notes: possible unsupported structural detail remains, passes mechanically but reads generic/sterile
