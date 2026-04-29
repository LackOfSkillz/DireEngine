# MT-425 Findings

MT-425 ran a single six-room validation pass against the condensed v5 room-description prompt using Qwen 2.5 14B Instruct at temperature 0.5 on the live LM Studio endpoint. The report below captures the standard rubric metrics and checks the specific regressions called out from MT-419 and MT-421 without iteration.

## Inputs

- Endpoint: `http://127.0.0.1:1234`
- Model: `qwen2.5-14b-instruct`
- Temperature: `0.5`
- Prompt version: `v5_diremud_condensed`
- Export: `exports/sample_descriptions_mt425_qwen14b_v5.txt`
- Passes: `1`

## Standard Metrics

| Metric | Value |
| --- | ---: |
| successful outputs | 6/6 |
| request failures | 0 |
| safe | 3/6 |
| useful | 2/6 |
| wrapper | 0 |
| average words | 56.5 |
| under 45 words | 0 |
| 45-90 words | 6 |
| over 90 words | 0 |
| average sentences | 3.0 |
| under 3 sentences | 0 |
| 3-5 sentences | 6 |
| over 5 sentences | 0 |
| geometry violations | 1 |
| second-person violations | 0 |
| structural-fabrication flag count | 3 |
| poetic filler total | 1 |

## Room Reviews

## demo1 / CRO_500_100

### Full Output

```text
A narrow passage runs through this space, extending downward and to the west. The earthen floor is worn smooth where frequent footfalls have passed, with the western edge showing more signs of use. Downward sloping ground marks the route leading further below, while the walls remain close and unadorned throughout.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## demo1 / CRO_500_150

### Full Output

```text
A narrow passage ends here with a rough earthen floor and close boundaries on all sides except to the north where it opens into CRO_500_100. The walls show signs of wear from occasional use, though no other features mark this dead-end space. The air is still, carrying no sounds beyond.
```

### Prior Failure Check

- room-id leakage: recurred (`\bCRO_500_100\b` x1)
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## crossingV2 / crossingV2_192_132

### Full Output

```text
At the end of this narrow lane, the worn cobblestones slope gently toward the river’s edge to the east, where a faint mist rises from the water. To the west, the lane continues through crossingV2_178_132, leading deeper into the bustling heart of the trade city. The air carries the mingled scents of fresh fish and baking bread, with occasional shouts of merchants echoing off the nearby buildings.
```

### Prior Failure Check

- invented atmosphere: recurred (`\bfish\b` x1)
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## crossingV2 / crossingV2_178_132

### Full Output

```text
The narrow hallway of the bustling tavern runs east and south, its floor showing signs of steady wear from frequent traffic. A hearth set against the north wall casts a warm glow over the passage, its smoke curling up towards the ceiling. The air carries hints of cooking food and ale, mingling with the faint scent of river mist that seeps in from outside.
```

### Prior Failure Check

- tavern hallucination: recurred (`\bhearth\b` x1, `\bale\b` x1)
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / amberwick-lane-western-run-4213-4213-4213

### Full Output

```text
Amberwick Lane forms an intersection here, with cobbled paths running east and west through the narrow lane. To the southwest, another route branches off from the main thoroughfare. The fitted stones show wear where traffic frequently passes between these directions, maintaining a clear path for travelers moving along the well-trodden street.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / saltward-street-and-amberwick-lane-4217-4217

### Full Output

```text
Saltward Street runs west from here, narrowing into Amberwick Lane to the south. The cobbled surface shows steady wear along the passage, with scuff marks indicating frequent travel between these two routes. Building fronts press in close on either side, their stone facades marking the boundaries of this urban thoroughfare.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## Conclusion

This report is single-pass only. Use the room-by-room checks above to separate prompt-behavior observations from any runtime instability observed during the live run.
