# MT-427 Findings

MT-427 ran a single six-room validation pass after suppressing zone-ID leakage in the prompt assembly, using Qwen 2.5 14B Instruct at temperature 0.5 on the live LM Studio endpoint. The report below checks that zone code identifiers no longer appear in the generated prose while preserving the same room-by-room review format.

## Inputs

- Endpoint: `http://127.0.0.1:1234`
- Model: `qwen2.5-14b-instruct`
- Temperature: `0.5`
- Prompt version: `v6_diremud_condensed_zone_scrub`
- Export: `exports/sample_descriptions_mt427_qwen14b.txt`
- Passes: `1`

## Standard Metrics

| Metric | Value |
| --- | ---: |
| successful outputs | 6/6 |
| request failures | 0 |
| safe | 5/6 |
| useful | 2/6 |
| wrapper | 0 |
| average words | 54.33 |
| under 45 words | 1 |
| 45-90 words | 5 |
| over 90 words | 0 |
| average sentences | 3.0 |
| under 3 sentences | 0 |
| 3-5 sentences | 6 |
| over 5 sentences | 0 |
| geometry violations | 0 |
| second-person violations | 0 |
| structural-fabrication flag count | 2 |
| poetic filler total | 0 |

## Room Reviews

## demo1 / CRO_500_100

### Full Output

```text
A narrow passage stretches from the west to the east, with a downward path leading south at its eastern end. The earthen floor is uneven and marked by occasional footprints, indicating frequent travel through this corridor. At the far end, the passage narrows slightly before opening to a descent heading south.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## demo1 / CRO_500_150

### Full Output

```text
A narrow passage leads upward from this dead-end space, its rough walls and floor indicating frequent use. The ceiling looms close above, suggesting the route continues vertically rather than horizontally. With no other exits, the focus is on the ascent ahead.
```

### Prior Failure Check

- room-id leakage: suppressed
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## crossingV2 / crossingV2_192_132

### Full Output

```text
At the western edge of Market Lane, a dead-end alley narrows between two stone buildings, their facades showing signs of wear from years of use. Cobblestones pave the ground, worn smooth by constant foot traffic leading west back towards the heart of the market district. The air carries faint hints of river mist and distant shouts of merchants hawking goods, underscoring the bustling nature of this late-medieval trade city.
```

### Prior Failure Check

- invented atmosphere: recurred (`\bmerchants? hawking\b` x1)
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## crossingV2 / crossingV2_178_132

### Full Output

```text
The narrow hallway of the bustling tavern runs east and south between worn stone walls. A hearth at the eastern end casts a warm glow across the space, its faint smoke mingling with the scent of roasting meats from nearby kitchens. The floor shows steady wear where patrons frequently tread, marking well-worn paths through this riverside establishment.
```

### Prior Failure Check

- tavern hallucination: recurred (`\bhearth\b` x1, `\bpatrons?\b` x1)
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / amberwick-lane-western-run-4213-4213-4213

### Full Output

```text
Amberwick Lane intersects here in Western Run, with pathways branching out to the east, southwest, and west. The worn cobbles indicate frequent traffic at this busy intersection, particularly towards the eastern and southwestern exits. Building fronts press closely around the lane, framing its narrow path without encroaching on the open space needed for movement.
```

### Prior Failure Check

- zone-id leakage: suppressed
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / saltward-street-and-amberwick-lane-4217-4217

### Full Output

```text
Saltward Street runs as a narrow passage to the south and west from Amberwick Lane. The fitted cobbles underfoot show steady wear, indicating frequent travel through this thoroughfare. To the south, Saltward Street narrows slightly before continuing on, while to the west, it widens marginally as it approaches an intersection.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## Conclusion

This report is single-pass only. Use the room-by-room checks above to confirm that zone identifier leakage is gone while comparing the qualitative outputs against MT-426.
