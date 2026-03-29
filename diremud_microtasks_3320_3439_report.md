# DireMUD Microtasks 3320-3439 Report

This report covers the first full justice implementation slice: capture, confiscation, judge flow, fines, stocks, law zones, and regional warrants.

## Scope Completed

- Added justice state fields to Character for capture, confiscation, fines, plea state, stocks, surrender, and warrants.
- Replaced guard crime response with capture-driven justice processing through shared helpers in `utils/crime.py`.
- Added confiscation and item return flow using a burlap sack and persistent confiscated item IDs.
- Added judge entry, plea handling, sentence generation, fine payment, collateral lock state, and unpaid fine liquidation.
- Added stocks state, movement lock, ability lock, tomato throwing, crowd ambience, and early release.
- Added room law and region helpers through `world/law.py` and `typeclasses/rooms.py`.
- Added law-gated crime handling so lawless areas suppress crime flagging and guard response.
- Added regional warrants with hourly decay and automatic guard response when a wanted player re-enters a lawful room.
- Added player justice commands: `justice`, `surrender`, `plead`, `pay fine`, `throw tomato`, and `plead release`.
- Stamped Brookhollow rooms with justice metadata at server start, including a public-stocks flag on Town Square and lawless handling for the low quarter.

## Reconciliation Notes

- The microtasks referenced `gold`, but the live codebase uses `coins`, so all payment and fine logic was integrated against `db.coins` rather than introducing a parallel currency field.
- The microtasks asked for dedicated room IDs; this implementation uses stable room keys for `Guard Post`, `Town Hall Chamber`, and `Town Square` so the justice flow survives database rebuilds more safely.
- Town Square is currently used as the public stocks location to avoid introducing a new builder-only room before the justice slice is proven in play.

## Validation Performed

- Static validation on all touched files reported no errors.
- Justice hooks compile across command registration, room law helpers, character state, crime utilities, and server start hooks.

## Recommended Live Checks

1. Trigger a lawful crime and confirm immediate capture instead of combat.
2. Confirm items are confiscated on capture and returned in a sack when the fine is paid immediately.
3. Confirm unpaid fines block trade and liquidation clears collateral after the timestamp threshold.
4. Confirm `plead guilty` reduces fines and `plead innocent` sometimes clears the case.
5. Confirm Town Square behaves as public stocks and `throw tomato` only works on stocked targets.
6. Confirm crimes in the low quarter do not create crime flags or summon guards.
7. Confirm leaving and re-entering Brookhollow with a warrant retriggers guard capture in lawful rooms.