DireMud Builder Mode + AI Content System
Full Engineering Blueprint

Implementation log for concrete Builder decisions and completed slices lives in `direBuilderAsBuilt.md` and should be updated as substantive work lands.

0. Canonical Live World Schema

This section defines the authoritative structure of the game world as stored and manipulated in Evennia. All systems such as Builder Mode, AreaForge, startup scripts, and future APIs must produce and operate on this structure.

0.1 World Authority

The Evennia world is the single source of truth.

All mutations must occur through:

- Evennia typeclasses
- builder service layer when Builder is installed
- controlled API endpoints

No system may maintain a parallel live world model.

0.2 Room Model

Rooms are Evennia objects using `typeclasses.rooms.Room`.

Required canonical fields:

- `id` (dbref now, with room for a future stable identifier policy)
- `db.desc`
- `db.map_x`
- `db.map_y`

Optional but standard fields:

- `db.map_layer` (new, for multi-floor support)
- `db.region`
- `db.environment_type`
- `db.terrain_type`

Current room flags that fit the model:

- `db.is_shop`
- `db.is_bank`
- `db.is_guardhouse`
- `db.is_jail`
- `db.is_shrine`

Rooms contain:

- exits via Evennia `Exit` objects
- contents via Evennia `contents`

0.3 Exit Model

Exits are Evennia objects using `typeclasses.exits.Exit`.

Canonical fields:

- `location` (source room)
- `destination` (target room)
- `key` (direction)
- optional `db.exit_display_name`

Rules:

- movement is always exit-based
- coordinates are never used for traversal
- reverse exits are optional but recommended

0.4 Object Model

All world entities are Evennia objects.

Current canonical categories:

- items: `typeclasses.objects.Object`
- NPCs: Evennia objects with NPC-specific typeclasses, scripts, or behavior attached

Shared structure:

- `id`
- `key`
- `db.desc`
- `location` (room or container)

0.5 Template Model

Templates define reusable content.

Templates are not live world objects. They are definitions used to create instances.

Required fields:

- `template_id`
- `type` (`item` or `npc`)
- `name`
- `tags`
- `description`

Optional fields:

- `behavior_profile`
- `vendor_profile`

Templates must be stored in a centralized registry or structured data store.

0.6 Instance Model

Instances are live Evennia objects created from templates.

Canonical rule:

- instances are stored as Evennia objects
- template linkage is stored on the instance via `db.template_id`

0.7 Placement Model

Placement is defined by Evennia `location`.

Canonical rules:

- room placement: `obj.location = room`
- containment: `obj.location = container`
- surface placement in the first implementation uses the same location model as containment
- surface semantics are differentiated by flags such as `container.db.is_surface = True`

Constraints:

- no circular containment
- an object cannot contain itself
- validation is required for nesting depth

0.8 NPC Role Model

NPCs may define:

- `db.role_type`

Valid values:

- `generic`
- `vendor`
- `trainer`
- `guard`
- `quest_giver`
- `banker`
- `innkeeper`

0.9 Vendor Model

Vendor behavior is defined via `db.vendor_profile`.

Example:

{
	"is_vendor": true,
	"currency": "gold",
	"buy_types": ["weapon", "armor"],
	"pricing_profile": "standard"
}

Vendor inventory is stored as:

- `npc.contents`

Not as room placement metadata.

0.10 Map Coordinates

Coordinates are used for:

- visualization
- builder tools
- client map rendering

Coordinates are not used for:

- movement
- traversal rules

0.11 Map File Contract

Builder-generated maps must describe:

- rooms with coordinates
- exit relationships
- optional room metadata

All imports must resolve into:

- Evennia rooms
- Evennia exits

0.12 System Compatibility Rule

All world-authoring systems must conform to this schema:

- Builder Mode
- AreaForge
- admin scripts
- startup builders
- future tools

No system may introduce:

- alternate room graphs
- parallel object hierarchies
- incompatible placement logic

0.13 Phase 0 Outcome

This section is the contract all future builder work should target.

It exists to prevent:

- Builder-authored rooms behaving differently from AreaForge-imported rooms
- placement drift between tools
- exit inconsistencies
- incompatible world mutation paths

0.14 Builder Isolation and Optionality

This section defines a hard architectural constraint for DireBuilder.

DireBuilder must be:

- fully isolated from core DireEngine code
- safe to exclude from the public repository
- safe to ignore via `.gitignore`
- non-breaking when not present
- dynamically enabled only when installed

0.14.1 Core Dependency Rule

DireEngine must never depend on DireBuilder.

DireBuilder may depend on DireEngine.

The dependency direction is one-way only.

0.14.2 Required Directory Isolation

Builder code should live in its own isolated tree so it can be excluded cleanly.

Target structure:

```text
world/
  builder/
	__init__.py
	services/
	api/
	content_generation/
	templates/
	validators/
	config.py
```

If the project remains private, that tree can be ignored entirely without affecting core engine runtime.

Practical rule:

- no builder code in core Evennia typeclass modules
- no builder code in unrelated engine services
- no builder-only modules mixed into mandatory startup paths

0.14.3 Safe Import Rule

Core code must never use unconditional imports of builder modules.

Forbidden pattern:

```python
from world.builder.services.room_service import update_room
```

Allowed pattern:

```python
try:
	import world.builder
	BUILDER_AVAILABLE = True
except ImportError:
	BUILDER_AVAILABLE = False
```

Preferred pattern:

- central capability check such as `is_builder_available()`
- all builder feature exposure guarded behind that capability check
- explicit required-service probing rather than hand-written chained boolean expressions

Recommended capability pattern:

```python
REQUIRED_SERVICES = [
	"room_service",
	"template_service",
	"spawn_service",
	"placement_service",
	"instance_service",
]

for service_name in REQUIRED_SERVICES:
	__import__(f"world.builder.services.{service_name}")
```

This avoids:

- silent typos in availability checks
- stale partial-import conditions
- malformed chained boolean expressions as Builder services grow

0.14.3.1 Evennia Search Import Rule

When Builder code needs Evennia object lookup helpers, import them explicitly from the stable utility module.

Required pattern:

```python
from evennia.utils.search import search_object
```

Do not rely on:

- `from evennia import search_object`
- implicit or re-exported search helpers

This rule is intentionally strict so Builder API and service code does not drift across mixed Evennia import surfaces or runtime-specific re-export behavior.

0.14.4 Feature Gating Rule

All builder-only functionality must fail closed when Builder is absent.

Examples:

- builder UI hidden
- builder endpoints not registered
- builder commands unavailable
- builder API returns a controlled unavailable error instead of crashing

Core gameplay must continue normally.

0.14.5 API Isolation Rule

Builder web/API surfaces must remain isolated from the core API tree and only load conditionally.

Examples:

- builder routes grouped under a dedicated builder API surface
- URL registration only happens when Builder is installed
- no mandatory import of builder URL modules from core URL configuration

0.14.6 Service Isolation Rule

Builder services are optional extension services, not core engine dependencies.

Allowed:

- Builder calling core services
- Builder mutating Evennia rooms, exits, and objects through approved mutation paths

Not allowed:

- core systems calling builder services as a requirement for normal runtime
- startup logic assuming builder services exist

0.14.7 Data Compatibility Rule

Builder must use the live Evennia world model and compatible `.db` fields.

Safe examples:

- `room.db.map_layer = 1`
- `obj.db.template_id = "vendor_blacksmith_t1"`

Unsafe direction:

- core runtime logic depending on builder-only metadata structures to function

Builder data may extend the world model, but core gameplay must not require Builder-specific storage in order to run.

0.14.8 No Core Mutation Assumptions

DireEngine must not assume the existence of:

- template registries
- builder services
- AI generation services
- vendor-template tooling
- builder validation subsystems

Those are optional builder concerns unless and until they are promoted into the open core intentionally.

0.14.9 Valid Runtime States

Two runtime states must be supported.

With Builder installed:

- builder UI may be enabled
- builder API may be enabled
- template tooling may be enabled
- AI-assisted authoring may be enabled

Without Builder installed:

- the game still boots normally
- rooms, exits, items, NPCs, and movement still work
- no builder endpoints are required
- no builder imports are required
- no runtime errors occur because Builder is missing

0.14.10 Test Requirement

Builder isolation is not complete until this removal test passes:

1. exclude or ignore `world/builder/`
2. start DireEngine
3. confirm there are no import errors
4. confirm normal gameplay still works

This is a release gate, not a nice-to-have.

0.14.11 Future Packaging Outcome

This isolation model keeps DireBuilder viable as any of the following later:

- a private in-repo plugin
- a separate private repository
- a package installed into selected environments only

Final rule:

DireBuilder must behave like a plugin that hooks into DireEngine, not like a subsystem DireEngine requires in order to run.

1. Product Goal

Create a live world authoring system embedded in the Godot client that allows authorized users (GM/Admin/Builder) to:

Live Editing
Walk the world like a player
Edit rooms in-place
Modify exits
Add/remove NPCs and items
Place objects hierarchically (room / on / inside)
Content Creation
Create new rooms, NPCs, and items
Use AI-assisted generation for descriptions, behavior, and flavor
World Building
Design new areas using a visual map editor
Export and import structured map files
Rapidly iterate on world layout and content
2. Core Architecture Principles
2.1 Mode Separation

Player Mode and Builder Mode must be separate.
Builder Mode is a privileged UI state.

2.2 Evennia is Authority

All world state lives in Evennia:

rooms
exits
objects (items and NPCs)
containment
persistence

Godot is responsible for:

UI
editor
visualization
2.3 Service Layer Required

All builder actions must flow through:

Godot → Builder API → Evennia Services → World State

No direct database writes from the client.

2.4 Template vs Instance Model
Concept	Example
Template	wooden table
Instance	table_456 in room_4411
2.5 Placement is a Relationship

candelabra → located_on → table
table → located_in → room

2.6 Hierarchical World Model

Room
├── Table
│ └── Candelabra
├── Crate
│ └── Apples
└── NPC (Guard)

3. Feature System Overview
3.1 Builder Mode Entry
Admin-only access
Mode toggle
Replaces player UI with builder UI
3.2 Walk and Edit System

Builder can:

Move room to room
Edit current room

Editable:

name
description
tags
coordinates
layer/floor
3.3 Exit Editor

Supports:

add/remove exits
relink exits
create new rooms
optional reverse linking
3.4 NPC System

Add NPC flow:

Create new template
Search existing templates
Spawn NPC instance into room
3.5 Item System

Add Item flow:

Create template or select existing
Choose placement:
In Room
On Object
Inside Object
3.6 Content Hierarchy Panel

Displays nested contents:

Room
├── Table
│ └── Candelabra
└── Guard

Supports:

move
remove
reassign location
3.7 Room Creation
Create new room from exit
Auto-link exits
Open editor immediately
3.8 Visual Map Designer

Godot-based editor:

Create room nodes
Drag nodes
Assign coordinates
Connect exits
Multi-layer support
Export/import JSON
3.9 Map Import and Export

map.json → Evennia importer → creates rooms and exits

3.9.1 Deterministic Map Diff Model

Map diff must be treated as explicit world mutation, not inferred reconciliation.

Builder must not implement:

- compare two full maps and guess intended deletes
- implicit reconciliation side effects
- rename detection
- hidden exit cleanup

Builder should implement:

- explicit change sets
- deterministic ordered application
- service-driven orchestration over existing room and exit services

The canonical diff shape for the first implementation is:

```json
{
	"area_id": "area-1",
	"operations": [
		{"id": "op-001", "op": "create_room", "room": {...}},
		{"id": "op-002", "op": "update_room", "room_id": "r1", "updates": {...}},
		{"id": "op-003", "op": "delete_room", "room_id": "r1"},
		{"id": "op-004", "op": "set_exit", "source_id": "r1", "direction": "east", "target_id": "r2"},
		{"id": "op-005", "op": "delete_exit", "source_id": "r1", "direction": "east"}
	]
}
```

Operation `id` should be supported as an optional field in `v1`.

Rules:

- if present, it must be a non-empty string
- it is for traceability, audit linking, and future undo support
- it must not change execution semantics
- operation order still comes from list order, not lexical id order

Internal normalization rule:

```python
operation_id = op.get("id") or f"auto-{index}"
```

Where `index` is the zero-based position in the `operations` list.

Implications:

- callers are not required to provide ids in `v1`
- every applied operation still gets a stable trace id within a single diff payload
- audit entries can always include an `operation_id`
- preview responses should include normalized `operation_ids` in execution order so UI, debugging, and audit correlation can map validation results directly to the diff payload

Design rule:

- explicit operation ids are required for any persistent, replayable, collaborative, or undo-capable diff
- fallback ids are acceptable for testing, ad-hoc usage, and immediate runtime traceability only

Only these operations should be supported in `v1`:

- `create_room`
- `update_room`
- `delete_room`
- `set_exit`
- `delete_exit`

No additional operation types should be added until the first deterministic workflow is stable.

3.9.2 Diff Service Contract

The first diff implementation should live at:

```text
world/builder/services/map_diff_service.py
```

Primary entry point:

```python
def apply_diff(diff: dict):
```

Execution model:

- validate the diff payload first
- apply operations in listed order
- stop immediately on first failure
- do not batch
- do not parallelize
- treat diff state as progressive, not snapshot-based
- validate and execute each operation against the state produced by all earlier operations in the same diff
- capture undo pre-state immediately before each invertible operation executes against that progressive state

Recommended dispatcher shape:

```python
def apply_operation(op):
		op_type = op["op"]

		if op_type == "create_room":
				...
		elif op_type == "update_room":
				...
		elif op_type == "delete_room":
				...
		elif op_type == "set_exit":
				...
		elif op_type == "delete_exit":
				...
		else:
				raise ValueError("Unknown operation")
```

3.9.3 Diff Integration Rule

The diff service is an orchestrator only.

It must not:

- mutate `.db` fields directly
- create Evennia objects directly
- bypass validation already owned by lower services
- replace the importer or exit reconciliation model

It must reuse existing Builder services:

- `room_service.create_room`
- `room_service.update_room`
- `instance_service.delete_instance`
- `exit_service.ensure_exit`
- `exit_service.delete_exit`

3.9.4 Diff Validation Rule

The first validation layer should remain minimal but explicit.

Required checks:

- `area_id` exists and is non-empty
- `operations` exists and is a list
- each operation includes the required fields for its `op`
- optional operation `id`, if present, must be a non-empty string
- unknown operation types fail immediately

This layer should validate structure, not infer intent.

3.9.5 Diff Safety Rules

The following rules are non-negotiable for the first implementation:

1. No hidden deletes.
2. No continuation after failure.
3. Deterministic application order.
4. Reapplying the same diff must converge without corrupting state.

The first room deletion policy should be conservative:

- room delete should fail when incoming exits still reference the room
- incoming exits should not be auto-removed implicitly in `v1`

3.9.6 Diff Audit Rule

Each applied operation should emit a structured audit event.

Recommended audit shape:

```python
log_audit_event("diff_apply", object_id, {
	"operation_id": operation_id,
		"operation": op_type,
		"payload": op,
})
```

This keeps diff history aligned with the existing audit-first Builder model.

If operation ids are present, audit entries should carry them through unchanged. If they are absent, the normalized fallback id should be used instead.

If a diff is submitted with a top-level `group_id`, audit entries should also carry that `group_id` through as metadata for logical UI grouping only.

3.9.7 Diff API Rule

The first diff endpoint should be:

```text
POST /api/builder/map/diff/
```

Request shape:

```json
{
	"diff": {...}
}
```

Response shape:

```json
{
	"ok": true,
	"applied": 5
}
```

The endpoint should remain thin and delegate fully to the diff service.

When diff application fails, the API should return structured failure context including:

- `failed_operation_index`
- `failed_operation_id`
- `failed_operation`

This is for debugging and UI feedback only and does not change execution semantics.

Optional request metadata may include:

- `session_id`
- `group_id`

Rules:

- `session_id` identifies a logical editing context only; it is not an auth session and does not change diff execution semantics
- `group_id` is metadata for logical grouping only; it does not change execution order, validation, or failure behavior
- neither field should introduce batching, nesting, or transactional semantics in `v1`

3.9.8 Diff Test Targets

Minimum required validation targets for the first slice:

1. create room then update room
2. set exit then replace the same exit target
3. create exit then delete exit
4. successful operation followed by failing operation stops further application

These are workflow tests for deterministic mutation, not inference tests.

3.10 Template System

Supports:

item templates
NPC templates

Fields:

name
category
tags
description
behavior hooks (later)
3.11 Search System

Example:
Search: "table"

Returns:

wooden_table_basic
noble_dining_table
3.12 Validation System

Checks:

broken exits
orphan rooms
containment loops
invalid placement
3.13 Audit Logging

Track:

actor
action
before/after values
timestamp
4. AI Content Generation System
4.1 Purpose

Solve:

description bottleneck
consistency issues
content scaling
4.2 Model

Local LM Studio:

mistral-nemo-12b-instruct

4.3 Architecture

Godot UI
→ Builder API
→ Prompt Builder
→ LM Studio
→ Response returned to UI

4.4 Input Model
Tags (Primary)

Examples:

urban
coastal
working_class
wealthy
grimy
Object Context

Optional:

visible objects
materials
NPC types
Neighbor Context (Later)
nearby room descriptions
4.5 Output Constraints
Type	Length
Room	3–6 sentences
NPC	1–2 sentences
Item	1–2 sentences
4.6 UI Integration

Room Editor:

Generate
Regenerate
Refine

Tag selection via dropdowns:

environment
wealth level
condition
material tone
4.7 Prompt System

services/content_generation/

Includes:

room_generator
npc_generator
item_generator
behavior_generator
inventory_generator
prompt_builder
5. NPC Behavior and Vendor System
5.1 NPC Template Structure

template_id
name
description
tags
role_type
behavior_profile
vendor_profile (optional)

5.2 Role System

role_type:

generic
vendor
trainer
guard
quest_giver
banker
innkeeper
5.3 Behavior Profiles

Example:

{
"type": "guard",
"aggression": "medium",
"patrol": false,
"assist_faction": "city_watch"
}

5.4 AI-Assisted Behavior

Builder UI:

Generate Behavior
Edit Behavior
5.5 Vendor System

Vendor is a profile attached to NPC.

Example:

{
"is_vendor": true,
"currency": "gold",
"buy_types": ["weapon", "armor"],
"sell_inventory": [],
"pricing_profile": "standard"
}

5.6 Vendor Inventory

Managed through UI:

Add item
Add template item
Set quantity

Supports:

static inventory
template-driven inventory (later)
5.7 Inventory Model

Vendor inventory is stored as:

npc.contents

Not room placement.

5.8 AI-Assisted Inventory Generation

Input:

vendor role
tags
category

Output:

list of items appropriate to context
5.9 Optional Dialogue Generation

Later:

greetings
refusal lines
ambient chatter
6. Data Model
Room

id
name
description
map_x
map_y
map_layer
tags
exits
contents

Exit

direction
source_room
target_room

Template

template_id
type (npc or item)
name
tags
definition

Instance

instance_id
template_id
location_id

Placement

room
surface
container

7. File Structure
Godot

godot_client/
scenes/builder/
scripts/builder/
scripts/api/
scripts/map/

Evennia

world/builder/
api.py
services/
validators/
content_generation/

Map Data

data/maps/
draft/
published/

8. API Contract
Room

GET /builder/room/{id}
PATCH /builder/room/{id}

Exits

POST /builder/exits
DELETE /builder/exits/{id}

Templates

GET /builder/templates
POST /builder/templates

Spawn

POST /builder/spawn

Move Instance

POST /builder/move-instance

NPC Vendor

POST /builder/npc/{id}/vendor

NPC Inventory

POST /builder/npc/{id}/inventory

AI Generation

POST /builder/generate/room
POST /builder/generate/npc
POST /builder/generate/item
POST /builder/generate/npc-behavior
POST /builder/generate/vendor-inventory

Map

POST /builder/map/import
GET /builder/map/export

9. Map File Format

{
"area_id": "west_reach",
"rooms": [
{
"id": "wr_001",
"name": "Alley",
"map_x": 8,
"map_y": -4,
"map_layer": 0,
"exits": {
"east": "wr_002"
}
}
]
}

Coordinates are for display only. Movement is exit-based.

10. Implementation Phase Plan
Phase 1 — Builder Mode Core
mode toggle
permissions
base UI
Phase 2 — Room Editing
edit name
edit description
save
Phase 3 — Exit Editing
create/remove exits
create new rooms
Phase 4 — NPC and Item Spawn
template search
spawn instance
Phase 5 — Placement System
placement modal
containment logic
hierarchy UI
Phase 6 — Template Creation
create NPC and item templates
assign roles
Phase 7 — NPC Behavior System
behavior profiles
role system
Phase 8 — Vendor System
vendor toggle
inventory UI
pricing hooks
Phase 9 — AI Integration
room generation
NPC generation
behavior generation
inventory generation
Phase 10 — Map Designer
visual editor
export JSON
Phase 11 — Map Import
build world from JSON
Phase 12 — Validation and Safety
validation rules
audit logs
basic undo support
Phase 13 — Diff-Based Map Editing
explicit diff payloads
ordered application
thin diff API endpoint
11. Risks
Mixing builder UI with player UI
Skipping template system
Ignoring containment hierarchy
Unconstrained AI output
Building map editor too early
12. Final Positioning

This system is not just a UI feature or map tool.

It is a full world authoring platform that includes:

spatial design
structural design
content creation
behavior definition
economic systems
AI-assisted generation
13. Recommended Starting Point

After spells system completion:

Start with:

Phase 1
Phase 2
Phase 3

Do not begin with:

map editor
AI generation
advanced template complexity

Build the foundation first, then layer intelligence on top.

14. Codebase-Specific Reconnaissance (2026-04-13)

This section captures the current Dragons Ire code reality that should shape the builder detour.

14.1 Client and Transport Reality

- Godot support exists, but the browser client is still the primary player-facing surface.
- The Godot websocket bridge is already enabled in `server/conf/settings.py` on `127.0.0.1:4008`.
- Structured client payload helpers already exist in `world/area_forge/utils/messages.py` via `send_structured(...)`.
- There is already a validation/debug command for structured Godot payloads in `commands/cmd_testgodot.py`.

Implication:

Builder mode does not need a brand-new transport model first. It can likely use:

- Django JSON endpoints for request/response CRUD
- existing websocket structured payloads for live refresh/push updates

14.2 Web API Pattern Already In Use

- Current JSON APIs live under `web/api/`.
- URL routing is defined in `web/api/urls.py`.
- View pattern is defined in `web/api/views.py`.
- Authenticated JSON endpoints already use `JsonLoginRequiredView` and `JsonResponse`.
- The existing character builder is a good pattern reference: `web/character_builder.py`, `web/api/views.py`, and `web/static/website/js/character_builder.js`.

Implication:

The builder API should probably be added as a first-class Django API surface in the existing web stack rather than inventing a separate service host.

14.3 World Authority and Mutation Reality

- Evennia is already the authority, which matches the blueprint.
- Rooms are implemented in `typeclasses/rooms.py`.
- Exits are implemented in `typeclasses/exits.py`.
- Current world construction is still mostly done through direct `create_object(...)` calls inside builder scripts and admin/debug commands.
- Examples:
	- `world/the_landing.py`
	- `world/areas/crossing/empath_guild/build.py`
	- `world/areas/crossing/cleric_guild/build.py`
	- `commands/cmd_spawnnpc.py`
	- `commands/cmd_spawnvendor.py`

Important gap:

- There is no dedicated `world/builder/` subsystem yet.
- There is no builder-specific service layer or audit log implementation yet.

Implication:

The first backend milestone should be a real builder mutation/service layer, not the UI.

14.4 Existing Room Schema We Can Reuse

`typeclasses.rooms.Room` already carries a meaningful amount of editable world metadata.

Current room fields already present include:

- `db.desc`
- `db.environment_type`
- `db.terrain_type`
- `db.allowed_professions`
- `db.is_bank`
- `db.is_guardhouse`
- `db.is_jail`
- `db.is_shop`
- `db.is_shrine`
- `db.is_vault`
- `db.is_recovery_point`
- `db.region`
- `db.law_type`
- `db.fishable`

Map coordinates already exist today as:

- `db.map_x`
- `db.map_y`

Important schema gap:

- `map_layer` appears in this blueprint, but there is no current code usage for `db.map_layer` yet.

Implication:

Room editing can start from existing fields immediately, but any multi-floor or layer model is still a new schema decision.

14.5 Existing Exit Behavior We Can Reuse

`typeclasses.exits.Exit` already supports:

- standard Evennia destination-based travel
- traversal hooks
- custom presentation through `db.exit_display_name`

Implication:

The exit editor should build around current exit objects and `destination`, not around a separate edge model detached from Evennia objects.

14.6 Existing Map and Area Model

- Area membership is already inferred through room tags in category `build`.
- `world/area_forge/map_api.py` already builds serialized zone payloads from live rooms/exits.
- That map payload already includes room nodes, edges, exits, player room id, and zone id.
- Existing world builders already populate `db.map_x` and `db.map_y`.

AreaForge is already a real artifact pipeline, not a hypothetical one.

Current standard artifacts include:

- `manifests/<area_id>.yaml`
- `build/areaspec.json`
- `build/review.txt`
- `build/snapshots/<area_id>.json`

Implication:

The future map import/export workflow should target the Evennia world structure and current map API first, with optional bridges to or from AreaForge artifacts only where that is useful.

14.6.1 Diff Workflow Rule

Map editing should evolve toward:

- export current world state when needed
- emit explicit diffs for edits
- apply diffs deterministically through Builder services

It should not evolve toward broad full-map comparison with inferred destructive behavior.

Implication:

The preferred future builder workflow is:

- current world state
- explicit edit intent
- deterministic diff operations
- audit trail

not:

- full map replacement
- guesswork reconciliation
- hidden cleanup

14.7 Placement and Containment Reality

The blueprint describes placement as explicit relationships like:

- `located_on`
- `located_in`

The current codebase does not have a generalized surface-placement system yet.

What exists now:

- containment is primarily Evennia `location` / `contents`
- nested containment already works for containers and held objects
- portable items use `typeclasses.objects.Object`
- containers are currently modeled with flags like `db.is_container`

Important gap:

- there is no generic persistent distinction yet between:
	- in room
	- inside container
	- on top of surface

Implication:

The placement system is one of the real backend design tasks, not just a UI feature.

14.8 Templates Do Not Exist Yet As A Unified System

The blueprint assumes reusable NPC/item templates.

Current state:

- there is no unified template registry or template persistence model yet
- current spawn/admin commands create instances directly
- vendor inventory today is simple runtime data such as `vendor.db.inventory`
- current world builder scripts create NPCs/items directly at build time

Implication:

The template model must be designed before advanced spawn/search UI can be considered stable.

14.9 Permissions Already Exist

Builder permissions are already expressed in command lockstrings such as:

- `perm(Builder)`
- `perm(Admin)`
- `perm(Developer)`

Examples are already present in builder/admin commands, including `commands/cmd_spawnvendor.py`.

Implication:

Builder mode authorization should reuse the same permission language and not invent a separate role system first.

Lock rule:

- all Builder API mutations must pass an API-layer Builder permission gate before calling Builder services
- Builder services themselves must remain permission-agnostic so internal scripts and CLI usage stay available

14.10 Recommended Repo-Specific Start Order

For this repo specifically, the safest order is:

1. Create builder backend services for room and exit CRUD.
2. Expose those services through Django JSON endpoints under the existing web API tree.
3. Reuse existing structured websocket/map payload helpers for live client refresh.
4. Add a minimal builder UI for current-room editing and exit editing only.
5. Define template persistence and lookup.
6. Add spawn/move flows after the template model exists.
7. Add placement hierarchy only after deciding how `on` versus `in` is persisted.
8. Add AI generation last, after validation and mutation paths are trustworthy.

14.11 Concrete Decisions Still Needed Before Implementation Starts

The blueprint still needs explicit answers for these code-level decisions:

- What is the client-facing stable room identifier: dbref, area tag + room tag, or another slug?
- Where does builder orchestration live: `engine/services/`, `world/builder/`, or both?
- What is the persistence model for templates?
- What is the persistence model for surface placement versus container placement?
- Do we add `db.map_layer`, tags, or a richer coordinate object for multi-floor maps?
- Where do audit records go: Evennia log only, database model, or both?
- Which updates are request/response only, and which should push live over websocket?

14.12 Overall Assessment

This is a valid detour, but it is not primarily a Godot problem.

It is a world-mutation architecture problem with four front ends layered on top:

- permissions
- mutation services
- API contract
- client/editor UX

If those backend contracts are not established first, the builder UI will become a second world-building path that diverges from startup scripts, AreaForge, and live Evennia behavior.

14.13 AreaForge vs Builder Mode (Important Correction)

AreaForge and Builder Mode are not the same kind of system.

They should be treated as two separate pipelines that feed the same world model.

AreaForge:

- purpose: ingest legacy or external map sources
- example input: DragonRealms-style map images
- workflow: image -> OCR/parsing -> reconstruction -> playable zone
- role in the product: import/bootstrap tool

Builder Mode:

- purpose: create and edit zones from scratch
- workflow: builder UI -> API -> services -> Evennia world
- role in the product: primary forward authoring system

This means:

- Builder Mode should not depend on AreaForge
- Builder Mode should not use OCR logic
- Builder Mode should not care about source map images
- Builder Mode should not inherit AreaForge's reconstruction assumptions

But both systems must still converge on the same live world structure:

- same Evennia room model
- same exit model
- same typeclasses
- same containment/location rules
- same map payload expectations where the live client consumes them

Practical rule:

AreaForge is for reconstruction from imperfect data.

Builder Mode is for authoritative creation from clean data.

That distinction should stay intact.

14.14 What To Reuse From AreaForge

Builder Mode should not be based on AreaForge internals, but a few concepts remain reusable:

- final world output shape
- zone/grouping conventions when they are useful
- validation concepts such as unreachable rooms or broken exits
- existing live map payload expectations in `world/area_forge/map_api.py`

What should not be reused as a design basis for Builder Mode:

- OCR stages
- parser assumptions
- image-derived ambiguity handling
- legacy import constraints as first-order authoring rules

14.15 Revised Mental Model

The correct long-term model is:

- AreaForge imports old or external content into the game
- Builder Mode creates and evolves content natively inside the game

Optional bridge work can exist later, but it is optional bridge work:

- export Builder-authored zones into an AreaForge-compatible artifact
- import AreaForge-produced artifacts into Builder-editable JSON or live world state

That bridge is not the foundation of the builder system.