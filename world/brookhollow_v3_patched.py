
from evennia import create_object
from evennia.utils.search import search_object, search_tag

ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
CHAR_TYPECLASS = "typeclasses.npcs.NPC"
OBJ_TYPECLASS = "typeclasses.objects.Object"

TOWN_TAG = ("brookhollow_v3", "build")
DIR_ALIASES = {
    "north": ["n"],
    "south": ["s"],
    "east": ["e"],
    "west": ["w"],
    "northeast": ["ne"],
    "northwest": ["nw"],
    "southeast": ["se"],
    "southwest": ["sw"],
    "up": ["u"],
    "down": ["d"],
    "inside": ["in"],
    "outside": ["out"],
}

def cleanup_old_build():
    old = list(search_tag(TOWN_TAG[0], category=TOWN_TAG[1]))
    for obj in old:
        try:
            obj.delete()
        except Exception:
            pass

def make_room(key, desc, district, street_name=None, segment_index=None, surface=None, patrol_zone=None, tags=None):
    room_tags = tags or []
    room = create_object(
        ROOM_TYPECLASS,
        key=key,
        attributes=[
            ("desc", desc),
            ("district", district),
            ("street_name", street_name or key),
            ("segment_index", segment_index),
            ("surface", surface),
            ("patrol_zone", patrol_zone or district),
            ("room_tags", room_tags),
            ("is_shop", "shop" in room_tags),
            ("alert_level", 0),
        ],
    )
    room.tags.add(*TOWN_TAG)
    return room

def make_exit(src, direction, dest, reverse_direction, secret=False):
    existing = [obj for obj in search_object(direction) if getattr(obj, "location", None) == src]
    if not existing:
        ex = create_object(
            EXIT_TYPECLASS,
            key=direction,
            aliases=DIR_ALIASES.get(direction, []),
            location=src,
            destination=dest,
            locks="view:false();traverse:all()" if secret else None,
            attributes=[("secret", secret), ("hidden_exit", secret)],
        )
        ex.tags.add(*TOWN_TAG)
    existing_rev = [obj for obj in search_object(reverse_direction) if getattr(obj, "location", None) == dest]
    if not existing_rev:
        ex2 = create_object(
            EXIT_TYPECLASS,
            key=reverse_direction,
            aliases=DIR_ALIASES.get(reverse_direction, []),
            location=dest,
            destination=src,
            locks="view:false();traverse:all()" if secret else None,
            attributes=[("secret", secret), ("hidden_exit", secret)],
        )
        ex2.tags.add(*TOWN_TAG)

def make_secret_exit(src, direction, dest, reverse_direction):
    make_exit(src, direction, dest, reverse_direction, secret=True)

def make_npc(key, location, desc, role, wander=False, wander_zone=None, patrol_route=None):
    is_shopkeeper = bool(location and hasattr(location, "is_shop") and location.is_shop())
    npc = create_object(
        CHAR_TYPECLASS,
        key=key,
        location=location,
        attributes=[
            ("desc", desc),
            ("role", role),
            ("wander", wander),
            ("wander_zone", wander_zone),
            ("patrol_route", patrol_route or []),
            ("is_shopkeeper", is_shopkeeper),
        ],
    )
    npc.tags.add(*TOWN_TAG)
    return npc

def make_item(key, location, desc, category, value=0, shop_stock=False):
    obj = create_object(
        OBJ_TYPECLASS,
        key=key,
        location=location,
        attributes=[
            ("desc", desc),
            ("category", category),
            ("value", value),
            ("shop_stock", shop_stock),
            ("stealable", category != "fixture"),
        ],
    )
    obj.tags.add(*TOWN_TAG)
    return obj


def stock_shopkeepers():
    for room in search_tag(TOWN_TAG[0], category=TOWN_TAG[1]):
        if not getattr(getattr(room, "db", None), "is_shop", False):
            continue
        shopkeepers = [obj for obj in room.contents if getattr(getattr(obj, "db", None), "is_shopkeeper", False)]
        if not shopkeepers:
            continue
        shopkeeper = shopkeepers[0]
        for item in list(room.contents):
            if item == shopkeeper or getattr(item, "destination", None):
                continue
            if not getattr(getattr(item, "db", None), "shop_stock", False):
                continue
            item.move_to(shopkeeper, quiet=True, move_type="stock")

def make_road(name, count, district, surface, desc_template, tags=None):
    segments = []
    for i in range(1, count + 1):
        desc = desc_template.format(i=i)
        room = make_room(
            key=name,
            desc=desc,
            district=district,
            street_name=name,
            segment_index=i,
            surface=surface,
            patrol_zone=district,
            tags=(tags or []) + ["road"],
        )
        segments.append(room)
    return segments

cleanup_old_build()

roads = {}

# CENTRAL / COBBLED DISTRICT
roads["Market Way"] = make_road(
    "Market Way", 8, "center", "cobbles",
    "This segment of Market Way is paved in old cobbles polished by boots, carts, and hooves. Segment {i} sits among the liveliest trade in Brookhollow, where calls from merchants overlap under painted signs and hanging lanterns.",
    ["market", "busy"],
)
roads["Brook Street"] = make_road(
    "Brook Street", 6, "center", "cobbles",
    "Brook Street runs straighter than most roads in town, its cobbles neatly set and its shopfronts orderly. Segment {i} carries a little more civility than noise, though trade still hums close by.",
    ["central"],
)
roads["Hall Lane"] = make_road(
    "Hall Lane", 4, "center", "cobbles",
    "Hall Lane bends toward the civic buildings on clean stone, with trimmed hedges, notices, and polished doorways lending segment {i} an official air.",
    ["civic"],
)
roads["Bank Lane"] = make_road(
    "Bank Lane", 4, "center", "cobbles",
    "Bank Lane is a shorter, broader lane where the stonework is cleaner and guards linger more often. Segment {i} feels watched without ever becoming truly tense.",
    ["bank"],
)
roads["Flower Row"] = make_road(
    "Flower Row", 3, "center", "cobbles",
    "Flower Row is bright with ribbons, potted herbs, and cut stems gathered in buckets. Even segment {i} carries a faint green dampness and sweet perfume on the air.",
    ["flowers"],
)
roads["Lantern Row"] = make_road(
    "Lantern Row", 3, "center", "cobbles",
    "Lantern Row keeps iron hooks and bracketed lamps over the street, making segment {i} feel safer after dusk than most of Brookhollow.",
    ["central"],
)

town_square = make_room(
    "Town Square",
    "The cobbled heart of Brookhollow opens around a worn stone well ringed by benches, handbills, and flower carts. Roads radiate outward in all directions, and almost every errand in town seems to begin or end here.",
    "center",
    street_name="Town Square",
    surface="cobbles",
    tags=["hub", "civic"],
)
wellside_bench = make_room(
    "Wellside Bench",
    "A shallow rise and a ring of benches beside the old well give waiting folk a place to sit, gossip, and watch the town move through the square below.",
    "center",
    street_name="Town Square",
    surface="cobbles",
    tags=["overlook"],
)

# RESIDENTIAL / OUTSKIRTS
roads["Hearth Lane"] = make_road(
    "Hearth Lane", 10, "residential", "packed earth",
    "This stretch of Hearth Lane winds between fences, herb plots, and low-roofed cottages. Segment {i} feels lived in rather than busy, with chimney smoke and turned soil softening the air.",
    ["residential", "homes"],
)
roads["Willow Walk"] = make_road(
    "Willow Walk", 8, "residential", "packed earth",
    "Willow Walk follows a gentler curve through modest homes and hanging garden boxes. Segment {i} is quieter than the town center, broken only by dogs, distant chickens, and household voices.",
    ["residential"],
)
roads["South Hedge Road"] = make_road(
    "South Hedge Road", 8, "residential", "packed earth",
    "South Hedge Road runs along clipped hedges and back fences where the town thins toward fields. Segment {i} is wide enough for carts but still informal underfoot.",
    ["residential", "edge"],
)
roads["West Field Road"] = make_road(
    "West Field Road", 8, "residential", "packed earth",
    "West Field Road leads toward the meadows and little crofts beyond town. Segment {i} carries the smell of grass, stable hay, and open weather more than smoke.",
    ["residential", "edge"],
)
roads["Garden Path"] = make_road(
    "Garden Path", 6, "residential", "packed earth",
    "Garden Path is narrower than the main roads, threading between trellises, rain barrels, and tidy little vegetable patches. Segment {i} feels almost private.",
    ["residential", "sidepath"],
)

# WAREHOUSE / TEAMSTER DISTRICT
roads["Warehouse Row"] = make_road(
    "Warehouse Row", 8, "warehouse", "packed earth",
    "Warehouse Row is broad and rough with tamped dirt, wheel ruts, and scattered straw. Segment {i} sits between tall timber storehouses, rope coils, and the hard rhythm of work.",
    ["warehouse", "labor"],
)
roads["Storeyard Lane"] = make_road(
    "Storeyard Lane", 6, "warehouse", "packed earth",
    "Storeyard Lane threads around loading bays, stacked crates, and open yard space. Segment {i} smells of grain, dust, and tarred rope.",
    ["warehouse"],
)
roads["Cart Yard Road"] = make_road(
    "Cart Yard Road", 6, "warehouse", "packed earth",
    "Cart Yard Road is practical rather than pretty, worn by axle weight and teamsters' boots. Segment {i} is lined by hitching rails, sheds, and work wagons.",
    ["warehouse", "transport"],
)

# LOW QUARTER / THIEF DISTRICT
roads["Crooked Alley"] = make_road(
    "Crooked Alley", 8, "low", "packed earth",
    "Crooked Alley twists between patched walls, leaning stoops, and hanging laundry. Segment {i} is narrow enough that a cautious person could vanish into a doorway or shadow quickly.",
    ["low", "shadowy"],
)
roads["Ratline Lane"] = make_road(
    "Ratline Lane", 6, "low", "packed earth",
    "Ratline Lane is muddier and meaner underfoot, lined by back steps, stacked barrels, and half-maintained doors. Segment {i} seems to keep its own secrets.",
    ["low", "shadowy"],
)
roads["Whisper Lane"] = make_road(
    "Whisper Lane", 6, "low", "packed earth",
    "Whisper Lane carries sound strangely between close walls and sagging eaves. Segment {i} feels like the sort of place where people notice strangers but pretend not to.",
    ["low", "thief"],
)

# BUILDINGS / INTERIORS
banking_hall = make_room("Stone Bank", "A sturdy stone banking hall with polished counters, iron grilles, and a guarded calm. Ink, wax, and coin lend the room an air of tidy seriousness.", "center", street_name="Bank Lane", surface="stone floor", tags=["bank", "interior"])
bank_upper = make_room("Stone Bank Upper Office", "Ledgers, lockboxes, and narrow desks crowd the upper office above the bank. From here, a careful clerk could watch both the forecourt and the square.", "center", street_name="Bank Lane", surface="planks", tags=["bank", "interior"])
bank_vault = make_room("Stone Bank Vault", "A cold vault below the bank, hemmed in by thick stone and iron. The sound here is oddly close, as if even whispers would rather not travel far.", "center", street_name="Bank Lane", surface="stone floor", tags=["bank", "vault"])

town_hall = make_room("Town Hall Entry", "A sturdy civic entry hall with benches, posted notices, and a broad stair. Everything here is plain, maintained, and slightly more formal than the rest of town.", "center", street_name="Hall Lane", surface="timber floor", tags=["civic", "interior"])
council_chamber = make_room("Town Hall Chamber", "A timber-beamed meeting room with a long table, practical chairs, and shelves of wax-sealed records. It feels more useful than grand.", "center", street_name="Hall Lane", surface="timber floor", tags=["civic", "interior"])
records_loft = make_room("Town Hall Records Loft", "Bundles of old maps, ledgers, and weathered minutes are kept in this dusty loft under the rafters.", "center", street_name="Hall Lane", surface="planks", tags=["civic", "interior"])

armor_shop = make_room("Armor Shop", "Helms, shields, and partial suits hang or stand in orderly ranks, turning the dim interior into a gallery of leather, rivets, and steel.", "center", street_name="Brook Street", surface="timber floor", tags=["shop", "armor"])
armor_loft = make_room("Armor Shop Loft", "Wrapped bundles of finer armor and spare fittings are stored overhead where a careful owner can keep a close eye on them.", "center", street_name="Brook Street", surface="planks", tags=["shop", "armor"])

weapons_shop = make_room("Weapons Shop", "Blades, bowstaves, spearheads, and hafts line the walls in neat and almost reverent order. The place smells of oil, wood, and sharpened metal.", "center", street_name="Market Way", surface="timber floor", tags=["shop", "weapons"])
weapons_upper = make_room("Weapons Shop Upper Rack", "Rare bows, carefully balanced blades, and boxed fittings are kept above the main shop floor.", "center", street_name="Market Way", surface="planks", tags=["shop", "weapons"])

clothing_shop = make_room("Clothing Shop", "Bolts of cloth, dyed cloaks, fitted coats, and sturdy countrywear soften the room in layers of texture and color.", "center", street_name="Brook Street", surface="timber floor", tags=["shop", "clothing"])
clothing_upper = make_room("Clothing Shop Upper Floor", "A fitting room and sewing floor sit beneath sloped beams, with patterns, half-finished garments, and baskets of thread arranged by patient hands.", "center", street_name="Brook Street", surface="planks", tags=["shop", "clothing"])

general_store = make_room("General Store", "Shelves and barrels hold rope, lamp oil, crockery, nails, seed, tools, and all the odd practical needs a town can never quite do without.", "center", street_name="Market Way", surface="timber floor", tags=["shop", "general"])
apothecary = make_room("Apothecary", "Drying herbs, bottled tinctures, roots, powders, and labeled jars give the apothecary a precise and earthy scent.", "center", street_name="Flower Row", surface="timber floor", tags=["shop", "apothecary"])
flower_shop = make_room("Flower Shop", "Buckets of cut stems, potted herbs, and ribboned bundles lend this little shop color and a cool damp sweetness.", "center", street_name="Flower Row", surface="timber floor", tags=["shop", "flowers"])

inn_common = make_room("Three Lanterns Inn", "A warm common room with firelight, benches, and worn boards underfoot. The noise here is friendly enough to conceal a quiet word without ever becoming rowdy.", "center", street_name="Market Way", surface="timber floor", tags=["inn", "interior"])
inn_upper_hall = make_room("Three Lanterns Upper Hall", "A creaking upper hall runs past simple guest rooms and one small window looking down toward the brighter streets.", "center", street_name="Market Way", surface="planks", tags=["inn", "interior"])
inn_third_room = make_room("Three Lanterns Attic Room", "A narrow third-floor room tucked under the roofline. It is cheap, private, and far enough from the common room to hear little but the weather.", "center", street_name="Market Way", surface="planks", tags=["inn", "interior"])
inn_kitchen = make_room("Three Lanterns Kitchen", "A broad stove, a scarred prep table, and simmering pots make this kitchen the true heart of the inn.", "center", street_name="Market Way", surface="stone floor", tags=["inn", "interior"])
inn_cellar = make_room("Three Lanterns Cellar", "Barrels, casks, and spare stores rest in the cool dark beneath the inn.", "center", street_name="Market Way", surface="packed earth", tags=["inn", "cellar"])

guard_post = make_room("Guard Post", "A compact watch station with pegs for weapons, a duty desk, and the kind of narrow bench only a tired guard would call comfortable.", "center", street_name="Hall Lane", surface="timber floor", tags=["guard", "interior"])
guard_roof = make_room("Guard Post Roof Walk", "A roof walk over the guard post offers a practical view of nearby streets and the square.", "center", street_name="Hall Lane", surface="planks", tags=["guard", "overlook"])

shrine = make_room("Small Shrine", "A modest public shrine with wax drippings, folded petitions, and a hush that survives even the market's nearness.", "center", street_name="Lantern Row", surface="stone floor", tags=["shrine"])

cottages = []
for _ in range(1, 6):
    cottages.append(make_room("Cottage Interior", "A simple cottage interior with a table, a hearth, and evidence of ordinary family life. This one feels lived in, not staged, with useful clutter and small personal touches.", "residential", street_name="Hearth Lane", surface="timber floor", tags=["home", "interior"]))

warehouse_interiors = []
for _ in range(1, 6):
    warehouse_interiors.append(make_room("Warehouse Interior", "Tall stacks of crates and hanging hooks define this broad warehouse interior. Dust, timber, rope, and labor have all left their mark here.", "warehouse", street_name="Warehouse Row", surface="packed earth", tags=["warehouse", "interior"]))
counting_house = make_room("Counting House", "A cramped office with ledgers, chalk tallies, and an unlovely but necessary devotion to weights, measures, and signatures.", "warehouse", street_name="Storeyard Lane", surface="planks", tags=["warehouse", "office"])
warehouse_loft = make_room("Warehouse Loft", "High rafters and a plank loft overlook the stacked interior below, good for inventory counts or keeping an eye on who comes and goes.", "warehouse", street_name="Warehouse Row", surface="planks", tags=["warehouse", "loft"])

fence_cellar = make_room("Fence Cellar", "A low hidden cellar lit by hooded lamps and used for quiet deals. Crates are stacked more for concealment than order, and even the air seems wary.", "low", street_name="Whisper Lane", surface="packed earth", tags=["low", "secret", "fence"])
safehouse = make_room("Safehouse Loft", "A cramped hidden loft above a neglected rooming house, just large enough for a cot, a shuttered lamp, and a stash no one asks about.", "low", street_name="Crooked Alley", surface="planks", tags=["low", "secret"])
rag_shop = make_room("Rag Shop", "Bundles of secondhand clothing, scavenged cloth, and patched blankets crowd this little storefront in no very orderly fashion.", "low", street_name="Ratline Lane", surface="timber floor", tags=["low", "shop"])
pawn_room = make_room("Pawn Counter", "A mean little counter and barred shelf separate customers from whatever goods are still worth haggling over.", "low", street_name="Ratline Lane", surface="timber floor", tags=["low", "shop"])

def connect_chain(chain, direction_a="south", direction_b="north"):
    for idx in range(len(chain) - 1):
        make_exit(chain[idx], direction_a, chain[idx + 1], direction_b)

for chain_name in roads:
    connect_chain(roads[chain_name])

# Central hub connections
make_exit(town_square, "north", roads["Market Way"][0], "south")
make_exit(town_square, "south", roads["Hearth Lane"][0], "north")
make_exit(town_square, "east", roads["Brook Street"][0], "west")
make_exit(town_square, "west", roads["Bank Lane"][0], "east")
make_exit(town_square, "northeast", roads["Hall Lane"][0], "southwest")
make_exit(town_square, "northwest", roads["Flower Row"][0], "southeast")
make_exit(town_square, "southeast", roads["Lantern Row"][0], "northwest")
make_exit(town_square, "up", wellside_bench, "down")

# Cross-connections in center
make_exit(roads["Market Way"][1], "east", roads["Brook Street"][1], "west")
make_exit(roads["Market Way"][2], "west", roads["Bank Lane"][1], "east")
make_exit(roads["Market Way"][3], "northeast", roads["Hall Lane"][1], "southwest")
make_exit(roads["Brook Street"][2], "north", roads["Lantern Row"][1], "south")
make_exit(roads["Flower Row"][1], "east", roads["Brook Street"][3], "west")
make_exit(roads["Bank Lane"][2], "north", roads["Hall Lane"][2], "south")
make_exit(roads["Hall Lane"][3], "east", roads["Flower Row"][2], "west")
make_exit(roads["Brook Street"][4], "south", roads["Market Way"][4], "north")
make_exit(roads["Lantern Row"][2], "west", roads["Market Way"][5], "east")

# Center to districts
make_exit(roads["Market Way"][7], "south", roads["Warehouse Row"][0], "north")
make_exit(roads["Brook Street"][5], "south", roads["Storeyard Lane"][0], "north")
make_exit(roads["Hearth Lane"][4], "west", roads["Willow Walk"][0], "east")
make_exit(roads["Hearth Lane"][6], "east", roads["Garden Path"][0], "west")
make_exit(roads["South Hedge Road"][0], "northwest", roads["Hearth Lane"][8], "southeast")
make_exit(roads["West Field Road"][0], "northeast", roads["Willow Walk"][4], "southwest")
make_exit(roads["Crooked Alley"][0], "north", roads["Flower Row"][2], "south")
make_exit(roads["Ratline Lane"][0], "northwest", roads["Market Way"][6], "southeast")
make_exit(roads["Whisper Lane"][0], "west", roads["Brook Street"][5], "east")

# Residential loops
for idx in range(0, 7):
    make_exit(roads["Hearth Lane"][idx], "east", roads["South Hedge Road"][idx], "west")
for idx in range(0, 6):
    make_exit(roads["Willow Walk"][idx], "south", roads["Garden Path"][idx], "north")
for idx in range(0, 7):
    make_exit(roads["South Hedge Road"][idx], "west", roads["West Field Road"][idx], "east")
for idx in range(1, 7):
    make_exit(roads["Garden Path"][idx-1], "southwest", roads["West Field Road"][idx], "northeast")

# Warehouse loops
for idx in range(0, 6):
    make_exit(roads["Warehouse Row"][idx], "east", roads["Storeyard Lane"][idx], "west")
for idx in range(0, 6):
    make_exit(roads["Storeyard Lane"][idx], "south", roads["Cart Yard Road"][idx], "north")
for idx in range(0, 6):
    make_exit(roads["Warehouse Row"][idx+1], "southeast", roads["Cart Yard Road"][idx], "northwest")

# Low quarter loops
for idx in range(0, 6):
    make_exit(roads["Crooked Alley"][idx], "east", roads["Ratline Lane"][idx], "west")
for idx in range(0, 6):
    make_exit(roads["Ratline Lane"][idx], "southeast", roads["Whisper Lane"][idx], "northwest")
for idx in range(1, 6):
    make_exit(roads["Whisper Lane"][idx], "west", roads["Crooked Alley"][idx+1], "east")

# Building entrances
make_exit(roads["Bank Lane"][1], "inside", banking_hall, "outside")
make_exit(banking_hall, "up", bank_upper, "down")
make_exit(banking_hall, "down", bank_vault, "up")

make_exit(roads["Hall Lane"][1], "inside", town_hall, "outside")
make_exit(town_hall, "north", council_chamber, "south")
make_exit(council_chamber, "up", records_loft, "down")

make_exit(roads["Brook Street"][1], "inside", armor_shop, "outside")
make_exit(armor_shop, "up", armor_loft, "down")

make_exit(roads["Market Way"][1], "inside", weapons_shop, "outside")
make_exit(weapons_shop, "up", weapons_upper, "down")

make_exit(roads["Brook Street"][2], "inside", clothing_shop, "outside")
make_exit(clothing_shop, "up", clothing_upper, "down")

make_exit(roads["Market Way"][2], "inside", general_store, "outside")
make_exit(roads["Flower Row"][1], "inside", apothecary, "outside")
make_exit(roads["Flower Row"][0], "inside", flower_shop, "outside")

make_exit(roads["Market Way"][3], "inside", inn_common, "outside")
make_exit(inn_common, "up", inn_upper_hall, "down")
make_exit(inn_upper_hall, "up", inn_third_room, "down")
make_exit(inn_common, "west", inn_kitchen, "east")
make_exit(inn_common, "down", inn_cellar, "up")

make_exit(roads["Hall Lane"][2], "inside", guard_post, "outside")
make_exit(guard_post, "up", guard_roof, "down")

make_exit(roads["Lantern Row"][1], "inside", shrine, "outside")

make_exit(roads["Hearth Lane"][1], "inside", cottages[0], "outside")
make_exit(roads["Hearth Lane"][3], "inside", cottages[1], "outside")
make_exit(roads["Willow Walk"][2], "inside", cottages[2], "outside")
make_exit(roads["South Hedge Road"][4], "inside", cottages[3], "outside")
make_exit(roads["West Field Road"][5], "inside", cottages[4], "outside")

make_exit(roads["Warehouse Row"][1], "inside", warehouse_interiors[0], "outside")
make_exit(roads["Warehouse Row"][3], "inside", warehouse_interiors[1], "outside")
make_exit(roads["Storeyard Lane"][2], "inside", warehouse_interiors[2], "outside")
make_exit(roads["Cart Yard Road"][3], "inside", warehouse_interiors[3], "outside")
make_exit(roads["Warehouse Row"][6], "inside", warehouse_interiors[4], "outside")
make_exit(roads["Storeyard Lane"][4], "inside", counting_house, "outside")
make_exit(warehouse_interiors[0], "up", warehouse_loft, "down")

make_exit(roads["Ratline Lane"][2], "inside", rag_shop, "outside")
make_exit(roads["Ratline Lane"][4], "inside", pawn_room, "outside")
make_secret_exit(roads["Whisper Lane"][3], "down", fence_cellar, "up")
make_secret_exit(inn_cellar, "south", fence_cellar, "north")
make_secret_exit(roads["Crooked Alley"][5], "up", safehouse, "down")

# INVENTORIES
for key, desc, val in [
    ("leather cap", "A practical leather cap with stitched seams and sweat-darkened lining.", 18),
    ("buckler", "A round buckler with a reinforced rim.", 25),
    ("quilted jack", "A padded jack useful for travel or militia duty.", 40),
    ("chain shirt", "A shirt of linked steel rings, heavier than it first appears.", 85),
    ("steel helm", "A well-made steel helm with a nasal guard.", 65),
]:
    make_item(key, armor_shop, desc, "armor", value=val, shop_stock=True)

for key, desc, val in [
    ("short sword", "A practical short sword balanced for close work.", 55),
    ("long knife", "A sturdy long knife with a sharpened back edge.", 22),
    ("ash bow", "A simple bow of ash wood, well-kept and lightly waxed.", 48),
    ("boar spear", "A spear with a broad head and stout shaft.", 42),
    ("quiver of arrows", "A serviceable quiver filled with goose-feathered arrows.", 15),
]:
    make_item(key, weapons_shop, desc, "weapon", value=val, shop_stock=True)

for key, desc, val in [
    ("traveler's cloak", "A weathered cloak meant for drizzle and road dust.", 24),
    ("wool tunic", "A plain but warm tunic of good wool.", 16),
    ("linen shirt", "A clean linen shirt with simple stitching.", 10),
    ("patched breeches", "Sturdy breeches mended with care rather than elegance.", 12),
    ("soft boots", "Soft leather boots fit for walking town lanes.", 19),
]:
    make_item(key, clothing_shop, desc, "clothing", value=val, shop_stock=True)

for key, desc, val in [
    ("lamp oil flask", "A stoppered flask of lamp oil.", 6),
    ("coil of rope", "A coil of rough hemp rope.", 9),
    ("tin cup", "A simple but durable tin cup.", 2),
    ("travel rations", "A wrapped packet of dried meat, oats, and hard bread.", 7),
    ("sewing needle kit", "Needles, thread, and a little cloth roll.", 5),
]:
    make_item(key, general_store, desc, "general", value=val, shop_stock=True)

for key, desc, val in [
    ("healing tonic", "A bitter tonic meant to steady the body after strain.", 20),
    ("dried comfrey", "A packet of dried herb for poultices.", 8),
    ("sleep draught", "A carefully measured sleeping draught in a corked vial.", 18),
    ("marigold salve", "A little clay pot of herbal salve.", 12),
]:
    make_item(key, apothecary, desc, "apothecary", value=val, shop_stock=True)

for key, desc, val in [
    ("lavender bunch", "A fresh bunch of lavender tied in twine.", 4),
    ("wreath of herbs", "A fragrant little wreath of rosemary and thyme.", 7),
    ("sunflower bundle", "A bright cut bundle wrapped in ribbon.", 5),
]:
    make_item(key, flower_shop, desc, "flowers", value=val, shop_stock=True)

for key, desc, val in [
    ("unmarked ring", "A small ring whose provenance is better left vague.", 35),
    ("silver spoon", "A polished spoon with a crest partially filed away.", 14),
    ("fine belt buckle", "A decorative buckle that clearly used to belong to someone wealthier.", 20),
]:
    make_item(key, fence_cellar, desc, "contraband", value=val, shop_stock=True)

# NPCS
captain = make_npc("Captain Elra Thane", guard_post, "A stern but level-eyed captain of the town watch, more interested in patterns than bluster.", "guard_captain", patrol_route=[room.dbref for room in [guard_post, roads["Hall Lane"][2], town_square, roads["Bank Lane"][1], guard_post]])
guard1 = make_npc("Watchman Corl", roads["Bank Lane"][0], "A watchman who looks twice at anything worth stealing and once at everyone else.", "guard", patrol_route=[room.dbref for room in [roads["Bank Lane"][0], town_square, roads["Hall Lane"][1], roads["Bank Lane"][2]]])
guard2 = make_npc("Watchwoman Sera", roads["Market Way"][4], "A steady-eyed watchwoman who walks market routes with practiced patience.", "guard", patrol_route=[room.dbref for room in [roads["Market Way"][2], roads["Market Way"][4], roads["Flower Row"][1], town_square]])
guard3 = make_npc("Watchman Pell", roads["Warehouse Row"][2], "A warehouse watchman with dusty boots and a suspicious habit of checking locks twice.", "guard", patrol_route=[room.dbref for room in [roads["Warehouse Row"][1], roads["Warehouse Row"][4], roads["Storeyard Lane"][3], counting_house]])

make_npc("Master Berren Vale", banking_hall, "A cautious banker with tidy cuffs and a better memory than he lets on.", "banker")
make_npc("Mayor Osric Fen", council_chamber, "A practical mayor in well-kept but unshowy clothes.", "mayor")
make_npc("Rulda Ironweave", armor_shop, "A broad-shouldered armorer who inspects every rivet as if it has personally offended her.", "armorer")
make_npc("Jorren Pike", weapons_shop, "A smith and fletcher who handles even simple wares with professional respect.", "weaponsmith")
make_npc("Mira Threadwell", clothing_shop, "A sharp-eyed clothier with a warm smile and exacting standards.", "clothier")
make_npc("Tamsin Reed", general_store, "A genial general merchant who somehow remembers who owes what.", "shopkeeper")
make_npc("Old Nessa Vale", apothecary, "A quiet herbalist whose certainty does half the healing before any tonic is poured.", "apothecary")
make_npc("Pela Brightstem", flower_shop, "A cheerful florist with dirt under her nails and ribbons at her wrist.", "florist")
make_npc("Hobb Rake", fence_cellar, "A narrow-eyed fence who smiles only when the goods are good enough.", "fence")
make_npc("Marn at the Three Lanterns", inn_common, "The innkeeper has the broad patience of someone who has already heard this story twice tonight.", "innkeeper")

stock_shopkeepers()

for name, location, desc, zone in [
    ("Carter Wren", roads["Warehouse Row"][0], "A teamster who always smells faintly of horse, wet rope, and road dust.", "warehouse"),
    ("Old Bessa", roads["Hearth Lane"][2], "An elderly townswoman carrying a basket and a great deal of unsolicited opinion.", "residential"),
    ("Pip the Runner", roads["Market Way"][0], "A quick-footed messenger forever one errand behind and another ahead.", "center"),
    ("Miller's Son", roads["South Hedge Road"][2], "A lanky youth with flour on one sleeve and mud on both boots.", "residential"),
    ("Tin Jory", roads["Crooked Alley"][1], "A scavenger with bright eyes, quick hands, and an uneven grin.", "low"),
    ("Doran Feld", roads["Brook Street"][3], "A respectable trader who looks like he belongs wherever the coin is moving.", "center"),
    ("Sister Hale", roads["Lantern Row"][1], "A wandering sister with a quiet voice and a habit of noticing who is troubled.", "center"),
    ("Mira Cobb", roads["West Field Road"][1], "A farmer's wife in town for supplies, keeping a brisk pace and a practical eye.", "residential"),
]:
    make_npc(name, location, desc, "townsfolk", wander=True, wander_zone=zone)

# Fixtures
make_item("public well", town_square, "A stone-ringed public well worn smooth by generations of hands and rope.", "fixture")
make_item("notice board", town_square, "Postings for caravans, missing goats, civic notices, and rumors overlap in crowded layers.", "fixture")
make_item("ledger stand", banking_hall, "A ledger stand with neat columns and a sharpened quill beside it.", "fixture")
make_item("armor stand", armor_shop, "A polished stand displaying a half-suit of steel.", "fixture")
make_item("weapons rack", weapons_shop, "A rack of blades and bowstaves arranged with almost ceremonial care.", "fixture")
make_item("cut flower buckets", flower_shop, "Buckets of fresh cut flowers brighten the little room.", "fixture")
make_item("common-room hearth", inn_common, "A broad hearth throwing steady warmth into the inn.", "fixture")

all_objs = list(search_tag(TOWN_TAG[0], category=TOWN_TAG[1]))
room_count = len([obj for obj in all_objs if obj.is_typeclass(ROOM_TYPECLASS, exact=False)])
print(f"Brookhollow v3 loaded. Rooms created: {room_count}")
