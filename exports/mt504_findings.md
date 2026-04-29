# MT-504 Findings: Qwen vs Claude Markup Comparison

Single rerun only. No prompt iteration. Comparison source: `exports/mt503_qwen_vs_claude_markup.txt` generated after confirming `ANTHROPIC_API_KEY` was visible to the agent shell and LM Studio was reachable at `http://127.0.0.1:1234`.

Rendered combined-state examples below were produced by removing all inactive `$state(...)` fragments exactly as emitted, without hand-fixing spacing. That makes whitespace and grammar failures visible.

## Room: crossingV2_192_132

Applicable groups: season, time, weather, invasion  
Applicable states: spring, summer, autumn, winter, morning, midday, evening, night, rain, snow, fog, invasion

### Qwen

- Fragments emitted: 8. States used: rain, snow, winter, morning, midday, evening, night, invasion.
- Per-group coverage: Pass. Season is covered by `winter`. Time, weather, and invasion are all represented.
- Syntactic correctness: Pass. All fragments use valid `$state(name, content)` form.
- Whitespace handling: Mixed. Removing all fragments leaves clean prose. Active-state rendering is not clean because fragments omit leading spaces, producing joins like `stallsand even more so now` and `clamorreduced to occasional echoes and whispers`.
- Grounding: Mostly grounded. Rain, snow, frost, changing market noise, and invasion noise all fit an exposed city lane. The invasion fragment is more forceful than the baseline but does not introduce clearly incompatible scenery.

Default render:

```text
The narrow lane ends abruptly here against a high stone wall to the east, with its sole exit leading west toward the bustling heart of the city. Cobblestones underfoot are well-worn from constant traffic, darkened and slick in spots where vendors once set up their stalls. The air carries faint traces of river water mixed with distant market clamor.
```

Realistic combination render (`night` + `rain`):

```text
The narrow lane ends abruptly here against a high stone wall to the east, with its sole exit leading west toward the bustling heart of the city. Cobblestones underfoot are well-worn from constant traffic, darkened and slick in spots where vendors once set up their stallsand even more so now. The air carries faint traces of river water mixed with distant market clamorreduced to occasional echoes and whispers.
```

### Claude

- Fragments emitted: 8. States used: rain, snow, fog, morning, midday, evening, night, invasion.
- Per-group coverage: Fail. Time, weather, and invasion are covered, but season is entirely missing.
- Syntactic correctness: Pass. All fragments use valid `$state(name, content)` form.
- Whitespace handling: Mixed. Removing all fragments leaves clean prose. Active-state rendering is not clean because fragments omit leading spaces, producing joins like `stallswith rainwater pooling` and `clamornow eerily silent and distant`.
- Grounding: Partially grounded. Rain, snow, fog, quieter night traffic, and invasion smoke fit the lane. `fresh baking bread` and `heat shimmer of noon` are unsupported additions for this sparse room packet and go beyond the baseline description.

Default render:

```text
The narrow lane ends abruptly here against a high stone wall to the east, with its sole exit leading west toward the bustling heart of the city. Cobblestones underfoot are well-worn from constant traffic, darkened and slick in spots where vendors once set up their stalls. The air carries faint traces of river water mixed with distant market clamor.
```

Realistic combination render (`night` + `rain`):

```text
The narrow lane ends abruptly here against a high stone wall to the east, with its sole exit leading west toward the bustling heart of the city. Cobblestones underfoot are well-worn from constant traffic, darkened and slick in spots where vendors once set up their stallswith rainwater pooling. The air carries faint traces of river water mixed with distant market clamornow eerily silent and distant.
```

## Room: crossingV2_178_132

Applicable groups: season, time, invasion  
Applicable states: spring, summer, autumn, winter, morning, midday, evening, night, invasion

### Qwen

- Fragments emitted: 8. States used: morning, midday, evening, night, spring, summer, autumn, winter.
- Per-group coverage: Fail. Time and season are covered, but invasion is missing entirely.
- Syntactic correctness: Pass. All fragments use valid `$state(name, content)` form.
- Whitespace handling: Mixed. Removing all fragments leaves clean prose. Active-state rendering is not clean because fragments omit leading spaces, producing `lightweakly illuminating the space` when `night` is active.
- Grounding: Weak. The tavern hallway is interior, but Qwen injects `birdsong`, `rustling leaves`, and `a blanket of snow` into the ambient sound line. Those are exterior seasonal cues not supported by the room packet and do not fit this hallway cleanly.

Default render:

```text
A narrow hallway in a bustling tavern runs east and south, its earthen floor showing signs of wear from steady traffic. A hearth at the center casts flickering light over the worn surfaces. Outside, the sounds of river trade mix with the murmur of conversation within the hall.
```

Realistic combination render (`night` + `invasion`):

```text
A narrow hallway in a bustling tavern runs east and south, its earthen floor showing signs of wear from steady traffic. A hearth at the center casts flickering lightweakly illuminating the space over the worn surfaces. Outside, the sounds of river trade mix with the murmur of conversation within the hall.
```

### Claude

- Fragments emitted: 6. States used: morning, midday, evening, night, invasion, invasion.
- Per-group coverage: Fail. Time and invasion are covered, but season is missing entirely.
- Syntactic correctness: Pass. All fragments use valid `$state(name, content)` form, including two separate invasion fragments.
- Whitespace handling: Mixed. Removing all fragments leaves clean prose. Active-state rendering is not clean because fragments omit leading spaces, producing `castsdancing flickering light`, `sounds ofalarm`, and `hallnow edged with urgency`.
- Grounding: Better than Qwen on this room. The hearth-light variants and invasion noises fit the tavern hallway. The main issue is not invented scenery; it is incomplete seasonal coverage plus poor active-state insertion.

Default render:

```text
A narrow hallway in a bustling tavern runs east and south, its earthen floor showing signs of wear from steady traffic. A hearth at the center casts flickering light over the worn surfaces. Outside, the sounds of river trade mix with the murmur of conversation within the hall.
```

Realistic combination render (`night` + `invasion`):

```text
A narrow hallway in a bustling tavern runs east and south, its earthen floor showing signs of wear from steady traffic. A hearth at the center castsdancing flickering light over the worn surfaces. Outside, the sounds ofalarm and clashing steel mixed with river trade mix with the murmur of conversation within the hallnow edged with urgency.
```

## Room: CRO_500_100

Applicable groups: season  
Applicable states: spring, summer, autumn, winter

### Qwen

- Fragments emitted: 4. States used: spring, summer, autumn, winter.
- Per-group coverage: Pass. The only applicable group, season, is fully covered.
- Syntactic correctness: Pass. All fragments use valid `$state(name, content)` form.
- Whitespace handling: Mixed. Removing all fragments leaves clean prose. Active-state rendering is not clean because fragments omit a leading space, producing `moisturecold and dry`.
- Grounding: Acceptable. The seasonal air shifts stay within cave-passage atmosphere and do not invent props or surface features. `cold and dry` pulls against the baseline moisture cue, but it is still less intrusive than adding unsupported objects or scenery.

Default render:

```text
A narrow passage runs west and descends to the south through rough earthen walls. The floor is uneven, marked by occasional footprints that suggest sporadic use. The air carries a faint hint of moisture from beyond the passage's boundaries.
```

Realistic combination render (`winter`):

```text
A narrow passage runs west and descends to the south through rough earthen walls. The floor is uneven, marked by occasional footprints that suggest sporadic use. The air carries a faint hint of moisturecold and dry from beyond the passage's boundaries.
```

### Claude

- Fragments emitted: 4. States used: spring, summer, autumn, winter.
- Per-group coverage: Pass. The only applicable group, season, is fully covered.
- Syntactic correctness: Pass. All fragments use valid `$state(name, content)` form.
- Whitespace handling: Mixed. Removing all fragments leaves clean prose. Active-state rendering is not clean because fragments omit a leading space, producing `moisturecold and crystalline`.
- Grounding: Mostly grounded, with some extra interpretation. Seasonal air changes fit the cave passage overall. `tinged with decay` and especially `cold and crystalline` are more interpretive than the room packet supports, but they still stay closer to atmospheric modulation than to outright scene invention.

Default render:

```text
A narrow passage runs west and descends to the south through rough earthen walls. The floor is uneven, marked by occasional footprints that suggest sporadic use. The air carries a faint hint of moisture from beyond the passage's boundaries.
```

Realistic combination render (`winter`):

```text
A narrow passage runs west and descends to the south through rough earthen walls. The floor is uneven, marked by occasional footprints that suggest sporadic use. The air carries a faint hint of moisturecold and crystalline from beyond the passage's boundaries.
```

## Verdict

Claude did not produce reliably grounded markup across all three rooms. It was better grounded than Qwen on the tavern hallway, but it still missed required seasonal coverage there and introduced unsupported details on the city lane. Claude also did not consistently meet per-group coverage where Qwen did: Claude missed season on the lane and tavern, while Qwen covered all groups on the lane and the cave but missed invasion on the tavern. Claude was not usable as-is, mainly because active fragments broke spacing and because coverage remained incomplete in two of the three rooms.