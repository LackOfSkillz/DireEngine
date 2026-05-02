# DarkestDeath Chargen Lag Notes

## TL;DR

The lag is most likely coming from too many persistent writes during character creation.

The biggest offender is the body-part model if it is stored as many top-level persistent attributes like:

- `head_external_hp`
- `head_internal_hp`
- `head_external_bleeding_level`
- `head_internal_bleeding_level`
- `head_severed`
- repeated for every arm, leg, hand, foot, eye, chest, abdomen, back, neck, etc.

That turns one character into 100 to 200+ separate persistent fields before the player is even done with chargen.

## What Is Probably Causing The Lag

1. Chargen is writing directly to the real character object at every step.
2. Each body part has many separately persisted fields.
3. Derived values are also being persisted when they could be computed.
4. Full combat/anatomy state is being built too early instead of at finalization.
5. Some transient runtime flags are being stored persistently.

## Highest-Impact Fixes

### 1. Stop saving every chargen step

Do not write race, stats, appearance, body values, and gear directly to the real character every time the player clicks something.

Use a temporary in-memory blueprint during chargen.

Only finalize once the player confirms.

### 2. Collapse body-part fields into one grouped structure

Bad shape:

```python
char.db.head_external_hp = 80
char.db.head_internal_hp = 80
char.db.head_severed = False
char.db.left_arm_external_hp = 133
char.db.left_arm_internal_hp = 133
```

Better shape:

```python
char.db.body_state = {
    "head": {
        "external_hp": 80,
        "internal_hp": 80,
        "bleed": 0,
        "severed": False,
        "max_hp": 80,
    },
    "left_arm": {
        "external_hp": 133,
        "internal_hp": 133,
        "bleed": 0,
        "severed": False,
        "max_hp": 133,
    },
}
```

Better still: separate static anatomy from live injury state.

Example:

```python
char.db.body_template = {
    "head": {"max": 80, "vital": True},
    "left_arm": {"max": 133, "vital": False},
}

char.db.injuries = {
    "head": {"external": 0, "internal": 0, "bleed": 0, "severed": False},
    "left_arm": {"external": 0, "internal": 0, "bleed": 0, "severed": False},
}
```

### 3. Do not persist derived values unless needed

These usually should not be stored as their own persistent fields during chargen:

- `age_category`
- `encumbrance_description`
- `health_message`
- similar display text

Compute them when needed.

### 4. Move transient state out of persistent storage

These are often runtime-only and should not be part of chargen persistence unless there is a hard reason:

- targeting flags
- hand-in-range flags
- stalking targets
- temporary combat flags
- cached descriptions or combat text

### 5. Delay expensive subsystem setup

Do not fully initialize all of this during early chargen screens if the player does not need it yet:

- complete body/injury map
- protection tables
- full combat state
- derived messaging state
- equipment/runtime slot caches

Build the minimum needed for chargen preview, then finish the rest once the character is finalized.

## Best Migration Path

1. Add a temporary chargen blueprint object.
2. Stop writing to the real character during each step.
3. Replace exploded body-part attributes with one grouped payload.
4. Switch runtime code to read the grouped payload first.
5. Keep a temporary compatibility layer for old characters.
6. Remove legacy per-body-part fields later.

## Fastest Win

If only one thing gets fixed first, fix this:

Persist body-part state as one nested dict instead of hundreds of top-level attributes.

That is the most likely source of chargen lag.

## Second Fastest Win

If only two things get fixed:

1. Stage chargen in memory.
2. Finalize once.

That prevents repeated database churn while the player is still picking race, stats, and appearance.

## What To Measure

If he wants proof before refactoring, time these phases separately:

1. character object creation
2. default attribute initialization
3. body/anatomy initialization
4. gear creation
5. skill initialization
6. any post-create hooks

The likely hotspot is body-part persistence and repeated writes during step-based chargen.

## Bottom Line

Body parts are not the problem by themselves.

The problem is storing each body-part property as a separate persistent field and doing that work too early and too often during character creation.