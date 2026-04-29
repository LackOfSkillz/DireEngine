# MT-426 - Suppress Room-ID Leakage In Prompt Assembly

## Background

MT-425's outputs are mostly shippable when evaluated against the
project's actual quality standards: grounded prose, two or more senses
per room, and preserved environment. The atmospheric content the older
rubric flags as fabrication, such as fish smells in a market lane or a
hearth in a tavern hallway, is licensed by zone context and aligns with
the prompt's real goals.

The genuine bug is room-ID string leakage. `CRO_500_150` produced prose
that referred to `CRO_500_100` because the prompt assembly was exposing
raw room identifiers when the target room had no human-facing name.

## Phase A - Suppress Identifier Leakage

In `world/builder/prompting/room_description_prompt.py`:

1. When the room being described has no human-facing name, omit the line
   that introduces the room identifier.
2. When listing exits, never include raw target room IDs. Omit the
   target entirely unless a human-facing exit description already exists.

## Phase B - Re-run The Same 6-Room Slice

Use the same live configuration as MT-425 and save outputs as
`exports/sample_descriptions_mt426_qwen14b.txt`.

## Phase C - Confirm Fix

Verify that `CRO_500_150` contains no room-ID strings in the final
output and that the other five rooms remain consistent with MT-425's
quality bar.

Save findings to `exports/mt426_findings.md`.

## Stop And Report

Single test, single report.