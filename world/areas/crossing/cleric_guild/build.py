from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
NPC_TYPECLASS = "typeclasses.npcs.NPC"
GUILDLEADER_TYPECLASS = "typeclasses.npcs.ClericGuildmaster"
AREA_NAME = "Cleric Guild"
AREA_SPACE_TAG = "cleric_guild_space"
MAP_BUILD_TAG = "cleric-guild-map"
CANONICAL_TAG = "guild_cleric"
ENTRY_TAG = "guild_cleric_entry"
JOIN_SITE_TAG = "cleric_guildhall"
LANE_DBREF = 4233
LANE_KEY = "Ratwhistle Alley, North Reach"

ROOM_SPECS = {
    "main_hall": {
        "key": "Cleric Guild",
        "aliases": ["main hall", "guild", "hall"],
        "desc": (
            "A solemn central chamber forms the working heart of the guild. Stone arches, worn benches, and quiet devotional details keep the room from feeling austere, "
            "but nothing here is casual. Every passage suggests duty: counsel above, contemplation below, study to one side, and the practical work of the guild beyond."
        ),
        "room_tag": "main_hall",
        "coords": (0, 0),
    },
    "office": {
        "key": "Guildleader Esuin's Office",
        "aliases": ["office", "guildleader office", "esuin office"],
        "desc": (
            "A sturdy desk, orderly ledgers, and devotional tokens leave the office feeling more like a command post than a retreat. "
            "Judgment here would be calm, exacting, and impossible to mistake for softness."
        ),
        "room_tag": "office",
        "coords": (0, 2),
    },
    "library": {
        "key": "Cleric Guild, Library",
        "aliases": ["library", "archives", "stacks"],
        "desc": (
            "Shelves of sermons, histories, mortuary notes, and ritual manuals fill the room with the weight of studied faith. "
            "Even the quiet feels supervised, as though doctrine matters most when no one is speaking aloud."
        ),
        "room_tag": "library",
        "coords": (2, 0),
    },
    "glass_hall": {
        "key": "Cleric Guild, Glass Hall",
        "aliases": ["glass hall", "glass door", "east hall"],
        "desc": (
            "Light filters through panes and polished fittings here, softening the stone without diminishing the room's sense of purpose. "
            "A curtained doorway leads toward the garden, while the library remains close at hand behind the glass door."
        ),
        "room_tag": "glass_hall",
        "coords": (4, 0),
    },
    "garden": {
        "key": "Cleric Guild, Garden",
        "aliases": ["garden", "court garden", "herb garden"],
        "desc": (
            "A sheltered guild garden opens under clean air and careful order. Herbs, pale blossoms, and clipped greenery give the space the feel of a contemplative refuge rather than a public courtyard."
        ),
        "room_tag": "garden",
        "coords": (4, 2),
    },
    "arch_hall": {
        "key": "Cleric Guild, Arch Hall",
        "aliases": ["arch hall", "arch", "lower hall"],
        "desc": (
            "A broad arch marks the lower crossroads of the guild. Chapel, cellar, and refectory traffic all meet here, leaving the stone worn by both reverence and routine."
        ),
        "room_tag": "arch_hall",
        "coords": (0, -2),
    },
    "chapel": {
        "key": "Cleric Guild, Chapel",
        "aliases": ["chapel", "sanctuary"],
        "desc": (
            "Simple pews and a quiet altar make the chapel feel intimate rather than grand. It is a room for focused prayer, last rites, and the kind of silence that steadies the hands afterward."
        ),
        "room_tag": "chapel",
        "coords": (-2, -2),
    },
    "wine_cellar": {
        "key": "Cleric Guild, Wine Cellar",
        "aliases": ["wine cellar", "cellar", "casks"],
        "desc": (
            "Cool stone and neatly stacked casks keep the cellar practical, but not purely domestic. This part of the guild feels ready to provision rites, vigils, and hidden movement in equal measure."
        ),
        "room_tag": "wine_cellar",
        "coords": (2, -2),
    },
    "refectory_passage": {
        "key": "Cleric Guild, Refectory Passage",
        "aliases": ["refectory passage", "passage", "lower passage"],
        "desc": (
            "The lower passage trades ceremony for use. Foot traffic has left the floor polished in places, and the smell of kitchen warmth lingers close enough to follow west."
        ),
        "room_tag": "refectory_passage",
        "coords": (0, -4),
    },
    "refectory": {
        "key": "Cleric Guild, Refectory",
        "aliases": ["refectory", "tables", "hall"],
        "desc": (
            "Long tables and practical service pieces make the refectory feel communal without ever becoming noisy. It is the sort of room where tired clergy eat quickly and return to work with little fuss."
        ),
        "room_tag": "refectory",
        "coords": (-2, -4),
    },
    "cellar_arch": {
        "key": "Cleric Guild, Cellar Arch",
        "aliases": ["cellar arch", "archway", "south arch"],
        "desc": (
            "A narrow arch frames the southern edge of the cellar wing, where practical guild traffic gives way to stone that feels older and more secretive than the rest."
        ),
        "room_tag": "cellar_arch",
        "coords": (2, -4),
    },
    "tunnel_mouth": {
        "key": "Cleric Guild, Tunnel Mouth",
        "aliases": ["tunnel mouth", "tunnel", "escape tunnel"],
        "desc": (
            "A hidden tunnel mouth opens beyond the cellar, narrow, dry, and unmistakably meant for discreet movement rather than comfort. The deeper escape tunnels lie beyond, but this branch stops here for now."
        ),
        "room_tag": "tunnel_mouth",
        "coords": (4, -2),
    },
}

EXIT_SPECS = (
    ("main_hall", "north", ["door", "guildleader", "esuin"], "office"),
    ("office", "south", ["hall", "door", "out"], "main_hall"),
    ("main_hall", "east", ["library", "glass"], "library"),
    ("library", "west", ["hall", "guild"], "main_hall"),
    ("library", "east", ["glass door", "glass hall"], "glass_hall"),
    ("glass_hall", "west", ["library", "glass door"], "library"),
    ("glass_hall", "north", ["curt door", "curtain", "garden"], "garden"),
    ("garden", "south", ["hall", "curtain", "glass hall"], "glass_hall"),
    ("main_hall", "south", ["arch", "door"], "arch_hall"),
    ("arch_hall", "north", ["guild", "hall", "out"], "main_hall"),
    ("arch_hall", "west", ["arch", "chapel"], "chapel"),
    ("chapel", "east", ["out", "arch", "hall"], "arch_hall"),
    ("arch_hall", "east", ["cellar", "wine cellar"], "wine_cellar"),
    ("wine_cellar", "west", ["hall", "arch"], "arch_hall"),
    ("arch_hall", "south", ["build", "refectory", "passage"], "refectory_passage"),
    ("refectory_passage", "north", ["guild", "hall", "back"], "arch_hall"),
    ("refectory_passage", "west", ["refectory", "tables"], "refectory"),
    ("refectory", "east", ["passage", "out"], "refectory_passage"),
    ("wine_cellar", "south", ["arch", "out"], "cellar_arch"),
    ("cellar_arch", "north", ["cellar", "back"], "wine_cellar"),
    ("wine_cellar", "east", ["tunnel", "escape tunnels"], "tunnel_mouth"),
    ("tunnel_mouth", "west", ["cellar", "back"], "wine_cellar"),
)


def _find_room(*keys):
    wanted = [str(key or "").strip() for key in keys if str(key or "").strip()]
    for key in wanted:
        room = ObjectDB.objects.filter(db_key__iexact=key, db_typeclass_path=ROOM_TYPECLASS).first()
        if room:
            return room
    return None


def _find_exit(room, *names):
    wanted = {str(name or "").strip().lower() for name in names if str(name or "").strip()}
    if not room or not wanted:
        return None
    for exit_obj in list(getattr(room, "exits", []) or []):
        key = str(getattr(exit_obj, "key", "") or "").strip().lower()
        aliases = {str(alias or "").strip().lower() for alias in getattr(getattr(exit_obj, "aliases", None), "all", lambda: [])()}
        if key in wanted or aliases.intersection(wanted):
            return exit_obj
    return None


def _find_tagged_room(tag_name):
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        try:
            if room.tags.has(tag_name):
                return room
        except Exception:
            continue
    return None


def _clear_room_tags(room, tag_names):
    for tag_name in tag_names:
        try:
            room.tags.remove(tag_name)
        except Exception:
            continue


def _ensure_room(key, desc, aliases=None):
    room = _find_room(key)
    if not room:
        room = create_object(ROOM_TYPECLASS, key=key)
    room.key = key
    room.db.desc = desc
    room.db.area = AREA_NAME
    room.db.region_name = "The Landing"
    for alias in aliases or []:
        room.aliases.add(alias)
    return room


def _ensure_exit(src, key, dest, aliases=None, existing_keys=None):
    exit_obj = _find_exit(src, key, *(existing_keys or []))
    if not exit_obj:
        exit_obj = create_object(EXIT_TYPECLASS, key=key, location=src, destination=dest, home=src)
    exit_obj.key = key
    exit_obj.destination = dest
    exit_obj.aliases.clear()
    for alias in aliases or []:
        exit_obj.aliases.add(alias)
    for candidate in list(existing_keys or []):
        duplicate = ObjectDB.objects.filter(db_key__iexact=candidate, db_location=src).exclude(id=exit_obj.id).first()
        if duplicate:
            duplicate.delete()
    return exit_obj


def _ensure_npc(key, room, aliases=None, desc="", typeclass=NPC_TYPECLASS):
    npc = ObjectDB.objects.filter(db_key__iexact=key, db_location=room).first()
    if not npc:
        npc = create_object(typeclass, key=key, location=room, home=room)
    elif str(getattr(npc, "db_typeclass_path", "") or "") != typeclass:
        npc.swap_typeclass(typeclass, clean_attributes=False, no_default=False)
    npc.key = key
    npc.home = room
    if getattr(npc, "location", None) != room:
        npc.move_to(room, quiet=True, use_destination=False)
    npc.db.desc = desc
    npc.db.is_npc = True
    for alias in aliases or []:
        npc.aliases.add(alias)
    return npc


def ensure_crossing_cleric_guildhall():
    lane_room = ObjectDB.objects.get_id(LANE_DBREF)
    if lane_room and str(getattr(lane_room, "key", "") or "") != LANE_KEY:
        lane_room = None

    canonical_room = _find_tagged_room(CANONICAL_TAG) or _find_room(ROOM_SPECS["main_hall"]["key"])
    entry_room = _find_tagged_room(ENTRY_TAG) or canonical_room

    rooms = {}
    for room_key, spec in ROOM_SPECS.items():
        if room_key == "main_hall" and canonical_room:
            room = canonical_room
            room.key = spec["key"]
            room.db.desc = spec["desc"]
        elif room_key == "main_hall" and entry_room:
            room = entry_room
            room.key = spec["key"]
            room.db.desc = spec["desc"]
        else:
            room = _ensure_room(spec["key"], spec["desc"], aliases=spec.get("aliases"))
        room.db.area = AREA_NAME
        room.db.region_name = "The Landing"
        room.db.guild_tag = JOIN_SITE_TAG
        room.db.cleric_guild_room = spec["room_tag"]
        room.db.map_x = spec["coords"][0]
        room.db.map_y = spec["coords"][1]
        _clear_room_tags(room, [CANONICAL_TAG, ENTRY_TAG])
        room.tags.add(AREA_SPACE_TAG)
        room.tags.add(JOIN_SITE_TAG)
        room.tags.add(MAP_BUILD_TAG, category="build")
        if room_key == "main_hall":
            room.tags.add(CANONICAL_TAG)
            room.tags.add(ENTRY_TAG)
            room.tags.add("poi_guild_cleric")
        rooms[room_key] = room

    for source_key, exit_key, aliases, dest_key in EXIT_SPECS:
        _ensure_exit(rooms[source_key], exit_key, rooms[dest_key], aliases=aliases)

    if lane_room:
        lane_room.tags.add("guild_access_cleric")
        lane_to_guild = _ensure_exit(
            lane_room,
            "north",
            rooms["main_hall"],
            aliases=["guild", "cleric", "cleric guild", "door"],
            existing_keys=["guild"],
        )
        lane_to_guild.db.exit_display_name = "Cleric Guild"

        guild_to_lane = _ensure_exit(
            rooms["main_hall"],
            "out",
            lane_room,
            aliases=["west", "street", "alley", "back"],
            existing_keys=["west"],
        )
        guild_to_lane.db.exit_display_name = "Out"

        garden_to_lane = _ensure_exit(
            rooms["garden"],
            "out",
            lane_room,
            aliases=["door", "walk", "street", "garden"],
            existing_keys=["west"],
        )
        garden_to_lane.db.exit_display_name = "Out"

    leader = _ensure_npc(
        "Guildleader Esuin",
        rooms["office"],
        aliases=["esuin", "guildleader", "leader"],
        desc="Esuin carries himself with the calm authority of a priest who has spent years turning devotion into action rather than display.",
        typeclass=GUILDLEADER_TYPECLASS,
    )
    leader.db.guild_role = "guildmaster"
    leader.db.trains_profession = "cleric"

    librarian = _ensure_npc(
        "Guild Archivist",
        rooms["library"],
        aliases=["archivist", "librarian"],
        desc="A severe archivist keeps the guild's ritual books and death records in immaculate order.",
    )
    librarian.db.guild_role = "mentor"
    librarian.db.trains_profession = "cleric"

    acolyte = _ensure_npc(
        "Chapel Acolyte",
        rooms["chapel"],
        aliases=["acolyte", "priest"],
        desc="A quiet acolyte tends the chapel with the focused care of someone who knows reverence is work before it is comfort.",
    )
    acolyte.db.guild_role = "mentor"
    acolyte.db.trains_profession = "cleric"

    return rooms