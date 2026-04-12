# Authority Matrix

## Core Authorities

- Combat action resolution: `engine.services.combat_service.CombatService`
- XP and learning mutation: `engine.services.skill_service.SkillService`
- State mutation and damage application: `engine.services.state_service.StateService`
- Timed execution and cancellation: `world.systems.scheduler`
- Combat math and rule evaluation: `domain.combat.rules`

## Delegation Boundaries

- Commands resolve input and call services.
- Typeclasses expose state and delegation helpers.
- Services coordinate domain rules with state mutation.
- Domain modules remain side-effect free.

## Compatibility Surfaces

- `world.systems.skills.award_exp_skill()` remains a compatibility wrapper around `SkillService`, but new callers should prefer the service directly.
- `typeclasses.characters.Character.award_skill_experience()` remains a compatibility delegate for internal callers.

## Forbidden Authorities

- command modules mutating XP directly
- command or typeclass modules owning combat damage formulas
- non-scheduler timing entrypoints
- domain imports that reach into commands or typeclasses