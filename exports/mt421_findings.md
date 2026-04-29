# MT-421 Findings

MT-421 confirms the MT-420 diagnosis. After raising the live prompt budget to 12000 characters, the assembled prompts are no longer identical or truncated, and the model now receives room identity and exit context. On the same six-room Qwen slice, the two `new_landing` rooms switch from generic chamber/corridor outputs to urban street and lane descriptions, which strongly supports prompt truncation as the cause of the earlier cave-collapse. Residual quality issues remain in other rooms, but the environment-substitution failure on the urban rooms was materially corrected by this fix.

## Inputs

- Endpoint used: `http://127.0.0.1:1234`
- Model used: `qwen2.5-14b-instruct`
- Previous baseline: `exports/sample_descriptions_mt419_qwen14b.txt`
- Fixed run: `exports/sample_descriptions_mt421_qwen14b.txt`

## Prompt Audit

Prompt audit artifact: `exports/mt421_assembled_prompts.md`

- Distinct room-name lines present: 3
- Untrimmed prompt count: 3
- The three MT-421 assembled prompts are no longer identical and now include room identity and exit context.

## Metric Comparison

| Metric | MT-419 Qwen | MT-421 Qwen | Delta |
| --- | ---: | ---: | ---: |
| Wrapper-affected samples | 0 | 0 | 0 |
| Safe samples | 5 | 6 | 1 |
| Useful samples | 4 | 6 | 2 |
| Average words | 65.0 | 62.33 | -2.67 |
| 45-90 word band | 6 | 6 | 0 |
| 3-5 sentence band | 6 | 6 | 0 |
| Poetic filler total | 1 | 0 | -1 |
| Geometry violations | 0 | 0 | 0 |
| Second-person violations | 6 | 2 | -4 |
| Structural-fabrication flag count | 5 | 2 | -3 |

## Room Reviews

## demo1 / CRO_500_100

- Source environment: no explicit structure tag in loaded room data
- MT-419 label: cave-like
- MT-421 label: cave-like
- MT-421 verdict: source ambiguous; output reads as cave-like

### MT-419

```text
A wide chamber stretches before you, its shape defined by four straight walls that meet at right angles. The floor is smooth underfoot, worn from constant use, suggesting a high volume of traffic through this space. Two exits are clearly visible: one to the north and another to the east, both offering clear pathways out of the room without any obstructions or narrowing passages.
```

### MT-421

```text
The narrow passage winds downward and stretches to the west, its rough-hewn walls bearing the marks of ancient tools. The floor is uneven underfoot, with occasional small stones jutting out from the worn surface. As you move westward, the passage gradually narrows slightly, suggesting a more confined space ahead.
```

## demo1 / CRO_500_150

- Source environment: no explicit structure tag in loaded room data
- MT-419 label: cave-like
- MT-421 label: cave-like
- MT-421 verdict: source ambiguous; output reads as cave-like

### MT-419

```text
A wide chamber stretches before you, its four walls meeting at right angles to form a square room. The floor is made of rough stone tiles that have been worn down by constant use, revealing patches of smoother surface where feet have trodden frequently. At the north end of the room, an open archway leads out, while two additional exits are located on the east and west walls.
```

### MT-421

```text
This narrow passage ends abruptly here, leaving only the way up visible ahead. The stone walls press in tightly on either side, their surfaces rough and uneven under the dim light that filters from above. As you stand at this dead end, the sound of distant footsteps echoes faintly from the path leading upward, hinting at its continuation through CRO_500_100.
```

## crossingV2 / crossingV2_192_132

- Source environment: no explicit structure tag in loaded room data
- MT-419 label: cave-like
- MT-421 label: urban-like
- MT-421 verdict: source ambiguous; output reads as urban-like

### MT-419

```text
A spacious chamber opens before you, its four walls extending straight upwards to a high ceiling not visible from the ground level. The room is rectangular with no visible furnishings or decorations; only the worn stone surface of the floor hints at frequent use over time. Four exits are clearly marked: one each in the north, south, east, and west walls, providing easy passage in all cardinal directions.
```

### MT-421

```text
This narrow alleyway serves as a dead-end intersection within the bustling heart of the late-medieval river trade city. Cobblestones worn by constant foot traffic crunch underfoot, and the scent of fish and spices mingles in the air. To the west, the alley opens up into a wider street, where the sounds of merchants hawking their wares and carts clattering along cobblestone paths echo through the narrow passage.
```

## crossingV2 / crossingV2_178_132

- Source environment: structure tag: hallway
- MT-419 label: cave-like
- MT-421 label: urban-like
- MT-421 verdict: source ambiguous; output reads as urban-like

### MT-419

```text
A narrow passage winds between towering stone walls, its surface worn by time but free of debris. The air is cool and dry, carrying faint traces of earth and moss from the nearby forest. This corridor branches to the east after a short distance, narrowing slightly as it continues westward, suggesting an intersection ahead.
```

### MT-421

```text
The narrow hallway of the tavern winds through the bustling late-medieval city, its stone floor worn by frequent foot traffic. A hearth set into the southern wall casts flickering light across the passage, filling it with the scent of roasting meat and ale. The space opens slightly to the east and continues southward, maintaining a steady flow of people moving through this riverside thoroughfare.
```

## new_landing / amberwick-lane-western-run-4213-4213-4213

- Source environment: urban lane in a city; raw YAML has environment: city and no tags.structure
- MT-419 label: cave-like
- MT-421 label: urban-like
- MT-421 verdict: correct urban environment

### MT-419

```text
This room is a simple chamber with four exits: north, east, south, and west. The floor is made of rough stone, uneven and worn in places where it meets the walls. To the east, the passage widens slightly before continuing on, while to the west, it remains steady and straight without any changes in width or direction. The air here feels still, with no noticeable smells or sounds except for an occasional echo from one of the distant corridors.
```

### MT-421

```text
Amberwick Lane forms an intersection here, with the path branching in three directions. To the east and west, the lane continues straight, while a southwestward turn leads to Kingshade Street. The worn stone surface of the pathway feels rough underfoot, hinting at frequent use by travelers. The space opens up slightly around the intersections, allowing for easy movement between the different directions.
```

## new_landing / saltward-street-and-amberwick-lane-4217-4217

- Source environment: urban street intersection in a city; raw YAML has environment: city and no tags.structure
- MT-419 label: cave-like
- MT-421 label: urban-like
- MT-421 verdict: correct urban environment

### MT-419

```text
A large chamber opens up before you, its dimensions stretching out into shadowy recesses at the far end. The floor is a rough-hewn stone surface, uneven underfoot but free of debris or obstructions. To your left, a narrow passageway branches off from the main room, while to your right, another corridor continues straight ahead without interruption.
```

### MT-421

```text
Saltward Street stretches ahead, narrowing slightly as it continues to the south. To the west, Amberwick Lane offers a parallel passage that diverges from this path. The surface of the dirt road is uneven, with small stones and pebbles scattered about, making each step require careful footing. The air here feels open, with no immediate boundary or obstruction save for the continuation of these two paths.
```

## Conclusion

The prompt-truncation diagnosis was correct. This change is sufficient to get urban context into the model again, and the two previously collapsed `new_landing` rooms now read as streets/lanes instead of stone chambers. The remaining work is narrower: improve groundedness for the other rooms and reduce residual second-person / passage-default behavior without reopening the truncation bug.
