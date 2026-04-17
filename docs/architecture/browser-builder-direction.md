# Browser-First Builder Direction

## Decision

DireBuilder should move to the web stack and live inside the main browser client instead of continuing as a separate Godot-based editor.

This is a product and architecture decision, not just a UI preference.

## Why This Direction Fits The Repo Better

The browser client is already the primary player-facing surface.

The existing web client already contains the beginnings of a builder integration:

- builder state in `web/static/webclient/js/dragonsire-browser-v2.js`
- a builder panel in `web/templates/webclient/webclient.html`
- web builder APIs under `web/api/builder/`
- existing map export, diff, history, undo, and redo flows

By contrast, the Godot path adds a second UI platform, second interaction model, second rendering stack, second deployment/debug surface, and an extra launcher bridge.

## New Product Shape

The browser client becomes both:

- the player client
- the builder workspace

The builder should stop being a sidecar whose main purpose is to launch another app.

Instead, the builder becomes a dedicated browser mode inside the existing client shell.

## Core Principle

Do not build a separate browser builder app unless we hit a hard constraint.

Start by extending the current web client into a mode-aware workspace that can switch between:

- play mode
- build mode

That preserves shared identity, auth, session context, map state, and UI language.

## Immediate Architecture Shift

### Keep

- Evennia + Django backend
- existing builder HTTP endpoints
- diff-based mutation model
- browser map payloads and local map rendering knowledge
- builder history / preview / undo / redo model

### De-emphasize

- local Godot launcher workflow
- Godot-specific builder layout work
- builder behavior that depends on a second client runtime

### Build Next

- a first-class builder workspace inside the browser client
- a browser-native map editing canvas
- a browser-native inspector and operation journal
- shared UI chrome for both playing and building

## UI Direction

The browser client should be redesigned so the builder feels native to Dragons Ire rather than pasted into a debug rail.

Recommended top-level structure:

- left rail: character, context, and builder tool palette when in build mode
- center stage: world log in play mode, editable map canvas in build mode
- right rail: local map / inspector / inventory / content lists depending on mode
- bottom strip: command line in play mode, operation journal / validation in build mode

The important shift is that builder mode gets the center stage, not a small right-rail panel.

## Proposed Implementation Phases

### Phase 1: Browser Builder Shell

Replace the current small builder rail panel with a builder workspace toggle in the web client.

Deliverables:

- `Play` / `Build` mode switch in browser UI
- builder workspace layout in the main client shell
- current builder area state synced from active zone/map state
- remove dependency on `Launch Builder` for primary workflow

### Phase 2: Read-Only Builder Canvas

Reuse export payloads and current map knowledge to render a larger dedicated builder canvas.

Deliverables:

- pan / zoom / fit
- room nodes and exits
- selected room state
- visual zone context

### Phase 3: Inspector + Selection Pipeline

Bring room selection, exit selection, and object selection into the browser workspace.

Deliverables:

- room inspector
- exit inspector
- entity selection state
- property editing forms bound to staged diffs

### Phase 4: Tool System

Move the active-tool concept into the browser client.

Deliverables:

- select
- create room
- draw exit
- move room
- delete

All actions should still go through staged diff operations.

### Phase 5: Journal + Validation

Make the operation journal visible and useful inside the browser workspace.

Deliverables:

- staged operations list
- preview results
- apply / undo / redo
- history browser
- validation/conflict surfacing

### Phase 6: Content Placement

After rooms and exits are stable, move NPC/item placement into the same workspace.

Deliverables:

- content tree
- template palette
- instance placement
- inspector edits

## Codebase Guidance

### Primary Frontend Surface

Use these files as the initial browser-builder anchor:

- `web/templates/webclient/webclient.html`
- `web/static/webclient/js/dragonsire-browser-v2.js`

### Backend Surface

Use these existing builder services rather than inventing a second command path:

- `web/api/builder/`
- `world/builder/services/`

### Godot Scope Going Forward

Treat the Godot builder as experimental or legacy during the migration.

Do not keep investing in parity between two full builder clients.

If a feature is implemented next, it should land in the browser builder unless there is a hard blocker.

## Practical First Milestone

The first browser-builder milestone should not try to finish the whole editor.

It should prove this loop inside the web client:

1. switch into build mode
2. load current zone into a large builder canvas
3. select a room
4. create a room
5. draw an exit
6. preview and apply diff
7. refresh map in-place

If that loop works smoothly, the platform decision is validated.

## Recommended Next Task

Refactor the current browser builder rail into a real builder workspace in the web client and retire the launcher-driven `Launch Builder` path from the primary UX.