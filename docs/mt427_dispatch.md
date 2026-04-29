# MT-427 - Suppress Zone-ID Leakage In Prompt Assembly

## Background

MT-426 fixed room-ID leakage. The same pattern persists with zone IDs:
`amberwick-lane-western-run-4213-4213-4213` produced prose that said
`within the new_landing area` because the prompt assembly emitted the
zone identifier directly.

## Phase A - Apply Identifier Suppression To Zone Names

In `world/builder/prompting/room_description_prompt.py`, find where the
zone name is incorporated into the model-facing prompt. Apply the same
suppression heuristic used for room names: if the zone name appears to
be a code identifier, omit it from the model-facing prompt rather than
feeding the raw identifier to the model.

## Phase B - Re-run The Same Six-Room Slice

Use the same live configuration as MT-426 and save outputs as
`exports/sample_descriptions_mt427_qwen14b.txt`.

Verify that `amberwick-lane-western-run-4213-4213-4213` no longer
contains `new_landing` or any other code-style zone identifier.

Save findings to `exports/mt427_findings.md`.

## Stop And Report

Single test, single report.