# MT-505 Findings: Claude Sonnet 4.5 Capability Test for Stateful Descriptions

Single run only. No prompt iteration during execution. All 40 planned API calls completed successfully: 20 Pass 1 prose generations and 20 Pass 2 markup generations.

Run totals:
- Input tokens: 75,514
- Output tokens: 7,918
- Anthropic Claude Sonnet 4.5 pricing used for calculation: $3 / MTok input and $15 / MTok output
- Total run cost: $0.345312

Global mechanical summary:
- Pass 2 syntax was valid in all 20 rooms. Every emitted `$state(...)` fragment parsed cleanly.
- Per-group coverage was complete in all 20 rooms. No room missed a required state group.
- Default renders were clean across the set.
- The old merged-word failure did not recur when renders preserved the leading space inside fragment content.
- Remaining render problems were mostly grammatical integration problems at the insertion point, not whitespace stripping.

## mt505_landing_low_river_alley — A Narrow River-Side Alley

1. Pass 1 quality: Strong. The prose stays in a low-quarter urban alley, preserves the river-side labor district feel, and stays grounded in the provided smells, walls, dirt, and worn condition.
2. Fragment count and coverage: 10 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid `$state(name, content)` forms.
4. Whitespace: Default render is clean. Active renders avoid merged words, but some insertions are still clunky, such as `nearby docks mixed with the scent of cook-fires` and the invasion clause attaching as a bare tail.
5. Environment grounding: Mostly grounded. The only mild stretch is `ice clinging to the eaves`, which invents a more specific architectural detail than the room packet provides.
6. Time coherence: Good. Morning cook-fires, midday worker traffic, evening cheap stew, and quieter night all fit the alley's social environment.
7. Per-axis sensibility: Weather and invasion fragments fit the room type. Invasion stays atmospheric rather than replacing the alley with a battle scene.

## mt505_landing_low_dockside_street — Dockside Street, Saltway River

1. Pass 1 quality: Strong. The prose remains a working dock street with bollards, cobbles, warehouses, river sound, and dock traffic all preserved.
2. Fragment count and coverage: 13 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are well formed.
4. Whitespace: Default render is clean. Active renders read without merged words, but some are mechanically awkward, especially `nearby docks sharp and cold` and the warehouse night clause attaching directly to `storage`.
5. Environment grounding: Mostly grounded. `watchman's lamp` is an unsupported addition, and `supper fires from the warehouses` is more speculative than the room packet supports.
6. Time coherence: Good overall. Morning opening doors, midday dock stench, evening fires, and quieter night river sounds all fit the location.
7. Per-axis sensibility: Weather and invasion are sensible for a dock street. Season coverage is thin but acceptable through the moss fragment.

## mt505_landing_merchant_market_square — The Merchant Quarter Market Square

1. Pass 1 quality: Strong. The prose stays squarely in an urban market and uses the well, stalls, cobbles, bread, spices, and vendor calls effectively.
2. Fragment count and coverage: 12 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders generally read cleanly, though some time fragments still feel bolted on, such as `use as vendors arrive to set up their wares`.
5. Environment grounding: Mixed. Most fragments fit, but `potted herbs at the vegetable stands` is a specific invented prop set not licensed by the packet.
6. Time coherence: Strong. Morning setup, midday crowding, evening pack-down, and night emptiness are all appropriate to a market square.
7. Per-axis sensibility: Weather and invasion both fit. Invasion reduces commerce rather than turning the square into a combat vignette, which is appropriate.

## mt505_landing_merchant_shop_street — A Merchant Quarter Street

1. Pass 1 quality: Strong. The prose remains a clean merchant street with shops below and residences above, and it preserves the modest-prosperity tone.
2. Fragment count and coverage: 12 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders avoid merged words, but the main commerce sentence takes too many attachments and often reads mechanically.
5. Environment grounding: Mixed. `window boxes above` and `a baker's doorway` are unsupported specifics added on top of a generic merchant street packet.
6. Time coherence: Good. Opening shutters in the morning, busiest trade at midday, winding down in the evening, and sparse traffic at night all make sense.
7. Per-axis sensibility: Weather and invasion are appropriate. The main weakness is over-specific embellishment rather than wrong state choice.

## mt505_landing_high_avenue — A High Quarter Avenue

1. Pass 1 quality: Strong. The prose preserves the high-quarter avenue, manor walls, railings, quiet traffic, and elite maintenance level.
2. Fragment count and coverage: 12 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders are readable but several additions attach too directly to the preceding clause, especially the time and invasion tails on the traffic sentence.
5. Environment grounding: Mixed. The social tone fits, but `opening gates`, `private carriage`, `night watchman`, and `guarded` details add unsupported temporary actors and structures.
6. Time coherence: Good. The chosen time-of-day beats all fit an affluent district.
7. Per-axis sensibility: Weather fragments fit the open avenue. Invasion also fits conceptually, but it leans harder into temporary scene staging than the rest of the room allows.

## mt505_landing_high_lake_terrace — Lakeview Terrace

1. Pass 1 quality: Strong. The prose remains a terrace overlooking the lake and keeps the lake breeze, water sound, balustrade, and high-quarter backdrop intact.
2. Fragment count and coverage: 15 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders remain readable, but the extra morning, evening, and night fragments on the final sentence make some combinations feel over-stacked.
5. Environment grounding: Mostly grounded. The only softer spots are temporary human-presence additions like `early risers`, `couples and families`, and `anxious citizens`.
6. Time coherence: Strong. Dawn light, midday brilliance, evening color, and moonlit water all fit a lake overlook.
7. Per-axis sensibility: Weather, season, and invasion all fit the exposed terrace well. This is one of the stronger edge-of-city outputs.

## mt505_bramblefold_village_green — The Village Green

1. Pass 1 quality: Strong. The prose preserves the green, old oak, village paths, cottages, smoke, and distant sheep cleanly.
2. Fragment count and coverage: 17 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders avoid merged words, but stacked additions on the paths and chimneys sentences produce stiff composites.
5. Environment grounding: Mostly grounded. `children chasing one another` and meal-specific `porridge and baking bread` are temporary embellishments rather than stable room facts.
6. Time coherence: Good. Morning activity, midday lull, evening return from fields, and night stillness all fit hamlet life.
7. Per-axis sensibility: Weather and invasion are sensible for a village green. The invasion treatment stays atmospheric rather than cinematic.

## mt505_bramblefold_road — The Hamlet Road

1. Pass 1 quality: Strong. The road stays rural and grounded in earth, ruts, hedgerows, cottages, birdsong, and soil smell.
2. Fragment count and coverage: 11 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders are readable, though the birdsong time inserts remain somewhat tacked on.
5. Environment grounding: Good. No obvious environment mismatch appears here.
6. Time coherence: Good. Morning birdsong, evening settling quiet, and owl call at night all fit the road's rural surroundings.
7. Per-axis sensibility: Weather and invasion both fit. The invasion fragment as distant valley smoke is restrained and appropriate.

## mt505_bramblefold_smithy_threshold — Outside the Smithy

1. Pass 1 quality: Strong. The threshold remains a smithy exterior with packed earth, doorway smoke, hot-metal smell, and anvil noise.
2. Fragment count and coverage: 10 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders no longer merge words, but the time fragments still append to `anvil` a little abruptly.
5. Environment grounding: Good overall. The invasion fragment about hurried repairs is plausible for a smithy threshold.
6. Time coherence: Strong. Morning startup, midday peak forge heat, evening slowdown, and night silence all fit the smithy.
7. Per-axis sensibility: Weather and invasion both fit the room type well. This is one of the stronger utilitarian outputs.

## mt505_forest_canopy_path — A Path Beneath the Canopy

1. Pass 1 quality: Strong. The prose remains a dim forest path under canopy with moss, packed dirt, birdsong, pine, and earth.
2. Fragment count and coverage: 13 fragments. Coverage complete for season, time, and weather.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders are readable, though the double time treatment of both light and birdsong can make some combinations feel crowded.
5. Environment grounding: Good. Wildflowers, fallen leaves, filtered light, owl call, and damp path all fit the forest environment.
6. Time coherence: Strong. Morning filtering light, midday dapple, evening deep shadow, and limited night moonlight under canopy all make sense.
7. Per-axis sensibility: Weather fragments are appropriate to a forest path. No invasion group applies, and the room stays properly non-urban.

## mt505_plain_crossroads — A Crossroads on the Open Plain

1. Pass 1 quality: Strong. The prose stays on open grassland with a signpost, wide sky, wind, and distant tree line.
2. Fragment count and coverage: 12 fragments. Coverage complete for season, time, and weather.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders read cleanly enough, though combined sky fragments can feel formulaic rather than deeply integrated.
5. Environment grounding: Strong. The fragments stay inside open-plain weather and sky effects.
6. Time coherence: Strong. Dawn, midday brightness, evening color, and star-filled night all fit the crossroads.
7. Per-axis sensibility: Weather is fully appropriate here. This is one of the most stable wilderness outputs.

## mt505_mountain_switchback — A Mountain Switchback

1. Pass 1 quality: Strong. The prose preserves the steep trail, loose stone, exposed bedrock, wind, vista, and runoff wear.
2. Fragment count and coverage: 13 fragments. Coverage complete for season, time, and weather.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders remain readable, though the two separate rain fragments and some vista-time inserts make combinations feel busy.
5. Environment grounding: Good. The fragments stay within mountain weather, distance, wind, and surface conditions.
6. Time coherence: Good. Morning mist, midday clarity, evening shadow, and night valley lamps all fit the terrain.
7. Per-axis sensibility: Weather fragments are sensible for an exposed mountain trail. This room handles multi-axis variation well.

## mt505_castle_great_hall — The Great Hall of Caerwall Keep

1. Pass 1 quality: Strong. The prose remains a keep great hall and uses the ceiling, banners, table, hearth, and upper windows effectively.
2. Fragment count and coverage: 11 fragments. Coverage complete for season, time, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders are readable, but the time inserts on the table and windows clauses are noticeably bolted on.
5. Environment grounding: Mixed. The overall hall is correct, but `bread and ale`, `platters`, `trenchers`, `cups`, and `armed men` introduce temporary props and occupants that the packet does not license.
6. Time coherence: Good in sequence. Morning breaking fast, midday meal remains, evening supper, and night embers all fit the hall's daily cycle.
7. Per-axis sensibility: Season and invasion choices fit, but the output drifts toward staged scene-setting rather than stable room truth.

## mt505_castle_corridor — A Stone Corridor of the Keep

1. Pass 1 quality: Strong. The corridor stays interior, narrow, stone-built, cool, and duty-traveled.
2. Fragment count and coverage: 9 fragments. Coverage complete for season, time, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders avoid merged words, though some time inserts read like appended subordinate clauses without enough connective tissue.
5. Environment grounding: Mostly grounded. `torches` are supported by the room's torch-smoke sensory cue, and the windows are in the short description.
6. Time coherence: Strong. Early light, bright midday shafts, evening torch-lighting, and torchlit night all fit the corridor.
7. Per-axis sensibility: Season and invasion fragments are sensible. This is a solid interior result.

## mt505_guild_workshop — The Cartwright's Workshop

1. Pass 1 quality: Strong. The prose remains a functioning workshop and preserves benches, timber stock, tools, sawdust, and work paths.
2. Fragment count and coverage: 11 fragments. Coverage complete for season, time, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders are readable, but some inserts, especially the invasion clauses, make the last sentence overly heavy.
5. Environment grounding: Mixed. Most content fits well, but the `corner brazier` is an unsupported object addition.
6. Time coherence: Strong. Fresh first cuts in the morning, occupied benches at midday, cleanup in the evening, and cleared benches at night all make sense.
7. Per-axis sensibility: Season and invasion are sensible. The invasion fragments stay tied to labor disruption rather than generic battle noise.

## mt505_guild_conference — The Guild Conference Room

1. Pass 1 quality: Strong. The prose preserves the chamber, long table, chairs, records, timber floor, ink, and leather.
2. Fragment count and coverage: 10 fragments. Coverage complete for season, time, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders read fairly cleanly, though several time inserts still feel like afterthoughts on the chairs sentence.
5. Environment grounding: Mixed. `fresh parchment`, `scribes`, and `high window` are added specifics not present in the room packet.
6. Time coherence: Good. Arrivals in the morning, recent discussion at midday, close of business in the evening, and emptiness at night all fit the room.
7. Per-axis sensibility: Invasion is plausible as archival scrambling rather than combat, which is appropriate for this space.

## mt505_cave_entrance — The Mouth of the Roetcave

1. Pass 1 quality: Strong. The prose preserves the threshold character cleanly: narrow cleft, fading exterior light, cool air, and deeper darkness.
2. Fragment count and coverage: 9 fragments. Coverage complete for season, time, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders remain readable, though the time inserts attach directly to `beyond` and can feel abrupt.
5. Environment grounding: Strong. The fragments stay within a cave-mouth threshold where outside light and some exterior material can still plausibly appear.
6. Time coherence: Strong. Morning, midday, evening, and night light descriptions all make sense at an entrance rather than deep underground.
7. Per-axis sensibility: Season and invasion both fit the threshold well. This is a good boundary-case result.

## mt505_cave_passage_deep — A Passage Within the Roetcave

1. Pass 1 quality: Strong. The prose remains a deep cave passage with rock, uneven floor, drip, still air, and darkness all preserved.
2. Fragment count and coverage: 4 fragments. Coverage complete for the only applicable group, season.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active seasonal renders also read cleanly enough because the fragments attach to an existing sound clause rather than to a hard object boundary.
5. Environment grounding: Strong. No daylight, no surface weather, and no exterior life intrudes into the deep cave.
6. Time coherence: Not applicable beyond season. The seasonal modulation stays restrained and cave-appropriate.
7. Per-axis sensibility: This is the most disciplined cave output in the set. Seasonal effects are indirect and do not break underground grounding.

## mt505_temple_sanctuary — The Sanctuary of the Tide

1. Pass 1 quality: Strong. The prose preserves the sanctuary, clerestory light, carved walls, benches, altar, incense, and quiet well.
2. Fragment count and coverage: 12 fragments. Coverage complete for season, time, weather, and invasion.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders avoid merged words, but the time and weather inserts still read as appended phrases rather than fully integrated clauses.
5. Environment grounding: Mixed to weak. `fresh flowers`, `dried herbs`, `sanctuary lamps`, and the explicit kneeling worshippers are all extra ritual details not provided by the packet.
6. Time coherence: Mostly coherent. Morning, midday, evening, and night lighting all make sense, though the unsupported lamps weaken the night fragment.
7. Per-axis sensibility: Weather is handled better than in many interior rooms because the clerestory and roof context justify indirect outside effects. Invasion remains appropriately subdued.

## mt505_old_bridge_span — A Span of the Old Bridge

1. Pass 1 quality: Strong. The prose stays on the bridge, preserves the parapets, river sound, spray, wind, and crossing traffic, and keeps the directional urban context intact.
2. Fragment count and coverage: 11 fragments. Coverage complete for season, time, and weather.
3. Syntactic correctness: All fragments are valid.
4. Whitespace: Default render is clean. Active renders avoid merged words, but the river-sound sentence becomes awkward in time combinations like `The river sounds below its current loud in the quiet of early day`.
5. Environment grounding: Mostly grounded. The one notable strain is `careful footsteps on the white-dusted parapets`, which places traffic on the parapets rather than the span surface.
6. Time coherence: Good. Morning quiet, midday full sun, evening cooling wind, and darker river noise at night all fit the bridge.
7. Per-axis sensibility: Weather and season are appropriate for an exposed bridge span. This is a good edge-case result apart from a few wording choices.

## Verdict

Claude Sonnet 4.5 produced reliably grounded markup in broad strokes across the full environment set, and it was materially stronger on caves, wilderness, thresholds, bridges, and most working exteriors than the earlier small-sample Haiku run. Per-group coverage was fully consistent in this 20-room test: all 20 rooms covered every required state group, and all emitted fragments were syntactically valid. The main systematic weaknesses were not missing groups or broken `$state(...)` syntax but over-specific embellishment in social interiors and civic/religious spaces, plus active-state phrasing that was often grammatically awkward even when whitespace was preserved correctly. Output was not usable as-is for final shipping text because several rooms still invented temporary actors, props, or ritual details, and many active renders need tighter insertion-point control. Total API cost for the run was $0.345312.