# MT-509 Generate Description Validation

## Successful generation

- Route: `POST /direbuilder/api/zone/builder2/room/CRO_450_300/generate-description/`
- Result: success in live DireBuilder UI on `http://localhost:4001/direbuilder/?zone=builder2`
- Applicable groups: `season`, `time`
- Applicable states: `spring`, `summer`, `autumn`, `winter`, `morning`, `midday`, `evening`, `night`
- Telemetry:
  - `input_tokens`: `3530`
  - `output_tokens`: `199`
  - `elapsed_ms`: `9455`
  - `approximate_cost_usd`: `0.013575`
  - UI display: `Last generation: $0.014 · 9.5s`

### Pass 2 output

```text
The stone walls of this compact space rise close on all sides, their fitted blocks showing careful placement$state(winter,  with a faint rime of frost along the mortar lines where cold has settled)$state(summer,  the stone holding a faint warmth from heat that seeps through from above). The floor is level and unmarked, offering no sign of regular passage or use$state(morning,  though a thin shaft of light from some unseen crack above marks the early hour)$state(night,  darkness complete save for whatever light you bring). No exits break the enclosing boundaries, leaving the space sealed within its own dimensions.
```

## Map lockout during generation

- Starting room title before request: `CRO_450_300 TEMP CHECK`
- Generate button text during request: `Generating...`
- During the in-flight request, a click was dispatched to room node `CRO_450_350`
- Room title during request remained: `CRO_450_300 TEMP CHECK`
- Room title after request remained: `CRO_450_300 TEMP CHECK`
- Conclusion: the map selection callback was successfully ignored while generation was in flight, so the response could not land on a different room.

## Save round-trip verification

- After successful generation, the Save button changed to `Save Zone*`
- Saving via DireBuilder cleared the dirty marker back to `Save Zone`
- Reloading `/direbuilder/?zone=builder2` preserved the generated description exactly
- After reload, the Description tab still showed the generated `$state(...)` text and the button label was `Regenerate`

## Failed generation case

- Test method:
  - Overrode `ANTHROPIC_API_KEY` in the live server terminal to `invalid-key-for-mt509`
  - Restarted the server in that same terminal session so the bad env var was inherited by the process
  - Clicked `Regenerate` in DireBuilder
- HTTP result: `500`
- JSON response:

```json
{
  "ok": false,
  "error": "generation_failed",
  "message": "Error code: 401 - {'type': 'error', 'error': {'type': 'authentication_error', 'message': 'invalid x-api-key'}, 'request_id': 'req_011CaaACHd8AbL9u8FCvuTZ8'}",
  "retriable": false
}
```

- UI behavior:
  - Persistent MT-507z banner was reused successfully
  - Banner kicker changed to `Generation Error`
  - Banner body showed the authentication failure message
  - Generate button re-enabled after the failed request
  - Room description remained unchanged
  - Save button remained `Save Zone` because the failure path did not mutate working state

## Legacy route check

- `/builder/` still does not include MT-509 DireBuilder-specific markers:
  - no `#direbuilder-generate-description`
  - no `#direbuilder-description-telemetry`
  - no `window.DireBuilderPageApi`
- Conclusion: MT-509 wiring stayed scoped to DireBuilder and did not attach the new production path to the legacy builder route.

## Environment cleanup

- Restored the original `ANTHROPIC_API_KEY`
- Restarted the local Evennia web stack again after the failure-path validation