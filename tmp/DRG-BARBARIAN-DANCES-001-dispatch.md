# DRG-BARBARIAN-DANCES-001 — Eight Canonical Combat Dances

- Type: Eighth Barbarian program dispatch.
- Scope: Ship the eight canonical combat dances as a new self-targeted, single-active Barbarian ability category using `spellbook2` bits `1-8`.
- Canon sources: `S12052` (dance roster, learning order, `spellbook2` manipulation), `S03387` (dance lifecycle/effects `3387100` and `3387001`), `S03089` (Dance-Roar power interaction).

Required outputs:

- `domain/abilities/dances/` with eight per-dance definition files and a registry.
- `engine/services/dance_service.py` for begin/tick/end/mutex/duration.
- `commands/cmd_dance.py` command surface.
- `typeclasses/characters.py` `spellbook2` helpers and bounded dance bonus readers.
- `domain/combat/resolution.py` bounded combat-hook consumption.
- `engine/services/roar_service.py` bounded Dance-Roar power hook via active dance effect `3387001`.
- Focused dance tests, cumulative Barbarian validation, preservation + Ranger-adjacent reruns, and 12-scenario live smoke with orphan delta `0`.

Frozen decisions:

- Dances are a sibling substrate to roars, not an extension of `RoarService`.
- Only one dance may be active at a time; starting a new dance ends the old one.
- Pit masters and pit rooms are metadata only in this dispatch.
- War Stomp is explicitly out of scope.
- Production-code ceiling: 800 lines.