# Starry Road findings

## Scope

This note separates three different things:

- what the external PostgreSQL lore database on `127.0.0.1:5432` contains
- what this repo's research/docs layer says about `starry road`
- what the live game implementation currently says to the dead player, the room, and observers

The key finding is that `starry road` exists as a lore/research phrase, but it is not currently present in the shipped death/depart player messaging I found in the game code.

## PostgreSQL findings

I connected directly to the PostgreSQL server on `5432` with `user/pass` using `psycopg` and confirmed the available databases are:

- `direlore`
- `interq_db`
- `postgres`

I then inspected the likely text-bearing tables in `direlore` and queried the exact text columns for `starry road`.

### `direlore` table shapes inspected

- `public.raw_pages`: `url`, `title`, `raw_html`, `raw_text`, `fetched_at`, `content_hash`
- `public.sections`: `id`, `url`, `heading`, `content`, `section_tag`
- `knowledge.document_chunks`: `id`, `source_url`, `entity_id`, `section_id`, `content`, `chunk_index`, `created_at`, `embedding`
- `public.facts`: `id`, `entity_id`, `key`, `value`, `source_url`, `confidence`, `normalized_key`, `normalized_value`, `provenance`

### `direlore` direct query result

The targeted query against `raw_pages.raw_text`, `sections.content`, `document_chunks.content`, and `facts.value` did return `starry road` hits in the lore database output. The repo already preserves one of those extracted results in the death/favor research note:

- `DEPART ing`: soul takes a trip on the `starry road`; body attachment time is based on spirit; first-circle favor-free death protection is documented.

The research note also preserves a second direct lore-state formulation derived from SQL-backed extraction:

- `Departed soul on the starry road.`

That is enough to conclude the external lore database contains `starry road` as part of DragonRealms death/favor material.

### `interq_db`

I confirmed `interq_db` exists on the server, but I did not find evidence during this pass that it is the relevant source for Starry Road death lore. All concrete Starry Road findings in hand point back to `direlore`-derived material.

## Repo research/doc findings

The strongest repo-side source is the research extraction note at [docs/research/clericDeathFavor.md](c:/Users/gary/dragonsire/docs/research/clericDeathFavor.md).

That file explicitly states its data source was direct SQL queries against `direlore` on `localhost:5432` and includes these Starry Road references:

- `DEPART` dissolves the mortal shell, leaves behind a grave, and sends the soul on the `starry road`.
- `Departed soul on the starry road.`
- Death/favor tone includes mythic phrasing like `mortal shell`, `starry road`, `Immortal's attention`, and `Death's Sting`.
- `DEPART ing`: soul takes a trip on the `starry road`; body attachment time is based on spirit.

There is also broader status/context in [docs/archive/root-workfiles/Cleric.md](c:/Users/gary/dragonsire/docs/archive/root-workfiles/Cleric.md), but that file is more of an implementation status note than a source of literal Starry Road strings.

## Live implementation findings

The current game implementation does have a full death/depart pipeline, but it does not currently use the phrase `starry road` in the player-facing messaging I checked.

### Player messaging on death

From [world/systems/death.py](c:/Users/gary/dragonsire/world/systems/death.py):

- `You have died.`
- `You feel yourself slipping free from your body.`
- `You feel your wealth slip from your grasp as you fall.` when coins are lost

### Dead-state command gate messaging

From [commands/command.py](c:/Users/gary/dragonsire/commands/command.py):

- `You are dead. You can still look, speak, check your state, depart, or wait for resurrection.`

From [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):

- `You are dead. You must wait for resurrection or type DEPART to let go.`
- there is also a banner-style reminder path with `You are dead. Type DEPART to return.`

### Depart messaging

From [commands/cmd_depart.py](c:/Users/gary/dragonsire/commands/cmd_depart.py):

- `Are you sure you wish to depart? This will forfeit your body.`
- `Your resolve slips. Type DEPART again if you still wish to let go.`
- `DEPART <mode> will spend favor. Type DEPART CONFIRM to proceed.`

From [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):

- `You release your hold on the body and leave a grave behind.`

This is the clearest shipped substitute for the mythic Starry Road line. Mechanically it is the same transition. Tonally it is much flatter.

### Death status / corpse status messaging

From [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py):

Dead players can inspect structured state, including:

- `State: Dead`
- `Depart Path: ...`
- `Soul: ...`
- `Soul Strength: ...`
- `Corpse Condition: ...`
- `Memory: ...`
- `Memory Decay: ...`
- `Corpse Decay: ...`
- `You are suffering from Death's Sting.`
- `Severity: ...`
- `Time Remaining: ...`

And corpse inspection returns:

- `Corpse: ...`
- `Condition: ...`
- `Time Until Decay: ...`
- `Memory: ...`
- `Location: ...`
- `Body State: Irrecoverable`
- `Preparation: ...`

Again, this is functional and information-dense, but not mythic.

### Room / observer messaging

There are two room-visible death surfaces in the current code.

From [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py), the death emote shown to others is randomized from:

- `<name> collapses suddenly, life leaving their body.`
- `<name> staggers, then falls motionless.`
- `<name> crumples to the ground.`

From [world/systems/death.py](c:/Users/gary/dragonsire/world/systems/death.py), the room receives that death emote with the dying character excluded.

From [typeclasses/characters.py](c:/Users/gary/dragonsire/typeclasses/characters.py), after `depart`, the corpse room receives:

- `A disturbed patch of ground marks where someone fell.`

This is the only concrete room-side depart aftermath string I found in the shipped implementation.

### Event hooks vs visible messaging

The character does emit death lifecycle hooks:

- `on_character_death`
- `on_depart`
- `on_grave_created`
- `on_resurrection`

But in the local code search I did not find dedicated room/object handler methods implementing richer observer prose off those hook names. So the hook system exists, but the visible Starry Road-style messaging is not currently hanging off it.

## Compare: lore concept vs shipped behavior

### What the lore layer says

The lore/research side presents death and depart in mythic language:

- soul leaves the mortal shell
- soul goes onto the `starry road`
- favors and resurrection interact with a divine/metaphysical framework

### What the live implementation says

The live implementation presents death and depart in practical language:

- you died
- you are slipping free from your body
- you may wait for resurrection or depart
- depart forfeits the body
- depart leaves a grave behind

### Gap

The conceptual gap is straightforward:

- the DragonRealms lore phrase `starry road` is present in research and external lore data
- the current game code does not surface that phrase to the player, room, or observers
- the current implementation communicates the same state transition, but in a more literal and less mythic voice

## Direct answer to the messaging question

If the specific question is whether there is already implemented `starry road` room/player/observer messaging in this repo, the answer appears to be no.

What exists today is:

- player death messaging
- dead-state instructional messaging
- depart confirmation and completion messaging
- structured death/corpse status output
- room-visible death emotes
- a minimal room aftermath line after depart

What I did not find in shipped implementation:

- a player-facing line that explicitly says the soul walks the `starry road`
- a room-facing observer line that explicitly references the `starry road`
- a dedicated `observer`-specific Starry Road message branch
- hook handlers that convert `on_depart` or related events into mythic Starry Road prose

## Bottom line

`starry road` is present in the external lore/research layer and appears to be a real DragonRealms death concept preserved in `direlore`-derived documentation.

But the live DireEngine death implementation currently does not surface that phrase in room, player, or observer messaging. The shipped messaging is functional and mechanically clear, but it is not yet using the mythic Starry Road framing.