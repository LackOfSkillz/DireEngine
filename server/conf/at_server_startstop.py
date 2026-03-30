"""
Server startstop hooks

This module contains functions called by Evennia at various
points during its startup, reload and shutdown sequence. It
allows for customizing the server operation as desired.

This module must contain at least these global functions:

at_server_init()
at_server_start()
at_server_stop()
at_server_reload_start()
at_server_reload_stop()
at_server_cold_start()
at_server_cold_stop()

"""

import time

from evennia import TICKER_HANDLER
from evennia import SESSION_HANDLER
from evennia import search_object
from evennia import search_script
from evennia.objects.models import ObjectDB
from django.conf import settings
from evennia.utils import logger
from evennia.utils.create import create_object

from typeclasses.objects import BountyBoard
from utils.contests import run_contest
from world.the_landing import build_the_landing


_NPC_TICK_CACHE = {"expires_at": 0.0, "objects": []}
ROOM_TYPECLASS = "typeclasses.rooms.Room"
EXIT_TYPECLASS = "typeclasses.exits.Exit"
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
}

_BROOKHOLLOW_LAWLESS_KEYS = {
    "Crooked Alley",
    "Ratline Lane",
    "Whisper Lane",
    "Fence Cellar",
    "Safehouse Loft",
    "Rag Shop",
    "Pawn Counter",
}


def _configure_brookhollow_justice():
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        street_name = getattr(getattr(room, "db", None), "street_name", None)
        if street_name:
            room.db.region = "brookhollow"
        elif str(getattr(room, "key", "") or "") in _BROOKHOLLOW_LAWLESS_KEYS | {"Town Square", "Guard Post", "Town Hall Chamber", "Town Hall Entry"}:
            room.db.region = "brookhollow"

        room_key = str(getattr(room, "key", "") or "")
        if room_key in _BROOKHOLLOW_LAWLESS_KEYS:
            room.db.law_type = "none"
        elif getattr(room.db, "region", None) == "brookhollow" and not getattr(room.db, "law_type", None):
            room.db.law_type = "standard"

        if room_key == "Town Square":
            room.db.is_stocks = True

    town_square = ObjectDB.objects.filter(db_key="Town Square", db_typeclass_path=ROOM_TYPECLASS).first()
    if town_square and not any(str(getattr(obj, "key", "") or "").lower() == "a bounty board" for obj in town_square.contents):
        create_object(BountyBoard, key="a bounty board", location=town_square)


def _get_cached_tick_npcs():
    now = time.time()
    if now >= _NPC_TICK_CACHE["expires_at"]:
        _NPC_TICK_CACHE["objects"] = list(ObjectDB.objects.filter(db_typeclass_path="typeclasses.npcs.NPC"))
        _NPC_TICK_CACHE["expires_at"] = now + 30.0
    return list(_NPC_TICK_CACHE["objects"])


def _iter_tick_characters():
    active = {}

    try:
        sessions = list(SESSION_HANDLER.values()) if hasattr(SESSION_HANDLER, "values") else []
    except Exception:
        sessions = []

    for session in sessions:
        puppet = session.get_puppet() if hasattr(session, "get_puppet") else None
        if puppet and getattr(puppet, "pk", None):
            active[puppet.pk] = puppet

    for npc in _get_cached_tick_npcs():
        if getattr(npc, "pk", None):
            active[npc.pk] = npc

    return list(active.values())


def _ensure_room(key, desc, aliases=None, home=None):
    room = ObjectDB.objects.filter(db_key=key, db_location__isnull=True).first()
    if not room:
        room = create_object(ROOM_TYPECLASS, key=key, home=home)

    room.db.desc = desc
    room.home = home or room.home or room
    if aliases:
        room.aliases.add(*aliases)
    return room


def _ensure_exit(src, direction, dest):
    exit_obj = ObjectDB.objects.filter(db_key__iexact=direction, db_location=src).first()
    if not exit_obj:
        exit_obj = create_object(
            EXIT_TYPECLASS,
            key=direction,
            aliases=DIR_ALIASES.get(direction, []),
            location=src,
            destination=dest,
            home=src,
        )
    else:
        exit_obj.destination = dest
        for alias in DIR_ALIASES.get(direction, []):
            exit_obj.aliases.add(alias)
    return exit_obj


def _ensure_jekar_training_complex(workshop):
    room_specs = {
        "north": {
            "reverse": "south",
            "key": "Knifering Pit",
            "aliases": ["pit", "combat room"],
            "desc": "A chalk ring stains the floor around battered posts, hanging sandbags, and scarred sparring dummies. Practice blades, cudgels, and blunted knives rest in easy reach, turning the room into a bruiser's den built for dirty work.",
        },
        "south": {
            "reverse": "north",
            "key": "Blackthread Infirmary",
            "aliases": ["infirmary", "healing room"],
            "desc": "Folding cots line the walls beneath hooded lamps, and a narrow altar sits hidden behind hanging black cloth. Bandages, tonic bottles, stitched masks, and a chalk-marked resurrection slab give the place the feel of a healer's den maintained by people who expect knives in the dark.",
        },
        "east": {
            "reverse": "west",
            "key": "Vial & Venom Bench",
            "aliases": ["apothecary", "venom bench"],
            "desc": "Shelves of dried herbs, poison vials, mortar bowls, and stoppered glass clutter a long side bench. The room smells of camphor, ash root, and sharp spirits, more alley apothecary than noble laboratory.",
        },
        "west": {
            "reverse": "east",
            "key": "Shadewalk Course",
            "aliases": ["shadewalk", "sneaking room"],
            "desc": "Curtains, screens, loose boards, and dangling chimes turn the room into a maze of noise traps and blind corners. It is built to teach quiet feet, patient breathing, and how to disappear while someone is looking straight at you.",
        },
        "northeast": {
            "reverse": "southwest",
            "key": "Whisperglass Sanctum",
            "aliases": ["sanctum", "magic room"],
            "desc": "Sigils in silver chalk circle the floor around a narrow casting stand littered with burned candles and stolen grimoires. The place feels like a cutpurse's answer to a wizard's study: practical, hidden, and prepared for spells cast in a hurry.",
        },
        "northwest": {
            "reverse": "southeast",
            "key": "Crowfeather Range",
            "aliases": ["range", "ranged room"],
            "desc": "Targets crowd the far wall at odd heights, with firing marks scratched into the floor and bundles of arrows stacked by the door. Hooks for bows, throwing knives, and sling stones make the room feel like a rooftop hunter's private range.",
        },
        "southeast": {
            "reverse": "northwest",
            "key": "Snaremaker's Annex",
            "aliases": ["annex", "trap room"],
            "desc": "Pressure plates, bell wires, spring arms, and half-built snares cover the benches here. Every surface offers a lesson in traps, disarming, and how to leave behind one nasty surprise on the way out.",
        },
        "southwest": {
            "reverse": "northeast",
            "key": "Fence's Ledger Den",
            "aliases": ["ledger den", "fence room"],
            "desc": "Coded ledgers, false-bottom strongboxes, marked coins, and pawn tags are spread across a slanted desk. It feels like the counting room of a careful thief, where stolen goods become tidy profit and every favor earns an entry.",
        },
        "up": {
            "reverse": "down",
            "key": "Roofline Perch",
            "aliases": ["perch", "lookout"],
            "desc": "A narrow loft opens onto rafters, signal lanterns, grapnels, and a city map pinned full of sight lines. From here a thief could study approach routes, practice observation, or vanish across the roofs before the watch ever saw a face.",
        },
        "down": {
            "reverse": "up",
            "key": "Underlock Vault",
            "aliases": ["vault", "cellar"],
            "desc": "Trap chests, practice locks, and hidden compartments fill this cool stone cellar. The room doubles as stash and classroom, a place for lockwork, buried secrets, and the sort of valuables never meant for daylight.",
        },
    }

    for direction, spec in room_specs.items():
        room = _ensure_room(spec["key"], spec["desc"], aliases=spec["aliases"], home=workshop)
        _ensure_exit(workshop, direction, room)
        _ensure_exit(room, spec["reverse"], workshop)


def _ensure_workshop_lockpicks(workshop, count=10):
    existing = list(
        ObjectDB.objects.filter(
            db_typeclass_path="typeclasses.lockpick.Lockpick",
            db_location=workshop,
        )
    )

    if len(existing) >= count:
        return

    missing = count - len(existing)
    for _ in range(missing):
        lockpick = create_object(
            "typeclasses.lockpick.Lockpick",
            key="basic lockpick",
            location=workshop,
            home=workshop,
        )
        lockpick.db.grade = "standard"
        lockpick.db.quality = lockpick.get_quality() if hasattr(lockpick, "get_quality") else 1.0
        lockpick.db.durability = 10


def _ensure_limbo_training_dummy():
    limbo = ObjectDB.objects.filter(
        db_key__in=["Limbo", "Jekar's hidden workshop"],
        db_location__isnull=True,
    ).first()
    if not limbo:
        return

    limbo.db_key = "Jekar's hidden workshop"
    limbo.db.desc = (
        "A scarred workbench dominates the room, cluttered with practice locks, bent picks, tension tools, and"
        " half-finished trap parts laid out with a thief's careful order. The air smells of lamp oil, cold iron,"
        " and old leather. A coat stand near the wall holds a long charcoal coat with tiny bells sewn into its"
        " pockets for pickpocket practice, while nearby shelves sag under lockboxes, wire, and hidden-compartment"
        " tricks. Every inch of the place feels built for quiet hands, sharp eyes, and work done behind a bolted door."
    )
    limbo.aliases.add("workshop", "hidden workshop", "jekar's workshop")

    _ensure_jekar_training_complex(limbo)
    _ensure_workshop_lockpicks(limbo)

    dummy = ObjectDB.objects.filter(
        db_key__iexact="training dummy",
        db_location=limbo,
    ).first()

    if not dummy:
        dummy = create_object(
            "typeclasses.npcs.NPC",
            key="training dummy",
            location=limbo,
            home=limbo,
        )

    dummy.db.desc = "A battered sparring dummy rigged to lash back when struck."
    dummy.aliases.add("dummy", "sparring dummy")
    if hasattr(dummy, "ensure_core_defaults"):
        dummy.ensure_core_defaults()
    dummy.db.is_npc = True
    dummy.db.hp = dummy.db.max_hp
    dummy.db.balance = dummy.db.max_balance
    dummy.db.fatigue = 0
    dummy.db.roundtime_end = 0
    dummy.db.in_combat = False
    dummy.db.target = None


def _log_slow_tick(name, started_at, threshold):
    duration = time.perf_counter() - started_at
    if duration > threshold:
        logger.log_warn(f"{name} slow: {duration:.4f}s")


def process_passive_perception(char):
    if not getattr(char, "location", None):
        return

    states = char.db.states or {}
    awareness = states.get("awareness") or "normal"
    observing = bool(states.get("observing"))
    if awareness == "normal" and not observing:
        return

    for obj in char.get_room_observers():
        if not hasattr(obj, "is_hidden") or not obj.is_hidden():
            continue

        result = run_contest(
            char.get_perception_total() + (10 if observing else 0),
            obj.get_stealth_total() + obj.get_hidden_strength(),
        )
        if result["outcome"] == "strong":
            char.msg(f"You suddenly notice {obj.key}!")
            obj.msg(f"{char.key} notices you!")
            obj.break_stealth()


def process_status_tick():
    if not getattr(settings, "ENABLE_GLOBAL_STATUS_TICK", True):
        return

    # Never reintroduce a global per-second sweep that does meaningful work for
    # every character. This tick must stay state-gated so load scales with
    # activity rather than total object count.
    started_at = time.perf_counter()

    for character in _iter_tick_characters():
        character.incoming_attackers = 0
        balance = character.db.balance or 0
        max_balance = character.db.max_balance or 0
        fatigue = character.db.fatigue or 0
        attunement = character.db.attunement or 0
        max_attunement = character.db.max_attunement or 0
        in_combat = bool(character.db.in_combat)
        is_npc = bool(getattr(character.db, "is_npc", False))
        has_ai_target = bool(getattr(character.db, "target", None))
        states = character.db.states or {}
        awareness = states.get("awareness") or "normal"
        observing = bool(states.get("observing"))

        injuries = character.db.injuries or {}
        total_bleed = sum(part.get("bleed", 0) for part in injuries.values()) if injuries else 0
        wound_state = dict(getattr(character.db, "wounds", None) or {})
        has_wound_conditions = bool(int(wound_state.get("poison", 0) or 0) > 0 or int(wound_state.get("disease", 0) or 0) > 0)
        has_magic_state = any(
            bool(states.get(key))
            for key in ["augmentation_buff", "debilitated", "warding_barrier", "utility_light", "exposed_magic", "active_cyclic"]
        )
        active_cyclic = bool(states.get("active_cyclic"))
        has_justice_state = any(
            [
                bool(getattr(character.db, "is_captured", False)),
                bool(getattr(character.db, "in_stocks", False)),
                bool(getattr(character.db, "awaiting_plea", False)),
                bool(getattr(character.db, "jail_timer", 0)),
                bool(getattr(character.db, "fine_due", 0)),
                bool(getattr(character.db, "warrants", None)),
            ]
        )
        has_thief_state = any(
            [
                bool(getattr(character.db, "khri_active", None)),
                bool(getattr(character.db, "slipping", False)),
                bool(getattr(character.db, "theft_memory", None)),
                bool(getattr(character.db, "intimidated", False)),
                bool(getattr(character.db, "roughed", False)),
                bool(getattr(character.db, "staggered", False)),
                bool(getattr(character.db, "marked_target", None)),
                bool(getattr(character.db, "recent_action", False)),
                bool(getattr(character.db, "post_ambush_grace", False)),
                getattr(character.db, "position_state", "neutral") != "neutral",
                getattr(character.db, "attention_state", "idle") != "idle",
            ]
        )
        has_warrior_state = any(
            [
                bool(getattr(character.db, "war_tempo", 0)),
                bool((character.db.states or {}).get("warrior_surge")),
                bool((character.db.states or {}).get("warrior_crush")),
                bool((character.db.states or {}).get("warrior_press")),
                bool((character.db.states or {}).get("warrior_sweep")),
                bool((character.db.states or {}).get("warrior_whirl")),
                bool((character.db.states or {}).get("warrior_hold")),
                bool((character.db.states or {}).get("warrior_frenzy")),
            ]
        )
        has_ranger_state = bool(
            getattr(character, "is_profession", None)
            and character.is_profession("ranger")
        )
        has_empath_state = bool(
            getattr(character, "is_profession", None)
            and character.is_profession("empath")
        )

        if (
            balance >= max_balance and fatigue <= 0 and attunement >= max_attunement and total_bleed <= 0 and not has_wound_conditions
            and not has_magic_state and not in_combat and not has_ai_target and awareness == "normal" and not observing and not has_justice_state and not has_thief_state and not has_warrior_state and not has_ranger_state and not has_empath_state
        ):
            continue

        if in_combat and hasattr(character, "process_combat_range_tick"):
            character.process_combat_range_tick()
            in_combat = bool(character.db.in_combat)

        if balance < max_balance and hasattr(character, "recover_balance"):
            character.recover_balance()
        if fatigue > 0 and hasattr(character, "recover_fatigue"):
            character.recover_fatigue()
        if attunement < max_attunement and hasattr(character, "regen_attunement"):
            character.regen_attunement()
        if has_magic_state and hasattr(character, "process_magic_states"):
            character.process_magic_states()
        if active_cyclic and hasattr(character, "process_cyclic"):
            character.process_cyclic()
        if total_bleed > 0:
            if hasattr(character, "process_bleed"):
                character.process_bleed()
            if hasattr(character, "update_bleed_state"):
                character.update_bleed_state()
        if has_wound_conditions and hasattr(character, "process_wound_conditions"):
            character.process_wound_conditions()
        if awareness != "normal" or observing:
            process_passive_perception(character)
            awareness = (character.db.states or {}).get("awareness") or "normal"
            if awareness == "searching":
                character.set_awareness("normal")
            elif awareness == "alert" and in_combat and not observing:
                character.set_awareness("normal")
        if hasattr(character, "tick_subsystem_state"):
            character.tick_subsystem_state()
        if hasattr(character, "process_justice_tick"):
            character.process_justice_tick()
        if hasattr(character, "process_thief_tick"):
            character.process_thief_tick()
        if hasattr(character, "process_warrior_tick"):
            character.process_warrior_tick()
        if is_npc and hasattr(character, "ai_tick"):
            character.ai_tick()

    for trap in ObjectDB.objects.filter(db_typeclass_path="typeclasses.trap_device.TrapDevice"):
        if hasattr(trap, "at_tick"):
            trap.at_tick()

    _log_slow_tick(
        "process_status_tick",
        started_at,
        getattr(settings, "STATUS_TICK_WARN_SECONDS", 0.01),
    )


def process_learning_tick():
    if not getattr(settings, "ENABLE_GLOBAL_STATUS_TICK", True):
        return

    # Learning is intentionally frequency-separated from combat/status work so
    # rank progression cannot starve the reactor during busy combat periods.
    started_at = time.perf_counter()

    for character in _iter_tick_characters():
        skills = character.db.skills or {}
        has_learning = any((skill_data or {}).get("mindstate", 0) > 0 for skill_data in skills.values())
        has_teaching = bool(character.get_state("learning_from")) if hasattr(character, "get_state") else False
        if not has_learning and not has_teaching:
            continue
        if hasattr(character, "process_learning_pulse"):
            character.process_learning_pulse()
        if has_teaching and hasattr(character, "process_teaching_pulse"):
            character.process_teaching_pulse()

    _log_slow_tick(
        "process_learning_tick",
        started_at,
        getattr(settings, "LEARNING_TICK_WARN_SECONDS", 0.01),
    )


def at_server_init():
    """
    This is called first as the server is starting up, regardless of how.
    """
    pass


def at_server_start():
    """
    This is called every time the server starts up, regardless of
    how it was shut down.
    """
    try:
        TICKER_HANDLER.remove(1, process_status_tick, idstring="global_status_tick", persistent=True)
    except Exception:
        pass

    try:
        TICKER_HANDLER.remove(10, process_learning_tick, idstring="global_learning_tick", persistent=True)
    except Exception:
        pass

    try:
        TICKER_HANDLER.remove(1, process_status_tick, idstring="global_bleed_tick", persistent=True)
    except Exception:
        pass

    try:
        TICKER_HANDLER.remove(1, process_learning_tick, idstring="global_bleed_tick", persistent=True)
    except Exception:
        pass

    if getattr(settings, "ENABLE_GLOBAL_STATUS_TICK", True):
        TICKER_HANDLER.add(1, process_status_tick, idstring="global_status_tick", persistent=True)
        TICKER_HANDLER.add(10, process_learning_tick, idstring="global_learning_tick", persistent=True)

    for character in ObjectDB.objects.filter(
        db_typeclass_path__in=["typeclasses.characters.Character", "typeclasses.npcs.NPC"]
    ):
        if hasattr(character, "ensure_core_defaults"):
            character.ensure_core_defaults()

    for script in search_script("bleed_ticker"):
        if script.typeclass_path == "typeclasses.scripts.BleedTicker":
            script.delete()

    _ensure_limbo_training_dummy()
    build_the_landing()
    _configure_brookhollow_justice()


def at_server_stop():
    """
    This is called just before the server is shut down, regardless
    of it is for a reload, reset or shutdown.
    """
    pass


def at_server_reload_start():
    """
    This is called only when server starts back up after a reload.
    """
    pass


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    pass


def at_server_cold_start():
    """
    This is called only when the server starts "cold", i.e. after a
    shutdown or a reset.
    """
    pass


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or
    reset.
    """
    pass
