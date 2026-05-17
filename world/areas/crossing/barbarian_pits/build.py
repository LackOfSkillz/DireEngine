from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from domain.abilities.dances.registry import DANCE_BY_BIT
from world.areas.crossing.barbarian_guild.build import ensure_crossing_barbarian_guildhall


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
PIT_MASTER_TYPECLASS = "typeclasses.npcs.BarbarianPitMaster"
AREA_NAME = "Barbarian Pits"
AREA_TAG = "barbarian_pit_space"
BUILD_TAG = "barbarian-pit-map"

_ROOM_FLAVOR = {
    "swan": "The floor is clear and open, with just enough room to trace precise arcs until grace starts to feel like a weapon.",
    "cobra": "Tight lines and scarred posts force every motion to stay compact, sharp, and close to the point of danger.",
    "badger": "The walls are thick with blunt impact marks, built for holding ground until stubbornness turns into craft.",
    "eagle": "The pit rises in narrow tiers, giving long sightlines and forcing every stance to account for distance and timing.",
    "bear": "Heavy beams, sanded stone, and split targets reward weight, patience, and the kind of force that does not hurry.",
    "wolverine": "Everything in the room invites pressure and crowding, as if the lesson starts only once the space grows mean.",
    "panther": "Low light and angled cover break every line cleanly, leaving the room built around speed, stealth, and strike lanes.",
    "dragon": "The largest pit mixes open ground, broken sightlines, and brutal footing until every skill has to live together or fail.",
}


def _ordered_dances():
    return [DANCE_BY_BIT[index] for index in sorted(DANCE_BY_BIT)]


PIT_ROOM_SPECS = {
    definition.name: {
        "key": f"Barbarian Pit, {definition.canonical_display_name}",
        "aliases": [definition.name, definition.canonical_display_name.lower(), "pit"],
        "desc": _ROOM_FLAVOR[definition.name],
        "canonical_room_id": int(definition.canonical_pit_room),
        "pit_master": str(definition.canonical_pit_master),
    }
    for definition in _ordered_dances()
}


def _find_room(*keys):
    wanted = {str(key or "").strip().lower() for key in keys if str(key or "").strip()}
    if not wanted:
        return None
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        if str(getattr(room, "key", "") or "").strip().lower() in wanted:
            return room
    return None


def _find_exit(source, *keys):
    if not source:
        return None
    wanted = {str(key or "").strip().lower() for key in keys if str(key or "").strip()}
    for obj in list(getattr(source, "contents", []) or []):
        if getattr(obj, "db_typeclass_path", "") != EXIT_TYPECLASS:
            continue
        if str(getattr(obj, "key", "") or "").strip().lower() in wanted:
            return obj
    return None


def _ensure_room(key, desc, *, aliases=None):
    room = _find_room(key, *(aliases or []))
    if room is None:
        room = create_object(ROOM_TYPECLASS, key=key, nohome=True)
    room.key = key
    room.db.desc = desc
    for alias in aliases or []:
        room.aliases.add(alias)
    return room


def _ensure_exit(source, key, destination, *, aliases=None, existing_keys=None):
    exit_obj = _find_exit(source, key, *(existing_keys or []), *(aliases or []))
    if exit_obj is None:
        exit_obj = create_object(EXIT_TYPECLASS, key=key, location=source, destination=destination, nohome=True)
    exit_obj.key = key
    exit_obj.destination = destination
    for alias in aliases or []:
        exit_obj.aliases.add(alias)
    return exit_obj


def _ensure_pit_master(definition, room):
    npc = None
    for obj in list(getattr(room, "contents", []) or []):
        if getattr(obj, "db_typeclass_path", "") != PIT_MASTER_TYPECLASS:
            continue
        if str(getattr(obj, "key", "") or "").strip().lower() == str(definition.canonical_pit_master or "").strip().lower():
            npc = obj
            break
    if npc is None:
        npc = create_object(PIT_MASTER_TYPECLASS, key=definition.canonical_pit_master, location=room, home=room, nohome=True)
    npc.key = definition.canonical_pit_master
    npc.location = room
    npc.home = room
    npc.db.trains_profession = "barbarian"
    npc.db.guild_role = "pit_master"
    npc.db.teaches_dance = definition.name
    npc.db.required_level = int(definition.required_level)
    npc.db.canonical_room_id = int(definition.canonical_pit_room)
    npc.db.default_inquiry_response = f"{definition.canonical_pit_master} says, 'Ask me about the {definition.canonical_display_name} dance if that is what you came for.'"
    for alias in ["pit master", definition.name, definition.canonical_display_name.lower()]:
        npc.aliases.add(alias)
    return npc


def ensure_crossing_barbarian_pits():
    guild_rooms = ensure_crossing_barbarian_guildhall()
    training_floor = guild_rooms["training_floor"]
    rooms = {}
    ordered = []

    for index, definition in enumerate(_ordered_dances()):
        spec = PIT_ROOM_SPECS[definition.name]
        room = _ensure_room(spec["key"], spec["desc"], aliases=spec["aliases"])
        room.db.area = AREA_NAME
        room.db.region_name = "The Landing"
        room.db.canonical_room_id = int(spec["canonical_room_id"])
        room.db.pit_master_name = spec["pit_master"]
        room.db.barbarian_pit_dance = definition.name
        room.db.map_x = index
        room.db.map_y = 0
        room.tags.add(AREA_TAG)
        room.tags.add(BUILD_TAG, category="build")
        rooms[definition.name] = room
        ordered.append((definition, room))
        _ensure_pit_master(definition, room)

    first_definition, first_room = ordered[0]
    _ensure_exit(training_floor, "pits", first_room, aliases=["pit", first_definition.name, "dance pits"])

    for index, (_definition, room) in enumerate(ordered):
        _ensure_exit(room, "out", training_floor, aliases=["back", "training floor", "guild"])
        if index == 0:
            continue
        previous_definition, previous_room = ordered[index - 1]
        _ensure_exit(previous_room, "east", room, aliases=["next", _definition.name], existing_keys=["east"])
        _ensure_exit(room, "west", previous_room, aliases=["back", previous_definition.name], existing_keys=["west"])

    return rooms