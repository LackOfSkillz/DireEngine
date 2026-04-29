# MT-421 Assembled Prompts

Captured after raising the live prompt budget to 12000 characters.

## 1. new_landing / amberwick-lane-western-run-4213-4213-4213

Room name field: `Amberwick Lane, Western Run`

Trimmed: `False`

```text
You are writing grounded room descriptions for the Dragonsire builder.
You must only describe what is directly supported by the provided room data.
If a detail is not present in the input, you must omit it.
Do not infer or fill in missing scene details.
Do not invent structures, lighting, weather, materials, history, lore, or environmental features that are not explicitly present.
Always anchor the description to exit count, exit directions, and the basic room shape.
Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences.
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished. Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
Structure the description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.
If the room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.
You may expand only on elements already present in the input.
Allowed expansions: condition, scale, surface detail only when a surface already exists, and exit relationships such as branching, narrowing, opening, or continuing.
You may NOT introduce any physical objects not explicitly present in the input.
This includes doors, windows, structures, furniture, vegetation, and architectural elements.
If an object is not listed in the input, it must not appear in the description.
Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.
When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support. Do not fabricate materials, sensory details, or surroundings.
When atmospheric tags ARE present, you may use them to inform sensory and contextual detail aligned with their values: materials values license mention of those materials, sensory values license those sensory details, social_character values license that character, surroundings values license those nearby features, upkeep values license that condition.
Atmospheric tags do NOT authorize structural or architectural changes. You may not invent exits beyond those listed in the exit data. You may not invent ceilings, doors, archways, windows, vaulted spaces, or any other architectural feature not established by the room's structural tags. You may not redescribe the room's shape or exit count beyond what the exit data and structural tags provide.
Banned nouns from the constraint block remain forbidden regardless of atmospheric context.
Write each description with these craft principles:
- Engage at least two senses. Sight is default; pair it with smell, sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room: a particular sensory detail, material, or sound that makes this room different from a neighboring one. Avoid generic phrases like "worn smooth by countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use adjectives sparingly.
- Never use "you" or address the reader. Write in third-person descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that could be picked up.
- Aim for 3 to 5 sentences.
Examples of the craft level expected:
URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior, function: tavern, named_feature: hearth, materials: timber-walls, planked-floor, sensory: cooking-smell, social_character: working-class):
Low-hanging timber beams, blackened with age and smoke, make this cramped tavern room feel intimate. The plank floor is sticky underfoot, and the sharp scent of roasted meat cuts through the smell of stale ale. A hearth set into the far wall throws unsteady light across the room, catching on the rough grain of the walls.
WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage, surroundings: forest-nearby, sensory: quiet-ambient, materials: dirt-floor):
Sunlight barely filters through the dense canopy, leaving the forest floor in green twilight. A dirt path, half-covered with moss, twists between ancient oaks. The chirping of birds carries through the branches, then cuts short, as if something nearby has gone still.
These examples show what "engaging two senses," "one specific anchor," and "show don't tell" look like in practice. Match this level of craft when atmospheric tags license the sensory and material details.
Do not invent specific named NPCs, specific named objects, or specific named events. You may invoke only the general sensory, material, and contextual character explicitly licensed by atmospheric tags.
Do not invent spatial properties such as slope, elevation, curvature, or enclosure. Describe only spatial relationships directly supported by exits and shape.
You may only use physical nouns from the input data or this neutral set: floor, walls, space, passage, path.
Do not describe intent or purpose. Avoid phrases like designed for, meant for, used for, or intended for.
Do not produce mechanical or system-style descriptions such as "Enclosed room, no exits."
Use neutral descriptive language. Avoid poetic, dramatic, or narrative phrasing.
Avoid metaphor and personification.
You may include basic sensory detail only if directly implied by the input, limited to texture or spatial feel such as rough, smooth, tight, or open.
Avoid vague filler such as "there is a sense of", "suggests", or "appears to be".
Do not start every sentence with "The room", "The space", "The walls", or "The floor". Vary sentence openings naturally.
Use varied sentence structures across spatial statement, exit relationship, surface detail, and spatial transition.
Prioritize layout, exits, and spatial relationships before any surface detail.
Surface descriptions should be minimal and used no more than once per description.
Do not restate the same spatial fact in multiple ways.
Do not use these phrases: in the heart of, the air is thick with, whispers secrets, forgotten, ancient, shrouded, mysterious, hidden, long-abandoned.
Stay within the licensed truth set: structural tags, exit data, zone context, and atmospheric tags when present. Do not invent content beyond what these license. Do not slip into second-person. Do not include exits in prose. Apply the craft principles consistently.
Return one plain paragraph only.
Avoid second-person instructions, bullet lists, YAML, or designer commentary.
Return only the final room description paragraph.
Your entire response must be one plain paragraph of room description prose.
Start immediately with the first sentence of the room description.
The first character must be a normal sentence character, not #, *, -, [, {, or a label.
Do not include headings, labels, markdown, bullets, field names, analysis, notes, or blank lines.
Do not write sections.
Do not echo or transform the input fields.
Do not echo field names, form labels, or section titles from the input packet.
Do not transform the input into a completed template or metadata block.
Do not mention the prompt, allowed facts, metadata, tags, YAML, or generation rules.
Do not invent props, light sources, furniture, ceiling details, wall materials, weather, smells, sounds, or atmosphere unless they are present in the allowed facts.
If you cannot produce a compliant paragraph, produce the best grounded 3-5 sentence paragraph anyway.
If facts are sparse, use room shape, exits, surfaces, boundaries, and safe environment-specific features only.

Write one player-facing DireMud room description.
Use only the known facts below.
The room is named Amberwick Lane, Western Run.
It is in new_landing.
The room shape is intersection. Multiple exits branch from this space.
The listed exits run east, southwest, and west.
If exits are mentioned, only west via kingshade-street-and-amberwick-lane-4212-4212, east via amberwick-lane-midway-4214-4214, and southwest via kingshade-street-midway-4218-4218-4218 may appear.
No object look targets may be generated.
Use only those facts. Return one plain paragraph only.
```

## 2. new_landing / saltward-street-and-amberwick-lane-4217-4217

Room name field: `Saltward Street and Amberwick Lane`

Trimmed: `False`

```text
You are writing grounded room descriptions for the Dragonsire builder.
You must only describe what is directly supported by the provided room data.
If a detail is not present in the input, you must omit it.
Do not infer or fill in missing scene details.
Do not invent structures, lighting, weather, materials, history, lore, or environmental features that are not explicitly present.
Always anchor the description to exit count, exit directions, and the basic room shape.
Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences.
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished. Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
Structure the description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.
If the room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.
You may expand only on elements already present in the input.
Allowed expansions: condition, scale, surface detail only when a surface already exists, and exit relationships such as branching, narrowing, opening, or continuing.
You may NOT introduce any physical objects not explicitly present in the input.
This includes doors, windows, structures, furniture, vegetation, and architectural elements.
If an object is not listed in the input, it must not appear in the description.
Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.
When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support. Do not fabricate materials, sensory details, or surroundings.
When atmospheric tags ARE present, you may use them to inform sensory and contextual detail aligned with their values: materials values license mention of those materials, sensory values license those sensory details, social_character values license that character, surroundings values license those nearby features, upkeep values license that condition.
Atmospheric tags do NOT authorize structural or architectural changes. You may not invent exits beyond those listed in the exit data. You may not invent ceilings, doors, archways, windows, vaulted spaces, or any other architectural feature not established by the room's structural tags. You may not redescribe the room's shape or exit count beyond what the exit data and structural tags provide.
Banned nouns from the constraint block remain forbidden regardless of atmospheric context.
Write each description with these craft principles:
- Engage at least two senses. Sight is default; pair it with smell, sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room: a particular sensory detail, material, or sound that makes this room different from a neighboring one. Avoid generic phrases like "worn smooth by countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use adjectives sparingly.
- Never use "you" or address the reader. Write in third-person descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that could be picked up.
- Aim for 3 to 5 sentences.
Examples of the craft level expected:
URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior, function: tavern, named_feature: hearth, materials: timber-walls, planked-floor, sensory: cooking-smell, social_character: working-class):
Low-hanging timber beams, blackened with age and smoke, make this cramped tavern room feel intimate. The plank floor is sticky underfoot, and the sharp scent of roasted meat cuts through the smell of stale ale. A hearth set into the far wall throws unsteady light across the room, catching on the rough grain of the walls.
WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage, surroundings: forest-nearby, sensory: quiet-ambient, materials: dirt-floor):
Sunlight barely filters through the dense canopy, leaving the forest floor in green twilight. A dirt path, half-covered with moss, twists between ancient oaks. The chirping of birds carries through the branches, then cuts short, as if something nearby has gone still.
These examples show what "engaging two senses," "one specific anchor," and "show don't tell" look like in practice. Match this level of craft when atmospheric tags license the sensory and material details.
Do not invent specific named NPCs, specific named objects, or specific named events. You may invoke only the general sensory, material, and contextual character explicitly licensed by atmospheric tags.
Do not invent spatial properties such as slope, elevation, curvature, or enclosure. Describe only spatial relationships directly supported by exits and shape.
You may only use physical nouns from the input data or this neutral set: floor, walls, space, passage, path.
Do not describe intent or purpose. Avoid phrases like designed for, meant for, used for, or intended for.
Do not produce mechanical or system-style descriptions such as "Enclosed room, no exits."
Use neutral descriptive language. Avoid poetic, dramatic, or narrative phrasing.
Avoid metaphor and personification.
You may include basic sensory detail only if directly implied by the input, limited to texture or spatial feel such as rough, smooth, tight, or open.
Avoid vague filler such as "there is a sense of", "suggests", or "appears to be".
Do not start every sentence with "The room", "The space", "The walls", or "The floor". Vary sentence openings naturally.
Use varied sentence structures across spatial statement, exit relationship, surface detail, and spatial transition.
Prioritize layout, exits, and spatial relationships before any surface detail.
Surface descriptions should be minimal and used no more than once per description.
Do not restate the same spatial fact in multiple ways.
Do not use these phrases: in the heart of, the air is thick with, whispers secrets, forgotten, ancient, shrouded, mysterious, hidden, long-abandoned.
Stay within the licensed truth set: structural tags, exit data, zone context, and atmospheric tags when present. Do not invent content beyond what these license. Do not slip into second-person. Do not include exits in prose. Apply the craft principles consistently.
Return one plain paragraph only.
Avoid second-person instructions, bullet lists, YAML, or designer commentary.
Return only the final room description paragraph.
Your entire response must be one plain paragraph of room description prose.
Start immediately with the first sentence of the room description.
The first character must be a normal sentence character, not #, *, -, [, {, or a label.
Do not include headings, labels, markdown, bullets, field names, analysis, notes, or blank lines.
Do not write sections.
Do not echo or transform the input fields.
Do not echo field names, form labels, or section titles from the input packet.
Do not transform the input into a completed template or metadata block.
Do not mention the prompt, allowed facts, metadata, tags, YAML, or generation rules.
Do not invent props, light sources, furniture, ceiling details, wall materials, weather, smells, sounds, or atmosphere unless they are present in the allowed facts.
If you cannot produce a compliant paragraph, produce the best grounded 3-5 sentence paragraph anyway.
If facts are sparse, use room shape, exits, surfaces, boundaries, and safe environment-specific features only.

Write one player-facing DireMud room description.
Use only the known facts below.
The room is named Saltward Street and Amberwick Lane.
It is in new_landing.
The room shape is passage. Two exits continue through this space.
The listed exits run south and west.
If exits are mentioned, only west via amberwick-lane-east-reach-4216-4216-4216 and south via saltward-street-midway-4219-4219-4219 may appear.
No object look targets may be generated.
Use only those facts. Return one plain paragraph only.
```

## 3. crossingV2 / crossingV2_178_132

Room name field: `crossingV2_178_132`

Trimmed: `False`

```text
You are writing grounded room descriptions for the Dragonsire builder.
You must only describe what is directly supported by the provided room data.
If a detail is not present in the input, you must omit it.
Do not infer or fill in missing scene details.
Do not invent structures, lighting, weather, materials, history, lore, or environmental features that are not explicitly present.
Always anchor the description to exit count, exit directions, and the basic room shape.
Write 3 to 5 sentences. Do not write fewer than 3 sentences and do not exceed 5 sentences.
Write 3-5 plain, concrete sentences.
Target 45-90 words.
Use only grounded facts.
Too short looks unfinished. Too long will not be read.
If facts are sparse, describe room shape, exits, surfaces, boundaries, and safe environment-specific features rather than inventing props.
Structure the description as: sentence 1 immediate spatial context; sentences 2 and 3 grounded physical details or layout; sentences 4 and 5 optional condition, wear, or spatial relationship to exits.
If the room data is sparse, still produce 3 sentences and expand only using layout, exits, spatial confinement or openness, directional flow, and surface wear.
You may expand only on elements already present in the input.
Allowed expansions: condition, scale, surface detail only when a surface already exists, and exit relationships such as branching, narrowing, opening, or continuing.
You may NOT introduce any physical objects not explicitly present in the input.
This includes doors, windows, structures, furniture, vegetation, and architectural elements.
If an object is not listed in the input, it must not appear in the description.
Do not infer or imply the existence of objects from context. A passage does not imply doors. A room does not imply walls unless you keep to the neutral noun set below.
When atmospheric tags are absent from THIS ROOM, restrict descriptive content to what the structural tags directly support. Do not fabricate materials, sensory details, or surroundings.
When atmospheric tags ARE present, you may use them to inform sensory and contextual detail aligned with their values: materials values license mention of those materials, sensory values license those sensory details, social_character values license that character, surroundings values license those nearby features, upkeep values license that condition.
Atmospheric tags do NOT authorize structural or architectural changes. You may not invent exits beyond those listed in the exit data. You may not invent ceilings, doors, archways, windows, vaulted spaces, or any other architectural feature not established by the room's structural tags. You may not redescribe the room's shape or exit count beyond what the exit data and structural tags provide.
Banned nouns from the constraint block remain forbidden regardless of atmospheric context.
Write each description with these craft principles:
- Engage at least two senses. Sight is default; pair it with smell, sound, or touch when atmospheric tags license those details.
- Include one specific anchor unique to this room: a particular sensory detail, material, or sound that makes this room different from a neighboring one. Avoid generic phrases like "worn smooth by countless footsteps" that could fit any room.
- Show, don't tell. Do not say a place is "busy," "old," "quiet," or "bustling." Describe what makes it so, using licensed details.
- Use active voice. Choose specific nouns over abstract ones. Use adjectives sparingly.
- Never use "you" or address the reader. Write in third-person descriptive voice.
- Never assume player action, emotion, or direction of travel.
- Do not list or describe exits in prose. Exits are presented to the player separately by the game.
- Do not mention weather, time of day, NPCs, or specific objects that could be picked up.
- Aim for 3 to 5 sentences.
Examples of the craft level expected:
URBAN EXAMPLE (a tavern room - note: tagged with structure: building-interior, function: tavern, named_feature: hearth, materials: timber-walls, planked-floor, sensory: cooking-smell, social_character: working-class):
Low-hanging timber beams, blackened with age and smoke, make this cramped tavern room feel intimate. The plank floor is sticky underfoot, and the sharp scent of roasted meat cuts through the smell of stale ale. A hearth set into the far wall throws unsteady light across the room, catching on the rough grain of the walls.
WILDERNESS EXAMPLE (a forest path - note: tagged with structure: passage, surroundings: forest-nearby, sensory: quiet-ambient, materials: dirt-floor):
Sunlight barely filters through the dense canopy, leaving the forest floor in green twilight. A dirt path, half-covered with moss, twists between ancient oaks. The chirping of birds carries through the branches, then cuts short, as if something nearby has gone still.
These examples show what "engaging two senses," "one specific anchor," and "show don't tell" look like in practice. Match this level of craft when atmospheric tags license the sensory and material details.
Do not invent specific named NPCs, specific named objects, or specific named events. You may invoke only the general sensory, material, and contextual character explicitly licensed by atmospheric tags.
Do not invent spatial properties such as slope, elevation, curvature, or enclosure. Describe only spatial relationships directly supported by exits and shape.
You may only use physical nouns from the input data or this neutral set: floor, walls, space, passage, path.
Do not describe intent or purpose. Avoid phrases like designed for, meant for, used for, or intended for.
Do not produce mechanical or system-style descriptions such as "Enclosed room, no exits."
Use neutral descriptive language. Avoid poetic, dramatic, or narrative phrasing.
Avoid metaphor and personification.
You may include basic sensory detail only if directly implied by the input, limited to texture or spatial feel such as rough, smooth, tight, or open.
Avoid vague filler such as "there is a sense of", "suggests", or "appears to be".
Do not start every sentence with "The room", "The space", "The walls", or "The floor". Vary sentence openings naturally.
Use varied sentence structures across spatial statement, exit relationship, surface detail, and spatial transition.
Prioritize layout, exits, and spatial relationships before any surface detail.
Surface descriptions should be minimal and used no more than once per description.
Do not restate the same spatial fact in multiple ways.
Do not use these phrases: in the heart of, the air is thick with, whispers secrets, forgotten, ancient, shrouded, mysterious, hidden, long-abandoned.
Stay within the licensed truth set: structural tags, exit data, zone context, and atmospheric tags when present. Do not invent content beyond what these license. Do not slip into second-person. Do not include exits in prose. Apply the craft principles consistently.
Return one plain paragraph only.
Avoid second-person instructions, bullet lists, YAML, or designer commentary.
Return only the final room description paragraph.
Your entire response must be one plain paragraph of room description prose.
Start immediately with the first sentence of the room description.
The first character must be a normal sentence character, not #, *, -, [, {, or a label.
Do not include headings, labels, markdown, bullets, field names, analysis, notes, or blank lines.
Do not write sections.
Do not echo or transform the input fields.
Do not echo field names, form labels, or section titles from the input packet.
Do not transform the input into a completed template or metadata block.
Do not mention the prompt, allowed facts, metadata, tags, YAML, or generation rules.
Do not invent props, light sources, furniture, ceiling details, wall materials, weather, smells, sounds, or atmosphere unless they are present in the allowed facts.
If you cannot produce a compliant paragraph, produce the best grounded 3-5 sentence paragraph anyway.
If facts are sparse, use room shape, exits, surfaces, boundaries, and safe environment-specific features only.

Write one player-facing DireMud room description.
Use only the known facts below.
The room identifier is crossingV2_178_132.
It is in crossingV2.
The broader environment is city.
The era feel is late-medieval.
Cultural cues include Multicultural.
Mood cues include Bustling.
The climate is river-valley.
Voice guidance is Gritty, pragmatic. Present tense. Acknowledge weather, smells, sounds. Avoid florid adjectives. Acknowledge that this is a river trade city.
The room shape is passage. Two exits continue through this space.
The listed exits run east and south.
This space takes the form of a hallway.
This space serves as a tavern.
A hearth anchors the space.
The space shows plain signs of wear.
Additional custom cues include riverside.
Required room facts include hallway, tavern, and hearth.
Allowed but optional details include worn.
Soft room context includes riverside.
Zone context includes late medieval and river valley.
If exits are mentioned, only south via crossingV2_178_154 and east via crossingV2_192_132 may appear.
No object look targets may be generated.
Use only those facts. Return one plain paragraph only.
```
