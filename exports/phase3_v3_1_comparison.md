# Phase 3 v3.1 Comparison

Overall verdict: Approach not viable at this model size

## Compliance metrics
- Banned-noun leak rate: 4/4 in Phase 3 batch 1 vs 4/4 in v3.1.
- Geometry violations: ['run4'] in Phase 3 batch 1 vs ['run1', 'run2', 'run3', 'run4'] in v3.1.
- Structural fabrication on tagged rooms:
  - crossingV2_204_360: 4/4 runs flagged.
  - crossingV2_120_702: 4/4 runs flagged.
  - crossingV2_96_918: 4/4 runs flagged.
  - crossingV2_352_326: 0/4 runs flagged.
  - crossingV2_252_536: 4/4 runs flagged.
  - crossingV2_64_698: 4/4 runs flagged.
- Second-person violations: 34 total across runs ({'run1': 6, 'run2': 9, 'run3': 14, 'run4': 5}).
- Player-assumption violations: 0 total across runs ({'run1': 0, 'run2': 0, 'run3': 0, 'run4': 0}).
- Untagged drift sample:
  - crossingV2_472_564: drifted in v3.1; batch 1 was drifted.
  - crossingV2_686_294: drifted in v3.1; batch 1 was drifted.
  - crossingV2_350_362: drifted in v3.1; batch 1 was clean.

## Quality metrics
- Atmospheric keyword hits on tagged rooms:
  - crossingV2_204_360: 4.25 in Phase 3 batch 1 vs 0.25 in v3.1.
  - crossingV2_120_702: 5.75 in Phase 3 batch 1 vs 0.75 in v3.1.
  - crossingV2_96_918: 6 in Phase 3 batch 1 vs 0 in v3.1.
  - crossingV2_352_326: 5 in Phase 3 batch 1 vs 0 in v3.1.
  - crossingV2_252_536: 5 in Phase 3 batch 1 vs 0 in v3.1.
  - crossingV2_64_698: 5 in Phase 3 batch 1 vs 0 in v3.1.
- Repeated phrases top 10:
  - room data structure (75)
  - room data structure cave (71)
  - data structure cave (71)
  - room data structure cave passage (59)
  - data structure cave passage (59)
  - exits 2 north (59)
  - structure cave passage (59)
  - atmospheric tags materials (54)
  - exits 2 north east (53)
  - 2 north east (53)

## Spot checks
- crossingV2_252_536: failed: still invents structure or exits
- crossingV2_96_918: failed: still invents exits or room shape
- crossingV2_204_360: mixed: retains some atmosphere but still fabricates structure
- crossingV2_472_564: failed: untagged drift remains
- crossingV2_318_564: passed: banned-noun leak removed
