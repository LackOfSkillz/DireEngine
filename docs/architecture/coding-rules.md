# Coding Rules

## Layering

- no gameplay logic in commands
- no domain logic in `typeclasses/characters.py`
- service layer owns mutation
- scheduler is the only timing API

## Service Rules

- service entrypoints return `ActionResult`
- failures use `ValidationError`, `DomainError`, or `StateError` when a typed exception is clearer than a failed result
- do not bypass `CombatService`, `SkillService`, or `StateService` for new behavior

## Import Rules

- `commands` must not import `domain`
- `domain` must not import `commands`
- commands and typeclasses should prefer service imports over deep system reach-through when mutating state

## File Size Rules

- soft warning at 400 lines
- hard split required at 700 lines unless the file is a deliberate compatibility container under active consolidation

## Repo Rules

- artifacts, logs, and debug output stay out of source control
- archive obsolete planning and migration docs under `docs/archive/`

## Validation Rules

- add or update focused tests with each authority change
- run the architecture audit before landing structural changes