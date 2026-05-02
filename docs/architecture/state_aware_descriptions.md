# State-Aware Description Markup

## Overview

Dragonsire supports two coexisting patterns for state-aware room prose.

The first pattern is inline markup: `$state(group:values, content)`. This is for
additive atmospheric fragments inside an otherwise stable description. The second
pattern is full variant override through `desc_<state>` attributes selected by the
 existing `room_state` tag flow in `ExtendedDireRoom`.

The render order is fixed:

1. `ExtendedDireRoom.get_stateful_desc()` resolves the base description or a
   `desc_<state>` override.
2. The resolved description string is passed through the runtime `$state(...)`
   renderer.
3. The final rendered string is returned to Evennia's room appearance flow.

This means both authoring patterns compose. A `desc_storm` override can itself
contain `$state(invasion:goblin_raid, ...)` markup, and the invasion fragment will be
evaluated after the storm variant is selected.

## Syntax

The supported syntax is:

```text
$state(group:value, content)
$state(group:value_one|value_two, content)
```

Examples:

```text
The lane lies quiet.$state(time:night, Lanternlight gathers in the puddles.)

The square opens to the river.$state(weather:storm|heavy_rain, Rain lashes across the stones.)

The alley seems ordinary.$state(invasion:goblin_raid, Fresh goblin tracks score the mud.)
```

Rules:

- `group` is required and must be one of the registered state groups.
- Values are pipe-separated within one group.
- Matching is exact after lowercasing and trimming whitespace.
- Content is inserted literally when the state matches.
- Content renders as empty string when the state does not match.
- Nested `$state(...)` fragments are not supported.
- A closing parenthesis inside content must be escaped as `\)`.

## Registered State Groups

### `weather`

Queries `world.weather.get_current_weather(zone_id)`.

Known values:

- `clear`
- `cloudy`
- `light_rain`
- `heavy_rain`
- `storm`
- `fog`
- `light_snow`
- `heavy_snow`
- `blizzard`
- `sandstorm`

Example:

```text
$state(weather:storm|heavy_rain, Rain pelts the flagstones.)
```

### `invasion`

Queries `world.invasion.get_current_invasion(zone_id)`.

Known values:

- `none`
- `goblin_raid`
- `bandit_incursion`
- `monster_horde`
- `siege`
- `infestation`

Example:

```text
$state(invasion:goblin_raid, A goblin banner hangs in tatters from the fence.)
```

### `season`

Queries `world.calendar.get_current_season()`.

Known values:

- `spring`
- `summer`
- `autumn`
- `winter`

Example:

```text
$state(season:winter, Frost clings to the exposed roots.)
```

### `time`

Queries `world.calendar.get_current_time_of_day()`.

Known values:

- `night`
- `morning`
- `afternoon`
- `evening`

Example:

```text
$state(time:night, The shutters are drawn against the dark.)
```

## Authoring Guidance

Inline state fragments are additive atmosphere, not load-bearing prose.

Write the base sentence so it still reads cleanly when every fragment renders as empty.
The renderer does not repair punctuation or grammar after a non-match; it only removes
the fragment content.

Good pattern:

```text
The square lies open to the sky.$state(weather:storm, Rain lashes from roof to roof.)
```

Bad pattern:

```text
The square $state(weather:storm, is drowned in rain) and $state(weather:clear, basks in sunlight).
```

The second example makes too much of the sentence depend on matching fragments.

## Authoring Patterns

### Pattern 1: Inline Atmospheric Fragments

Use `$state(...)` when the room mostly stays the same and current state only adds a
sentence or phrase of atmosphere.

```text
The lane narrows between leaning walls.$state(time:night, Shadows pool beneath the eaves.)
```

### Pattern 2: Full Variant Override

Use `desc_<state>` when the room genuinely needs different prose, not just a fragment.
Examples include flood conditions, major destruction, or seasonal transformations that
change the whole scene.

Example authoring shape:

```text
desc = "The ford lies shallow and stony."
desc_storm = "The ford has swollen into a churning brown rush that swallows the old stepping stones."
```

### Pattern 3: Combined

Both patterns can be layered.

```text
desc_storm = "The ford has swollen into a churning brown rush.$state(invasion:goblin_raid, Broken goblin shields spin in the eddies.)"
```

The storm override is selected first. The invasion fragment inside that override is then
evaluated.

## Error Behavior

Malformed markup never reaches players verbatim.

When the parser encounters malformed `$state(...)` syntax:

- the fragment is stripped from player-facing output
- surrounding plain text is preserved where the fragment boundary is unambiguous
- a warning is logged for staff with the room identity and a description preview

When a fragment references an unknown state group or a registry query fails:

- the fragment renders as empty
- a warning is logged for staff
- rendering continues

## Examples

### Weather Only

```text
The quay smells of wet rope and river mud.$state(weather:storm|heavy_rain, Rain hammers the pilings.)
```

### Invasion Only

```text
The market road is broad and well worn.$state(invasion:bandit_incursion, Bootprints and dropped bolts litter the roadside.)
```

### Combined Weather And Invasion

```text
A small clearing.$state(weather:storm|heavy_rain, Rain pelts the ground.)$state(invasion:goblin_raid, A goblin's footprints are scattered nearby.) The trees sway gently.
```

Example outputs:

- `weather=clear`, `invasion=none`
  `A small clearing. The trees sway gently.`
- `weather=storm`, `invasion=none`
  `A small clearing. Rain pelts the ground. The trees sway gently.`
- `weather=storm`, `invasion=goblin_raid`
  `A small clearing. Rain pelts the ground. A goblin's footprints are scattered nearby. The trees sway gently.`

## Current Boundaries

This is v1 of the runtime markup system.

Out of scope and unsupported:

- nested `$state(...)` fragments
- logical operators across groups
- computed variables or template expansion
- unregistered ad hoc groups
- caching rendered output by state vector

If content authoring later proves those limits too tight, they belong in a separate v2
design and implementation pass.