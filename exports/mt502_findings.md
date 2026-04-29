# MT-502 Findings

Single-pass evaluation only. No prompt iteration was performed.

## crossingV2 / crossingV2_192_132

- applicable_state_groups: season, time, weather, invasion
- applicable_states: spring, summer, autumn, winter, morning, midday, evening, night, rain, snow, fog, invasion
- fragments found: 2
- at least one fragment per applicable group: no
- syntactically correct: yes
- only allowed states used: yes
- whitespace check passes: yes
- prose reads correctly with all fragments removed: no
- combined active-state render looks grammatical: no
- permanent features kept outside fragments: yes
- meta-commentary about state variability: no
- missing required groups: season, time

### Raw Output

```text
The narrow lane ends abruptly here against a high stone wall to the east, with its sole exit leading west toward the bustling heart of the city. Cobblestones underfoot are well-worn from constant traffic, darkened and slick in spots where vendors once set up their stalls. The air carries faint traces of river water mixed with distant market clamor, which$state(invasion, grows tense with distant shouts)$state(rain, is dampened by the sound of raindrops).
```

### Parsed Fragments

- `invasion` -> ` grows tense with distant shouts`
- `rain` -> ` is dampened by the sound of raindrops`

### Rendered Versions

Default state (no fragments active):

```text
The narrow lane ends abruptly here against a high stone wall to the east, with its sole exit leading west toward the bustling heart of the city. Cobblestones underfoot are well-worn from constant traffic, darkened and slick in spots where vendors once set up their stalls. The air carries faint traces of river water mixed with distant market clamor, which.
```

Combined state (night, rain):

```text
The narrow lane ends abruptly here against a high stone wall to the east, with its sole exit leading west toward the bustling heart of the city. Cobblestones underfoot are well-worn from constant traffic, darkened and slick in spots where vendors once set up their stalls. The air carries faint traces of river water mixed with distant market clamor, which is dampened by the sound of raindrops.
```

## crossingV2 / crossingV2_178_132

- applicable_state_groups: season, time, invasion
- applicable_states: spring, summer, autumn, winter, morning, midday, evening, night, invasion
- fragments found: 0
- at least one fragment per applicable group: no
- syntactically correct: yes
- only allowed states used: yes
- whitespace check passes: yes
- prose reads correctly with all fragments removed: yes
- combined active-state render looks grammatical: yes
- permanent features kept outside fragments: yes
- meta-commentary about state variability: no
- missing required groups: season, time, invasion

### Raw Output

```text
A narrow hallway in a bustling tavern runs east and south, its earthen floor showing signs of wear from steady traffic. A hearth at the center casts flickering light over the worn surfaces, casting shadows that dance with each shift in flame. Outside, the sounds of river trade mix with the murmur of conversation within the hall.
```

### Parsed Fragments

- none

### Rendered Versions

Default state (no fragments active):

```text
A narrow hallway in a bustling tavern runs east and south, its earthen floor showing signs of wear from steady traffic. A hearth at the center casts flickering light over the worn surfaces, casting shadows that dance with each shift in flame. Outside, the sounds of river trade mix with the murmur of conversation within the hall.
```

Combined state (night, invasion):

```text
A narrow hallway in a bustling tavern runs east and south, its earthen floor showing signs of wear from steady traffic. A hearth at the center casts flickering light over the worn surfaces, casting shadows that dance with each shift in flame. Outside, the sounds of river trade mix with the murmur of conversation within the hall.
```

## demo1 / CRO_500_100

- applicable_state_groups: season
- applicable_states: spring, summer, autumn, winter
- fragments found: 0
- at least one fragment per applicable group: no
- syntactically correct: yes
- only allowed states used: yes
- whitespace check passes: yes
- prose reads correctly with all fragments removed: yes
- combined active-state render looks grammatical: yes
- permanent features kept outside fragments: yes
- meta-commentary about state variability: no
- missing required groups: season

### Raw Output

```text
A narrow passage runs west and descends to the south through rough earthen walls. The floor is uneven, marked by occasional footprints that suggest sporadic use. During spring, the air feels slightly cooler as it carries a hint of moisture from beyond the passage’s boundaries.
```

### Parsed Fragments

- none

### Rendered Versions

Default state (no fragments active):

```text
A narrow passage runs west and descends to the south through rough earthen walls. The floor is uneven, marked by occasional footprints that suggest sporadic use. During spring, the air feels slightly cooler as it carries a hint of moisture from beyond the passage’s boundaries.
```

Combined state (winter):

```text
A narrow passage runs west and descends to the south through rough earthen walls. The floor is uneven, marked by occasional footprints that suggest sporadic use. During spring, the air feels slightly cooler as it carries a hint of moisture from beyond the passage’s boundaries.
```
