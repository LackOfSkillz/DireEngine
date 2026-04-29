# MT-419 Findings

Phase A shows the checked `new_landing` YAML entries are urban `environment: city` rooms with no `tags.structure` or `atmosphere.materials` block, so the raw YAML did not encode the MT-417 cave collapse. Phase C shows Qwen 2.5 removed wrapper leakage on this six-room slice entirely, but it did not preserve environment context reliably: the two `new_landing` urban rooms still failed to read as streets/lanes, and other rooms were often recast as generic chambers, corridors, or cave-like spaces. The next step should be to investigate prompt/input structure and room-data shaping before committing to Qwen as a drop-in replacement.

## Inputs

- Endpoint used: `http://127.0.0.1:1234`
- Model used: `qwen2.5-14b-instruct`
- Phase A report: `tmp/mt419_phase_a_room_data.md`
- Qwen export: `exports/sample_descriptions_mt419_qwen14b.txt`
- MT-417 comparison source: `exports/sample_descriptions_mt417_run1.txt` filtered to the same 6 rooms

## Phase A Verdict

Finding A2 applies for the checked `new_landing` rooms. The raw YAML is urban and does not encode `cave-passage` in the requested fields.

## Metric Comparison

| Metric | MT-417 Slice | MT-419 Qwen | Delta |
| --- | ---: | ---: | ---: |
| Wrapper-affected samples | 6 | 0 | -6 |
| Safe samples | 0 | 5 | 5 |
| Useful samples | 0 | 4 | 4 |
| Average words | 75.83 | 65.0 | -10.83 |
| 45-90 word band | 6 | 6 | 0 |
| 3-5 sentence band | 6 | 6 | 0 |
| Poetic filler total | 3 | 1 | -2 |
| Geometry violations | 2 | 0 | -2 |
| Second-person violations | 4 | 6 | 2 |
| Structural-fabrication flag count | 6 | 5 | -1 |

## Room Reviews

## demo1 / CRO_500_100

- Source environment: no explicit structure tag in loaded room data
- Environment verdict: source ambiguous; output reads as generic enclosed room

```text
A wide chamber stretches before you, its shape defined by four straight walls that meet at right angles. The floor is smooth underfoot, worn from constant use, suggesting a high volume of traffic through this space. Two exits are clearly visible: one to the north and another to the east, both offering clear pathways out of the room without any obstructions or narrowing passages.
```

## demo1 / CRO_500_150

- Source environment: no explicit structure tag in loaded room data
- Environment verdict: source ambiguous; output reads as generic enclosed room

```text
A wide chamber stretches before you, its four walls meeting at right angles to form a square room. The floor is made of rough stone tiles that have been worn down by constant use, revealing patches of smoother surface where feet have trodden frequently. At the north end of the room, an open archway leads out, while two additional exits are located on the east and west walls.
```

## crossingV2 / crossingV2_192_132

- Source environment: no explicit structure tag in loaded room data
- Environment verdict: source ambiguous; output reads as cave-like

```text
A spacious chamber opens before you, its four walls extending straight upwards to a high ceiling not visible from the ground level. The room is rectangular with no visible furnishings or decorations; only the worn stone surface of the floor hints at frequent use over time. Four exits are clearly marked: one each in the north, south, east, and west walls, providing easy passage in all cardinal directions.
```

## crossingV2 / crossingV2_178_132

- Source environment: structure tag: hallway
- Environment verdict: source ambiguous; output reads as cave-like

```text
A narrow passage winds between towering stone walls, its surface worn by time but free of debris. The air is cool and dry, carrying faint traces of earth and moss from the nearby forest. This corridor branches to the east after a short distance, narrowing slightly as it continues westward, suggesting an intersection ahead.
```

## new_landing / amberwick-lane-western-run-4213-4213-4213

- Source environment: urban lane in a city; raw YAML has environment: city and no tags.structure
- Environment verdict: incorrect: substituted cave environment

```text
This room is a simple chamber with four exits: north, east, south, and west. The floor is made of rough stone, uneven and worn in places where it meets the walls. To the east, the passage widens slightly before continuing on, while to the west, it remains steady and straight without any changes in width or direction. The air here feels still, with no noticeable smells or sounds except for an occasional echo from one of the distant corridors.
```

## new_landing / saltward-street-and-amberwick-lane-4217-4217

- Source environment: urban street intersection in a city; raw YAML has environment: city and no tags.structure
- Environment verdict: incorrect: substituted cave environment

```text
A large chamber opens up before you, its dimensions stretching out into shadowy recesses at the far end. The floor is a rough-hewn stone surface, uneven underfoot but free of debris or obstructions. To your left, a narrow passageway branches off from the main room, while to your right, another corridor continues straight ahead without interruption.
```

## Recommendation

Qwen is better than MT-417 on wrapper control for this slice, but it is not yet shippable as-is because environment preservation is still unstable and structural fabrication remains present. The next move should be input/prompt-structure investigation, especially how source room identity is represented before the model sees it, rather than more blind model iteration.
