# DireMUD Microtasks 2200-2260 Report

## Scope

This report tracks implementation of MT 2200-2260 from [MT 2200 - 2260.md](c:/Users/gary/dragonsire/MT%202200%20-%202260.md), adapted to the current Evennia browser client.

Implementation rule used for this batch:
- When the task file described a browser-visible outcome, the existing browser client was extended instead of creating a parallel map subsystem.
- When the task file specified graph-driven navigation, coordinates were kept display-only and routing was implemented from exits only.

Current progress in this report:
- Completed MT 2200-2259
- MT 2260 is not defined in the current task file contents

## Implemented

### MT 2200-2219
- Expanded [world/area_forge/map_api.py](c:/Users/gary/dragonsire/world/area_forge/map_api.py) with a new `get_zone_map(character)` helper.
- Implemented area-tag-based room collection so the active area map is sent as a full zone graph instead of a radius-limited local snapshot when area metadata is available.
- Standardized zone payloads to include:
  - `rooms`
  - `edges`
  - `exits`
  - `player_room_id`
  - `zone`
- Ensured room payloads include display coordinates, room name, and current-room flags.
- Updated structured map sending so [world/area_forge/map_api.py](c:/Users/gary/dragonsire/world/area_forge/map_api.py) now uses zone-map delivery by default and falls back to the existing local map where area tags are unavailable.
- Added [commands/cmd_maptest.py](c:/Users/gary/dragonsire/commands/cmd_maptest.py) for manual `maptest zone` and `maptest local` verification.
- Registered `maptest` in [commands/default_cmdsets.py](c:/Users/gary/dragonsire/commands/default_cmdsets.py).

### MT 2220-2239
- Extended [web/static/webclient/js/dragonsire-browser-v2.js](c:/Users/gary/dragonsire/web/static/webclient/js/dragonsire-browser-v2.js) with map drag state:
  - `mapOffset`
  - `isDragging`
  - `lastMouse`
  - click suppression while dragging
- Reworked the canvas map renderer to use persistent world offsets so the player can pan across the full zone.
- Added client-side BFS pathfinding using the exit graph only.
- Added path-to-direction conversion using exit `dir` metadata only.
- Added controlled auto-walk dispatch with stepwise command sends and guard state.
- Added click-to-route behavior so clicking a room computes a graph path and begins movement commands.
- Added route debugging logs for payloads, computed paths, and directions.

### MT 2240-2259
- Updated [web/templates/webclient/webclient.html](c:/Users/gary/dragonsire/web/templates/webclient/webclient.html) with a dedicated fullscreen toggle in the map panel.
- Extended [web/static/webclient/css/dragonsire-browser.css](c:/Users/gary/dragonsire/web/static/webclient/css/dragonsire-browser.css) with fullscreen map styles and dragging cursor states.
- Added current-room centering logic in [web/static/webclient/js/dragonsire-browser-v2.js](c:/Users/gary/dragonsire/web/static/webclient/js/dragonsire-browser-v2.js).
- Prevented forced recentering while the player is actively dragging the map.
- Added auto-walk interruption when the user types into the command input.
- Added auto-walk interruption and retargeting when the player clicks a new room.
- Preserved and extended edge rendering through the existing canvas renderer rather than introducing a separate SVG map layer.
- Added resize-aware re-rendering for fullscreen and browser window changes.

## Validation

Validated outcomes for MT 2200-2219:
- The server map API now supports a full zone payload for area-tagged regions.
- `maptest` is available for manual structured map payload checks.
- The live browser client still accepts structured `map` messages without JS or template errors.

Validated outcomes for MT 2220-2239:
- The browser client now has drag/pan state and click suppression during drags.
- Pathfinding uses exits only and does not depend on display coordinates.
- Clicking a non-current room computes a route and sends stepwise movement commands.

Validated outcomes for MT 2240-2259:
- The map panel has a fullscreen toggle and fullscreen styling.
- The map recenters on the current room when appropriate and avoids recentering during active drags.
- Auto-walk can be interrupted by direct input or re-targeting.
- Edited Python, HTML, CSS, and JS files were checked with the workspace error checker and reported no errors.

## Notes

- The current task file content defines microtasks through 2259; 2260 does not appear as a discrete item in the file.
- The task document called for a simple SVG line layer in one step, but the existing browser client already had a functioning canvas line renderer, so the implementation kept that path and extended it instead of creating a second rendering layer.
- Browser validation still needs an in-client gameplay pass to confirm map scale and panning feel correct on the live Landing map.

### 2026-03-29 Follow-up Polish

- Adjusted fullscreen map behavior so the map refits after the canvas actually resizes into fullscreen instead of using the old docked dimensions.
- Added explicit `Fit` and `Center` controls to recover the viewport without manual drag correction.
- Stabilized fullscreen panel layout so the map canvas occupies the intended center row instead of visually sliding out of frame.

### 2026-03-29 Generic Area Fallback

- Updated [world/area_forge/map_api.py](c:/Users/gary/dragonsire/world/area_forge/map_api.py) so rooms without `db.map_x` and `db.map_y` no longer collapse to `(0, 0)`.
- Added a deterministic exit-driven fallback layout that synthesizes positions from the room graph when AreaForge coordinates are missing.
- Preserved existing AreaForge coordinates for tagged areas and only used the fallback layout for rooms that do not already have map positions.
- Validated the fix against room `#2 (Limbo)`, which now returns an 11-room local map with visible directional spread instead of an all-zero overlap.
- Re-validated the tagged `new_landing` zone map after the change and confirmed it still returns 211 rooms and 470 exits with the existing zone coordinates.

### 2026-03-29 Small-Map Visibility Follow-up

- Updated [web/static/webclient/js/dragonsire-browser-v2.js](c:/Users/gary/dragonsire/web/static/webclient/js/dragonsire-browser-v2.js) so compact local maps render with thicker edges, larger nodes, and room-name labels.
- Updated [web/templates/webclient/webclient.html](c:/Users/gary/dragonsire/web/templates/webclient/webclient.html) to load the map client with a cache-busting query string after the renderer change.
- Reloaded the Evennia server after the browser asset update so connected clients can pick up the refreshed local-map rendering path.

### 2026-03-29 Vertical Exit Placement

- Adjusted the fallback direction vectors in [world/area_forge/map_api.py](c:/Users/gary/dragonsire/world/area_forge/map_api.py) so `up` and `down` no longer share the same straight-line axis as `north` and `south`.
- Re-validated the Limbo local map payload and confirmed the direct vertical exits from room `#2` now render on their own branch instead of appearing to hang off rooms `1316` and `1318`.

### 2026-03-29 Stable Fallback Layout Anchor

- Updated [world/area_forge/map_api.py](c:/Users/gary/dragonsire/world/area_forge/map_api.py) so fallback local-map layouts are anchored to a stable graph center instead of the player's current room.
- Validated the Limbo payload from room `#2`, `Roofline Perch`, and `Underlock Vault`, confirming the same room coordinates are now returned across movement instead of the graph re-centering and flipping branches.
