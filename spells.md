# Elanthipedia Spells Survey

Source searched: https://elanthipedia.play.net/Spells
Date: 2026-04-13

## Scope

The top-level `Spells` page is a hub page, not a paginated spell list. It branches into spell indexes by:

- mana type
- guild
- spell family / spell type
- related magic reference pages

The most useful downstream pages for structured spell data were the guild pages, mana-type category pages, and the `Cyclic spells` and `Ritual spells` category pages.

## What The Spells Hub Exposes

### By mana type

- Arcane
- Elemental
- Holy
- Life
- Lunar

### By guild

- Bard
- Cleric
- Empath
- Moon Mage
- Necromancer
- Paladin
- Ranger
- Trader
- Warrior Mage

### By other factors

- Augmentation spells
- Debilitation spells
- Targeted spells
- Utility spells
- Warding spells
- Cyclic spells
- Ritual spells
- Area of effect spells
- Scroll spells
- Spell tiers
- contest-type spell groupings

### Related reference pages

- Spell preparations
- Spell abbreviations
- Magical feats
- Magical research
- Attunement
- Mana and mana levels
- Spell slots
- Planned spells

## Important Structural Finding

The `Spells` page itself does not provide subsequent paginated pages in the normal sense. Instead, the real spell information is distributed into category pages, each with a structured `Summary of Spell Information` table.

Typical fields exposed in those tables:

- spell name
- abbreviation
- short effect summary
- cast style such as `standard`, `battle`, `cyclic`, `ritual`, `metamagic`
- spell family such as `augmentation`, `debilitation`, `targeted`, `utility`, `warding`
- contest type when relevant
- prep range
- rank range
- duration
- slot cost
- difficulty tier
- spellbook

## Guild Spell Pages

### Bard spells

Count found: `32`

Representative entries:

- `Blessing of the Fae (BOTF)`: `+Attunement pool`, `+Attunement pool regeneration`, cyclic augmentation
- `Eye of Kertigen (EYE)`: periodic search utility
- `Phoenix's Pyre (PYRE)`: cyclic area pulsing damage
- `Words of the Wind (WORD)`: `+Mojo regeneration`
- `Aether Wolves (AEWO)`: `-Attunement pool regeneration`

Spellbooks surfaced:

- Elemental Invocations
- Emotion Control
- Fae Arts
- Sound Manipulation

### Cleric spells

Count found: `48`

Representative entries:

- `Persistence of Mana (POM)`: `+Attunement skill`, `+Attunement pool regeneration`, ritual augmentation
- `Eylhaar's Feast (EF)`: converts spirit health to attunement, vitality, or fatigue
- `Auspice`: `+Spirit health`, `+Spirit health regeneration`
- `Revelation (REV)`: cyclic magical search utility
- `Resurrection (REZZ)`: cyclic resurrection utility

Spellbooks surfaced:

- Divine Intervention
- Holy Defense
- Holy Evocations
- Metamagic
- Spirit Manipulation
- Antinomic Sorcery

### Empath spells

Count found: `33`

Representative entries:

- `Circle of Sympathy (COS)`: creates a tree that allows Empaths to share attunement
- `Regenerate`: cyclic wound/scar healing
- `Raise Power (RP)`: `+Mana level`, fatigue damage, self damage, life mana only
- `Heart Link (HL)`: vitality equalization and bleed/poison/disease slowing
- `Absolution`: allows Empath to attack undead without shock

Spellbooks surfaced:

- Body Purification
- Healing
- Life Force Manipulation
- Mental Preparation
- Protection

### Moon Mage spells

Count found: `57`

Representative entries:

- `Moongate (MG)`: cyclic teleport utility
- `Starlight Sphere (SLS)`: cyclic pulsing single-target damage
- `Braun's Conjecture (BC)`: ritual teleport/prediction support
- `Invocation of the Spheres (IOTS)`: ritual stat augmentation
- `Iyqaromos Fire-Lens (IFL)`: boosts `Burn` based on moons/sun
- `Shadowling`: `+Attunement pool`, attunement heal, lunar users only

Spellbooks surfaced:

- Enlightened Geometry
- Moonlight Manipulation
- Perception
- Psychic Projection
- Stellar Magic
- Teleologic Sorcery

### Necromancer spells

Count found: `40`

Representative entries:

- `Rite of Forbearance (ROF)`: reduced attunement when casting, freezes attunement regeneration, integrity-piercing behavior
- `Call from Within (CFW)`: cyclic summoned undead bug
- `Universal Solvent (USOL)`: cyclic randomized AoE damage
- `Obfuscation`: stealth and masking utility
- `Kura-Silma (KS)`: `+Attunement skill`, `+Perception skill`

Spellbooks surfaced:

- Anabasis
- Animation
- Blood Magic
- Corruption
- Synthetic Creation
- Transcendental Necromancy

### Paladin spells

Count found: `29`

Representative entries:

- `Holy Warrior (HOW)`: cyclic weapon blessing / warding utility
- `Truffenyi's Rally (TR)`: cyclic balance-heal and dispel support
- `Divine Armor (DA)`: armor and shield enhancement
- `Rutilor's Edge (RUE)`: weapon quality improvement
- `Alamhif's Gift (AG)`: ritual death's-sting / soul-pool effect

Spellbooks surfaced:

- Inspiration
- Justice
- Sacrifice

### Ranger spells

Count found: `35`

Representative entries:

- `Awaken Forest (AF)`: cyclic spawn ally
- `Memory of Nature (MON)`: ritual to preserve ranger bonus outside wilderness
- `See the Wind (STW)`: ranged-skill augmentation
- `Bloodthorns`: ritual wound-heal / retaliatory defense
- `Compost`: utility effect, explicitly noted as not boosting life mana

Spellbooks surfaced:

- Animal Abilities
- Nature Manipulation
- Wilderness Survival

### Trader spells

Count found: `26`

Representative entries:

- `Arbiter's Stylus (ARS)`: cyclic damage spell
- `Mask of the Moons (MOM)`: cyclic warding
- `Stellar Collector (STC)`: collects and stores starlight energy
- `Noumena (NOU)`: enables starlight aura regeneration under worse conditions
- `Avtalia Array (AVTA)`: passively charges worn cambrinth/gaethzen outdoors while `Noumena` is active

Spellbooks surfaced:

- Fabrication
- Illusion
- Noematics

### Warrior Mage spells

Count found: `56`

Representative entries:

- `Aether Cloak (AC)`: cyclic TM barrier and reflect
- `Ethereal Fissure (ETF)`: `+Mana level`, room-wide elemental only
- `Electrostatic Eddy (EE)`: cyclic AoE nerve damage / anti-hide pressure
- `Fire Rain (FR)`: cyclic AoE multistrike
- `Rimefang (RIM)`: cyclic pulsing melee damage

Spellbooks surfaced:

- Aether Manipulation
- Air Manipulation
- Earth Manipulation
- Electricity Manipulation
- Fire Manipulation

## Current In-Game Registered Spells

Source: [domain/spells/spell_definitions.py](domain/spells/spell_definitions.py)
Date: 2026-04-13

Current structured spell registry count: `17`

This section is the full set of spells currently implemented in the live structured registry. It is not a lore-complete or guild-complete spell list.

### Healing

- `empath_heal` — Heal (`hl`)
	- mana: `life`
	- professions: `empath`
	- target: `single`
	- spellbook: `Healing`

- `cleric_minor_heal` — Minor Heal (`mh`)
	- mana: `holy`
	- professions: `cleric`
	- target: `single`
	- spellbook: `Spirit Manipulation`

### Augmentation

- `bolster` — Bolster (`bol`)
	- mana: `elemental`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `self`
	- spellbook: `Fundamentals`

### Warding

- `minor_barrier` — Minor Barrier (`mb`)
	- mana: `holy`
	- professions: `cleric`
	- target: `self`
	- spellbook: `Holy Defense`

- `shielding` — Shielding (`sh`)
	- mana: `holy`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `self`
	- spellbook: `Fundamentals`

- `shared_guard` — Shared Guard (`sg`)
	- mana: `holy`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `group`
	- spellbook: `Fundamentals`

### Targeted Magic

- `flare` — Flare (`fl`)
	- mana: `elemental`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `single`
	- spellbook: `Elemental Targeting`

### AoE

- `arc_burst` — Arc Burst (`ab`)
	- mana: `elemental`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `room`
	- spellbook: `Elemental Targeting`

- `radiant_burst` — Radiant Burst (`rb`)
	- mana: `holy`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `room`
	- spellbook: `Fundamentals`

### Debilitation

- `daze` — Daze (`dz`)
	- mana: `lunar`
	- professions: `moon_mage`
	- target: `single`
	- spellbook: `Psychic Projection`

- `hinder` — Hinder (`hin`)
	- mana: `lunar`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `single`
	- spellbook: `Fundamentals`

- `slow` — Slow (`sl`)
	- mana: `holy`
	- professions: `cleric`
	- target: `single`
	- spellbook: `Spirit Manipulation`

### Cyclic

- `regenerate` — Regenerate (`reg`)
	- mana: `life`
	- professions: `empath`
	- target: `self`
	- spellbook: `Healing`

- `wither` — Wither (`wth`)
	- mana: `lunar`
	- professions: `moon_mage`
	- target: `single`
	- spellbook: `Psychic Projection`

- `storm_field` — Storm Field (`sf`)
	- mana: `elemental`
	- professions: `warrior_mage`
	- target: `room`
	- spellbook: `Elemental Targeting`

### Utility

- `glimmer` — Glimmer (`gli`)
	- mana: `elemental`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `self`
	- spellbook: `Fundamentals`

- `cleanse` — Cleanse (`cln`)
	- mana: `holy`
	- professions: `bard`, `cleric`, `empath`, `moon_mage`, `necromancer`, `paladin`, `ranger`, `warrior_mage`
	- target: `self`
	- spellbook: `Fundamentals`

## Referenced But Not Registered

- `radiant_aura`
	- status: referenced in tests as deprecated legacy cyclic metadata
	- runtime behavior: intentionally fails closed as unregistered
	- reason: blocked until it gets a real structured registry definition

## Important Note

If a spell appears in design references, guild charts, or external sources but is not listed in the registry section above, it is not currently implemented as a live registered spell in this codebase.
- Hylomorphic Sorcery
- Water Manipulation

## Mana-Type Category Pages

### Elemental magic

Primary guilds surfaced:

- Bard
- Warrior Mage

Key findings:

- Elemental pages merge both guilds into one shared mana-type view.
- `Elemental Efficacy` behavior is emphasized on Bard and Warrior Mage pages.
- Many rows include guild and spellbook columns, making the mana-type page useful for cross-guild comparisons.

Representative entries:

- `Blessing of the Fae`
- `Echoes of Aether`
- `Aether Cloak`
- `Ethereal Fissure`
- `Fire Rain`

### Holy magic

Primary guilds surfaced:

- Cleric
- Paladin

Key findings:

- The page explicitly ties Cleric casting feel to devotion and Paladin casting feel to soul state.
- Holy spell rows include both support/ritual systems and offensive holy effects.

Representative entries:

- `Persistence of Mana`
- `Eylhaar's Feast`
- `Auspice`
- `Holy Warrior`
- `Truffenyi's Rally`

### Life magic

Primary guilds surfaced:

- Empath
- Ranger

Key findings:

- The page describes Life mana as arising from the struggle between order and chaos.
- Ranger and Empath spell tables are merged here for cross-profession comparison.

Representative entries:

- `Circle of Sympathy`
- `Regenerate`
- `Raise Power`
- `Awaken Forest`
- `Memory of Nature`

### Lunar magic

Primary guilds surfaced:

- Moon Mage
- Trader

Key findings:

- Lunar spell data is shared across Moon Mages and Traders.
- This page is useful for separating Moon Mage celestial magic from Trader starlight/fabrication systems while keeping them under one mana type.

Representative entries:

- `Moongate`
- `Braun's Conjecture`
- `Invocation of the Spheres`
- `Mask of the Moons`
- `Stellar Collector`

### Arcane magic

Primary guild surfaced:

- Necromancer

Key findings:

- The page frames Arcane magic as esoteric and hard to codify.
- It also references sorcery-adjacent surfaces and non-Necromancer arcane entries.
- Necromancer remains the dominant structured spell source under Arcane.

Representative entries:

- `Rite of Forbearance`
- `Universal Solvent`
- `Call from Within`
- `Kura-Silma`
- `Obfuscation`

## Spell-Family Category Pages

### Cyclic spells

Count found: `40`

Key findings:

- The page explicitly describes cyclic spells as continually draining held mana, cambrinth, or attunement.
- It states only one cyclic spell may be active at a time, with Bard `Segue` as an exception path.
- The page is one of the clearest cross-guild references for ongoing upkeep-style mana behavior.

Representative entries across mana types:

- `Aether Cloak`
- `Electrostatic Eddy`
- `Fire Rain`
- `Ghost Shroud`
- `Hydra Hex`
- `Resurrection`
- `Soul Attrition`
- `Moongate`
- `Starlight Sphere`
- `Call from Within`
- `Rite of Forbearance`
- `Awaken Forest`
- `Regenerate`

### Ritual spells

Count found: `23`

Key findings:

- The page states ritual spells may require a ritual focus.
- It is a strong cross-guild source for long-duration setup magic and important mana-adjacent support systems.

Representative entries across mana types:

- `Persistence of Mana`
- `Circle of Sympathy`
- `Embrace of the Vela'tohr`
- `Braun's Conjecture`
- `Invocation of the Spheres`
- `Book Burning`
- `Aegis of Granite`
- `Mantle of Flame`
- `Memory of Nature`
- `Bloodthorns`

## Implementation Note: Spell Exposure And Acquisition Gating

As this system is built, spells should not be globally exposed just because they exist in the data.

Required gating rules:

- Cleric spells are only exposed to Cleric characters.
- Bard spells are only exposed to Bard characters.
- The same rule applies for every profession-specific spell list: Empath, Moon Mage, Necromancer, Paladin, Ranger, Trader, and Warrior Mage.
- Shared mana type does not imply shared spell access. For example, Paladins and Clerics both use Holy mana, but should still only see their own spell lists unless a spell is explicitly cross-profession by design.

Within a profession, spell exposure should also be gated by progression and learn state:

- circle requirements
- skill rank requirements
- spell acquiring method

Spell acquiring method must be tracked explicitly, not treated as flavor text. At minimum the system should distinguish:

- taught by player
- taught by NPC
- learned from spellbook / scroll / written source

Implementation consequence:

- a spell should only appear in the player's available spell list when profession access is valid
- a spell should only become learnable when its circle and rank prerequisites are satisfied
- a spell should only become known/castable once its acquisition path has actually been completed
- acquisition source should be stored as structured state so the engine can audit how the spell was learned

Recommended model constraint:

- `spell catalog` answers what exists in the world
- `profession spell access` answers which professions may ever learn it
- `spell prerequisites` answers when it becomes eligible
- `character spell knowledge` answers whether this specific character has actually learned it and by what method

## Relevant Mechanics Reconfirmed While Surveying Spell Pages

These spell pages reinforce several mana-system concepts already identified elsewhere:

- attunement pool and attunement regeneration are directly modified by spells such as `Persistence of Mana`, `Blessing of the Fae`, `Aether Wolves`, and `Shadowling`
- mana level can be modified or surfaced by spells such as `Ethereal Fissure`, `Raise Power`, and `Nexus`
- cyclic spells are a distinct upkeep-drain class
- ritual spells form a distinct long-duration / special-casting-support class
- profession identity materially changes how mana-facing spells are expressed

## DireLore DB Extraction: Spell Mechanics, Messaging, And Profession Lists

Source queried directly: local PostgreSQL `direlore` on `127.0.0.1:5432` using the repo's live config in `world/systems/canon_seed.py`.

Primary tables used in this pass:

- `public.page_metadata`
- `public.sections`
- `public.raw_pages`
- `public.canon_spells`
- `knowledge.document_chunks`

### Data-quality note on circle sorting

DireLore does **not** currently preserve a clean, complete per-circle unlock table for each guild spellbook.

What it does preserve reliably:

- profession spell categories such as `Cleric spells`, `Moon Mage spells`, and `Warrior Mage spells`
- progression-style buckets such as `Intro abilities`, `Basic abilities`, `Intermediate abilities`, and `Advanced abilities`
- acquisition-adjacent tags such as `Scroll spells` and `Guild Leader spells`
- isolated direct circle evidence on a small number of pages

Because of that, the profession lists below are grouped by the best progression proxy actually present in DireLore right now: `Intro`, `Basic`, `Intermediate`, `Advanced`, then `No preserved progression band`.

Direct circle evidence recovered in this pass:

- `Category:Magic` preserves `Apprentice Spells` for analogous patterns: from `1st` to `10th` circle, players have free access to `Burden`, `Ease Burden`, `Manifest Force`, and `Strange Arrow`; those are removed at `11th` circle unless learned permanently or accessed through scrolls.
- `Moongate` explicitly says you need the rank of a `50th degree adept` to begin casting it, approximately `250 Utility` ranks.
- `Moongate` and `Teleport` also preserve `100th circle ability` behavior tied to casting on `Grazhir` and to safe handling of unavailable moon targets.

### High-signal mechanics and cast-message findings from DireLore

- `Magic Feats` preserves spell-preparation concealment and recognition rules. `Legerdemain` raises the difficulty of others noticing or recognizing your preparation when using `PREPARE /HIDE`. `Silent Preparation` makes alternate preparations easier to conceal and removes the `3` second prep-time penalty from `PREPARE /HIDE`. `Basic Preparation Recognition` is required to identify another caster's spell name, spellbook, and realm while it is being prepared.
- `Moongate` preserves concrete cast syntax and cyclic fuel rules: `CAST Katamba / Xibar / Yavash`, or `CAST Grazhir` with the `100th circle ability`. It is explicitly cyclic, drains ongoing fuel, accepts cambrinth or raw attunement with `Raw Channeling`, and supports `5` to `45` mana streams. Harnessing after prep extends duration instead of strength.
- `Teleport` preserves target and consequence rules: valid targets are `Katamba`, `Xibar`, and `Yavash`, with `CAST RIPPLEGATE` unlocking a predetermined location through `Ripplegate Theory`. Teleport distance scales with mana, not raw Primary Magic skill, and arrival stun grows with distance and travel context.
- `Truffenyi's Rally` preserves group-targeting and target-side messaging. It attempts one dispel per group member if potency is sufficient, and a preserved example target message is: `Unspoken words of gibberish resembling [Paladin]'s voice grate in your ears, causing you to falter!`
- `Category:Prophets of G'nar Peth` preserves alternate preparation flavor with explicit self messaging: `You focus your sense of touch on the energies in the air while chanting the mantra for the Shadows spell.`
- `Magic comments` preserves player-observed Bard messaging behavior. `DRUM` can produce third-person messaging about yourself, and `PYRE` targeting a player can emit both second- and third-person lines to the victim at once.

### Profession spell lists from DireLore

#### Bard

DireLore pages found: `32`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `32`
- `Guild Leader spells`: `31`
- `Signature spells`: `16`

##### Intro

- `Aether Wolves`, `Aura of Tongues`, `Caress of the Sun`, `Eillie's Cry`, `Faenella's Grace`

##### Basic

- `Breath of Storms`, `Damaris' Lullaby`, `Demrris' Resolve`, `Failure of the Forge`, `Glythtide's Joy`, `Hodierna's Lilt`, `Redeemer's Pride`, `Whispers of the Muse`, `Words of the Wind`

##### Intermediate

- `Blessing of the Fae`, `Drums of the Snake`, `Echoes of Aether`, `Eye of Kertigen`, `Misdirection`, `Naming of Tears`, `Rage of the Clans`, `Resonance`, `Will of Winter`

##### Advanced

- `Abandoned Heart`, `Albreda's Balm`, `Beckon the Naga`, `Desert's Maelstrom`, `Harmony`, `Nexus`, `Phoenix's Pyre`, `Sanctuary`, `Soul Ablaze`

#### Cleric

DireLore pages found: `48`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `45`
- `Guild Leader spells`: `40`
- `Signature spells`: `21`

##### Intro

- `Bless`, `Centering`, `Visage`

##### Basic

- `Aspects of the All-God`, `Auspice`, `Divine Radiance`, `Fists of Faenella`, `Glythtide's Gift`, `Harm Evil`, `Horn of the Black Unicorn`, `Huldah's Pall`, `Protection from Evil`, `Rejuvenation`, `Sanctify Pattern`, `Soul Bonding`, `Soul Shield`, `Soul Sickness`, `Starry Waters`, `Uncurse`, `Vigil`

##### Intermediate

- `Aesrela Everild`, `Benediction`, `Chill Spirit`, `Curse of Zachriedek`, `Eylhaar's Feast`, `Ghost Shroud`, `Hand of Tenemlor`, `Harm Horde`, `Malediction`, `Mass Rejuvenation`, `Meraud's Cry`, `Persistence of Mana`, `Phelim's Sanction`, `Resurrection`, `Revelation`, `Shield of Light`, `Soul Attrition`

##### Advanced

- `Fire of Ushnish`, `Halo`, `Hydra Hex`, `Idon's Theft`, `Murrula's Flames`, `Osrel Meraud`, `Sanyu Lyba`, `Spite of Dergati`

##### No preserved progression band

- `Bitter Feast`, `Heavenly Fires`, `Time of the Red Spiral`

#### Empath

DireLore pages found: `33`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `33`
- `Guild Leader spells`: `30`
- `Signature spells`: `18`

##### Intro

- `Heal Scars`, `Heal Wounds`, `Refresh`

##### Basic

- `Aggressive Stance`, `Blood Staunching`, `Gift of Life`, `Innocence`, `Iron Constitution`, `Lethargy`, `Mental Focus`, `Paralysis`, `Vitality Healing`

##### Intermediate

- `Absolution`, `Awaken`, `Circle of Sympathy`, `Compel`, `Cure Disease`, `Flush Poisons`, `Heal`, `Heart Link`, `Nissa's Binding`, `Raise Power`, `Tranquility`, `Vigor`

##### Advanced

- `Aesandry Darlaeth`, `Calculated Rage`, `Embrace of the Vela'Tohr`, `Fountain of Creation`, `Guardian Spirit`, `Perseverance of Peri'el`, `Regenerate`

##### No preserved progression band

- `Adaptive Curing`, `Icutu Zaharenela`

#### Moon Mage

DireLore pages found: `57`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `53`
- `Guild Leader spells`: `46`
- `Signature spells`: `34`

##### Intro

- `Calm`, `Clear Vision`, `Focus Moonbeam`, `Shadows`, `Telekinetic Throw`

##### Basic

- `Artificer's Eye`, `Aura Sight`, `Dazzle`, `Destiny Cipher`, `Dinazen Olkar`, `Partial Displacement`, `Piercing Gaze`, `Psychic Shield`, `Refractive Field`, `Rend`, `Sever Thread`, `Sleep`, `Tangled Fate`, `Teleport`, `Tenebrous Sense`, `Whole Displacement`

##### Intermediate

- `Braun's Conjecture`, `Burn`, `Cage of Light`, `Contingency`, `Distant Gaze`, `Locate`, `Machinist's Touch`, `Moonblade`, `Moongate`, `Seer's Sense`, `Shadow Web`, `Shadowling`, `Shift Moonbeam`, `Sorrow`, `Sovereign Destiny`, `Steps of Vuan`, `Telekinetic Storm`, `Tezirah's Veil`, `Thoughtcast`, `Unleash`

##### Advanced

- `Invocation of the Spheres`, `Mental Blast`, `Mind Shout`, `Read the Ripples`, `Saesordian Compass`, `Shadewatch Mirror`, `Shadow Servant`, `Shear`, `Starlight Sphere`, `Telekinetic Shield`

##### No preserved progression band

- `Empower Moonblade`, `Hypnotize`, `Iyqaromos Fire-Lens`, `Riftal Summons`, `Ripplegate Theory`, `Shape Moonblade`

#### Necromancer

DireLore pages found: `40`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `35`
- `Guild Leader spells`: `35`
- `Signature spells`: `28`

##### Intro

- `Acid Splash`, `Heighten Pain`, `Obfuscation`

##### Basic

- `Butcher's Eye`, `Eyes of the Blind`, `Ivory Mask`, `Kura-Silma`, `Petrifying Visions`, `Quicken the Earth`, `Solace`

##### Intermediate

- `Blood Burst`, `Calcified Hide`, `Call from Beyond`, `Consume Flesh`, `Emuin's Candlelight`, `Ghoulflesh`, `Necrotic Reconstruction`, `Philosopher's Preservation`, `Researcher's Insight`, `Resection`, `Reverse Putrefaction`, `Rite of Contrition`, `Rite of Forbearance`, `Rite of Grace`, `Siphon Vitality`, `Viscous Solution`, `Visions of Darkness`

##### Advanced

- `Book Burning`, `Call from Within`, `Devour`, `Universal Solvent`, `Vivisection`, `Worm's Mist`

##### No preserved progression band

- `Alkahest Edge`, `Chirurgia`, `Covetous Rebirth`, `Ebon Blood of the Scorpion`, `Liturgy`, `Relight`, `Spiteful Rebirth`

#### Paladin

DireLore pages found: `29`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `29`
- `Guild Leader spells`: `28`
- `Signature spells`: `11`

##### Intro

- `Aspirant's Aegis`, `Heroic Strength`, `Stun Foe`

##### Basic

- `Courage`, `Divine Guidance`, `Footman's Strike`, `Halt`, `Hands of Justice`, `Righteous Wrath`, `Sentinel's Resolve`, `Shatter`, `Tamsine's Kiss`, `Vessel of Salvation`

##### Intermediate

- `Anti-Stun`, `Banner of Truce`, `Bond Armaments`, `Clarity`, `Divine Armor`, `Marshal Order`, `Rebuke`, `Rutilor's Edge`, `Soldier's Prayer`

##### Advanced

- `Alamhif's Gift`, `Crusader's Challenge`, `Holy Warrior`, `Smite Horde`, `Truffenyi's Rally`

##### No preserved progression band

- `Sidasas Sedra`, `Veteran Insight`

#### Ranger

DireLore pages found: `35`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `34`
- `Guild Leader spells`: `34`
- `Signature spells`: `13`

##### Intro

- `Athleticism`, `Compost`, `Eagle's Cry`, `See the Wind`

##### Basic

- `Carrion Call`, `Deadfall`, `Earth Meld`, `Embed the Cycle`, `Essence of Yew`, `Hands of Lirisa`, `Harawep's Bonds`, `Instinct`, `Senses of the Tiger`, `Stampede`, `Wolf Scent`

##### Intermediate

- `Blend`, `Claws of the Cougar`, `Devitalize`, `Devolve`, `Forestwalker's Boon`, `Grizzly Claws`, `Oath of the Firstborn`, `Plague of Scavengers`, `River in the Sky`, `Skein of Shadows`, `Swarm`, `Wisdom of the Pack`

##### Advanced

- `Awaken Forest`, `Bear Strength`, `Bloodthorns`, `Cheetah Swiftness`, `Curse of the Wilds`, `Memory of Nature`, `Syamelyo Kuniyo`

##### No preserved progression band

- `Electrogenesis`

#### Trader

DireLore pages found: `23`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `23`
- `Guild Leader spells`: `23`
- `Signature spells`: `10`

##### Intro

- `Fluoresce`, `Noumena`, `Trabe Chalice`

##### Basic

- `Blur`, `Crystal Dart`, `Finesse`, `Iridius Rod`, `Last Gift of Vithwok IV`, `Membrach's Greed`, `Nonchalance`, `Turmar Illumination`

##### Intermediate

- `Arbiter's Stylus`, `Avren Aevareae`, `Platinum Hands of Kertigen`, `Regalia`

##### Advanced

- `Enrichment`, `Mask of the Moons`, `Starcrash`, `Stellar Collector`

##### No preserved progression band

- `Avtalia Array`, `Bespoke Regalia`, `Elision`, `Resumption`

#### Warrior Mage

DireLore pages found: `56`

Acquisition-adjacent tags preserved:

- `Scroll spells`: `55`
- `Guild Leader spells`: `54`
- `Signature spells`: `24`

##### Intro

- `Air Lash`, `Ethereal Shield`, `Fire Shards`, `Gar Zeng`, `Geyser`, `Stone Strike`

##### Basic

- `Aethrolysis`, `Air Bubble`, `Anther's Call`, `Arc Light`, `Gam Irnan`, `Ice Patch`, `Ignite`, `Mark of Arhat`, `Substratum`, `Sure Footing`, `Swirling Winds`, `Tailwind`, `Ward Break`, `Zephyr`

##### Intermediate

- `Chain Lightning`, `Dragon's Breath`, `Electrostatic Eddy`, `Ethereal Fissure`, `Fire Ball`, `Frost Scythe`, `Frostbite`, `Lightning Bolt`, `Magnetic Ballista`, `Paeldryth's Wrath`, `Rising Mists`, `Thunderclap`, `Tingle`, `Tremor`, `Veil of Ice`, `Vertigo`, `Y'ntrel Sechra`

##### Advanced

- `Aegis of Granite`, `Aether Cloak`, `Blufmor Garaen`, `Fire Rain`, `Fortress of Ice`, `Grounding Field`, `Mantle of Flame`, `Rimefang`, `Ring of Spears`, `Shockwave`

##### No preserved progression band

- `Elementalism`, `Expansive Infusions`, `Fiery Infusions`, `Flame Shockwave`, `Icy Infusions`, `Ignition Point`, `Quick Infusions`, `Reinforced Infusions`, `Shocking Infusions`

## URL / Fetch Notes

Some obvious spell-family slugs did not resolve cleanly through the fetch tool when requested as direct pages or straightforward category URLs:

- `Augmentation_spells`
- `Debilitation_spells`
- `Targeted_spells`
- `Utility_spells`
- `Warding_spells`

That did not block the survey, because the guild, mana-type, cyclic, and ritual pages already expose the majority of the structured spell data needed for mechanics work.

## Bottom Line

The `Spells` hub is mainly a router into category-backed spell tables.

For mechanics excavation, the highest-yield downstream pages are:

1. guild spell pages
2. mana-type category pages
3. `Cyclic spells`
4. `Ritual spells`

Those pages expose a large, structured spell corpus with effect summaries, prep/rank ranges, duration, slot pressure, spellbooks, and enough profession context to support mana-system analysis.
