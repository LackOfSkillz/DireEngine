# Direlore Race Research

This report is a direct read-only extraction from the local `direlore` PostgreSQL database on port `5432`.

## Database Notes

- Confirmed database: `direlore`
- Confirmed user: `postgres`
- Confirmed server: PostgreSQL 16.9
- The `public.canon_races` table is not the real source of truth by itself. It mostly acts as an index into crawler-derived content.
- The authoritative race lore currently lives in the crawl/entity tables, primarily:
  - `public.entities`
  - `public.sections`
  - `public.raw_pages`
  - `public.facts`
  - `public.page_metadata`
- Supporting race mechanics were also found in:
  - `https://elanthipedia.play.net/Language_command`
  - `https://elanthipedia.play.net/Dismantle_command`
  - `https://elanthipedia.play.net/Age`

## High-Level Findings

- Direlore currently exposes 11 DragonRealms player races:
  - Dwarves
  - Elotheans
  - Elves
  - Gnomes
  - Gor'Togs
  - Halflings
  - Humans
  - Kaldar
  - Prydaen
  - Rakash
  - S'Kra Mur
- The live Dragonsire race implementation now exposes 11 playable races in [world/races/definitions.py](c:/Users/gary/dragonsire/world/races/definitions.py).
- The DragonRealms-derived archetypes are now mapped into custom Dragonsire identities:
  - Gor'Tog -> Volgrin
  - S'Kra Mur -> Saurathi
  - Kaldar -> Valran
  - Elothean -> Aethari
  - Prydaen -> Felari
  - Rakash -> Lunari
- The current Dragonsire race model is also much simpler than the Direlore/DragonRealms source material.
  - Direlore race pages expose DR-style starting stats and TDP modifiers for 8 stats.
  - Dragonsire currently uses a 6-stat model and simplified learning/carry tuning.
  - Direlore also carries racial language/accent access, age-visibility behavior, and race-specific command flavor that Dragonsire does not yet model.

## Cross-Race Systems

### Languages And Accents

From `Language_command`:

| Accent / Tongue | Race |
| --- | --- |
| Common | all |
| Gamgweth | Human |
| Gerenshuge | Elothean |
| Gorbesh | Kaldar and Gnome |
| Haakish | Dwarf |
| Ilithic | Elf |
| Olvi | Halfling |
| Prydaenese | Prydaen |
| Rakash | Rakash |
| S'Kra | S'Kra Mur |
| Toggish | Gor'Tog |

This matters for implementation because race is not just passive stats. In the source data, race also gates available accents and racial tongues.

### Race-Gated Command Hooks

The crawl exposed clear race-gated branches on `Dismantle_command`:

| Command Variant | Requirement |
| --- | --- |
| `CHOMP` | Rakash |
| `CLAW` | Prydaen |
| `CRUSH` | Gor'Tog or Strength > 30 |
| `JUMP` | Gnome |
| `PRESS` | Elothean |
| `SLAM` | Kaldar |
| `STOMP` | Dwarf |
| `TINKER` | Gnome |

These are implementation-relevant because they show race-specific flavor can be embedded inside otherwise generic commands, not only in dedicated racial verbs.

### Visible Age / Look Behavior

The shared `Age` page contains player-visible aging labels and, for some races, a split between what the race sees and what outsiders see.

Important implementation notes:

- Humans are the baseline progression.
- Dwarves, Elotheans, Elves, Gnomes, Gor'Togs, and Kaldar mostly use "People See" progression bands.
- Halflings, Prydaen, Rakash, and S'Kra Mur have more race-flavored or outsider-distorted visible-age labels.
- Rakash is the most special case because it has separate outsider visibility in human form versus moonskin.

## Race Roster

## Dwarves

- Canon URL: `https://elanthipedia.play.net/Concept:Dwarves`
- Description:
  - Hard-headed, stubborn, durable, disciplined, and physically powerful.
  - Beard growth and beard ornamentation carry strong cultural status, including for females.
  - Closely associated with mountains, endurance, drink, and deep-earth identity.
- Character creation look:
  - Short, wide, heavily bearded, physically solid, unflinching, and powerful.
- Starting stats / TDP mods:
  - Strength `10 (0)`
  - Reflex `8 (+1)`
  - Agility `8 (+1)`
  - Charisma `10 (0)`
  - Discipline `12 (-1)`
  - Wisdom `10 (0)`
  - Intelligence `10 (0)`
  - Stamina `12 (-1)`
- Physical details:
  - Male height: `4.5` to `5.5` feet
  - Female height: `4.0` to `5.0` feet
  - Average lifespan: `400` years
  - Maximum lifespan: `500` years
  - Average gestation: `8.5` Elanthian months
- Visible age behavior from the shared `Age` page:
  - By about age `100`, a Dwarf already looks roughly like a Human in the mid-50s.
  - After that, visible aging slows sharply.
  - Labels progress through `child`, `young`, `adult`, `mature`, `patronly/matronly`, `distinguished`, `ancient`, `elder`, `archaic`.
- Commands:
  - The main race page did not expose a `Special Commands` heading.
  - The dedicated `Dwarf_Verbs` category page confirms these Dwarf command pages:
    - `Dip`
    - `Dismantle`
    - `Gobble`
    - `Grunt`
    - `Roar`
    - `Snap`
    - `Stare`
    - `Sweat`
    - `Twiddle`
- Other race-linked hooks:
  - `Dismantle STOMP` is Dwarf-gated.
- Materials:
  - Adamantia steel, Asharsh'dai, Darkstone, Dwalgim, Dwarven iron, Eldring, Knarn fur, Mikkhalbamar, Sungold, Svelae, Uthamar.

## Elotheans

- Canon URL: `https://elanthipedia.play.net/Elotheans`
- Description:
  - Knowledge-focused, hierarchical, logical, honor-bound, and strongly tied to Ilithi and Shard.
  - Often described by others as half-human or half-elven, a claim their own traditions reject.
  - Peace, scholarship, logic, structure, and religion all matter heavily.
- Character creation look:
  - Tall and thin, large-eyed, composed, controlled, and observant.
- Starting stats / TDP mods:
  - Strength `8 (+1)`
  - Reflex `12 (-1)`
  - Agility `10 (0)`
  - Charisma `10 (0)`
  - Discipline `10 (0)`
  - Wisdom `12 (-1)`
  - Intelligence `12 (-1)`
  - Stamina `6 (+2)`
- Physical details:
  - Language: `Gerenshuge`
  - Average lifespan: `250` years
  - Maximum lifespan: `350` years
- Visible age behavior from the shared `Age` page:
  - Mature slightly slower than Humans.
  - Visible aging slows after the physical prime.
  - Unlike Elves or Dwarves, senescence is still fully felt eventually.
  - Labels progress through `child`, `young`, `adult`, `in his prime`, `middle-aged`, `mature`, `venerable`, `elderly`, `aged`, `wizened`, `venerated`, `one of the Wise`, `archaic`.
- Commands:
  - `Bow`
  - `Eye`
  - `Gobble`
  - `Purr`
  - `Snap`
  - `Stare`
  - `Sweat`
  - `Twiddle`
- Other race-linked hooks:
  - `Dismantle PRESS` is Elothean-gated.
- Materials:
  - Anlora-avtoma, Elothean lace, Elothean silk, Fyearikil agani, Lotus jade, Lotusweave, Negerith, Sanguinai, Songsilk, Truegold.

## Elves

- Canon URL: `https://elanthipedia.play.net/Concept:Elves`
- Description:
  - Aloof, clever, graceful, refined, mischievous, and strongly nature-aligned.
  - Older Elves are noted as still carrying friction with Humans over historical conflicts.
  - Long-range planners with strong cultural refinement.
- Character creation look:
  - Slightly taller than Humans, willowy, graceful, bright-eyed, refined, and ageless in presentation.
- Starting stats / TDP mods:
  - Strength `8 (+1)`
  - Reflex `12 (-1)`
  - Agility `12 (-1)`
  - Charisma `12 (-1)`
  - Discipline `8 (+1)`
  - Wisdom `10 (0)`
  - Intelligence `10 (0)`
  - Stamina `8 (+1)`
- Physical details:
  - Language: `Ilithic`
  - Male height: `6.0` to `7.0` feet
  - Female height: `5.5` to `6.5` feet
  - Average lifespan: `400` years
  - Maximum lifespan: `500` years
  - Average gestation: `8` Elanthian months
  - Reproduction note: very difficult fertility and no half-elves in the classic DR framing; children of mixed Elf/non-Elf pairings are born as one full race or the other.
- Visible age behavior from the shared `Age` page:
  - Same lifespan as Dwarves, but appear much younger.
  - Not sexually mature until their 40s.
  - Outsiders continue to read many Elves as younger than they are.
  - Self labels run through `child`, `young`, `adult`, `mature`, `patronly/matronly`, `distinguished`, `ancient`, `elder`, `archaic`.
  - Outsider labels lag behind and stay as `young`, then `adult`, then `in his prime`, then `mature` for very long spans.
- Commands:
  - `Blush`
  - `Gobble`
  - `Snap`
  - `Stare`
  - `Sweat`
  - `Twiddle`
- The dedicated `Elf_Verbs` page confirms the same set.
- Materials:
  - Acenite, Elamiri pearl, Elamiri sapphire, Eluned's tear sapphire, Elven gold, Elven lace, Elven silver, Elven snowlace, Elven wool, Firecloud clay, Haizeebo, Heartname leather, Helei leather, Hiromin, Ilithi emerald, Ivory, Pozumshi, Rimestone, Riverlimb, Sana'ati, Shireli lace, Smoi leather, Teiro's Hate ruby, Tidal bloodstone.

## Gnomes

- Canon URL: `https://elanthipedia.play.net/Concept:Gnomes`
- Description:
  - Tiny, clever, nimble, manipulative rather than forceful, historically tied to the Gorbesh.
  - Described as inventive, quick, and problem-solving specialists.
- Character creation look:
  - Slightly shorter than Halflings in the source text, pointed ears, twitching fingers, energetic wit.
- Starting stats / TDP mods:
  - Strength `4 (+3)`
  - Reflex `14 (-2)`
  - Agility `12 (-1)`
  - Charisma `10 (0)`
  - Discipline `10 (0)`
  - Wisdom `10 (0)`
  - Intelligence `14 (-2)`
  - Stamina `6 (+2)`
- Physical details:
  - Language / accent family: `Gorbesh`
  - Long-lived relative to Humans, up to roughly `300` years from the shared `Age` page.
- Visible age behavior from the shared `Age` page:
  - Human-like senescence stretched across a much longer lifespan.
  - Labels progress through `child`, `young`, `adult`, `mature`, `patronly/matronly`, `distinguished`, `ancient`, `elder`, `archaic`.
- Commands:
  - The main Gnome race page does not expose a `Special Commands` heading.
  - The page instead points at `Gorbesh Verbs` via Points of Interest.
  - That page was not available as a populated crawl result in the current DB snapshot, so the full canonical Gnome verb list is unresolved from this dataset.
- Other race-linked hooks:
  - `Dismantle JUMP` is Gnome-gated.
  - `Dismantle TINKER` is Gnome-gated.
- Materials:
  - Albarian lace, Atulave, Electrum, Ice-veined leather, Icesilk, Ixaemite, Kuwinite, Misiumosette, Sianedra, Spiritwood, Sraxaec's blood onyx, Tomiek.

## Gor'Togs

- Canon URL: `https://elanthipedia.play.net/Gor%27tog`
- Description:
  - Massive, strong, durable, blunt, practical, and culturally self-reliant.
  - Commonly stereotyped as the physically strongest but intellectually weakest common race.
  - Source text explicitly pushes back on that stereotype by citing notable Gor'Togs.
- Character creation look:
  - Tall, dark green, hairless, massively built, steady, solid, and forthright.
- Starting stats / TDP mods:
  - Strength `16 (-3)`
  - Reflex `8 (+1)`
  - Agility `10 (0)`
  - Charisma `10 (0)`
  - Discipline `10 (0)`
  - Wisdom `6 (+2)`
  - Intelligence `6 (+2)`
  - Stamina `14 (-2)`
- Physical details:
  - Language / accent family: `Toggish`
  - Lifespan from the shared `Age` page: up to about `115` years.
- Visible age behavior from the shared `Age` page:
  - Fairly steady and linear development and decline.
  - Labels progress through `child`, `young`, `adult`, `in his prime`, `middle-aged`, `mature`, `venerable`, `elderly`, `aged`, `wizened`, `ancient`, `archaic`.
- Commands:
  - `Gobble`
  - `Snap`
  - `Stare`
  - `Sweat`
  - `Twiddle`
- Other race-linked hooks:
  - `Dismantle CRUSH` is Gor'Tog-gated, with an alternate strength-based path.
- Materials:
  - Kau leather, Khor'vela.

## Halflings

- Canon URL: `https://elanthipedia.play.net/Halflings`
- Description:
  - Curious, clever, funny, physically agile, sweet-toothed, and known for furry feet.
  - Their simple and playful demeanor is repeatedly contrasted with the fact that Halflings have also played serious historical roles.
- Character creation look:
  - Short, merry, sharp-eyed, confident, and bright.
- Starting stats / TDP mods:
  - Strength `6 (+2)`
  - Reflex `12 (-1)`
  - Agility `14 (-2)`
  - Charisma `10 (0)`
  - Discipline `8 (+1)`
  - Wisdom `8 (+1)`
  - Intelligence `10 (0)`
  - Stamina `12 (-1)`
- Physical details:
  - Physical trait fact: `furry feet`
  - Language / accent family: `Olvi`
  - Rough height note from race page: about `3` to `4` feet
  - Average lifespan: about `100` years, average closer to `75`
- Visible age behavior:
  - Halflings see themselves with distinct race-specific labels, while outsiders see more generic age buckets.
  - Self labels: `kneebiter`, `tartsnatcher`, `whippersnapper`, `daydreamer`, `hairyfoot`, `pipesmoker/longbraids`, `porchsitter`, `grayroot`, `grayhair`, `talespinner`, `naptaker`, `archaic`.
  - Outsider labels: `child`, `young`, `adult`, `in his prime`, `middle-aged`, `mature`, `venerable`, `elderly`, `aged`, `wizened`, `archaic`.
- Commands:
  - `Dip`
  - `Footbrush`
  - `Gobble`
  - `Grunt`
  - `Roar`
  - `Stare`
  - `Sweat`
  - `Twiddle`
- Materials:
  - Berrybomb bast, Candysatin, Heartstring lace, Indurium, Khor'vela, Smokewhorl.

## Humans

- Canon URL: `https://elanthipedia.play.net/Concept:Humans`
- Description:
  - The middle road race, neither naturally inclined nor disinclined toward anything.
  - Relatively short-lived but adaptable, fertile, numerous, and historically central to inter-species empire-building.
- Character creation look:
  - Moderate height, visually central among the playable races, with few extremes.
- Starting stats / TDP mods:
  - Strength `10 (0)`
  - Reflex `10 (0)`
  - Agility `10 (0)`
  - Charisma `10 (0)`
  - Discipline `10 (0)`
  - Wisdom `10 (0)`
  - Intelligence `10 (0)`
  - Stamina `10 (0)`
- Physical details:
  - Language / accent family: `Gamgweth`
  - Male height: `5.5` to `6.0` feet
  - Female height: `5.0` to `5.75` feet
  - Average lifespan: `75` years
  - Maximum lifespan: `100` years
  - Average gestation: `7` Elanthian months
  - Cross-race conception note includes Dwarf, Elf, Elothean, Gnome, Halfling, Human, Kaldar, and Rakash pairings in the source page.
- Visible age behavior:
  - Human norm is the baseline used by the shared `Age` page.
  - Labels progress through `child`, `young`, `adult`, `in his prime`, `middle-aged`, `mature`, `venerable`, `elderly`, `aged`, `wizened`, `ancient`, `archaic`.
- Commands:
  - `Gobble`
  - `Snap`
  - `Stare`
  - `Sweat`
  - `Twiddle`
- Materials:
  - Alerce, Alshabi stone, Belzune, Cloudstone, Erythraean, Heliotrope, Kiralan, Shadowbark, Shadowleaf, Telothian, Ulhari prism, Wildlace.

## Kaldar

- Canon URL: `https://elanthipedia.play.net/Concept:Kaldar`
- Description:
  - Physically identical to Gorbesh but culturally and politically separate.
  - Strong, hardy, battle-oriented, cold-loving, and openly dismissive of softness and over-civilization.
- Character creation look:
  - Tall, limber, human-like on a larger scale, but with a stalwart spirit and sardonic humor.
- Starting stats / TDP mods:
  - Strength `12 (-1)`
  - Reflex `10 (0)`
  - Agility `10 (0)`
  - Charisma `12 (-1)`
  - Discipline `10 (0)`
  - Wisdom `8 (+1)`
  - Intelligence `8 (+1)`
  - Stamina `10 (0)`
- Physical details:
  - Language / accent family: `Gorbesh`
  - Average lifespan: `100` years
  - Maximum lifespan: `135` years
- Visible age behavior from the shared `Age` page:
  - Slightly slower development than Humans, but otherwise the same shape of aging.
  - Labels progress through `child`, `young`, `adult`, `in his prime`, `middle-aged`, `mature`, `venerable`, `elderly`, `aged`, `wizened`, `ancient`, `archaic`.
- Commands:
  - `Gobble`
  - `Hail`
  - `Pose`
  - `Roar`
  - `Snap`
  - `Stare`
  - `Sweat`
  - `Twiddle`
- Other race-linked hooks:
  - `Dismantle SLAM` is Kaldar-gated.
- Materials:
  - Albarian lace, Anjisis, Ice-veined leather, Icesilk, Irinai, Misiumosette, Moen takibena, Ruazin wool, Sianedra, Spiritwood, Sraxaec's blood onyx, Syrin's heart, Windsteel.

## Prydaen

- Canon URL: `https://elanthipedia.play.net/Concept:Prydaen`
- Description:
  - Solitary, proud, self-confident, graceful, distracting, impulsive, and culturally organized around the clan-wheel metaphor.
  - Refugee history and post-diaspora social disruption are central to modern Prydaen identity.
- Character creation look:
  - Human-sized, short-furred, tuft-eared, tailed, clawed, beautiful, and visually predatory.
- Starting stats / TDP mods:
  - Strength `10 (0)`
  - Reflex `14 (-2)`
  - Agility `10 (0)`
  - Charisma `12 (-1)`
  - Discipline `8 (+1)`
  - Wisdom `6 (+2)`
  - Intelligence `10 (0)`
  - Stamina `10 (0)`
- Physical details:
  - Homeland fact: `the West`
  - Language: `Prydaenese`
  - Average lifespan: `75` years
  - Maximum lifespan: `100` years
- Visible age behavior:
  - Outsiders often struggle to estimate Prydaen age.
  - Self labels: `tail-chaser`, `mouse-catcher`, `moth-stalker`, `bird-hunter`, `hyena-stalker`, `wind-catcher`, `shadow-prowler`, `sun-lounger`, `scar-bearer`, `dream-stalker`, `ancient`, `archaic`.
  - Outsiders tend to compress Prydaen into `child`, `young`, then `elderly` for broad spans.
- Commands:
  - The main race page points to `Prydaen Verbs: Trills, Ears, Tails, and other things.`
  - That page was not present as a populated crawl result in the current DB snapshot.
  - The current snapshot therefore confirms Prydaen command flavor exists, but it does not fully expose the command list in extracted sections.
- Other race-linked hooks:
  - `Dismantle CLAW` is Prydaen-gated.
- Materials:
  - Blighted gold, Blue gold, Dawnfire steel, Eu's promise crystal, Kadepa, Marblesilk, Senci, Storyplait, Sundream citrine, Vreeland pearwood.

## Rakash

- Canon URL: `https://elanthipedia.play.net/Concept:Rakash`
- Description:
  - Pack-centered, reactive, adaptable, survival-focused, and moonskin-shifting under the full Katamba moon.
  - Human-looking much of the time, but not fully separable from their wild identity even outside moonskin.
- Character creation look:
  - Moderate height, visually shifting between human-like and wolf-human features, with tail and ears in the half-human description.
- Starting stats / TDP mods:
  - Strength `10 (0)`
  - Reflex `12 (-1)`
  - Agility `8 (+1)`
  - Charisma `10 (0)`
  - Discipline `12 (-1)`
  - Wisdom `8 (+1)`
  - Intelligence `6 (+2)`
  - Stamina `14 (-2)`
- Physical details:
  - Language / accent family: `Rakash`
  - Average lifespan: `70` years
  - Maximum lifespan: `90` years
  - Average gestation: `7` Elanthian months
- Visible age behavior:
  - The only playable race with a shorter natural lifespan than Humans.
  - Age visibility splits three ways: what Rakash see, what outsiders see in human form, and what outsiders see in moonskin.
  - Self labels: `cub`, `underdog`, `cub-herder`, `pack hunter`, `pack beta`, `pack alpha`, `den watcher`, `grizzled elder`, `pack historian`, `forerunner`, `ancient`, `archaic`.
  - Outsider reading in moonskin stays artificially young for much longer.
- Commands:
  - `Blush`
  - `Ear`
  - `Gobble`
  - `Growl`
  - `Howl`
  - `Meow`
  - `Purr`
  - `Snap`
  - `Stare`
  - `Sweat`
  - `Tail`
  - `Twiddle`
- Other race-linked hooks:
  - `Dismantle CHOMP` is Rakash-gated.
- Materials:
  - Alavern, Asini, Avene, Cinacs, Enaada, Enelne's eye, Howlite, Kazene, Senci, Siksrajan applewood, Tursa, Uzil, Zeltfish-bone.

## S'Kra Mur

- Canon URL: `https://elanthipedia.play.net/S%27kra_mur`
- Description:
  - Serpentine, scaly, tailed, physically dangerous, and socially shaped by honor and tail-length.
  - The source explicitly notes they are neither cold-blooded nor venomous.
- Character creation look:
  - Tall and lithe, cold-skinned, scaled, slit-pupiled, with a short tail and a hypnotic, faintly repulsive presence.
- Starting stats / TDP mods:
  - Strength `12 (-1)`
  - Reflex `12 (-1)`
  - Agility `10 (0)`
  - Charisma `10 (0)`
  - Discipline `10 (0)`
  - Wisdom `8 (+1)`
  - Intelligence `8 (+1)`
  - Stamina `10 (0)`
- Physical details:
  - Language: `S'Kra Mur`
  - Physical traits fact: `scales`, `tail`
  - Average lifespan: `75` years
  - Maximum lifespan: `100` years
- Visible age behavior:
  - Self labels follow a normal DR sequence.
  - Outsiders struggle to judge age and often continue seeing them as `young`, then later `elderly` for long spans.
- Commands:
  - `Bask`
  - `Blush`
  - `Chirr`
  - `Flirt`
  - `Hiss`
  - `Meow`
  - `Purr`
  - `Stare`
  - `Sweat`
  - `Tail`
  - `Twiddle`
- Materials:
  - Aganylosh'a, Asharsh'dai, Dhhresh, Dragonvein agate, Hekemhhg lazuli, Ithridu, Keismin, Khiynit, Kor'athi, Korograth hide, Musparan silk, Negnetha, Sandskin, Scalene, Tel'athi, Velakan linen, Velakan pearl.

## Crawl Gaps And Caveats

- `public.canon_races` currently has weak `description` values like `2` or `of concept "Halflings"`. Do not use those rows directly as production text.
- Several entity rows point at `Special:Browse` URLs instead of the actual canonical page URL.
  - Dwarves, Elves, Humans, and Rakash needed manual resolution to `Concept:*` pages.
- `Prydaen Verbs` and `Gorbesh Verbs` were referenced by race pages but did not exist as usable extracted pages in the current crawl snapshot.
  - This means the current DB definitely proves those pages exist conceptually, but not all of their command lists are recoverable from this snapshot.

## Implementation Implications For Dragonsire

- Add the missing playable races first:
  - Elothean
  - Prydaen
  - Rakash
- Keep a separate canonical DR race layer from the current simplified balance layer.
  - Dragonsire's 6-stat system is not a one-to-one match for DR's 8-stat race tables.
  - If you want faithful reproduction, store the DR values in a canonical source table first, then derive game-facing mappings from that.
- Race should likely own more than stats:
  - default language/accent access
  - visible-age descriptors
  - race-specific verbs
  - hidden race branches inside generic commands
  - physical-trait-driven appearance text
  - special-state systems such as Rakash moonskin

## Suggested Next Passes

- Crawl or import the missing verb pages referenced by Prydaen and Gnome/Kaldar sources.
- Build a canonical Dragonsire race data file that stores:
  - race description
  - character creation blurb
  - DR starting stats and TDP mods
  - lifespan and height data
  - visible age labels
  - languages and accents
  - command access list
  - race-specific command hooks
- Decide explicitly how DR's 8-stat tables map into Dragonsire's current 6-stat runtime model before implementing modifiers.