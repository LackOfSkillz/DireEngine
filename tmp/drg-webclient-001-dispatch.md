# DRG-WEBCLIENT-001 — Webclient Session Lifecycle Fix

Type: Maintenance dispatch. Inserted between DRG-024.5d-3a and DRG-024.5d-3b to fix the recurring post-restart webclient reconnect failure that has blocked live verification across six consecutive magic-arc dispatches.

## Scope

- Fix UI overlap blocking the reconnect control
- Fix broken auto-reconnect timing after full stop/start
- Canonicalize host usage to `localhost`
- Correct invalid Popper integrity hash
- Re-run recovery smoke on a recovered post-restart session

## Must-haves

- Full `startWeb.bat` restart followed by browser interaction recovers to a playable session without console intervention
- Reconnect control is reachable in the attached browser viewport
- Refreshed play tabs restore playable sessions
- One canonical host serves play links
- Popper integrity error no longer appears on page load
- Magic-arc recovery smoke completes on a recovered session

## Required Step 0

1. Reverify the pre-flight findings against current code with no edits
2. Reproduce the failure again on the current code before patching

## Implementation notes

- Keep server-side account/session restoration logic unchanged unless Step 0 disproves the pre-flight
- Run `evennia collectstatic --noinput` after CSS/JS/template edits before browser verification
- Use reproduction-driven verification first; executable preservation tests remain required

## Recovery smoke targets

1. DRG-024.5a prepare/cast/release lifecycle
2. DRG-024.5b Burden, Gauge Flow, Strange Arrow
3. DRG-024.5c Manifest Force plus barrier absorption
4. DRG-024.5d-1 slots and spells
5. DRG-024.5d-2 feats, learn feat, forget feat
6. DRG-024.5d-3a harness plus cyclic sustain/drain
