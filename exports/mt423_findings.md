# MT-423 Findings

MT-423 ran a single six-room validation pass against the installed v4 room-description prompt using Qwen 2.5 14B Instruct at temperature 0.5 on the live LM Studio endpoint. The report below captures the standard rubric metrics and checks the specific regressions called out from MT-419 and MT-421 without iteration.

## Inputs

- Endpoint: `http://127.0.0.1:1234`
- Model: `qwen2.5-14b-instruct`
- Temperature: `0.5`
- Export: `exports/sample_descriptions_mt423_qwen14b.txt`
- Passes: `1`

## Standard Metrics

| Metric | Value |
| --- | ---: |
| successful outputs | 2/6 |
| request failures | 4 |
| safe | 2/2 |
| useful | 2/2 |
| wrapper | 0 |
| average words | 57.0 |
| under 45 words | 0 |
| 45-90 words | 2 |
| over 90 words | 0 |
| average sentences | 3.0 |
| under 3 sentences | 0 |
| 3-5 sentences | 2 |
| over 5 sentences | 0 |
| geometry violations | 0 |
| second-person violations | 0 |
| structural-fabrication flag count | 0 |
| poetic filler total | 0 |

## Room Reviews

## demo1 / CRO_500_100

### Full Output

```text
[ERROR] LLM request timed out [2f03e1acb8f7]:
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## demo1 / CRO_500_150

### Full Output

```text
[ERROR] LLM API error [f2f8564208a4]: Model reloaded.
```

### Prior Failure Check

- room-id leakage: suppressed
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## crossingV2 / crossingV2_192_132

### Full Output

```text
[ERROR] LLM request timed out [4d660484411f]:
```

### Prior Failure Check

- invented atmosphere: suppressed
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## crossingV2 / crossingV2_178_132

### Full Output

```text
[ERROR] LLM request timed out [dfb936477e8d]:
```

### Prior Failure Check

- tavern hallucination: suppressed
- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / amberwick-lane-western-run-4213-4213-4213

### Full Output

```text
Amberwick Lane forms an intersection here, with the road branching east and southwest from this point. To the west, Kingshade Street connects to Amberwick Lane at a steady pace of traffic wear along the cobbles. The space is defined by its crossing shape and the routes that lead through it, offering clear paths in multiple directions without any notable permanent fixtures to draw attention.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## new_landing / saltward-street-and-amberwick-lane-4217-4217

### Full Output

```text
Saltward Street runs south from here, narrowing the passage as it continues beyond. To the west, Amberwick Lane stretches further, maintaining a steady path between close-set buildings. The space feels like a simple crossing, defined by its routes and the pressure of nearby structures pressing in around the exits.
```

### Prior Failure Check

- banned phrase: the air is thick with: suppressed
- banned phrase: in the heart of: suppressed
- second-person: suppressed

## Conclusion

This report is single-pass only, per MT-423 stop conditions. Four of the six live requests failed during the run, so the qualitative comparison is only based on the two successful descriptions. Use the room-by-room checks above to separate prompt-behavior observations from runtime instability.
