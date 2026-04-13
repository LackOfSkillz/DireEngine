# DireBuilder As Built

This file is the lightweight implementation log for DireBuilder planning and build work.

Use it to answer:

- what Builder decisions have already been locked
- which files changed for each substantive Builder step
- how another developer can reasonably reproduce or continue the work
- what remains intentionally undecided

## Update Rule

Append a short entry for each substantive Builder step.

Do not log tiny wording tweaks or typo-only edits. Log real changes in architecture, contracts, isolation rules, API shape, persistence shape, or implementation slices.

Use this timestamp format:

`2026-04-13 hh:mm:ss`

## Entry Template

2026-04-13 hh:mm:ss
## TASK DB-XXX [Short Name]
### What changed
### Files touched
### Reproduction notes
### What the next dev should know
### Known limits

2026-04-13 15:46:38
## TASK DB-000 Create Builder As-Built Log
### What changed
Created this file as the running implementation log for DireBuilder so future work can be reproduced without rereading the full blueprint or chat history.

### Files touched
- `direBuilderAsBuilt.md`
- `DireBuilder.md`

### Reproduction notes
Start from `DireBuilder.md` for the target architecture and append one short entry here whenever Builder work materially changes the plan or implementation. Keep entries concise and implementation-focused.

### What the next dev should know
This file is intended to be lighter than the blueprint. It should explain what changed, where it changed, and what assumptions are now locked.

### Known limits
This is a process artifact, not a full design document. It does not replace `DireBuilder.md`.

2026-04-13 15:46:39
## TASK DB-001 Lock Canonical Live World Schema
### What changed
Formalized Phase 0 as the authoritative live world contract in `DireBuilder.md`. The schema now explicitly defines rooms, exits, objects, templates, instances, placement, vendor behavior, coordinates, and map import expectations against Evennia's live world model.

### Files touched
- `DireBuilder.md`

### Reproduction notes
Read Section `0. Canonical Live World Schema` first. Any future Builder backend or import/export work should map back to that contract instead of inventing a parallel room graph or object hierarchy.

### What the next dev should know
The key lock is that movement remains exit-based, placement remains Evennia-location-based, and Builder/AreaForge/admin tools must all converge on the same live world structure.

### Known limits
Stable room identifiers, full template persistence, and multi-floor coordinate policy are still open decisions.

2026-04-13 15:46:40
## TASK DB-002 Separate AreaForge From Builder Mode
### What changed
Rewrote the builder blueprint to explicitly separate AreaForge from Builder Mode. AreaForge is now documented as an import and reconstruction pipeline, while Builder Mode is documented as the forward-authoring system for native world creation and editing.

### Files touched
- `DireBuilder.md`

### Reproduction notes
Review Sections `14.13`, `14.14`, and `14.15` in `DireBuilder.md`. When designing Builder features, reuse only the compatible live-world output shape and map payload expectations from AreaForge, not OCR or parser assumptions.

### What the next dev should know
Builder Mode must not be built on top of AreaForge internals. The shared target is the Evennia world model, not the same pipeline.

### Known limits
Bridge work between Builder-authored data and AreaForge artifacts is still optional future work, not foundation work.

2026-04-13 15:46:41
## TASK DB-003 Add Repo-Specific Builder Reconnaissance
### What changed
Appended a repo-grounded reconnaissance section to the builder blueprint describing the current code reality: browser and Godot transport surfaces, existing Django JSON API patterns, live world mutation paths, room and exit schema reuse, AreaForge map payload shape, template-system gaps, and the safest implementation order for this repo.

### Files touched
- `DireBuilder.md`

### Reproduction notes
Read Section `14. Codebase-Specific Reconnaissance (2026-04-13)` before writing any Builder code. It identifies the current owning surfaces in the repo and the gaps that still need real design instead of UI-first work.

### What the next dev should know
The biggest current gap is not client UX. It is the absence of a dedicated builder mutation/service layer and the lack of a unified template persistence model.

### Known limits
This reconnaissance is accurate to the repo state inspected on 2026-04-13. It should be refreshed if the underlying runtime architecture changes significantly.

2026-04-13 15:46:42
## TASK DB-004 Lock Builder Isolation And Optionality
### What changed
Added Phase `0.14 Builder Isolation and Optionality` to require that DireBuilder remain a private, optional, plugin-style extension that DireEngine can run without. The blueprint now explicitly requires isolated directory structure, guarded imports, feature gating, conditional API loading, and a removal test where the engine still boots without Builder.

### Files touched
- `DireBuilder.md`

### Reproduction notes
Read Section `0.14` before creating any Builder package or endpoint. If a change would make core engine runtime depend on `world/builder/`, it violates the current architecture lock.

### What the next dev should know
The hard rule is: DireEngine must never know DireBuilder exists. Dependency direction is one-way only. Builder may call into the engine; the engine may not require Builder.

### Known limits
This step locks the architecture rule, not the implementation. The capability helper, conditional URL registration, and private package layout still need to be built when Builder implementation starts.

2026-04-13 15:46:43
## TASK DB-005 Build Foundation Slice For Schema, Room Service, And Map Import
### What changed
Built the first private Builder implementation slice under `world/builder/`: a locked `map_schema_v1` validator, a minimal room mutation service, and a two-pass map importer that creates rooms before exits. Added a `world/builder/` ignore rule so the private Builder tree stays out of normal git flows unless intentionally included later.

### Files touched
- `.gitignore`
- `world/builder/__init__.py`
- `world/builder/schemas/__init__.py`
- `world/builder/schemas/map_schema_v1.py`
- `world/builder/services/__init__.py`
- `world/builder/services/room_service.py`
- `world/builder/services/map_importer.py`
- `direBuilderAsBuilt.md`

### Reproduction notes
From a repo checkout with the Evennia environment available, create the private `world/builder/` package locally, keep it ignored in `.gitignore`, then import `validate_map_schema(...)`, `create_room(...)`, and `import_map(...)` from the new modules. The importer contract is schema-first, pass-1 room creation, pass-2 exit creation.

### What the next dev should know
This slice proves the foundation only. It intentionally does not include templates, placement hierarchy, AI generation, vendor logic, or UI hooks. Stable builder IDs are stored on `room.db.builder_id`, and rooms are also tagged for lookup by Builder services.

### Known limits
Because `world/builder/` is now ignored, these files stay local unless the ignore rule is changed or files are force-added intentionally. The importer is minimal and idempotent for rooms and same-key exits, but it does not yet handle reverse-exit policy, deletion sync, or richer metadata.