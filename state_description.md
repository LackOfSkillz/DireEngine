# State-Driven Room Descriptions

This note explains how we got the LLM to emit Evennia extended room-state markup directly inside generated room descriptions, instead of trying to generate separate descriptions for every condition.

## Goal

We wanted one grounded room description that could vary at render time for things like time of day, season, weather, and invasion state. The output format we targeted was Evennia's inline state markup:

```text
$state(name, content)
```

That lets the base description stay stable while optional atmospheric fragments appear only when the matching state is active.

## The Core Approach

We made this work by combining three things:

1. Code decides which state groups apply to a room.
2. Prompt assembly injects the exact allowed states into the LLM input.
3. The system prompt forces the model to wrap only variable text in `$state(...)` fragments.

The result is a single paragraph with permanent facts outside fragments and state-dependent flavor inside fragments.

## Step 1: Decide Which States Apply

The state vocabulary is fixed in `world/builder/prompting/room_description_prompt.py`:

```python
_STATE_GROUP_VOCABULARY = {
    "time": ("morning", "midday", "evening", "night"),
    "season": ("spring", "summer", "autumn", "winter"),
    "weather": ("rain", "snow", "fog"),
    "invasion": ("invasion",),
}
```

Then `determine_applicable_state_groups(...)` classifies the room from tags, environment, exits, and a small legacy cave fallback:

```python
if is_underground:
    return ["season"]
if is_interior:
    return ["season", "time", "invasion"]
if is_urban_exterior:
    return ["season", "time", "weather", "invasion"]
return ["season", "time", "weather"]
```

That policy matters because it tells the model what kinds of variation are legal for this room type.

## Step 2: Expand Groups Into Exact State Names

Once we know the groups, `determine_applicable_states(...)` flattens them into the exact state names the model is allowed to use:

```python
def determine_applicable_states(...):
    states: list[str] = []
    for group in determine_applicable_state_groups(room_payload, zone_payload, generation_context):
        states.extend(_STATE_GROUP_VOCABULARY[group])
    return states
```

For an urban exterior, that usually becomes:

```text
spring, summer, autumn, winter, morning, midday, evening, night, rain, snow, fog, invasion
```

## Step 3: Inject Those States Into the Prompt

The assembled room prompt explicitly tells the LLM which groups and which state names apply:

```python
if applicable_state_groups:
    lines.append(f"Applicable state groups for this room are {_natural_join(applicable_state_groups)}.")
if applicable_states:
    lines.append(f"The applicable_states list for this room is {_natural_join(applicable_states)}.")
else:
    lines.append("The applicable_states list for this room is empty.")
```

This is the key control surface. The prompt does not leave state selection fuzzy. It gives the model an explicit allowed list.

## Step 4: Tell the Model How To Write Stateful Text

The system prompt in `world/builder/templates/room_description_system_prompt.txt` contains the rules that make the markup work:

```text
STATEFUL FRAGMENTS
When this room has applicable_states listed, some atmospheric content must vary based on world state. Wrap variable content using Evennia's $state syntax:

    $state(name, content)

When the state is active, the content appears. When inactive, it is removed entirely.
Only use states from this room's applicable_states list, which is provided in the room-specific input.
```

And the most important enforcement rules are:

```text
- Permanent features such as exits, layout, route directions, and building positions must never be inside fragments.
- Include at least one fragment for each applicable state group listed for this room.
- Each fragment must be grammatically optional.
- Keep any needed leading or trailing spaces inside the fragment so removal does not leave double spaces or missing spaces.
- Do not write fragments for states that are not in this room's applicable_states list.
```

This is what made the output stable. We stopped asking for alternate descriptions and instead asked for one description with optional inline fragments.

## Step 5: Keep Permanent Truth Outside the Markup

The prompt also teaches a structural split:

- Base layout, exits, surfaces, and boundaries stay outside `$state(...)`
- Time, weather, season, and invasion flavor go inside `$state(...)`

The system prompt includes this example:

```text
"Stone Lane ends here against close-packed buildings, its narrow cobbles worn smooth by steady traffic. Light$state(morning, spreads gold from the east)$state(evening, fades behind the rooftops)$state(night, leaves the lane in dim outline). Underfoot, the stones$state(rain, glisten with rainwater)$state(snow, carry a fresh white covering)$state(winter, bear patches of frost where the buildings shadow them)."
```

That pattern is the whole trick: static truth first, optional atmospheric variation second.

## Step 6: Send the Assembled Prompt Directly To the LLM

Generation uses the assembled prompt directly:

```python
async def generate_room_description(...):
    prompt = assemble_room_description_prompt(room, zone, max_prompt_chars=max_prompt_chars)
    text = await client.generate(prompt.prompt, max_tokens=max_tokens, temperature=temperature)
```

So the model is expected to emit the final description paragraph with inline Evennia state markup already embedded.

## What Changed Conceptually

The important shift was this:

- Old idea: generate a plain description and somehow add state logic later.
- Working idea: make the LLM generate the state logic inline as part of the description format.

That only became reliable once we did all of the following together:

- defined a fixed state vocabulary
- derived allowed state groups from room type
- passed the exact `applicable_states` list into the prompt
- required `$state(name, content)` syntax explicitly
- forbade permanent room facts from going inside fragments
- required fragments to remain grammatically removable

## Example Output Shape

Real outputs now look like this:

```text
A narrow alley runs between rough stone walls, its packed dirt floor worn smooth by steady foot traffic$state(rain,  and slick with muddy runoff)$state(snow,  with a thin layer of trampled slush)$state(fog,  the walls fading into grey murk). The heavy smell of river water and fish carries from the nearby docks$state(morning,  mixed with the scent of cook-fires as workers break their fast)$state(midday,  thick in the still air as laborers pass through on their way to and from the wharves)$state(evening,  mingling with the smell of cheap stew from nearby tenements)$state(night,  hanging heavy in the quiet darkness)...
```

That example comes from `exports/mt505_state_renders.md` and shows the model producing one base description with multiple optional fragments layered into it.

## Files That Matter

- `world/builder/templates/room_description_system_prompt.txt`
- `world/builder/prompting/room_description_prompt.py`
- `world/builder/prompting/room_description_generation.py`
- `exports/mt505_state_renders.md`

## Short Version

We got Evennia extended room states working with the prompt by turning statefulness into an output-format requirement. The code decides which states are legal, the prompt injects that exact list, and the model is instructed to place only variable atmospheric text inside `$state(...)` fragments while keeping permanent room truth outside them.