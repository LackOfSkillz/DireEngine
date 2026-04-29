from __future__ import annotations


STATE_VOCABULARY = {
    "season": ["spring", "summer", "autumn", "winter"],
    "time": ["morning", "midday", "evening", "night"],
    "weather": ["rain", "snow", "fog"],
    "invasion": ["invasion"],
}


def _states(groups: list[str]) -> list[str]:
    states: list[str] = []
    for group in groups:
        states.extend(STATE_VOCABULARY[group])
    return states


LANDING_ZONE_CONTEXT = (
    "Landing — a river-trade city where the Saltway River meets the Great Lake to the south. "
    "Population mixed, late-medieval era, regional power center. The city is divided by long "
    "custom into three quarters: the low quarter near the docks (working class, mariners, dock "
    "laborers), the merchant quarter inland (shopkeepers, traders, craftspeople, modest "
    "prosperity), and the high quarter on the rises overlooking the lake (nobility, wealthy "
    "merchants, civic buildings). The city is known for fish, salt, and overland trade goods "
    "passing between the river network and the inland roads."
)

BRAMBLEFOLD_ZONE_CONTEXT = (
    "Bramblefold — a small farming hamlet two days' ride east of Landing. Population perhaps "
    "eighty souls, mostly farmers and a few artisans serving the local community. Late-medieval "
    "era. No walls, no garrison, just a green, a smithy, a tavern, and scattered cottages along "
    "an old packed-earth road."
)

WILDERNESS_ZONE_CONTEXT = (
    "The lands east of Landing — open country giving way to the Cresthorn Mountains in the far "
    "east. Untamed but not hostile. Late-medieval era. Roads are old trade routes between "
    "settlements; the wilderness between them is rolling plain, mixed forest, and rocky uplands."
)

CAERWALL_ZONE_CONTEXT = (
    "Caerwall Keep — a regional fortress of moderate size garrisoned by the local lord's "
    "household. Stone construction, late-medieval, functional rather than ornamental. Houses the "
    "lord's family, a small standing garrison, and various retainers."
)

GUILD_ZONE_CONTEXT = (
    "The Cartwright's Guild Hall — a working guild building in the merchant quarter of Landing. "
    "Two stories, stone ground floor and timber upper floor. Houses the guild's workshops, "
    "meeting rooms, and apprentice quarters. Active during business hours, mostly empty after "
    "dark."
)

CAVE_ZONE_CONTEXT = (
    "The Roetcave — a network of natural caves in the foothills of the Cresthorn Mountains, "
    "occasionally used by smugglers and local prospectors. The entrance is a narrow cleft in a "
    "rock wall; the passages within are unmaintained natural rock."
)

TEMPLE_ZONE_CONTEXT = (
    "The Temple of the Tide — a stone temple in the high quarter of Landing dedicated to the "
    "local water god. Mid-sized, stone construction, with high clerestory windows that admit "
    "light throughout the day. The sanctuary is the temple's central public space."
)

BRIDGE_ZONE_CONTEXT = (
    "The Old Bridge — the oldest stone bridge across the Saltway River in central Landing, built "
    "generations ago. Three spans, low parapets, fitted stone, wide enough for two carts to pass. "
    "Connects the merchant quarter on the north bank to the low quarter on the south."
)


def _room(
    room_id: str,
    name: str,
    environment: str,
    tags: dict,
    short_desc: str,
    zone_context: str,
    applicable_state_groups: list[str],
) -> dict:
    return {
        "room_id": room_id,
        "name": name,
        "environment": environment,
        "tags": tags,
        "short_desc": short_desc,
        "zone_context": zone_context,
        "applicable_state_groups": applicable_state_groups,
        "applicable_states": _states(applicable_state_groups),
    }


TEST_ROOMS = [
    _room(
        "mt505_landing_low_river_alley",
        "A Narrow River-Side Alley",
        "urban",
        {
            "structure": "alley",
            "function": None,
            "named_feature": None,
            "condition": "worn",
            "custom": [],
            "atmosphere": {
                "materials": ["packed-dirt", "rough-stone-walls"],
                "sensory": ["river-smell", "fish-smell"],
                "social_character": ["working-class", "labourers"],
                "surroundings": ["river-nearby", "warehouses-nearby"],
                "upkeep": "shabby",
            },
        },
        "A narrow alley in the low quarter, packed dirt underfoot, river smell heavy in the air.",
        LANDING_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_landing_low_dockside_street",
        "Dockside Street, Saltway River",
        "urban",
        {
            "structure": "street",
            "function": None,
            "named_feature": "dock-bollards",
            "condition": "worn",
            "custom": [],
            "atmosphere": {
                "materials": ["fitted-cobbles", "timber-bollards"],
                "sensory": ["salt-smell", "fish-smell", "river-water-sound"],
                "social_character": ["dock-workers", "mariners"],
                "surroundings": ["docks-immediate", "warehouses-nearby"],
                "upkeep": "well-used",
            },
        },
        "A working dockside street running along the Saltway River, fitted cobbles, dock bollards along the water side.",
        LANDING_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_landing_merchant_market_square",
        "The Merchant Quarter Market Square",
        "urban",
        {
            "structure": "square",
            "function": "market",
            "named_feature": "well",
            "condition": "well-maintained",
            "custom": [],
            "atmosphere": {
                "materials": ["fitted-cobbles", "timber-stalls"],
                "sensory": ["bread-smell", "spice-smell", "vendor-calls"],
                "social_character": ["traders", "shoppers", "mixed-class"],
                "surroundings": ["shops-on-all-sides"],
                "upkeep": "well-maintained",
            },
        },
        "An open market square in the merchant quarter, fitted cobbles, public well at center, market stalls around the edges.",
        LANDING_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_landing_merchant_shop_street",
        "A Merchant Quarter Street",
        "urban",
        {
            "structure": "street",
            "function": None,
            "named_feature": None,
            "condition": "well-maintained",
            "custom": [],
            "atmosphere": {
                "materials": ["fitted-cobbles", "timber-and-stone-buildings"],
                "sensory": ["mild-trade-bustle", "hanging-sign-creak"],
                "social_character": ["merchants", "shoppers", "modest-prosperity"],
                "surroundings": ["shops-ground-floor", "residential-above"],
                "upkeep": "well-maintained",
            },
        },
        "A clean, well-kept street in the merchant quarter, shops on the ground floor, residences above, hanging trade signs.",
        LANDING_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_landing_high_avenue",
        "A High Quarter Avenue",
        "urban",
        {
            "structure": "avenue",
            "function": None,
            "named_feature": None,
            "condition": "pristine",
            "custom": [],
            "atmosphere": {
                "materials": ["large-fitted-stones", "iron-railings"],
                "sensory": ["quiet", "occasional-coach-wheels"],
                "social_character": ["nobility", "wealthy-merchants", "household-servants"],
                "surroundings": ["manor-walls", "private-gardens-glimpsed"],
                "upkeep": "pristine",
            },
        },
        "A broad, quiet avenue in the high quarter, large fitted stones, iron railings, manor walls hiding private gardens.",
        LANDING_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_landing_high_lake_terrace",
        "Lakeview Terrace",
        "urban",
        {
            "structure": "terrace",
            "function": "viewpoint",
            "named_feature": "stone-balustrade",
            "condition": "pristine",
            "custom": [],
            "atmosphere": {
                "materials": ["white-fitted-stone", "carved-balustrade"],
                "sensory": ["lake-breeze", "lake-water-sound", "wide-vista"],
                "social_character": ["nobility", "promenading-citizens"],
                "surroundings": ["lake-view-south", "high-quarter-behind"],
                "upkeep": "pristine",
            },
        },
        "A wide stone terrace overlooking the Great Lake to the south, carved balustrade along the water side, white fitted stone underfoot.",
        LANDING_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_bramblefold_village_green",
        "The Village Green",
        "urban",
        {
            "structure": "green",
            "function": "common-pasture",
            "named_feature": "old-oak",
            "condition": "well-used",
            "custom": [],
            "atmosphere": {
                "materials": ["packed-grass", "trodden-earth-paths"],
                "sensory": ["rural-quiet", "distant-sheep", "woodsmoke"],
                "social_character": ["villagers", "farmers"],
                "surroundings": ["cottages-around-green", "fields-beyond"],
                "upkeep": "well-used",
            },
        },
        "Bramblefold's common green, an old oak at one corner, cottages around the edges, farm fields stretching beyond.",
        BRAMBLEFOLD_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_bramblefold_road",
        "The Hamlet Road",
        "urban",
        {
            "structure": "road",
            "function": None,
            "named_feature": None,
            "condition": "well-used",
            "custom": [],
            "atmosphere": {
                "materials": ["packed-earth", "wagon-ruts", "hedgerow-borders"],
                "sensory": ["rural-quiet", "birdsong-distant", "earth-smell"],
                "social_character": ["farmers", "occasional-travelers"],
                "surroundings": ["fields-and-hedgerows", "scattered-cottages"],
                "upkeep": "well-used",
            },
        },
        "A packed-earth road through Bramblefold, wagon ruts, hedgerow borders, scattered cottages along the way.",
        BRAMBLEFOLD_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_bramblefold_smithy_threshold",
        "Outside the Smithy",
        "urban",
        {
            "structure": "threshold",
            "function": "smithy-exterior",
            "named_feature": "anvil-sound",
            "condition": "well-used",
            "custom": [],
            "atmosphere": {
                "materials": ["packed-earth", "stone-foundation-of-smithy"],
                "sensory": ["smoke-smell", "anvil-clang", "hot-metal-smell"],
                "social_character": ["smith-at-work", "occasional-customer"],
                "surroundings": ["smithy-immediate", "village-beyond"],
                "upkeep": "working-well-used",
            },
        },
        "The packed-earth area outside Bramblefold's smithy, smoke and anvil-sound from within, hot-metal smell on the air.",
        BRAMBLEFOLD_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_forest_canopy_path",
        "A Path Beneath the Canopy",
        "wilderness",
        {
            "structure": "path",
            "function": None,
            "named_feature": None,
            "condition": "natural",
            "custom": [],
            "atmosphere": {
                "materials": ["forest-floor", "dirt-path", "moss-edges"],
                "sensory": ["forest-quiet", "birdsong", "pine-smell", "earth-smell"],
                "social_character": [],
                "surroundings": ["dense-forest-all-sides", "ancient-trees"],
                "upkeep": "natural",
            },
        },
        "A dirt path through dense forest, ancient trees on all sides, dim under heavy canopy.",
        WILDERNESS_ZONE_CONTEXT,
        ["season", "time", "weather"],
    ),
    _room(
        "mt505_plain_crossroads",
        "A Crossroads on the Open Plain",
        "wilderness",
        {
            "structure": "crossroads",
            "function": None,
            "named_feature": "weathered-signpost",
            "condition": "weathered",
            "custom": [],
            "atmosphere": {
                "materials": ["packed-earth-roads", "grass"],
                "sensory": ["wide-sky", "wind", "grass-rustling"],
                "social_character": [],
                "surroundings": ["open-grassland-all-directions", "distant-treeline"],
                "upkeep": "natural-weathered",
            },
        },
        "A simple crossroads on open grassland, weathered signpost at center, distant tree line on the horizon.",
        WILDERNESS_ZONE_CONTEXT,
        ["season", "time", "weather"],
    ),
    _room(
        "mt505_mountain_switchback",
        "A Mountain Switchback",
        "wilderness",
        {
            "structure": "trail",
            "function": None,
            "named_feature": None,
            "condition": "weathered",
            "custom": [],
            "atmosphere": {
                "materials": ["loose-stone", "exposed-bedrock", "dirt-with-roots"],
                "sensory": ["thin-air", "wind", "stone-and-earth-smell", "wide-vista"],
                "social_character": [],
                "surroundings": ["steep-slope-uphill", "open-drop-downhill", "distant-peaks"],
                "upkeep": "natural-weathered",
            },
        },
        "A switchback trail climbing through the Cresthorn foothills, loose stone and exposed bedrock, wide vista of the lower country.",
        WILDERNESS_ZONE_CONTEXT,
        ["season", "time", "weather"],
    ),
    _room(
        "mt505_castle_great_hall",
        "The Great Hall of Caerwall Keep",
        "interior",
        {
            "structure": "hall",
            "function": "great-hall",
            "named_feature": "great-hearth",
            "condition": "well-maintained",
            "custom": [],
            "atmosphere": {
                "materials": ["fitted-stone-walls", "timber-beams", "stone-flagged-floor"],
                "sensory": ["echoing-space", "hearth-smell-when-lit", "occasional-household-sound"],
                "social_character": ["lord's-household", "retainers", "occasional-visitor"],
                "surroundings": ["banners-on-walls", "long-table-center", "high-windows"],
                "upkeep": "well-maintained",
            },
        },
        "The great hall of the keep, vaulted timber ceiling, banners on stone walls, long table down the center, great hearth at the far end.",
        CAERWALL_ZONE_CONTEXT,
        ["season", "time", "invasion"],
    ),
    _room(
        "mt505_castle_corridor",
        "A Stone Corridor of the Keep",
        "interior",
        {
            "structure": "corridor",
            "function": None,
            "named_feature": None,
            "condition": "well-maintained",
            "custom": [],
            "atmosphere": {
                "materials": ["fitted-stone-walls", "stone-flagged-floor"],
                "sensory": ["cool-air", "echoing-footsteps", "torch-smoke-when-lit"],
                "social_character": ["servants-passing", "occasional-guard"],
                "surroundings": ["doors-to-side-rooms", "narrow-windows"],
                "upkeep": "well-maintained",
            },
        },
        "A narrow stone corridor in the keep, fitted stone walls and floor, doors to side rooms, narrow windows in the outer wall.",
        CAERWALL_ZONE_CONTEXT,
        ["season", "time", "invasion"],
    ),
    _room(
        "mt505_guild_workshop",
        "The Cartwright's Workshop",
        "interior",
        {
            "structure": "workshop",
            "function": "cartwright-workshop",
            "named_feature": "workbenches",
            "condition": "well-used",
            "custom": [],
            "atmosphere": {
                "materials": ["timber-floors-with-sawdust", "stone-walls", "timber-workbenches"],
                "sensory": ["wood-smell", "sawdust-smell", "tool-sounds-when-active", "varnish-smell"],
                "social_character": ["journeymen-at-work", "apprentices"],
                "surroundings": ["workbenches-along-walls", "tools-on-racks", "raw-timber-stock"],
                "upkeep": "well-used-organized",
            },
        },
        "The Cartwright's Guild workshop, sawdust on the timber floor, workbenches along the walls, tools on racks, raw timber stock at one end.",
        GUILD_ZONE_CONTEXT,
        ["season", "time", "invasion"],
    ),
    _room(
        "mt505_guild_conference",
        "The Guild Conference Room",
        "interior",
        {
            "structure": "chamber",
            "function": "meeting-room",
            "named_feature": "long-table",
            "condition": "well-maintained",
            "custom": [],
            "atmosphere": {
                "materials": ["timber-floor", "wood-paneled-walls", "long-oak-table"],
                "sensory": ["ink-smell-faint", "leather-binding-smell", "muffled-quiet"],
                "social_character": ["guild-officers-when-meeting"],
                "surroundings": ["chairs-around-table", "shelved-records-along-one-wall"],
                "upkeep": "well-maintained",
            },
        },
        "The guild's conference room, long oak table at the center, chairs around it, shelved records along one wall.",
        GUILD_ZONE_CONTEXT,
        ["season", "time", "invasion"],
    ),
    _room(
        "mt505_cave_entrance",
        "The Mouth of the Roetcave",
        "threshold",
        {
            "structure": "threshold",
            "function": "cave-entrance",
            "named_feature": "narrow-cleft",
            "condition": "natural",
            "custom": [],
            "atmosphere": {
                "materials": ["rough-rock-walls", "uneven-stone-floor", "outside-light-entering"],
                "sensory": ["cool-cave-air", "stone-and-earth-smell", "exterior-sounds-faint"],
                "social_character": [],
                "surroundings": ["wilderness-immediately-outside", "darkness-deeper-in"],
                "upkeep": "natural",
            },
        },
        "The narrow cleft entrance to the Roetcave, exterior light fading as the passage deepens, cool cave air, exterior sounds growing faint.",
        CAVE_ZONE_CONTEXT,
        ["season", "time", "invasion"],
    ),
    _room(
        "mt505_cave_passage_deep",
        "A Passage Within the Roetcave",
        "cave",
        {
            "structure": "passage",
            "function": None,
            "named_feature": None,
            "condition": "natural",
            "custom": [],
            "atmosphere": {
                "materials": ["rough-rock-walls", "uneven-stone-floor"],
                "sensory": ["cool-still-air", "drip-of-distant-water", "deep-quiet"],
                "social_character": [],
                "surroundings": ["narrow-walls-close", "darkness-ahead"],
                "upkeep": "natural",
            },
        },
        "A natural passage deep within the Roetcave, rough rock walls close on both sides, the distant drip of water somewhere ahead.",
        CAVE_ZONE_CONTEXT,
        ["season"],
    ),
    _room(
        "mt505_temple_sanctuary",
        "The Sanctuary of the Tide",
        "temple",
        {
            "structure": "sanctuary",
            "function": "worship-space",
            "named_feature": "altar",
            "condition": "pristine",
            "custom": [],
            "atmosphere": {
                "materials": ["polished-stone-floor", "carved-stone-walls", "high-clerestory-windows"],
                "sensory": ["incense", "echoing-quiet", "filtered-daylight-when-bright"],
                "social_character": ["worshippers-when-present", "clergy"],
                "surroundings": ["altar-at-far-end", "stone-benches-along-walls", "high-windows-above"],
                "upkeep": "pristine",
            },
        },
        "The temple sanctuary, polished stone floor, carved walls, altar at the far end, high clerestory windows admitting filtered light from above.",
        TEMPLE_ZONE_CONTEXT,
        ["season", "time", "weather", "invasion"],
    ),
    _room(
        "mt505_old_bridge_span",
        "A Span of the Old Bridge",
        "bridge",
        {
            "structure": "bridge-span",
            "function": "river-crossing",
            "named_feature": "stone-parapet",
            "condition": "weathered",
            "custom": [],
            "atmosphere": {
                "materials": ["fitted-stone", "carved-parapet"],
                "sensory": ["river-water-sound-below", "river-spray-faint", "wind-across-water", "river-smell"],
                "social_character": ["crossing-traffic", "mixed-class"],
                "surroundings": ["river-below", "merchant-quarter-north", "low-quarter-south"],
                "upkeep": "weathered-but-sound",
            },
        },
        "A central span of the Old Bridge, fitted stone with low carved parapets, the Saltway River sounding below.",
        BRIDGE_ZONE_CONTEXT,
        ["season", "time", "weather"],
    ),
]