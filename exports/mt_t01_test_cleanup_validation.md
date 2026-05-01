# MT-T01 Validation

Status: completed

## Scope Completed

- Canonicalized prompt/state time vocabulary to `night, morning, afternoon, evening` in the active prompt module, the room description system prompt, the state markup prompt, and the state design note.
- Repaired the active state-mapping regression in the prompt router so hallway-style interiors regain `invasion` and city-tagged urban exteriors regain `weather` and `invasion`.
- Updated stale prompt, API, import-normalization, and generation tests to match the current prompt architecture and normalized room-tag shape.

## B1 Resolution

- `hallway` was missing from the active building-interior structure set, which caused hallway interiors to lose the `invasion` state group.
- `city` was missing from the active urban-exterior environment set, which caused city exteriors without a more specific exterior structure tag to lose `weather` and `invasion`.
- The active urban-exterior structure set also lacked several older values (`intersection`, `courtyard`, `bridge`, `dock`) that still appeared in test fixtures and legacy content.

## B2 Classification

- The remaining `Description:` prompt-test failures were not a live payload regression.
- The assembled prompt now legitimately contains the instructional sentence `Do not echo input field names like "Room Description:" or "Structure:".` inside the system prompt.
- The blanket form-shape negative match was narrowed so it still rejects old packet-style sections while allowing instructional quoted field names in the modern prompt contract.

## Focused Validation

Command:

```powershell
$env:DJANGO_SETTINGS_MODULE='server.conf.settings'; c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest tests.test_room_description_prompt tests.test_builder_llm_api tests.test_import_zone_service tests.test_room_description_generation
```

Result:

```text
.........................................
----------------------------------------------------------------------
Ran 41 tests in 0.205s

OK
```

## Broader Validation

Command:

```powershell
$env:DJANGO_SETTINGS_MODULE='server.conf.settings'; c:/Users/gary/dragonsire/.venv/Scripts/python.exe -m unittest discover tests
```

Result:

```text
Ran 241 tests in 47.573s

OK (skipped=1)
```

## Notes

- The trim-budget prompt test now uses a realistic budget floor for the current system prompt size and an oversized fixture that actually exercises the trim path.
- The room description generation test now asserts on current prompt facts that are guaranteed to appear even when the room name is intentionally suppressed because it matches the room identifier.