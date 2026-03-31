# DireMUD Microtasks 3440-3499 Report

Implemented the remaining justice microtasks from the Dragonrealms justice document.

- Added bounty values to warrant entries and decayed them over time.
- Added bounty-board interaction commands for viewing and accepting contracts.
- Added contract capture payouts and warrant clearing for successful hand-ins.
- Added guard bribery with escalating resistance after prior attempts.
- Added target tracking with last-known-region hints, cooldowns, and stale-information risk.
- Added `lay low` to reduce warrant heat and clear the freshest regional trace.
- Added `active_bounty`, `last_known_region`, and `is_hidden_from_tracking` character state.
- Added a `BountyBoard` object and ensured one exists in Brookhollow Town Square.
