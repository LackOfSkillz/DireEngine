# MT-421 Findings

MT-421 confirms the MT-420 diagnosis. After raising the live prompt budget to 12000 characters, the assembled prompts are no longer identical or truncated, and the model now receives room identity and exit context. On the same six-room Qwen slice, the two `new_landing` rooms switch from generic chamber/corridor outputs to urban street and lane descriptions, which strongly supports prompt truncation as the cause of the earlier cave-collapse. Residual quality issues remain in other rooms, but the environment-substitution failure on the urban rooms was materially corrected by this fix.

## Inputs

- Endpoint used: `http://127.0.0.1:1234`
- Model used: `qwen2.5-14b-instruct`
- Previous baseline: `exports/sample_descriptions_mt419_qwen14b.txt`
- Fixed run: `exports/sample_descriptions_mt421_qwen14b_rerun_20260428.txt`

## Prompt Audit

Prompt audit artifact: `exports/mt421_assembled_prompts_rerun_20260428.md`

- Distinct room-name lines present: 3
- Untrimmed prompt count: 3
- The three MT-421 assembled prompts are no longer identical and now include room identity and exit context.

## Metric Comparison

| Metric | MT-419 Qwen | MT-421 Qwen | Delta |
| --- | ---: | ---: | ---: |
| Wrapper-affected samples | 0 | 0 | 0 |
| Safe samples | 5 | 6 | 1 |
| Useful samples | 4 | 3 | -1 |
| Average words | 65.0 | 56.0 | -9.0 |
| 45-90 word band | 6 | 5 | -1 |
| 3-5 sentence band | 6 | 6 | 0 |
| Poetic filler total | 1 | 0 | -1 |
| Geometry violations | 0 | 0 | 0 |
| Second-person violations | 6 | 0 | -6 |
| Structural-fabrication flag count | 5 | 1 | -4 |

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
The passage stretches downward and to the west, its boundaries tight but unmarked by walls or barriers. The surface beneath is worn smooth from constant use, particularly near the western exit where traffic seems heavier. Downward, the route continues in darkness, offering a stark contrast to the dim light filtering through the entrance to the west.
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
A narrow passage leads upward from the dead-end room, leaving little space to move in any other direction. The floor is worn along the path that continues up, hinting at regular traffic heading towards higher ground. With no other exits recorded, the room feels confined and focused solely on the route ahead.
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
A narrow lane ends here to the east, with buildings closing in from both sides. The cobbles show steady wear along the center, darkened by frequent traffic. To the west, the lane continues beyond a cluster of merchants and travelers gathered at the crossing.
```

## crossingV2 / crossingV2_178_132

- Source environment: structure tag: hallway
- MT-419 label: cave-like
- MT-421 label: cave-like
- MT-421 verdict: correct passage-like environment

### MT-419

```text
A narrow passage winds between towering stone walls, its surface worn by time but free of debris. The air is cool and dry, carrying faint traces of earth and moss from the nearby forest. This corridor branches to the east after a short distance, narrowing slightly as it continues westward, suggesting an intersection ahead.
```

### MT-421

```text
A narrow hallway runs east and south through this bustling tavern, its worn floor showing the steady traffic of patrons moving between rooms. A hearth set into the eastern wall casts flickering light across the space, illuminating rough-hewn timber beams that crisscross above. The air carries the scent of roasting meat mingled with the faint tang of ale from nearby barrels, suggesting a lively scene just beyond the passage’s bounds.
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
Amberwick Lane forms a busy intersection where it runs east and west, with a secondary route leading southwest. The road surface is worn along the center, showing steady traffic flow between the three exits. Building fronts press close to the lane on both sides, narrowing the thoroughfare near the southwestern exit.
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
Saltward Street runs south from Amberwick Lane, forming a narrow passage between close-set stone buildings. The lane narrows slightly to the west, where it meets Amberwick Lane, and broadens again as it continues south toward Saltward Street’s midpoint. Steady traffic has worn the cobbles along the center of both routes, creating darker paths that converge at this intersection.
```

## Conclusion

The prompt-truncation diagnosis was correct. This change is sufficient to get urban context into the model again, and the two previously collapsed `new_landing` rooms now read as streets/lanes instead of stone chambers. The remaining work is narrower: improve groundedness for the other rooms and reduce residual second-person / passage-default behavior without reopening the truncation bug.
