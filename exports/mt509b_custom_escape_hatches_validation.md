# MT-509b Custom Escape Hatches Validation

## Scope

- Route under test: `http://localhost:4001/direbuilder/?zone=builder2`
- Room under test: `CRO_450_300` / `CRO_450_300 TEMP CHECK`
- Atmosphere custom values exercised during validation:
  - `materials += weathered-brickwork`
  - `social_character += watchful-neighbors`
  - `surroundings += tide-marked-stalls`
  - `sensory += green-copper-smell`
  - `upkeep = freshly-swept`

## Add / Save / Reload

- Passed: each of the five atmosphere axes exposed the new `+ Add custom` affordance.
- Passed: entering the custom values above produced visually marked custom pills in the picker.
- Passed: adding the custom values dirtied the zone immediately.
- Passed: `Save Zone` completed successfully and a full page reload preserved all five custom values as custom-marked pills.
- Passed: the generated request payload from the live browser contained the saved custom values unchanged under `room.tags.atmosphere`.

## Generation Path

- Initial failure reproduced before the prompt-path fix:
  - HTTP status: `500`
  - Root cause: prompt assembly still called strict room-tag normalization, which rejected custom atmosphere values before the Anthropic call.
- Fix validation after prompt-path normalization change:
  - Live browser POST: `POST /direbuilder/api/zone/builder2/room/CRO_450_300/generate-description/`
  - HTTP status: `200`
  - Telemetry shown in UI: `Last generation: $0.015 · 9.4s`
  - Request body still contained:
    - `materials: ["stone-walls", "weathered-brickwork"]`
    - `social_character: ["watchful-neighbors"]`
    - `surroundings: ["tide-marked-stalls"]`
    - `sensory: ["green-copper-smell"]`
    - `upkeep: "freshly-swept"`

### Pass 2 output

```text
The narrow lane runs between weathered brick buildings, their stone foundations showing dark tide marks where water has risen and receded. Freshly swept cobbles lead past shuttered stalls, their copper fittings gone green with salt air$state(spring,  and gleaming with morning dew)$state(summer,  warm beneath the midday sun)$state(autumn,  scattered with fallen leaves from window boxes above)$state(winter,  slick with frost in the shadows between buildings). Building fronts press close on both sides, with neighbors visible at upper windows keeping watch over the street below$state(morning,  some calling greetings down to early vendors)$state(evening,  lamplight beginning to glow behind their shutters)$state(night,  their silhouettes barely visible in the dim light of street lanterns).
```

### Influence check

- Passed: the custom values influenced generated prose in the successful live run.
- Observed direct or obvious prompt-aligned influence in Pass 2 output:
  - `weathered-brickwork` -> `weathered brick buildings`
  - `tide-marked-stalls` -> `dark tide marks`
  - `freshly-swept` -> `Freshly swept cobbles`
  - `green-copper-smell` -> `copper fittings gone green with salt air`
  - `watchful-neighbors` -> `neighbors visible at upper windows keeping watch`

## Strict-Field Check

- Passed: zone-level controlled fields did not gain the custom affordance.
  - `setting_type`
  - `era_feel`
  - `climate`
  - `culture`
  - `mood`
- Passed: room-level non-atmosphere controlled tags did not gain the custom affordance.
  - `structure`
  - `specific_function`
  - `named_feature`
  - `condition`
- Passed: `tags.custom` retained its existing freeform behavior and was not changed by this dispatch.

## Removal Cleanup

- Passed: clicking each custom pill removed it from the selected room.
- Passed: a follow-up save succeeded with no save error.
- Passed: a reload showed no residual custom pills for the five temporary validation values.

## Result

- MT-509b acceptance criteria satisfied:
  - custom atmosphere terms can be added in the UI
  - custom values persist through save and reload
  - generation receives those values and returns successful Pass 2 output
  - strict zone-level and non-atmosphere room fields remain vocab-only