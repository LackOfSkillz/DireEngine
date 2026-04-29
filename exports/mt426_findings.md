# MT-426 Findings

MT-426 ran a single six-room validation pass after suppressing room-ID leakage in the prompt assembly, using Qwen 2.5 14B Instruct at temperature 0.5 on the live LM Studio endpoint. The report below checks the specific leakage fix and preserves the same room-by-room review format used in MT-425.

## Inputs

- Endpoint: `http://127.0.0.1:1234`
- Model: `qwen2.5-14b-instruct`
- Temperature: `0.5`
- Prompt version: `v5_diremud_condensed`
- Export: `exports/sample_descriptions_mt426_qwen14b.txt`
- Passes: `1`

## Standard Metrics

| Metric | Value |
| --- | ---: |
| successful outputs | 6/6 |
| request failures | 0 |
| safe | 6/6 |
| useful | 3/6 |
| wrapper | 0 |
| average words | 52.83 |
| under 45 words | 2 |
| 45-90 words | 4 |
| over 90 words | 0 |
| average sentences | 3.0 |
| under 3 sentences | 0 |
| 3-5 sentences | 6 |
| over 5 sentences | 0 |
| geometry violations | 0 |
| second-person violations | 2 |
| structural-fabrication flag count | 2 |
| poetic filler total | 0 |

## Room Reviews

## demo1 / CRO_500_100

### Full Output

```text
A narrow passage runs down and to the west between worn stone walls. The earthen floor is uneven, with slight depressions marking the path's wear from foot traffic. The boundaries press close, leaving little room for deviation as it continues in both directions.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## demo1 / CRO_500_150

### Full Output

```text
A narrow passage ends here with the walls closing in around you. The floor beneath your feet shows signs of regular use and wear. An upward route beckons from this dead-end, leading to what lies above.
```

### Prior Failure Check

- room-id leakage: suppressed
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: recurred (`\byou\b` x1, `\byour\b` x1)

## crossingV2 / crossingV2_192_132

### Full Output

```text
At the western edge of Market Square, a narrow alley dead-ends in a tangle of wooden crates and discarded barrels. The cobbled path narrows here, worn smooth by years of foot traffic and occasional cart wheels. To the west, the alley opens into the main thoroughfare, where the murmur of distant traders and the scent of river fish mingle with the city's usual bustle.
```

### Prior Failure Check

- invented atmosphere: recurred (`\bfish\b` x1)
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## crossingV2 / crossingV2_178_132

### Full Output

```text
The narrow hallway of the bustling tavern runs east and south between worn stone walls. A hearth at the eastern end casts a warm glow across the space, its smoke curling up through a vent in the ceiling. The earthen floor is marked by steady wear from frequent traffic, hinting at the lively trade that passes through this riverside city.
```

### Prior Failure Check

- tavern hallucination: recurred (`\bhearth\b` x1)
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / amberwick-lane-western-run-4213-4213-4213

### Full Output

```text
Amberwick Lane intersects here within the new_landing area, offering three routes to explore: continuing east, turning southwest, or heading west. The cobbled surface shows steady wear from frequent travel, marking paths where pedestrians and possibly carts often traverse. Building fronts line the lane on both sides, though no specific doorways or intersections interrupt its flow.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / saltward-street-and-amberwick-lane-4217-4217

### Full Output

```text
Saltward Street intersects with Amberwick Lane in a narrow passage that runs south and west from this point. The cobbled surface shows signs of regular use, particularly near the center where foot traffic has worn it smooth. Building fronts press closely on either side, offering little space for anything beyond steady pedestrian movement through the lane.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## Conclusion

This report is single-pass only. Use the room-by-room checks above to confirm that identifier leakage is gone while comparing the qualitative outputs against MT-425.
