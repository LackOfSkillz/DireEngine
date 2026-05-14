from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object


ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
TRAINER_TYPECLASS = "typeclasses.npcs.StatTrainerNPC"
AREA_NAME = "The Landing"
MAP_BUILD_TAG = "landing-stat-trainers"
HUB_DBREF = 4305
HUB_KEY = "Town Green NE"

TRAINER_ROOMS = {
    "strength": {
        "room_key": "The Strength Society",
        "trainer_key": "Master Bron of Strength",
        "entry_exit": "strength",
        "entry_aliases": ["strength society", "society", "bron"],
        "desc": (
            "Wooden practice dummies stand in disciplined ranks along the walls of The Strength Society. "
            "Iron weights, lifting stones, and reinforced striking posts crowd the central training floor. "
            "The air smells of sweat and tallow, with every surface scarred by repetition. "
            "A sturdy trainer watches every movement for signs of wasted effort."
        ),
        "trainer_desc": (
            "Master Bron carries the compact power of someone who has spent a lifetime correcting weak form. "
            "His arms are crossed, but his attention never drifts from the work at hand."
        ),
    },
    "stamina": {
        "room_key": "The Endurance Hall",
        "trainer_key": "Mistress Vala of Endurance",
        "entry_exit": "endurance",
        "entry_aliases": ["endurance hall", "endurance", "vala"],
        "desc": (
            "The Endurance Hall is arranged for long effort rather than showy strength. "
            "Weighted ropes, pacing tracks, and balance rigs circle the room in steady loops. "
            "Water buckets and clean towels line one wall, always within reach but never inviting idleness. "
            "The entire chamber feels built to teach you how long you can continue after comfort is gone."
        ),
        "trainer_desc": (
            "Mistress Vala looks composed in the way only tireless people can manage. "
            "Nothing about her stance suggests sympathy for anyone hoping to quit early."
        ),
    },
    "agility": {
        "room_key": "The Agility Salon",
        "trainer_key": "Master Thend of Agility",
        "entry_exit": "agility",
        "entry_aliases": ["agility salon", "salon", "thend"],
        "desc": (
            "The Agility Salon is crowded with ladders, low beams, and narrow platforms that reward economy of motion. "
            "Suspended rings sway overhead, forcing constant attention to balance and timing. "
            "Even the polished floor seems designed to punish hesitation. "
            "The room gives the impression that clumsiness is not an accident but a choice."
        ),
        "trainer_desc": (
            "Master Thend moves with precise, irritating ease around every obstacle in the room. "
            "He looks as though he has never once collided with the world by mistake."
        ),
    },
    "reflex": {
        "room_key": "The Reflex Hall",
        "trainer_key": "Mistress Quia of Reflex",
        "entry_exit": "reflex",
        "entry_aliases": ["reflex hall", "quia", "reflexes"],
        "desc": (
            "Targets, shutters, and pivoting frames line The Reflex Hall in patient silence. "
            "Every apparatus looks harmless until you imagine it moving without warning. "
            "A line of chalk marks on the floor hints at where the slow tend to stumble. "
            "The room seems to expect surprise and judge anything less than immediate response."
        ),
        "trainer_desc": (
            "Mistress Quia has the stillness of someone who notices the first twitch before anyone else sees it. "
            "Her attention feels quicker than speech."
        ),
    },
    "charisma": {
        "room_key": "The Discourse Hall",
        "trainer_key": "Master Cassio of Discourse",
        "entry_exit": "discourse",
        "entry_aliases": ["discourse hall", "discourse", "cassio"],
        "desc": (
            "The Discourse Hall resembles a debating chamber more than a gymnasium. "
            "Tiered benches and speaking circles encourage posture, command, and measured presence. "
            "Mirrored brass panels reflect every gesture back at the careless. "
            "The room teaches that influence is practiced as deliberately as any weapon form."
        ),
        "trainer_desc": (
            "Master Cassio speaks only when needed, but his voice lands exactly where he intends. "
            "Even at rest he looks ready to hold a room by force of bearing alone."
        ),
    },
    "discipline": {
        "room_key": "The Discipline Hall",
        "trainer_key": "Master Drael of Discipline",
        "entry_exit": "discipline",
        "entry_aliases": ["discipline hall", "drael", "focus"],
        "desc": (
            "The Discipline Hall is spare by design, stripped of any comfort that might excuse wandering attention. "
            "Counting beads, posture frames, and breathing stools sit in ordered rows beneath plain walls. "
            "Silence here feels intentional rather than empty. "
            "The room trains endurance of will more than endurance of body."
        ),
        "trainer_desc": (
            "Master Drael gives the impression that he has dismissed weaker distractions for years. "
            "His patience feels less kind than relentless."
        ),
    },
    "wisdom": {
        "room_key": "The Hall of Reflection",
        "trainer_key": "Mistress Saphine of Reflection",
        "entry_exit": "reflection",
        "entry_aliases": ["hall of reflection", "reflection", "saphine"],
        "desc": (
            "The Hall of Reflection is quiet without becoming sleepy, built around pools of still water and low reading stands. "
            "Lantern light falls softly across carved maxims and observation journals left open for study. "
            "Nothing in the room pushes for haste. "
            "It invites the harder work of noticing what most people rush past."
        ),
        "trainer_desc": (
            "Mistress Saphine watches with the calm interest of someone who values judgment over speed. "
            "Her expression suggests she has seen many people answer too quickly."
        ),
    },
    "intelligence": {
        "room_key": "The Academy of Intelligence",
        "trainer_key": "Master Korven of Knowledge",
        "entry_exit": "academy",
        "entry_aliases": ["academy of intelligence", "academy", "korven"],
        "desc": (
            "The Academy of Intelligence is crowded with slates, diagrams, and puzzle cabinets that demand active thought. "
            "Reference charts cover the walls from floor to ceiling, leaving almost no empty space to rest the eye. "
            "The scent of chalk and lamp oil hangs over every bench. "
            "It feels like the sort of room where ignorance is treated as a temporary but solvable problem."
        ),
        "trainer_desc": (
            "Master Korven has the absorbed look of someone forever one question ahead of the conversation. "
            "He seems more interested in precision than politeness."
        ),
    },
}


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


def _find_hub_room():
    room = ObjectDB.objects.get_id(HUB_DBREF)
    if room and str(getattr(room, "key", "") or "") == HUB_KEY:
        return room
    return _find_room(HUB_KEY)


def _ensure_room(key, desc):
    room = _find_room(key)
    if not room:
        room = create_object(ROOM_TYPECLASS, key=key)
    room.key = key
    room.db.desc = desc
    room.db.area = AREA_NAME
    room.db.region_name = "The Landing"
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
    return exit_obj


def _ensure_trainer(spec, room, stat_name):
    trainer = ObjectDB.objects.filter(db_key__iexact=spec["trainer_key"], db_location=room).first()
    if not trainer:
        trainer = create_object(TRAINER_TYPECLASS, key=spec["trainer_key"], location=room, home=room)
    trainer.key = spec["trainer_key"]
    trainer.db.is_trainer = True
    trainer.db.trains_stat = stat_name
    trainer.db.trains_profession = None
    trainer.db.desc = spec["trainer_desc"]
    trainer.db.greeting = f"{spec['trainer_key']} studies you, prepared to discuss the discipline of {stat_name}."
    return trainer


def ensure_the_landing_stat_trainers():
    hub_room = _find_hub_room()
    if not hub_room:
        return {}

    rooms = {}
    for stat_name, spec in TRAINER_ROOMS.items():
        room = _ensure_room(spec["room_key"], spec["desc"])
        room.tags.add(MAP_BUILD_TAG, category="build")
        room.tags.add(f"stat_trainer:{stat_name}")
        room.db.stat_trainer = stat_name
        _ensure_trainer(spec, room, stat_name)
        to_room = _ensure_exit(
            hub_room,
            spec["entry_exit"],
            room,
            aliases=[stat_name, spec["room_key"].lower(), *spec.get("entry_aliases", [])],
            existing_keys=[spec["entry_exit"]],
        )
        to_room.db.exit_display_name = spec["room_key"]
        to_hub = _ensure_exit(
            room,
            "out",
            hub_room,
            aliases=["back", "green", "town green", "hub"],
            existing_keys=["out"],
        )
        to_hub.db.exit_display_name = "Out"
        rooms[stat_name] = room

    return rooms