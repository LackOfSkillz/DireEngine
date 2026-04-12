# Engine Contract

## Dependency Direction

Allowed directions:

- `commands -> services -> domain`
- `typeclasses -> services`
- `services -> domain + infrastructure`
- `domain -> nothing`

Reusable world and system modules may still support gameplay flows, but mutation authority stays in services.

## Mutation Authority

- `CombatService` owns combat resolution entry.
- `SkillService` owns skill XP mutation.
- `StateService` owns generic state mutation such as damage, balance, fatigue, and roundtime delegation.
- `world.systems.scheduler` owns timed execution.

## Command Rule

- commands translate player intent, resolve targets, call services, and emit messages
- commands must not own combat math, XP mutation, or timing behavior

## Character Rule

- `typeclasses/characters.py` is a state container and compatibility surface
- Character methods may validate, read state, or delegate
- Character must not become the home for combat math, XP rules, or timing ownership

## Domain Rule

- domain code is pure rule and value logic
- domain code may not import commands, typeclasses, or services

## Timing Rule

- all timed execution must go through scheduler contract APIs
- direct `delay(...)` calls outside scheduler internals are forbidden

## Validation Rule

- new service entrypoints return `ActionResult`
- service failures must be explicit through `errors` or typed exceptions
- docs must describe the current authoritative path, not aspirational alternatives
