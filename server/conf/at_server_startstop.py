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
from evennia.scripts.models import ScriptDB
from evennia.server.models import ServerConfig
from django.conf import settings
from evennia.utils import logger
from evennia.utils.create import create_object, create_script
from twisted.internet import reactor

from engine.services.injury_service import InjuryService
from engine.services.mana_service import ManaService
from typeclasses.objects import BountyBoard
from utils.contests import run_contest
from world.systems.metrics import increment_counter, record_event
from world.systems.timing_audit import register_ticker_metadata, unregister_ticker_metadata
from world.systems.exp_pulse import EXP_TICKER_IDSTRING, PULSE_TICK, exp_pulse_tick, start_exp_ticker
from world.systems.guards import GUARD_TICK_INTERVAL, LEGACY_GUARD_RUNTIME_BLOCK_MSG, cleanup_legacy_guard_behavior_scripts, ensure_landing_guards, get_guard_patrol_mode, get_last_guard_tick_time, guard_has_per_guard_ownership, has_guard_behavior_script, is_diresim_enabled, iter_active_guards, log_legacy_guard_runtime_block, process_guard_tick, sync_all_guard_behavior_scripts
from world.the_landing import build_the_landing
from world.area_forge.map_api import prime_zone_map_cache


_NPC_TICK_CACHE = {"expires_at": 0.0, "objects": []}
_GUARD_REACTOR_CALL = None
_SERVER_START_BOOTSTRAP_CALL = None
_VALID_GUARD_PATROL_OWNERS = {"global_script", "ticker", "reactor", "disabled"}
_GUARD_STARTUP_TRACE_CONFIG_KEY = "guard_startup_diag_trace"
_GUARD_OWNER_HEARTBEAT_CONFIG_KEY = "guard_owner_heartbeat"
_SERVER_START_BOOTSTRAP_CHARACTER_BATCH_SIZE = 25
IDLE_RECOVERY_INTERVAL = 2.0
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

LANDING_AREA_ID = "new_landing"
LANDING_AREA_NAME = "New Landing"

_BROOKHOLLOW_LAWLESS_KEYS = {
    "Crooked Alley",
    "Ratline Lane",
    "Whisper Lane",
    "Fence Cellar",
    "Safehouse Loft",
    "Rag Shop",
    "Pawn Counter",
}


def _guard_startup_trace_enabled():
    return bool(getattr(settings, "ENABLE_GUARD_STARTUP_TRACE", False))


def _guard_startup_force_sync_enabled():
    return bool(getattr(settings, "ENABLE_GUARD_STARTUP_FORCE_SYNC_DIAGNOSTIC", False))


def _append_guard_startup_trace(hook_name, stage, **details):
    if not _guard_startup_trace_enabled():
        return None
    event = {
        "ts": time.time(),
        "hook": str(hook_name),
        "stage": str(stage),
        "details": details,
    }
    trace = list(ServerConfig.objects.conf(key=_GUARD_STARTUP_TRACE_CONFIG_KEY, default=[]) or [])
    trace.append(event)
    trace = trace[-100:]
    ServerConfig.objects.conf(key=_GUARD_STARTUP_TRACE_CONFIG_KEY, value=trace)
    logger.log_info(f"[Guards][StartupDiag] {hook_name} {stage} {details}")
    return event


def _append_guard_owner_heartbeat(owner_name, **details):
    if not _guard_startup_trace_enabled():
        return None
    event = {"ts": time.time(), "owner": str(owner_name), "details": details or {}}
    history = list(ServerConfig.objects.conf(key=_GUARD_OWNER_HEARTBEAT_CONFIG_KEY, default=[]) or [])
    history.append(event)
    if len(history) > 50:
        history = history[-50:]
    ServerConfig.objects.conf(key=_GUARD_OWNER_HEARTBEAT_CONFIG_KEY, value=history)
    return event


def _coerce_bootstrap_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _find_scripts_by_key(script_key):
    if callable(search_script):
        try:
            return list(search_script(script_key) or [])
        except Exception:
            pass
    try:
        return list(ScriptDB.objects.filter(db_key=script_key))
    except Exception:
        return []


def _collect_guard_startup_counts():
    guards = list(iter_active_guards())
    return {
        "guard_count": len(guards),
        "script_attached_count": sum(1 for guard in guards if has_guard_behavior_script(guard)),
        "per_guard_owned_count": sum(1 for guard in guards if guard_has_per_guard_ownership(guard)),
    }


def _run_guard_startup_sync_probe(hook_name, phase, force=False):
    if is_diresim_enabled():
        cleanup = cleanup_legacy_guard_behavior_scripts()
        _append_guard_startup_trace(hook_name, f"{phase}_skipped", reason="diresim_enabled", force=bool(force), **cleanup)
        return cleanup

    if not getattr(settings, "ENABLE_GUARD_SYSTEM", True):
        _append_guard_startup_trace(hook_name, f"{phase}_skipped", reason="guard_system_disabled")
        return None

    before_counts = _collect_guard_startup_counts()
    _append_guard_startup_trace(hook_name, f"{phase}_before_sync", force=bool(force), **before_counts)
    try:
        sync_result = sync_all_guard_behavior_scripts()
    except Exception as error:
        _append_guard_startup_trace(hook_name, f"{phase}_sync_exception", force=bool(force), error=str(error), **before_counts)
        logger.log_trace(f"[Guards][StartupDiag] {hook_name} {phase} sync exception: {error}")
        return None

    after_counts = _collect_guard_startup_counts()
    _append_guard_startup_trace(
        hook_name,
        f"{phase}_after_sync",
        force=bool(force),
        sync_result=sync_result,
        **after_counts,
    )
    return sync_result


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

    _ensure_brookhollow_justice_spaces()


def _should_enable_landing_guard_patrol(room):
    if room is None:
        return False
    if bool(getattr(getattr(room, "db", None), "no_guard", False)):
        return False
    if str(getattr(getattr(room, "db", None), "law_type", "standard") or "standard").strip().lower() == "none":
        return False

    area_name = str(getattr(getattr(room, "db", None), "area", "") or "").strip().lower()
    region_name = str(getattr(getattr(room, "db", None), "region_name", "") or "").strip().lower()
    street_name = str(getattr(getattr(room, "db", None), "street_name", "") or "").strip()
    lane_name = str(getattr(getattr(room, "db", None), "lane_name", "") or "").strip()
    room_key = str(getattr(room, "key", "") or "").strip().lower()
    canonical_area_name = LANDING_AREA_NAME.lower()

    if room_key in {"pillory square", "town jail", "town square", "town green ne"}:
        return True
    if area_name == canonical_area_name and (street_name or lane_name):
        return True
    if region_name == canonical_area_name and (street_name or lane_name):
        return True
    return False


def _configure_landing_guard_patrols():
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        if not _should_enable_landing_guard_patrol(room):
            continue
        room.db.zone = "landing"
        room.db.guard_zone = "landing"
        room.db.is_lawful = True
        room.db.guard_patrol = True


def _get_landing_guard_bootstrap_count():
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        if not bool(getattr(getattr(room, "db", None), "guard_patrol", False)):
            continue
        zone = str(getattr(getattr(room, "db", None), "zone", "") or "").strip().lower()
        if zone != "landing":
            continue
        area_name = str(getattr(getattr(room, "db", None), "area", "") or "").strip().lower()
        if area_name == LANDING_AREA_NAME.lower():
            return 15
    return 15


def _ensure_brookhollow_justice_spaces():
    town_green = _ensure_fishing_supplier_room() or ObjectDB.objects.filter(db_key__iexact="Town Green NE", db_typeclass_path=ROOM_TYPECLASS).first()
    if not town_green:
        return

    guardhouse_exterior = _ensure_room(
        "Guardhouse Exterior",
        (
            "A squat stone guardhouse faces the green with a barred lamp over the door and boot-worn steps below it. "
            "Petitioners, released prisoners, and nervous townsfolk linger here beneath the eyes of posted watchmen."
        ),
        aliases=["guardhouse exterior", "guardhouse entry", "guardhouse"],
        home=town_green,
    )
    guardhouse_exterior.db.is_lawful = True
    guardhouse_exterior.db.law_type = "standard"
    guardhouse_exterior.db.no_guard = False
    guardhouse_exterior.db.high_traffic = True
    guardhouse_exterior.db.guardhouse_exterior = True
    guardhouse_exterior.db.guard_patrol = True
    guardhouse_exterior.db.region = getattr(town_green.db, "region", None) or "brookhollow"

    guardhouse_interior = _ensure_room(
        "Guardhouse Interior",
        (
            "Benches, ledgers, and a heavy evidence locker crowd the narrow room beyond the guardhouse doors. "
            "A clerk's counter faces the entrance while a secure passage deeper inside leads toward the town cells."
        ),
        aliases=["guardhouse interior", "watch office", "evidence room"],
        home=guardhouse_exterior,
    )
    guardhouse_interior.db.is_guardhouse = True
    guardhouse_interior.db.is_lawful = True
    guardhouse_interior.db.law_type = "standard"
    guardhouse_interior.db.no_guard = False
    guardhouse_interior.db.guard_patrol = True
    guardhouse_interior.db.region = getattr(town_green.db, "region", None) or "brookhollow"

    pillory_room = _ensure_room(
        "Pillory Square",
        (
            "A bare public square opens just off the green, built to be seen rather than avoided. "
            "A weathered wooden pillory stands on a low platform where every passerby can judge the day's offenders. "
            "Merchants, idlers, and children on errands all drift through the space, making shame part of the sentence."
        ),
        aliases=["pillory square", "pillory"],
        home=town_green,
    )
    pillory_room.db.is_lawful = True
    pillory_room.db.law_type = "standard"
    pillory_room.db.no_guard = False
    pillory_room.db.high_traffic = True
    pillory_room.db.pillory = True
    pillory_room.db.guard_patrol = True
    pillory_room.db.region = getattr(town_green.db, "region", None) or "brookhollow"

    town_jail = _ensure_room(
        "Town Jail",
        (
            "Iron-barred cells line a cramped stone chamber that smells of damp straw, old lamp smoke, and cold metal. "
            "A turnkey's desk sits beneath a rack of keys while the front of the room opens toward the lawful center of town."
        ),
        aliases=["town jail", "jail"],
        home=town_green,
    )
    town_jail.db.is_lawful = True
    town_jail.db.law_type = "standard"
    town_jail.db.no_guard = False
    town_jail.db.is_jail = True
    town_jail.db.guard_patrol = True
    town_jail.db.region = getattr(town_green.db, "region", None) or "brookhollow"

    _ensure_custom_exit(town_green, "guardhouse", guardhouse_exterior, aliases=["watchhouse"], desc="A short walk leads to the guardhouse beside the green.")
    _ensure_custom_exit(guardhouse_exterior, "green", town_green, aliases=["square", "out"], desc="The town green lies just beyond the guardhouse steps.")
    _ensure_custom_exit(guardhouse_exterior, "inside", guardhouse_interior, aliases=["in", "office"], desc="The main guardroom lies inside the building.")
    _ensure_custom_exit(guardhouse_interior, "outside", guardhouse_exterior, aliases=["out", "entry"], desc="The guardhouse steps lead back toward the green.")
    _ensure_custom_exit(guardhouse_interior, "jail", town_jail, aliases=["cells"], desc="A secured passage leads from the guardroom to the town cells.")
    _ensure_custom_exit(town_jail, "guardhouse", guardhouse_interior, aliases=["office"], desc="The guardhouse interior lies beyond the cell corridor.")
    _ensure_custom_exit(town_green, "pillory", pillory_room, aliases=["stocks"], desc="A short walk leads to the public pillory.")
    _ensure_custom_exit(pillory_room, "green", town_green, aliases=["town green", "square"], desc="The town green lies just beyond the pillory platform.")
    _ensure_custom_exit(pillory_room, "jail", town_jail, aliases=["guardhouse"], desc="A guarded doorway leads toward the town jail.")
    _ensure_custom_exit(town_jail, "square", town_green, aliases=["green", "out"], desc="The lawful heart of town waits outside.")

    evidence_locker = None
    for obj in list(getattr(guardhouse_interior, "contents", []) or []):
        if bool(getattr(getattr(obj, "db", None), "is_evidence_locker", False)):
            evidence_locker = obj
            break
    if not evidence_locker:
        evidence_locker = create_object("typeclasses.objects.Object", key="evidence locker", location=guardhouse_interior, home=guardhouse_interior)
    evidence_locker.db.is_evidence_locker = True
    evidence_locker.db.desc = "A reinforced evidence locker secured with iron bands and a ledger tag for confiscated property."

    pillory = None
    for obj in list(getattr(pillory_room, "contents", []) or []):
        if str(getattr(obj, "key", "") or "").strip().lower() == "wooden pillory":
            pillory = obj
            break
    if not pillory:
        pillory = create_object("typeclasses.objects.Object", key="wooden pillory", location=pillory_room, home=pillory_room)
    pillory.db.is_pillory = True
    pillory.db.desc = "A heavy wooden pillory with iron fittings, positioned where the whole town can see who has been set in it."


def _get_cached_tick_npcs():
    now = time.time()
    if now >= _NPC_TICK_CACHE["expires_at"]:
        _NPC_TICK_CACHE["objects"] = list(ObjectDB.objects.filter(db_typeclass_path="typeclasses.npcs.NPC"))
        _NPC_TICK_CACHE["expires_at"] = now + 30.0
    return list(_NPC_TICK_CACHE["objects"])


def _consume_idle_recovery_window(character, now):
    next_tick_at = float(getattr(character.ndb, "next_idle_recovery_tick_at", 0.0) or 0.0)
    if now < next_tick_at:
        return False
    character.ndb.next_idle_recovery_tick_at = now + IDLE_RECOVERY_INTERVAL
    return True


def _npc_needs_status_tick(npc):
    if not npc or not getattr(npc, "pk", None):
        return False
    if not bool(getattr(npc.db, "is_npc", False)):
        return False
    if hasattr(npc, "is_dead") and npc.is_dead():
        return False

    states = getattr(npc.db, "states", None) or {}
    awareness = states.get("awareness") or "normal"
    observing = bool(states.get("observing"))
    has_magic_state = any(
        bool(states.get(key))
        for key in ["augmentation_buff", "debilitated", "warding_barrier", "utility_light", "exposed_magic"]
    ) or bool(dict(states.get("active_effects") or {}))
    if has_magic_state:
        return True

    if bool(getattr(npc.db, "in_combat", False)) or bool(getattr(npc.db, "target", None)):
        return True
    has_pending_ai_state = bool(states.get("last_seen_target")) or bool(states.get("empath_manipulated")) or bool(states.get("combat_timer"))
    if has_pending_ai_state:
        next_ai_tick_at = float(getattr(getattr(npc, "ndb", None), "next_ai_tick_at", 0.0) or 0.0)
        if time.time() >= next_ai_tick_at:
            return True
    if awareness != "normal" or observing:
        return True

    balance = int(getattr(npc.db, "balance", 0) or 0)
    max_balance = int(getattr(npc.db, "max_balance", 0) or 0)
    fatigue = int(getattr(npc.db, "fatigue", 0) or 0)
    attunement = int(getattr(npc.db, "attunement", 0) or 0)
    max_attunement = int(getattr(npc.db, "max_attunement", 0) or 0)
    if balance < max_balance or fatigue > 0 or attunement < max_attunement:
        return True

    injuries = getattr(npc.db, "injuries", None) or {}
    if isinstance(injuries, dict) and any(int((part or {}).get("bleed", 0) or 0) > 0 for part in injuries.values()):
        return True
    wounds = dict(getattr(npc.db, "wounds", None) or {})
    if int(wounds.get("poison", 0) or 0) > 0 or int(wounds.get("disease", 0) or 0) > 0:
        return True

    return False


def _iter_tick_characters():
    active = {}
    active_rooms = {}

    try:
        sessions = list(SESSION_HANDLER.values()) if hasattr(SESSION_HANDLER, "values") else []
    except Exception:
        sessions = []

    for session in sessions:
        puppet = session.get_puppet() if hasattr(session, "get_puppet") else None
        if puppet and getattr(puppet, "pk", None):
            active[puppet.pk] = puppet
            room = getattr(puppet, "location", None)
            if room and getattr(room, "pk", None):
                active_rooms[room.pk] = room

    for room in active_rooms.values():
        for obj in getattr(room, "contents", []):
            if not _npc_needs_status_tick(obj):
                continue
            active[obj.pk] = obj

    return list(active.values())


def _ensure_room(key, desc, aliases=None, home=None):
    room = ObjectDB.objects.filter(db_key=key, db_location__isnull=True).first()
    if not room:
        room = create_object(ROOM_TYPECLASS, key=key, home=home)

    room.db.desc = desc
    room.home = home or room.home or room
    if aliases:
        for alias in aliases:
            room.aliases.add(alias)
    return room


def _find_tagged_room(tag_key):
    if not tag_key:
        return None
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        try:
            if room.tags.has(str(tag_key)):
                return room
        except Exception:
            continue
    return None


def _find_exit(room, *names):
    if not room:
        return None
    wanted = {str(name or "").strip().lower() for name in names if str(name or "").strip()}
    if not wanted:
        return None
    for exit_obj in list(getattr(room, "exits", []) or []):
        key = str(getattr(exit_obj, "key", "") or "").strip().lower()
        aliases = {str(alias or "").strip().lower() for alias in getattr(getattr(exit_obj, "aliases", None), "all", lambda: [])()}
        if key in wanted or aliases.intersection(wanted):
            return exit_obj
    return None


def _find_empath_guild_duplicates():
    rooms = []
    seen_ids = set()
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS, db_key__iexact="Empath Guild"):
        if room.id in seen_ids:
            continue
        rooms.append(room)
        seen_ids.add(room.id)
    tagged_room = _find_tagged_room("guild_empath")
    if tagged_room and tagged_room.id not in seen_ids:
        rooms.append(tagged_room)
        seen_ids.add(tagged_room.id)

    larkspur_lane_room = ObjectDB.objects.get_id(4280)
    lane_guild_exit = None
    if larkspur_lane_room and str(getattr(larkspur_lane_room, "key", "") or "") == "Larkspur Lane, Midway":
        lane_guild_exit = _find_exit(larkspur_lane_room, "guild", "north")

    canonical_room = tagged_room or getattr(lane_guild_exit, "destination", None)
    duplicates = [room for room in rooms if canonical_room and room.id != canonical_room.id]
    non_room_matches = list(
        ObjectDB.objects.filter(db_key__iexact="Empath Guild").exclude(db_typeclass_path=ROOM_TYPECLASS)
    )
    return canonical_room, duplicates, non_room_matches


def _warn_empath_guild_duplicates():
    canonical_room, duplicates, non_room_matches = _find_empath_guild_duplicates()
    if not duplicates and not non_room_matches:
        return

    canonical_label = "missing"
    if canonical_room:
        canonical_label = f"{canonical_room.key}(#{canonical_room.id})"
    duplicate_labels = ", ".join(f"{room.key}(#{room.id})" for room in duplicates)
    collision_labels = ", ".join(
        f"{obj.key}(#{obj.id}, {obj.db_typeclass_path})" for obj in non_room_matches
    )
    logger.log_warn(
        f"Empath Guild duplicate rooms detected. Canonical room: {canonical_label}. Duplicate rooms: {duplicate_labels}. "
        f"Same-name non-room objects: {collision_labels}. Use tools/empath_guild_maintenance.py to deprecate or delete duplicates in a controlled pass."
    )


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


def _ensure_custom_exit(src, key, dest, aliases=None, desc=None, existing_keys=None):
    exit_obj = None
    for candidate in [key, *(list(existing_keys or []))]:
        exit_obj = ObjectDB.objects.filter(db_key__iexact=candidate, db_location=src).first()
        if exit_obj:
            break
    if not exit_obj:
        exit_obj = create_object(
            EXIT_TYPECLASS,
            key=key,
            aliases=list(aliases or []),
            location=src,
            destination=dest,
            home=src,
        )
    else:
        exit_obj.key = key
        exit_obj.destination = dest
        exit_obj.aliases.clear()
        for alias in list(aliases or []):
            exit_obj.aliases.add(alias)
    if not exit_obj.aliases.all():
        for alias in list(aliases or []):
            exit_obj.aliases.add(alias)
    if desc:
        exit_obj.db.desc = desc
    for candidate in list(existing_keys or []):
        duplicate = ObjectDB.objects.filter(db_key__iexact=candidate, db_location=src).exclude(id=exit_obj.id).first()
        if duplicate:
            duplicate.delete()
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
    for alias in ["workshop", "hidden workshop", "jekar's workshop"]:
        limbo.aliases.add(alias)

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
    for alias in ["dummy", "sparring dummy"]:
        dummy.aliases.add(alias)
    if hasattr(dummy, "ensure_core_defaults"):
        dummy.ensure_core_defaults()
    dummy.db.is_npc = True
    dummy.db.hp = dummy.db.max_hp
    dummy.db.balance = dummy.db.max_balance
    dummy.db.fatigue = 0
    dummy.db.roundtime_end = 0
    dummy.db.in_combat = False
    dummy.db.target = None


def _ensure_named_object(key, location, desc, aliases=None, typeclass="typeclasses.objects.Object"):
    obj = ObjectDB.objects.filter(db_key=key, db_location=location).first()
    if not obj:
        obj = create_object(typeclass, key=key, location=location, home=location)
    obj.db.desc = desc
    if getattr(obj.db, "weight", None) is None:
        obj.db.weight = 1.0
    if aliases:
        for alias in aliases:
            obj.aliases.add(alias)
    return obj


def _ensure_named_npc(key, location, desc, aliases=None, typeclass="typeclasses.npcs.NPC"):
    npc = ObjectDB.objects.filter(db_key__iexact=key).first()
    if not npc:
        npc = create_object(typeclass, key=key, location=location, home=location)
    elif getattr(npc, "location", None) != location:
        npc.move_to(location, quiet=True, use_destination=False)
    npc.home = location
    npc.db.desc = desc
    npc.db.is_npc = True
    if aliases:
        for alias in aliases:
            npc.aliases.add(alias)
    return npc


def _ensure_fishing_supplier_room():
    room = ObjectDB.objects.get_id(4305)
    if not room:
        logger.log_warn("Fishing room normalization skipped because room #4305 was not found.")
        return None

    room.key = "Town Green NE"
    room.db.desc = (
        "A wedge of town green opens between worn stone walks and low iron edging, giving the district a rare pocket of quiet. "
        "Trim grass and a few shade trees soften the square, while a broad pond occupies the northeastern side beneath a simple wooden rail. "
        "The water is calm enough for fishing, broken by reeds near the bank, drifting insects over the shallows, and the occasional ring spreading across the surface where something feeds below."
    )
    room.db.fishable = True
    room.db.fish_group = "River 1"
    room.db.area = getattr(room.db, "area", None) or "The Landing"
    room.db.region_name = getattr(room.db, "region_name", None) or "The Landing"
    for alias in ["town green ne", "town green", "green", "pond", "park"]:
        room.aliases.add(alias)
    room.save()
    return room


def _ensure_fishing_supplier_npc():
    room = _ensure_fishing_supplier_room()
    if not room:
        logger.log_warn("Fishing supplier spawn skipped because room #4305 was not found.")
        return None

    supplier = _ensure_named_npc(
        "Old Maren",
        room,
        (
            "An older woman with weathered hands and a patient expression. "
            "A small collection of fishing gear sits neatly beside her, along with a scale and a few empty baskets."
        ),
        aliases=["maren", "old maren", "supplier", "fish buyer"],
        typeclass="typeclasses.fishing_supplier.FishingSupplier",
    )
    supplier.db.is_fishing_supplier = True
    supplier.db.is_fish_buyer = True
    supplier.db.is_vendor = True
    supplier.db.vendor_type = "fish_buyer"
    supplier.db.accepted_item_types = ["fish", "fish_meat", "fish_skin", "junk"]
    supplier.db.trade_difficulty = 20
    supplier.db.trophy_sale_bonus_multiplier = 1.25
    return supplier


def _resolve_landing_arrival_room():
    preferred_regions = {"Central Crossing", "Upper Crossing", "North Crossing", "Lower Crossing"}
    landing_rooms = []
    for room in ObjectDB.objects.filter(db_typeclass_path=ROOM_TYPECLASS):
        if getattr(getattr(room, "db", None), "area", None) == "The Landing":
            landing_rooms.append(room)
    for room in landing_rooms:
        if getattr(room.db, "region_name", None) in preferred_regions:
            return room
    return landing_rooms[0] if landing_rooms else None


def _ensure_tutorial_goblin(room):
    goblin = ObjectDB.objects.filter(db_key__iexact="training goblin", db_location=room).first()
    if not goblin:
        goblin = create_object("typeclasses.npcs.NPC", key="training goblin", location=room, home=room)
    goblin.db.desc = "A scrawny goblin skulks here with more bluster than real menace, clearly meant for first lessons in combat."
    goblin.aliases.add("goblin")
    goblin.db.is_npc = True
    goblin.db.coin_min = 10
    goblin.db.coin_max = 20
    goblin.db.has_coins = True
    goblin.db.hp = 35
    goblin.db.max_hp = 35
    goblin.db.balance = 80
    goblin.db.max_balance = 80
    goblin.db.fatigue = 0
    return goblin


def _ensure_tutorial_vendor(room):
    vendor = ObjectDB.objects.filter(db_key__iexact="Quartermaster Nella", db_location=room).first()
    if not vendor:
        vendor = create_object("typeclasses.vendor.Vendor", key="Quartermaster Nella", location=room, home=room)
    vendor.db.desc = "A practical quartermaster watches new arrivals with patient eyes, ready to explain how trade works before the wider city starts charging for mistakes."
    for alias in ["nella", "quartermaster", "shopkeeper", "vendor"]:
        vendor.aliases.add(alias)
    vendor.db.vendor_type = "general"
    vendor.db.inventory = ["book", "gem pouch", "lockpick"]
    vendor.db.is_shopkeeper = True
    return vendor


def _cleanup_tutorial_helper_characters(rooms):
    tutorial_room_ids = {getattr(room, "id", None) for room in rooms.values()}
    role_targets = {
        "Marshal Vey": rooms.get("Wake Room"),
        "Pip the Gremlin": rooms.get("Intake Hall"),
    }

    for key, target_room in role_targets.items():
        matches = list(ObjectDB.objects.filter(db_key__iexact=key))
        if not matches:
            continue
        keep = next((obj for obj in matches if getattr(getattr(obj, "location", None), "id", None) == getattr(target_room, "id", None)), matches[0])
        if target_room and getattr(keep, "location", None) != target_room:
            keep.move_to(target_room, quiet=True)
        for extra in matches:
            if extra == keep:
                continue
            if bool(getattr(extra, "has_account", False)):
                continue
            extra.delete()

    for obj in ObjectDB.objects.filter(db_key__istartswith="entryfix"):
        location_id = getattr(getattr(obj, "location", None), "id", None)
        if bool(getattr(obj, "has_account", False)):
            continue
        if location_id in tutorial_room_ids or location_id is None:
            obj.delete()


def _ensure_new_player_tutorial():
    from typeclasses.objects import ChargenMirror, Object
    from systems import aftermath
    from world.areas.crossing.cleric_guild import ensure_crossing_cleric_guildhall
    from world.areas.crossing.empath_guild import ensure_crossing_empath_guildhall

    room_specs = {
        "Intake Chamber": {
            "aliases": ["intake", "chamber"],
            "desc": "Lantern light settles across slate floors scored with old lines, as if many have stood here before you and been measured the same way.\n\nThe air smells faintly of oil and leather.\n\nA lone figure waits, watching.\n\nThe only open path leads east.",
        },
        "Training Hall": {
            "aliases": ["hall", "training"],
            "desc": "The space opens, but only slightly.\n\nWeapons line the walls. Nothing polished. Nothing ceremonial.\n\nEverything here has been used.",
        },
        "Practice Yard": {
            "aliases": ["yard", "practice"],
            "desc": "The yard is already in motion. Steel, movement, and overlapping voices turn the space from drill ground into something closer to a breach that never fully ended.\n\nThe only open path leads east.",
        },
    }

    rooms = {}
    for key, spec in room_specs.items():
        room = _ensure_room(key, spec["desc"], aliases=spec["aliases"])
        room.db.area = "New Player Onboarding"
        room.db.region_name = "Onboarding"
        room.db.is_tutorial = True
        room.db.is_onboarding = True
        rooms[key] = room

    _ensure_exit(rooms["Intake Chamber"], "east", rooms["Training Hall"])
    _ensure_exit(rooms["Training Hall"], "east", rooms["Practice Yard"])

    landing_room = _resolve_landing_arrival_room()

    threshold_specs = {
        "Outer Yard": {
            "aliases": ["yard", "outer"],
            "desc": "The space opens wider than the rooms behind you.\n\nStone gives way to packed earth, worn by movement rather than training.\n\nA few figures pass through without stopping. No one watches you here.\n\nThe path continues east. A narrower passage cuts north.",
        },
        "Market Approach": {
            "aliases": ["market", "approach"],
            "desc": "The air shifts as you move forward--voices, movement, the low hum of trade.\n\nStalls line the edges of the street, loosely arranged but well-worn.\n\nNo one stops you. No one guides you.",
        },
        "Side Passage": {
            "aliases": ["passage", "side"],
            "desc": "The passage narrows, the sound of the yard fading behind you.\n\nLess traffic here. Fewer eyes.\n\nThe ground is uneven, marked by use but not care.",
        },
    }
    threshold_rooms = {}
    for key, spec in threshold_specs.items():
        room = _ensure_room(key, spec["desc"], aliases=spec["aliases"])
        room.db.area = "Threshold Zone"
        room.db.region_name = "Threshold"
        room.db.is_first_area = True
        threshold_rooms[key] = room

    larkspur_lane_room = ObjectDB.objects.get_id(4280)
    lane_guild_exit = None
    if larkspur_lane_room and str(getattr(larkspur_lane_room, "key", "") or "") == "Larkspur Lane, Midway":
        lane_guild_exit = _find_exit(larkspur_lane_room, "guild", "north")

    empath_rooms = ensure_crossing_empath_guildhall()
    empath_guild = empath_rooms["main_hall"]
    empath_guild.db.desc = aftermath.append_guild_triage_detail(str(getattr(empath_guild.db, "desc", "") or ""))
    aftermath.ensure_empath_orderly(empath_guild)

    ensure_crossing_cleric_guildhall()

    ranger_guild = _find_tagged_room("guild_ranger")
    if not ranger_guild:
        ranger_guild = _ensure_room(
            "Ranger Guild",
            "A tucked-away guild hall opens beneath sheltered beams and leaf-shadowed lantern light. A broad working table, weapon pegs, and neatly kept packs turn the room into equal parts camp and command post.",
            aliases=["ranger hall", "guild hall"],
        )

    ranger_map_rooms = {
        "Ranger Guild": {
            "room": ranger_guild,
            "desc": "A tucked-away guild hall opens beneath sheltered beams and leaf-shadowed lantern light. A broad working table, weapon pegs, and neatly kept packs turn the room into equal parts camp and command post.",
            "aliases": ["guild hall", "hall"],
            "coords": (0, 0),
        },
        "Ranger Guild Vestibule": {
            "desc": "A narrow vestibule buffers the guild proper from the alley beyond. Boots dry by the wall, spare ropes hang from pegs, and the place smells faintly of rain and worked leather.",
            "aliases": ["vestibule", "entry"],
            "coords": (-1, 0),
        },
        "Quiet Court": {
            "desc": "A small open court gives the guild a pocket of air and silence. Stone, timber, and trimmed greenery keep it hidden from the lane while still feeling close to the city around it.",
            "aliases": ["court", "yard"],
            "coords": (-2, 0),
        },
        "Storeroom": {
            "desc": "Shelves of field gear, bundled herbs, cordage, spare arrows, and carefully wrapped supplies line the walls in precise order.",
            "aliases": ["store", "storage"],
            "coords": (0, -1),
        },
        "Rope Walk": {
            "desc": "A narrow landing sits beside the first rise into the guild's climbing lanes. The low blind above looks reachable, but only if you stop fighting the rope and start reading it.",
            "aliases": ["rope walk", "rope landing"],
            "coords": (-1, -1),
        },
        "Low Blind": {
            "desc": "A tucked platform of rough boards and netting gives the first true perch above the yard. The climb onward is tighter and less forgiving than the stretch below.",
            "aliases": ["blind", "low blind"],
            "coords": (-1, -2),
        },
        "Middle Fort": {
            "desc": "A higher timber fort braces itself against the trunk and wind. From here, the final route narrows into a climb most people would rather admire than attempt. High above, the High Hide waits where not many reach it.",
            "aliases": ["fort", "middle fort"],
            "coords": (-1, -3),
        },
        "High Hide": {
            "desc": "A compact hide is lashed high into the branches, half perch and half command post. The city spreads below in quiet lines, and every piece of gear here looks chosen by someone who had to carry it up themselves.",
            "aliases": ["high hide", "hide", "lookout"],
            "coords": (-1, -4),
        },
        "Tunnel Access": {
            "desc": "A low stone corridor slips away from the main hall, quiet and dry, with enough space for a ranger to move gear without drawing notice.",
            "aliases": ["tunnel", "corridor"],
            "coords": (0, 1),
        },
        "Gate Walk": {
            "desc": "The passage broadens near a stout gate and a concealed turn in the stonework, suggesting routes beyond the guild for those who know where to go.",
            "aliases": ["gate walk", "gate"],
            "coords": (0, 2),
        },
    }

    ranger_build_tag = "ranger-guild-map"
    for room_name, spec in ranger_map_rooms.items():
        room = spec.get("room") or _ensure_room(room_name, spec["desc"], aliases=spec.get("aliases"))
        spec["room"] = room
        room.key = room_name
        room.db.desc = spec["desc"]
        room.db.area = "Ranger Guild"
        room.db.region_name = "The Landing"
        room.db.map_x = spec["coords"][0]
        room.db.map_y = spec["coords"][1]
        room.tags.add(ranger_build_tag, category="build")

    ranger_guild = ranger_map_rooms["Ranger Guild"]["room"]
    ranger_guild.db.guild_tag = "ranger_guildhall"
    ranger_guild.tags.add("guild_ranger")
    ranger_guild.tags.add("ranger_guild")
    ranger_guild.tags.add("ranger_guildhall")
    ranger_guild.tags.add("poi_guild_ranger")

    cracked_bell_alley = ObjectDB.objects.get_id(4244)
    if cracked_bell_alley and str(getattr(cracked_bell_alley, "key", "") or "") == "Cracked Bell Alley, East Reach":
        cracked_bell_alley.tags.add("guild_access_ranger")
        alley_to_guild = _ensure_custom_exit(
            cracked_bell_alley,
            "north",
            ranger_guild,
            aliases=["guild", "ranger", "ranger guild", "door"],
            desc="A discreet guild door is worked into the quieter stonework here, easy to miss unless you know to look for it.",
            existing_keys=["guild", "door"],
        )
        alley_to_guild.db.exit_display_name = ""
        guild_to_alley = _ensure_custom_exit(
            ranger_guild,
            "south",
            cracked_bell_alley,
            aliases=["out", "street", "alley", "back"],
            existing_keys=["out", "trail", "passage"],
        )
        guild_to_alley.db.exit_display_name = ""

    side_passage = threshold_rooms.get("Side Passage")
    if side_passage:
        side_passage.tags.remove("guild_access_ranger")
        old_ranger_exit = _find_exit(side_passage, "guild", "trail", "ranger")
        if old_ranger_exit and getattr(old_ranger_exit, "destination", None) == ranger_guild:
            old_ranger_exit.delete()

    guild_rooms = ranger_map_rooms
    vestibule = guild_rooms["Ranger Guild Vestibule"]["room"]
    quiet_court = guild_rooms["Quiet Court"]["room"]
    storeroom = guild_rooms["Storeroom"]["room"]
    rope_walk = guild_rooms["Rope Walk"]["room"]
    low_blind = guild_rooms["Low Blind"]["room"]
    middle_fort = guild_rooms["Middle Fort"]["room"]
    high_hide = guild_rooms["High Hide"]["room"]
    tunnel_access = guild_rooms["Tunnel Access"]["room"]
    gate_walk = guild_rooms["Gate Walk"]["room"]

    quiet_court.db.ranger_resources = ["grass", "stick"]
    low_blind.db.ranger_resources = ["stick"]
    middle_fort.db.ranger_prestige_room = high_hide
    middle_fort.db.ranger_prestige_presence_text = "You catch movement high above in the branches."

    guild_to_vestibule = _ensure_custom_exit(ranger_guild, "west", vestibule, aliases=["door", "vestibule", "entry"], existing_keys=["door"])
    guild_to_vestibule.db.exit_display_name = ""
    vestibule_to_guild = _ensure_custom_exit(vestibule, "east", ranger_guild, aliases=["door", "guild", "hall"], existing_keys=["door"])
    vestibule_to_guild.db.exit_display_name = ""

    vestibule_to_court = _ensure_custom_exit(vestibule, "west", quiet_court, aliases=["court", "path"], existing_keys=[])
    vestibule_to_court.db.exit_display_name = ""
    court_to_vestibule = _ensure_custom_exit(quiet_court, "east", vestibule, aliases=["entry", "vestibule"], existing_keys=[])
    court_to_vestibule.db.exit_display_name = ""

    guild_to_store = _ensure_custom_exit(ranger_guild, "north", storeroom, aliases=["curtain", "curt", "storeroom", "store"], existing_keys=["curtain"])
    guild_to_store.db.exit_display_name = ""
    store_to_guild = _ensure_custom_exit(storeroom, "south", ranger_guild, aliases=["guild", "hall", "back"], existing_keys=[])
    store_to_guild.db.exit_display_name = ""

    vestibule_to_rope = _ensure_custom_exit(vestibule, "down", rope_walk, aliases=["rope", "climb", "climb rope"], existing_keys=["rope", "climb"])
    vestibule_to_rope.db.exit_display_name = ""
    rope_to_vestibule = _ensure_custom_exit(rope_walk, "up", vestibule, aliases=["climb up", "ascend", "rope"], existing_keys=["climb", "down"])
    rope_to_vestibule.db.exit_display_name = ""

    rope_to_low = _ensure_custom_exit(rope_walk, "down", low_blind, aliases=["blind", "low blind", "climb"], existing_keys=["ladder"])
    rope_to_low.db.exit_display_name = ""
    rope_to_low.db.climb_contest = True
    rope_to_low.db.climb_tier = "low"
    rope_to_low.db.climb_difficulty = 5
    rope_to_low.db.climb_failure_destination = rope_walk
    rope_to_low.db.climb_action_command = "climb up"
    rope_to_low.db.climb_action_label = "climb up"
    rope_to_low.db.climb_default_action = True
    low_to_rope = _ensure_custom_exit(low_blind, "down", rope_walk, aliases=["climb down", "descend"], existing_keys=["climb"])
    low_to_rope.db.exit_display_name = ""

    low_to_middle = _ensure_custom_exit(low_blind, "up", middle_fort, aliases=["fort", "middle fort", "climb"], existing_keys=["oakladder"])
    low_to_middle.db.exit_display_name = ""
    low_to_middle.db.climb_contest = True
    low_to_middle.db.climb_tier = "mid"
    low_to_middle.db.climb_difficulty = 15
    low_to_middle.db.climb_failure_destination = low_blind
    low_to_middle.db.climb_action_command = "climb up"
    low_to_middle.db.climb_action_label = "climb up"
    low_to_middle.db.climb_default_action = True
    middle_to_low = _ensure_custom_exit(middle_fort, "down", low_blind, aliases=["climb down", "descend", "climb"], existing_keys=["climb"])
    middle_to_low.db.exit_display_name = ""

    middle_to_high = _ensure_custom_exit(middle_fort, "up", high_hide, aliases=["hide", "high hide", "climb"], existing_keys=[])
    middle_to_high.db.exit_display_name = ""
    middle_to_high.db.climb_contest = True
    middle_to_high.db.climb_tier = "high"
    middle_to_high.db.climb_difficulty = 22
    middle_to_high.db.climb_readiness_rank = 18
    middle_to_high.db.climb_failure_destination = middle_fort
    middle_to_high.db.climb_action_command = "climb up"
    middle_to_high.db.climb_action_label = "climb up"
    middle_to_high.db.climb_default_action = True
    high_to_middle = _ensure_custom_exit(high_hide, "down", middle_fort, aliases=["climb down", "descend", "climb"], existing_keys=[])
    high_to_middle.db.exit_display_name = ""

    guild_to_tunnel = _ensure_custom_exit(ranger_guild, "east", tunnel_access, aliases=["tunnel", "corridor"], existing_keys=["tunnel"])
    guild_to_tunnel.db.exit_display_name = ""
    tunnel_to_guild = _ensure_custom_exit(tunnel_access, "west", ranger_guild, aliases=["guild", "hall", "back"], existing_keys=["north"])
    tunnel_to_guild.db.exit_display_name = ""

    tunnel_to_gate = _ensure_custom_exit(tunnel_access, "east", gate_walk, aliases=["gate"], existing_keys=["south"])
    tunnel_to_gate.db.exit_display_name = ""
    gate_to_tunnel = _ensure_custom_exit(gate_walk, "west", tunnel_access, aliases=["tunnel", "back"], existing_keys=["north"])
    gate_to_tunnel.db.exit_display_name = ""

    elarion = ObjectDB.objects.filter(db_key__iexact="Elarion", db_location=ranger_guild).first()
    if not elarion:
        elarion = create_object("typeclasses.npcs.RangerGuildmaster", key="Elarion", location=ranger_guild, home=ranger_guild)
    elarion.db.is_npc = True
    elarion.db.is_trainer = True
    elarion.db.trains_profession = "ranger"
    elarion.db.guild_role = "guildmaster"
    elarion.db.desc = "A weathered ranger stands with the easy stillness of someone who trusts the woods more than walls. Every strap, knife, and bowstring on Elarion's gear looks worn by use rather than display."
    for alias in ["elarion", "guildmaster", "ranger guildmaster"]:
        elarion.aliases.add(alias)

    bram = _ensure_named_npc(
        "Bram Thornhand",
        quiet_court,
        "A broad-shouldered ranger with scarred hands and an easy stance watches the guild court like a man who has spent years learning what land will give and what it will take.",
        aliases=["bram", "thornhand"],
        typeclass="typeclasses.npcs.BramThornhand",
    )
    bram.db.is_trainer = True
    bram.db.trains_profession = "ranger"
    bram.db.guild_role = "mentor"
    bram.db.mentor_domain = "survival"

    serik = _ensure_named_npc(
        "Serik Vale",
        gate_walk,
        "A lean ranger keeps his bow close and his words spare, every motion measured like a shot he has already decided to take.",
        aliases=["serik", "vale"],
        typeclass="typeclasses.npcs.SerikVale",
    )
    serik.db.is_trainer = True
    serik.db.trains_profession = "ranger"
    serik.db.guild_role = "mentor"
    serik.db.mentor_domain = "hunting"

    lysa = _ensure_named_npc(
        "Lysa Windstep",
        high_hide,
        "A wiry ranger studies the lanes beyond the guild with patient attention, as if she is tracking movement no one else has noticed yet.",
        aliases=["lysa", "windstep"],
        typeclass="typeclasses.npcs.LysaWindstep",
    )
    lysa.db.is_trainer = True
    lysa.db.trains_profession = "ranger"
    lysa.db.guild_role = "mentor"
    lysa.db.mentor_domain = "scouting"
    lysa.db.is_vendor = True
    lysa.db.is_shopkeeper = True
    lysa.db.inventory = ["balanced climbing gloves", "lightweight ranger cloak", "reinforced rope", "fine skinning knife"]
    lysa.db.price_map = {
        "balanced climbing gloves": 18,
        "lightweight ranger cloak": 16,
        "reinforced rope": 14,
        "fine skinning knife": 18,
    }
    lysa.db.browse_action_label = "browse goods"
    lysa.db.browse_action_command = "shop"

    quartermaster = _ensure_named_npc(
        "Quartermaster",
        ranger_guild,
        "A practical quartermaster keeps the guild's everyday gear sorted in disciplined rows, with the look of someone who has no patience for wasted kit.",
        aliases=["quartermaster", "quarter"],
        typeclass="typeclasses.vendor.Vendor",
    )
    quartermaster.db.is_vendor = True
    quartermaster.db.is_shopkeeper = True
    quartermaster.db.inventory = ["basic cloak", "simple boots", "starter pack", "rope", "basic knife"]
    quartermaster.db.price_map = {
        "basic cloak": 8,
        "simple boots": 6,
        "starter pack": 9,
        "rope": 5,
        "basic knife": 6,
    }
    quartermaster.db.shop_intro_lines = ["The quartermaster cracks open a field chest and gestures across the starter kit with a curt nod."]
    quartermaster.db.browse_action_label = "browse goods"
    quartermaster.db.browse_action_command = "shop"

    field_buyer = _ensure_named_npc(
        "Field Buyer",
        quiet_court,
        "A compact trader in travel leathers weighs field goods with a quick eye and a quicker hand for coin.",
        aliases=["buyer", "field buyer"],
        typeclass="typeclasses.vendor.Vendor",
    )
    field_buyer.db.is_vendor = True
    field_buyer.db.is_shopkeeper = True
    field_buyer.db.vendor_type = "general"
    field_buyer.db.accepted_item_types = ["bundle", "braid", "hide"]
    field_buyer.db.sale_multiplier = 1.0
    field_buyer.db.sale_message = "The field buyer checks {item}, nods once, and pays you {value}."

    orren = _ensure_named_npc(
        "Orren Mossbinder",
        storeroom,
        "A quiet ranger tends bundled herbs and field notes with the care of someone who treats old knowledge as a tool instead of a trophy.",
        aliases=["orren", "mossbinder"],
        typeclass="typeclasses.npcs.OrrenMossbinder",
    )
    orren.db.is_trainer = True
    orren.db.trains_profession = "ranger"
    orren.db.guild_role = "mentor"
    orren.db.mentor_domain = "lore"

    aftermath.ensure_poi_tags()

    _ensure_exit(rooms["Practice Yard"], "out", threshold_rooms["Outer Yard"])
    _ensure_exit(rooms["Practice Yard"], "leave", threshold_rooms["Outer Yard"])
    _ensure_exit(threshold_rooms["Outer Yard"], "east", threshold_rooms["Market Approach"])
    _ensure_exit(threshold_rooms["Outer Yard"], "north", threshold_rooms["Side Passage"])
    _ensure_exit(threshold_rooms["Market Approach"], "west", threshold_rooms["Outer Yard"])
    _ensure_exit(threshold_rooms["Side Passage"], "south", threshold_rooms["Outer Yard"])
    if landing_room:
        _ensure_exit(threshold_rooms["Market Approach"], "east", landing_room)

    guide_descriptions = {
        "Intake Chamber": "The Intake Guide watches new arrivals with calm, practiced attention and none of the patience required for wandering minds.",
        "Training Hall": "The Intake Guide stands beside the weapon stand with the stillness of someone already listening for the next mistake.",
        "Practice Yard": "The Intake Guide stays off the line of attack, watching the yard the way other people watch weather turning bad.",
    }
    for room_name, desc in guide_descriptions.items():
        guide = ObjectDB.objects.filter(db_key__iexact="Intake Guide", db_location=rooms[room_name]).first()
        if not guide:
            guide = create_object(
                "typeclasses.onboarding_guide.OnboardingGuide",
                key="Intake Guide",
                location=rooms[room_name],
                home=rooms[room_name],
            )
        guide.db.desc = desc
        guide.db.is_onboarding_guide = True
        for alias in ["guide", "instructor"]:
            guide.aliases.add(alias)
        if not guide.scripts.get("onboarding_guide_prompt"):
            guide.scripts.add("typeclasses.onboarding_scripts.OnboardingGuidePromptScript")

    mirror = ObjectDB.objects.filter(db_key__iexact="assessment mirror", db_location=rooms["Intake Chamber"]).first()
    if not mirror:
        mirror = create_object(ChargenMirror, key="assessment mirror", location=rooms["Intake Chamber"], home=rooms["Intake Chamber"])
    mirror.db.desc = "A tall mirror in a blackened frame. It reflects more than posture and less than mercy."
    mirror.db.is_chargen_mirror = True
    for alias in ["mirror", "glass", "reflection"]:
        mirror.aliases.add(alias)

    gremlin = ObjectDB.objects.filter(db_key__iexact="Intake Gremlin", db_location=rooms["Intake Chamber"]).first()
    if not gremlin:
        gremlin = create_object("typeclasses.npcs.NPC", key="Intake Gremlin", location=rooms["Intake Chamber"], home=rooms["Intake Chamber"])
    gremlin.db.desc = "A narrow gremlin leans against the wall with the patience of someone hoping you choose badly and soon."
    gremlin.db.is_npc = True
    gremlin.db.onboarding_role = "gremlin"
    for alias in ["gremlin"]:
        gremlin.aliases.add(alias)

    sword = ObjectDB.objects.filter(db_key__iexact="training sword", db_location=rooms["Training Hall"]).first()
    if not sword:
        sword = create_object(Object, key="training sword", location=rooms["Training Hall"], home=rooms["Training Hall"])
    sword.db.item_type = "weapon"
    sword.db.weight = 3.0
    sword.db.weapon_type = "light_edge"
    sword.db.skill = "light_edge"
    sword.db.damage_type = "slice"
    sword.db.damage_types = {"slice": 1.0, "impact": 0.0, "puncture": 0.0}
    sword.db.damage = 4
    sword.db.damage_min = 2
    sword.db.damage_max = 5
    sword.db.roundtime = 3.0
    sword.db.weapon_profile = {
        "type": "light_edge",
        "skill": "light_edge",
        "damage": 4,
        "damage_min": 2,
        "damage_max": 5,
        "roundtime": 3.0,
    }
    sword.db.desc = "A blunt-edged training sword balanced for drills, not blood."
    sword.aliases.add("sword")
    sword.aliases.add("weapon")
    sword.aliases.add("blade")

    vest = ObjectDB.objects.filter(db_key__iexact="training vest", db_location=rooms["Training Hall"]).first()
    if not vest:
        vest = create_object("typeclasses.wearables.Wearable", key="training vest", location=rooms["Training Hall"], home=rooms["Training Hall"])
    vest.db.slot = "torso"
    vest.db.weight = 2.0
    vest.db.desc = "A rough leather vest cut for drills and fast buckling, more practical than comfortable."
    vest.db.is_onboarding_training_gear = True
    for alias in ["vest", "armor", "leathers"]:
        vest.aliases.add(alias)

    dummy = ObjectDB.objects.filter(db_key__iexact="training dummy", db_location=rooms["Practice Yard"]).first()
    if not dummy:
        dummy = create_object("typeclasses.npcs.NPC", key="training dummy", location=rooms["Practice Yard"], home=rooms["Practice Yard"])
    dummy.db.desc = "A battered hanging frame marks the edge of the yard, the sort of thing you hit only until something living takes its place."
    dummy.db.is_npc = True
    dummy.db.is_training_dummy = True
    dummy.db.is_tutorial_enemy = True
    dummy.db.onboarding_enemy_role = "training_dummy"
    dummy.db.hp = 999
    dummy.db.max_hp = 999
    dummy.db.balance = 0
    dummy.db.max_balance = 0
    for alias in ["dummy", "post"]:
        dummy.aliases.add(alias)

    vendor = ObjectDB.objects.filter(db_key__iexact="Street Vendor", db_location=threshold_rooms["Market Approach"]).first()
    if not vendor:
        vendor = create_object("typeclasses.vendor.Vendor", key="Street Vendor", location=threshold_rooms["Market Approach"], home=threshold_rooms["Market Approach"])
    vendor.db.desc = "A vendor stands beside a narrow stall with the patience of someone who has seen newcomers arrive before and will see more after you."
    vendor.db.is_vendor = True
    vendor.db.is_shopkeeper = True
    vendor.db.is_threshold_vendor = True
    vendor.db.vendor_type = "general"
    vendor.db.inventory = ["trail bread", "book"]
    vendor.db.price_map = {"trail bread": 0, "book": 20}
    for alias in ["vendor", "merchant", "stallkeeper"]:
        vendor.aliases.add(alias)
    if not vendor.scripts.get("first_area_vendor_prompt"):
        vendor.scripts.add("typeclasses.first_area_scripts.FirstAreaVendorPromptScript")

    traveler = ObjectDB.objects.filter(db_key__iexact="Passing Traveler", db_location=threshold_rooms["Market Approach"]).first()
    if not traveler:
        traveler = create_object("typeclasses.npcs.NPC", key="Passing Traveler", location=threshold_rooms["Market Approach"], home=threshold_rooms["Market Approach"])
    traveler.db.desc = "A traveler pauses only long enough to adjust a strap before moving on again, as if lingering here would count as a decision."
    traveler.db.is_npc = True
    for alias in ["traveler", "passerby"]:
        traveler.aliases.add(alias)

    _ensure_named_object(
        "painted sign",
        threshold_rooms["Market Approach"],
        "A weathered signboard leans against the stall, its lettering rubbed soft by years of hands and weather. The market lies east. The yard remains west.",
        aliases=["sign", "board"],
    )
    _ensure_named_object(
        "broken crate",
        threshold_rooms["Side Passage"],
        "One side has split open and stayed that way. There is nothing hidden here now, only the suggestion that someone once left in a hurry.",
        aliases=["crate", "debris"],
    )
    token = ObjectDB.objects.filter(db_key__iexact="wayfinder token", db_location=threshold_rooms["Side Passage"]).first()
    if not token:
        token = create_object(Object, key="wayfinder token", location=threshold_rooms["Side Passage"], home=threshold_rooms["Side Passage"])
    token.db.weight = 0.1
    token.db.item_value = 2
    token.db.value = 2
    token.db.desc = "A stamped brass token, worn almost smooth at the edges. It is worth very little, but not nothing."
    token.aliases.add("token")

    return rooms["Intake Chamber"]


def _new_player_tutorial_is_built():
    required_room_keys = [
        "Intake Chamber",
        "Training Hall",
        "Practice Yard",
        "Outer Yard",
        "Market Approach",
        "Side Passage",
    ]
    for room_key in required_room_keys:
        room = ObjectDB.objects.filter(db_key__iexact=room_key).first()
        if room is None:
            return False
    return True


def _log_slow_tick(name, started_at, threshold):
    duration = time.perf_counter() - started_at
    from tools.diretest.core.runtime import record_script_delay

    increment_counter("ticker.execute")
    increment_counter(f"ticker.execute.{name}")
    record_event("ticker.execute", duration * 1000.0, metadata={"ticker": name})
    record_script_delay(duration * 1000.0, source=f"ticker:{name}")
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
    now = time.time()

    guard_fallback_due = bool(
        not is_diresim_enabled()
        and getattr(settings, "ENABLE_GUARD_SYSTEM", True)
        and _get_guard_patrol_owner() == "status_fallback"
        and (now - get_last_guard_tick_time()) >= float(GUARD_TICK_INTERVAL)
    )

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
            for key in ["augmentation_buff", "debilitated", "warding_barrier", "utility_light", "exposed_magic"]
        ) or bool(dict(states.get("active_effects") or {}))
        has_justice_state = any(
            [
                bool(getattr(character.db, "is_captured", False)),
                bool(getattr(character.db, "in_stocks", False)),
                bool(getattr(character.db, "in_pillory", False)),
                bool(getattr(character.db, "in_jail", False)),
                bool(getattr(character.db, "awaiting_plea", False)),
                bool(getattr(character.db, "jail_timer", 0)),
                bool(getattr(character.db, "fine_due", 0)),
                bool(getattr(character.db, "justice_debt", 0)),
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
        has_cleric_state = bool(
            getattr(character, "is_profession", None)
            and character.is_profession("cleric")
        )
        soul_state = character.get_soul_state() if hasattr(character, "get_soul_state") else None
        has_soul_state = bool(character.is_dead() and isinstance(soul_state, dict) and soul_state.get("recoverable", False))
        states = character.db.states or {}
        has_recovery_state = bool(states.get("resurrection_fragility") or states.get("resurrection_instability"))

        if (
            balance >= max_balance and fatigue <= 0 and attunement >= max_attunement and total_bleed <= 0 and not has_wound_conditions
            and not has_magic_state and not in_combat and not has_ai_target and awareness == "normal" and not observing and not has_justice_state and not has_thief_state and not has_warrior_state and not has_ranger_state and not has_empath_state and not has_cleric_state and not has_soul_state and not has_recovery_state
        ):
            continue

        active_realtime_state = bool(
            in_combat
            or total_bleed > 0
            or has_wound_conditions
            or has_magic_state
            or has_ai_target
            or awareness != "normal"
            or observing
            or has_justice_state
            or has_thief_state
            or has_warrior_state
            or has_soul_state
            or has_recovery_state
        )
        allow_idle_recovery = active_realtime_state or _consume_idle_recovery_window(character, now)

        if in_combat and hasattr(character, "process_combat_range_tick"):
            character.process_combat_range_tick()
            in_combat = bool(character.db.in_combat)

        if allow_idle_recovery and balance < max_balance and hasattr(character, "recover_balance"):
            character.recover_balance()
        if allow_idle_recovery and fatigue > 0 and hasattr(character, "recover_fatigue"):
            character.recover_fatigue()
        if allow_idle_recovery and attunement < max_attunement and hasattr(character, "regen_attunement"):
            character.regen_attunement()
        if has_magic_state and hasattr(character, "process_magic_states"):
            character.process_magic_states()
        if has_wound_conditions and hasattr(character, "process_wound_conditions"):
            character.process_wound_conditions()
        if awareness != "normal" or observing:
            process_passive_perception(character)
            awareness = (character.db.states or {}).get("awareness") or "normal"
            if awareness == "searching":
                character.set_awareness("normal")
            elif awareness == "alert" and in_combat and not observing:
                character.set_awareness("normal")
        warrior_tick_needed = bool(
            has_warrior_state
            or in_combat
            or bool(getattr(character.db, "active_warrior_berserk", None))
            or bool(getattr(character.db, "active_warrior_roars", None))
            or bool(getattr(character.db, "warrior_roar_effects", None))
            or int(getattr(character.db, "combat_streak", 0) or 0) > 0
            or int(getattr(character.db, "pressure_level", 0) or 0) > 0
            or int(getattr(character.db, "exhaustion", 0) or 0) > 0
        )
        subsystem_tick_needed = bool(has_magic_state or has_ranger_state or has_empath_state or has_cleric_state or warrior_tick_needed)
        passive_subsystem_only = bool(subsystem_tick_needed and not has_magic_state and not warrior_tick_needed and not in_combat)

        if subsystem_tick_needed and (allow_idle_recovery or not passive_subsystem_only) and hasattr(character, "tick_subsystem_state"):
            character.tick_subsystem_state()
        if has_soul_state and hasattr(character, "process_soul_tick"):
            character.process_soul_tick()
        if has_recovery_state and hasattr(character, "process_resurrection_recovery_tick"):
            character.process_resurrection_recovery_tick()
        if has_justice_state and hasattr(character, "process_justice_tick"):
            character.process_justice_tick()
        if has_thief_state and hasattr(character, "process_thief_tick"):
            character.process_thief_tick()
        if warrior_tick_needed and hasattr(character, "process_warrior_tick"):
            character.process_warrior_tick()
        if is_npc and hasattr(character, "ai_tick"):
            character.ai_tick()

    if guard_fallback_due:
        process_guard_tick(source="status_fallback")
    elif (
        bool(getattr(settings, "ENABLE_GUARD_SYSTEM", True))
        and bool(getattr(settings, "ENABLE_GUARD_PATROL_DEBUG", False))
        and (now - get_last_guard_tick_time()) >= float(GUARD_TICK_INTERVAL)
        and _get_guard_patrol_owner() != "status_fallback"
    ):
        logger.log_info(f"[Guards] Status fallback skipped because owner={_get_guard_patrol_owner()}")

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
        if bool(getattr(character.db, "is_npc", False)):
            continue
        skills = character.db.skills or {}
        has_learning = any((skill_data or {}).get("mindstate", 0) > 0 for skill_data in skills.values())
        states = getattr(character.db, "states", None) or {}
        has_teaching = bool(states.get("learning_from"))
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


def _ensure_global_guard_patrol_script():
    from world.systems.guards import _guard_behavior_script_is_zombie

    if is_diresim_enabled():
        log_legacy_guard_runtime_block("_ensure_global_guard_patrol_script")
        _disable_global_guard_patrol_scripts()
        return None

    existing = []
    for script in _find_scripts_by_key("global_guard_patrol"):
        if getattr(script, "typeclass_path", "") == "typeclasses.scripts.GlobalGuardPatrolScript":
            existing.append(script)

    keeper = existing[0] if existing else None
    for duplicate in existing[1:]:
        try:
            duplicate.delete()
        except Exception:
            pass

    if keeper is not None:
        try:
            if _guard_behavior_script_is_zombie(keeper):
                logger.log_info("[Guards] Resetting broken global_guard_patrol script during startup ensure.")
                keeper.stop()
                keeper.start()
            else:
                keeper.start()
        except Exception as error:
            logger.log_trace(f"_ensure_global_guard_patrol_script failed to start existing script: {error}")
        return keeper
    script = create_script("typeclasses.scripts.GlobalGuardPatrolScript", key="global_guard_patrol")
    try:
        script.start()
    except Exception as error:
        logger.log_trace(f"_ensure_global_guard_patrol_script failed to start new script: {error}")
    return script


def _ensure_global_simulation_kernel_script():
    existing = []
    for script in _find_scripts_by_key("global_simulation_kernel"):
        if getattr(script, "typeclass_path", "") == "typeclasses.scripts.GlobalSimulationKernelScript":
            existing.append(script)

    keeper = existing[0] if existing else None
    for duplicate in existing[1:]:
        try:
            duplicate.delete()
        except Exception:
            pass

    if keeper is not None:
        try:
            keeper.start()
        except Exception as error:
            logger.log_trace(f"_ensure_global_simulation_kernel_script failed to start existing script: {error}")
        return keeper

    script = create_script("typeclasses.scripts.GlobalSimulationKernelScript", key="global_simulation_kernel")
    try:
        script.start()
    except Exception as error:
        logger.log_trace(f"_ensure_global_simulation_kernel_script failed to start new script: {error}")
    return script


def _get_guard_patrol_owner():
    owner = str(getattr(settings, "GUARD_PATROL_OWNER", "global_script") or "global_script").strip().lower()
    if owner not in _VALID_GUARD_PATROL_OWNERS:
        logger.log_warn(f"[Guards] Invalid GUARD_PATROL_OWNER={owner!r}; defaulting to 'global_script'.")
        return "global_script"
    return owner


def _guard_patrol_owner_enabled(owner_name):
    if is_diresim_enabled():
        return False
    return bool(getattr(settings, "ENABLE_GUARD_SYSTEM", True) and _get_guard_patrol_owner() == owner_name)


def _disable_global_guard_patrol_scripts():
    for script in _find_scripts_by_key("global_guard_patrol"):
        if getattr(script, "typeclass_path", "") != "typeclasses.scripts.GlobalGuardPatrolScript":
            continue
        try:
            script.delete()
        except Exception:
            pass


def _log_guard_patrol_owner_state():
    owner = _get_guard_patrol_owner()
    mode = get_guard_patrol_mode()
    skipped = []
    for candidate in ("global_script", "ticker", "reactor", "status_fallback", "reactor_fallback"):
        if candidate == owner:
            continue
        skipped.append(candidate)
    logger.log_info(f"[Guards] Patrol owner={owner}; mode={mode}; skipped={', '.join(skipped) if skipped else 'none'}")


def _bootstrap_guard_patrols(hook_name, phase_label="bootstrap"):
    if is_diresim_enabled():
        _append_guard_startup_trace(hook_name, "guard_bootstrap_skipped", phase=phase_label, reason="diresim_enabled")
        _cancel_guard_reactor_tick()
        _disable_global_guard_patrol_scripts()
        cleanup_legacy_guard_behavior_scripts()
        return

    if not getattr(settings, "ENABLE_GUARD_SYSTEM", True):
        return
    _append_guard_startup_trace(hook_name, "guard_bootstrap_entered", phase=phase_label)
    _configure_landing_guard_patrols()
    ensure_landing_guards(count=_get_landing_guard_bootstrap_count())
    if _guard_patrol_owner_enabled("reactor"):
        _schedule_guard_reactor_tick()
    else:
        _cancel_guard_reactor_tick()
    if _guard_patrol_owner_enabled("global_script"):
        _ensure_global_guard_patrol_script()
    else:
        _disable_global_guard_patrol_scripts()
    _run_guard_startup_sync_probe(hook_name, phase_label)


def _bootstrap_diresim_kernel(hook_name):
    if not bool(getattr(settings, "ENABLE_DIRESIM_KERNEL", True)):
        _append_guard_startup_trace(hook_name, "diresim_bootstrap_skipped", reason="kernel_disabled")
        return
    try:
        from world.simulation.registry import register_existing_guards

        _append_guard_startup_trace(hook_name, "diresim_bootstrap_entered")
        script = _ensure_global_simulation_kernel_script()
        summary = register_existing_guards()
        cleanup = cleanup_legacy_guard_behavior_scripts()
        _append_guard_startup_trace(
            hook_name,
            "diresim_bootstrap_finished",
            script_id=_coerce_bootstrap_int(getattr(script, "id", 0) or 0),
            registered=_coerce_bootstrap_int(summary.get("registered", 0) or 0),
            service_count=_coerce_bootstrap_int(summary.get("service_count", 0) or 0),
            removed_legacy_scripts=_coerce_bootstrap_int(cleanup.get("removed_script_count", 0) or 0),
        )
        logger.log_info(
            f"[DireSim] Bootstrap complete from {hook_name}: script={_coerce_bootstrap_int(getattr(script, 'id', 0) or 0)} registered={_coerce_bootstrap_int(summary.get('registered', 0) or 0)} services={_coerce_bootstrap_int(summary.get('service_count', 0) or 0)} removed_legacy_scripts={_coerce_bootstrap_int(cleanup.get('removed_script_count', 0) or 0)}"
        )
    except Exception as error:
        _append_guard_startup_trace(hook_name, "diresim_bootstrap_exception", error=str(error))
        logger.log_err(f"[DireSim] Bootstrap failed during {hook_name}: {error}")
        logger.log_trace(f"[DireSim] Bootstrap failed during {hook_name}: {error}")


def get_diresim_guard_lock_report():
    from world.simulation.kernel import SIM_KERNEL

    active_global_scripts = 0
    for script in _find_scripts_by_key("global_guard_patrol"):
        if getattr(script, "typeclass_path", "") != "typeclasses.scripts.GlobalGuardPatrolScript":
            continue
        if bool(getattr(script, "is_active", False)):
            active_global_scripts += 1

    guard_services = [service for service in SIM_KERNEL.services.values() if hasattr(service, "npc_ids")]
    raw_owner = str(getattr(settings, "GUARD_PATROL_OWNER", "") or "").strip().lower()
    reactor_active = bool(_GUARD_REACTOR_CALL is not None and getattr(_GUARD_REACTOR_CALL, "active", lambda: False)())
    legacy_fallback_registered = bool(
        reactor_active
        or (bool(getattr(settings, "ENABLE_GUARD_SYSTEM", True)) and raw_owner in {"ticker", "status_fallback"})
    )
    return {
        "diresim_enabled": bool(is_diresim_enabled()),
        "legacy_per_guard_scripts_found": sum(1 for guard in iter_active_guards() if has_guard_behavior_script(guard)),
        "legacy_global_guard_script_active": active_global_scripts > 0,
        "legacy_fallback_registered": legacy_fallback_registered,
        "guard_zone_service_count": len(guard_services),
        "guard_zone_registered_count": sum(len(getattr(service, "npc_ids", []) or []) for service in guard_services),
        "legacy_runtime_block_message": LEGACY_GUARD_RUNTIME_BLOCK_MSG,
    }


def _validate_diresim_guard_lock(hook_name):
    report = get_diresim_guard_lock_report()
    if not bool(report.get("diresim_enabled", False)):
        return report

    violations = []
    if int(report.get("legacy_per_guard_scripts_found", 0) or 0) > 0:
        violations.append(f"legacy_per_guard_scripts_found={int(report.get('legacy_per_guard_scripts_found', 0) or 0)}")
    if bool(report.get("legacy_global_guard_script_active", False)):
        violations.append("legacy_global_guard_script_active=True")
    if bool(report.get("legacy_fallback_registered", False)):
        violations.append("legacy_fallback_registered=True")

    if violations:
        logger.log_err(f"[DireSim] Legacy guard seal validation failed during {hook_name}: {'; '.join(violations)}")
        if bool(getattr(settings, "STRICT_DIRESIM_LEGACY_GUARD_SEAL", False)):
            raise RuntimeError(f"DireSim legacy guard seal violation: {'; '.join(violations)}")
    else:
        logger.log_info(
            f"[DireSim] Guard seal validated during {hook_name}: services={int(report.get('guard_zone_service_count', 0) or 0)} registered_guards={int(report.get('guard_zone_registered_count', 0) or 0)}"
        )
    return report


def _cancel_server_start_bootstrap_call():
    global _SERVER_START_BOOTSTRAP_CALL

    if _SERVER_START_BOOTSTRAP_CALL is not None and getattr(_SERVER_START_BOOTSTRAP_CALL, "active", lambda: False)():
        try:
            _SERVER_START_BOOTSTRAP_CALL.cancel()
        except Exception:
            pass
    _SERVER_START_BOOTSTRAP_CALL = None


def _run_deferred_server_start_bootstrap_after_character_init():
    try:
        _append_guard_startup_trace("at_server_start", "bootstrap_after_character_init", deferred=True)

        for script in search_script("bleed_ticker"):
            if script.typeclass_path == "typeclasses.scripts.BleedTicker":
                script.delete()
        _append_guard_startup_trace("at_server_start", "bootstrap_after_bleed_cleanup", deferred=True)

        _ensure_limbo_training_dummy()
        _append_guard_startup_trace("at_server_start", "bootstrap_after_limbo_dummy", deferred=True)
        build_the_landing(
            area_id=LANDING_AREA_ID,
            skip_if_built=True,
            diag_hook=lambda stage, **details: _append_guard_startup_trace(
                "at_server_start",
                f"build_the_landing_{stage}",
                deferred=True,
                **details,
            ),
        )
        _append_guard_startup_trace("at_server_start", "bootstrap_after_build_landing", deferred=True)
        try:
            primed_zones = prime_zone_map_cache(["new_landing", "empath-guild-map", "ranger-guild-map"])
            if primed_zones:
                logger.log_info(f"Primed AreaForge zone map cache: {', '.join(primed_zones)}")
        except Exception:
            logger.log_warn("AreaForge zone map cache priming failed during server start.")
        _append_guard_startup_trace("at_server_start", "bootstrap_after_zone_prime", deferred=True)
        if _new_player_tutorial_is_built():
            _append_guard_startup_trace("at_server_start", "bootstrap_skip_tutorial", deferred=True, reason="warm_start_already_built")
        else:
            logger.log_info("Ensuring new player tutorial bootstrap.")
            tutorial_entry = _ensure_new_player_tutorial()
            if tutorial_entry:
                logger.log_info(f"New player tutorial ready at {tutorial_entry.key}(#{tutorial_entry.id}).")
        _append_guard_startup_trace("at_server_start", "bootstrap_after_tutorial", deferred=True)
        try:
            from systems import aftermath

            aftermath.ensure_poi_tags()
        except Exception:
            logger.log_warn("[Aftermath] Failed to ensure POI tags during server start.")
        _append_guard_startup_trace("at_server_start", "bootstrap_after_aftermath", deferred=True)
        _warn_empath_guild_duplicates()
        _append_guard_startup_trace("at_server_start", "bootstrap_after_duplicate_warn", deferred=True)
        _configure_brookhollow_justice()
        _append_guard_startup_trace("at_server_start", "bootstrap_after_justice", deferred=True)
        _ensure_fishing_supplier_npc()
        _append_guard_startup_trace("at_server_start", "bootstrap_finished", deferred=True)

        if _guard_startup_force_sync_enabled():
            _run_guard_startup_sync_probe("at_server_start", "final", force=True)

        _append_guard_startup_trace("at_server_start", "finished", deferred=True)
    except Exception as error:
        _append_guard_startup_trace("at_server_start", "exception", deferred=True, error=str(error))
        logger.log_trace(f"[Guards][StartupDiag] deferred at_server_start exception: {error}")
        raise


def _run_deferred_character_bootstrap_batch(characters, start_index=0):
    batch_size = int(getattr(settings, "SERVER_START_BOOTSTRAP_CHARACTER_BATCH_SIZE", _SERVER_START_BOOTSTRAP_CHARACTER_BATCH_SIZE) or _SERVER_START_BOOTSTRAP_CHARACTER_BATCH_SIZE)
    end_index = min(len(characters), int(start_index) + max(1, batch_size))

    try:
        for character in characters[int(start_index):end_index]:
            if hasattr(character, "ensure_core_defaults"):
                character.ensure_core_defaults()
            InjuryService.bootstrap_scheduled_effects(character)
            ManaService.bootstrap_scheduled_effects(character)
    except Exception as error:
        _append_guard_startup_trace("at_server_start", "exception", deferred=True, error=str(error))
        logger.log_trace(f"[Guards][StartupDiag] deferred character bootstrap exception: {error}")
        raise

    if end_index >= len(characters):
        reactor.callLater(0, _run_deferred_server_start_bootstrap_after_character_init)
        return

    reactor.callLater(0, _run_deferred_character_bootstrap_batch, characters, end_index)


def _run_deferred_server_start_bootstrap():
    global _SERVER_START_BOOTSTRAP_CALL

    _SERVER_START_BOOTSTRAP_CALL = None
    try:
        if getattr(settings, "ENABLE_SERVER_STARTUP_BOOTSTRAP", True):
            _append_guard_startup_trace("at_server_start", "bootstrap_entered", deferred=True)
            characters = list(
                ObjectDB.objects.filter(db_typeclass_path__in=["typeclasses.characters.Character", "typeclasses.npcs.NPC"])
            )
            reactor.callLater(0, _run_deferred_character_bootstrap_batch, characters, 0)
            return

        if _guard_startup_force_sync_enabled():
            _run_guard_startup_sync_probe("at_server_start", "final", force=True)

        _append_guard_startup_trace("at_server_start", "finished", deferred=True)
    except Exception as error:
        _append_guard_startup_trace("at_server_start", "exception", deferred=True, error=str(error))
        logger.log_trace(f"[Guards][StartupDiag] deferred at_server_start exception: {error}")
        raise


def _schedule_server_start_bootstrap():
    global _SERVER_START_BOOTSTRAP_CALL

    _cancel_server_start_bootstrap_call()
    _append_guard_startup_trace("at_server_start", "bootstrap_deferred_scheduled")
    _SERVER_START_BOOTSTRAP_CALL = reactor.callLater(1.0, _run_deferred_server_start_bootstrap)


def _run_guard_ticker_tick():
    if is_diresim_enabled():
        log_legacy_guard_runtime_block("_run_guard_ticker_tick")
        _append_guard_owner_heartbeat("ticker", tick_source="ticker", ok=False, skipped="blocked_by_diresim")
        return

    summary = process_guard_tick(source="ticker")
    _append_guard_owner_heartbeat(
        "ticker",
        tick_source=str(summary.get("source") or "ticker"),
        ok=bool(summary.get("ok", False)),
        skipped=str(summary.get("skipped") or ""),
        moved_count=int(summary.get("moved_count", 0) or 0),
        idle_count=int(summary.get("idle_count", 0) or 0),
        global_owned_count=int(summary.get("global_owned_count", 0) or 0),
        per_guard_owned_count=int(summary.get("per_guard_owned_count", 0) or 0),
        skipped_per_guard_owned_count=int(summary.get("skipped_per_guard_owned_count", 0) or 0),
    )


def _cancel_guard_reactor_tick():
    global _GUARD_REACTOR_CALL

    if _GUARD_REACTOR_CALL is not None and getattr(_GUARD_REACTOR_CALL, "active", lambda: False)():
        try:
            _GUARD_REACTOR_CALL.cancel()
            _append_guard_startup_trace("guard_reactor", "cancelled_active_call")
        except Exception:
            pass
    _GUARD_REACTOR_CALL = None


def _schedule_guard_reactor_tick():
    global _GUARD_REACTOR_CALL

    if is_diresim_enabled():
        log_legacy_guard_runtime_block("_schedule_guard_reactor_tick")
        _append_guard_startup_trace("guard_reactor", "schedule_skipped", reason="diresim_enabled")
        _GUARD_REACTOR_CALL = None
        return

    if not _guard_patrol_owner_enabled("reactor"):
        _append_guard_startup_trace("guard_reactor", "schedule_skipped", reason="owner_disabled")
        _GUARD_REACTOR_CALL = None
        return

    if _GUARD_REACTOR_CALL is not None and getattr(_GUARD_REACTOR_CALL, "active", lambda: False)():
        _append_guard_startup_trace("guard_reactor", "schedule_skipped", reason="already_active")
        return

    def _run_guard_tick():
        global _GUARD_REACTOR_CALL

        _GUARD_REACTOR_CALL = None
        try:
            summary = None
            skipped = ""
            if (time.time() - get_last_guard_tick_time()) >= float(GUARD_TICK_INTERVAL):
                summary = process_guard_tick(source="reactor_fallback")
            else:
                skipped = "guard_tick_interval_gate"
            _append_guard_owner_heartbeat(
                "reactor",
                tick_source=str((summary or {}).get("source") or "reactor_fallback"),
                ok=bool((summary or {}).get("ok", False)),
                skipped=str((summary or {}).get("skipped") or skipped),
                moved_count=int((summary or {}).get("moved_count", 0) or 0),
                idle_count=int((summary or {}).get("idle_count", 0) or 0),
                global_owned_count=int((summary or {}).get("global_owned_count", 0) or 0),
                per_guard_owned_count=int((summary or {}).get("per_guard_owned_count", 0) or 0),
                skipped_per_guard_owned_count=int((summary or {}).get("skipped_per_guard_owned_count", 0) or 0),
            )
        except Exception as error:
            logger.log_trace(f"Guard reactor tick failed: {error}")
        finally:
            _schedule_guard_reactor_tick()

    _append_guard_startup_trace("guard_reactor", "scheduled", interval=float(GUARD_TICK_INTERVAL))
    _GUARD_REACTOR_CALL = reactor.callLater(float(GUARD_TICK_INTERVAL), _run_guard_tick)


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
    _append_guard_startup_trace(
        "at_server_start",
        "entered",
        startup_hooks=bool(getattr(settings, "ENABLE_SERVER_STARTUP_HOOKS", True)),
        startup_bootstrap=bool(getattr(settings, "ENABLE_SERVER_STARTUP_BOOTSTRAP", True)),
        guard_system=bool(getattr(settings, "ENABLE_GUARD_SYSTEM", True)),
        patrol_mode=get_guard_patrol_mode(),
    )
    if not getattr(settings, "ENABLE_SERVER_STARTUP_HOOKS", True):
        _append_guard_startup_trace("at_server_start", "skipped", reason="startup_hooks_disabled")
        return
    try:
        _append_guard_startup_trace("at_server_start", "pre_cleanup")
        try:
            TICKER_HANDLER.remove(1, process_status_tick, idstring="global_status_tick", persistent=True)
            unregister_ticker_metadata(1, idstring="global_status_tick", persistent=True)
        except Exception:
            pass

        try:
            TICKER_HANDLER.remove(10, process_learning_tick, idstring="global_learning_tick", persistent=True)
            unregister_ticker_metadata(10, idstring="global_learning_tick", persistent=True)
        except Exception:
            pass

        try:
            TICKER_HANDLER.remove(1, process_status_tick, idstring="global_bleed_tick", persistent=True)
            unregister_ticker_metadata(1, idstring="global_bleed_tick", persistent=True)
        except Exception:
            pass

        try:
            TICKER_HANDLER.remove(1, process_learning_tick, idstring="global_bleed_tick", persistent=True)
            unregister_ticker_metadata(1, idstring="global_bleed_tick", persistent=True)
        except Exception:
            pass

        try:
            TICKER_HANDLER.remove(PULSE_TICK, exp_pulse_tick, idstring=EXP_TICKER_IDSTRING, persistent=True)
            unregister_ticker_metadata(PULSE_TICK, idstring=EXP_TICKER_IDSTRING, persistent=True)
        except Exception:
            pass

        try:
            TICKER_HANDLER.remove(GUARD_TICK_INTERVAL, _run_guard_ticker_tick, idstring="global_guard_tick", persistent=True)
            unregister_ticker_metadata(GUARD_TICK_INTERVAL, idstring="global_guard_tick", persistent=True)
        except Exception:
            pass

        try:
            TICKER_HANDLER.remove(GUARD_TICK_INTERVAL, process_guard_tick, idstring="global_guard_tick", persistent=True)
            unregister_ticker_metadata(GUARD_TICK_INTERVAL, idstring="global_guard_tick", persistent=True)
        except Exception:
            pass

        _append_guard_startup_trace("at_server_start", "post_cleanup")

        try:
            from world.systems.tick_audit import scan_for_tick_violations

            for warning in scan_for_tick_violations()[:25]:
                logger.log_warn(
                    f"[TickAudit] {warning.get('kind')}: {warning.get('path')}:{int(warning.get('line', 0) or 0)} - {warning.get('message', '')}"
                )
        except Exception:
            logger.log_warn("[TickAudit] Soft timing audit failed during server start.")

        _cancel_guard_reactor_tick()
        if _get_guard_patrol_owner() != "global_script":
            _disable_global_guard_patrol_scripts()

        if getattr(settings, "ENABLE_GLOBAL_STATUS_TICK", True):
            TICKER_HANDLER.add(1, process_status_tick, idstring="global_status_tick", persistent=True)
            TICKER_HANDLER.add(10, process_learning_tick, idstring="global_learning_tick", persistent=True)
            if _guard_patrol_owner_enabled("ticker"):
                TICKER_HANDLER.add(GUARD_TICK_INTERVAL, _run_guard_ticker_tick, idstring="global_guard_tick", persistent=True)
            elif _guard_patrol_owner_enabled("global_script"):
                _ensure_global_guard_patrol_script()
            else:
                _disable_global_guard_patrol_scripts()
            if _guard_patrol_owner_enabled("reactor"):
                _schedule_guard_reactor_tick()
            start_exp_ticker()
            register_ticker_metadata(
                1,
                process_status_tick,
                idstring="global_status_tick",
                persistent=True,
                system="world.status_tick",
                reason="State-gated global status processing for recovery, subsystem state, justice/thief/warrior updates, and AI.",
            )
            register_ticker_metadata(
                10,
                process_learning_tick,
                idstring="global_learning_tick",
                persistent=True,
                system="world.learning_tick",
                reason="Frequency-separated learning and teaching pulse processing.",
            )
            if _guard_patrol_owner_enabled("ticker"):
                register_ticker_metadata(
                    GUARD_TICK_INTERVAL,
                    _run_guard_ticker_tick,
                    idstring="global_guard_tick",
                    persistent=True,
                    system="world.guards",
                    reason="Validated guard patrol, watch-state, pursuit, and justice response processing.",
                )

        _append_guard_startup_trace("at_server_start", "post_tick_setup")
        _log_guard_patrol_owner_state()
        _bootstrap_guard_patrols("at_server_start", phase_label="early")
        _bootstrap_diresim_kernel("at_server_start")
        _validate_diresim_guard_lock("at_server_start")
        _schedule_server_start_bootstrap()
    except Exception as error:
        _append_guard_startup_trace("at_server_start", "exception", error=str(error))
        logger.log_trace(f"[Guards][StartupDiag] at_server_start exception: {error}")
        raise


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
    _append_guard_startup_trace(
        "at_server_reload_start",
        "entered",
        startup_hooks=bool(getattr(settings, "ENABLE_SERVER_STARTUP_HOOKS", True)),
        startup_bootstrap=bool(getattr(settings, "ENABLE_SERVER_STARTUP_BOOTSTRAP", True)),
        guard_system=bool(getattr(settings, "ENABLE_GUARD_SYSTEM", True)),
        patrol_mode=get_guard_patrol_mode(),
    )
    if not getattr(settings, "ENABLE_SERVER_STARTUP_HOOKS", True):
        _append_guard_startup_trace("at_server_reload_start", "skipped", reason="startup_hooks_disabled")
        return

    try:
        if getattr(settings, "ENABLE_SERVER_STARTUP_BOOTSTRAP", True):
            _append_guard_startup_trace("at_server_reload_start", "bootstrap_entered")
            _bootstrap_guard_patrols("at_server_reload_start", phase_label="bootstrap")
            _bootstrap_diresim_kernel("at_server_reload_start")
            _ensure_fishing_supplier_npc()
            _append_guard_startup_trace("at_server_reload_start", "bootstrap_finished")

        if _guard_startup_force_sync_enabled():
            _run_guard_startup_sync_probe("at_server_reload_start", "final", force=True)

        _log_guard_patrol_owner_state()
        _validate_diresim_guard_lock("at_server_reload_start")
        _append_guard_startup_trace("at_server_reload_start", "finished")
    except Exception as error:
        _append_guard_startup_trace("at_server_reload_start", "exception", error=str(error))
        logger.log_trace(f"[Guards][StartupDiag] at_server_reload_start exception: {error}")
        raise


def at_server_reload_stop():
    """
    This is called only time the server stops before a reload.
    """
    if not getattr(settings, "ENABLE_SERVER_STARTUP_HOOKS", True):
        return

    _ensure_fishing_supplier_npc()


def at_server_cold_stop():
    """
    This is called only when the server goes down due to a shutdown or reset.
    """
    _cancel_guard_reactor_tick()


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
