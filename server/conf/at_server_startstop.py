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
_TRAP_TICK_STATE = {"next_sweep_at": 0.0}
IDLE_RECOVERY_INTERVAL = 2.0
TRAP_SWEEP_INTERVAL = 5.0
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
        for key in ["augmentation_buff", "debilitated", "warding_barrier", "utility_light", "exposed_magic", "active_cyclic"]
    )
    if has_magic_state:
        return True

    if bool(getattr(npc.db, "in_combat", False)) or bool(getattr(npc.db, "target", None)):
        return True
    if bool(states.get("last_seen_target")) or bool(states.get("empath_manipulated")) or bool(states.get("combat_timer")):
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
    room_specs = {
        "Wake Room": {
            "aliases": ["wake room", "intake start"],
            "desc": "You wake on a narrow cot in a stone chamber that smells of lamp oil, wet leather, and old readiness. Someone has been moving people through here in a hurry, and judging by the distant hammer of alarm bells, they are almost out of time.",
        },
        "Intake Hall": {
            "aliases": ["hall", "gender hall"],
            "desc": "Lanterns burn low over slate boards, stacked intake ledgers, and floor markings worn by nervous pacing. This is where the compound sorts who you are before it decides what to hand you.",
        },
        "Lineup Platform": {
            "aliases": ["platform", "lineup"],
            "desc": "A raised stone platform marked with faded sigils dominates the chamber. Different sets of gear rest at each position, sized and shaped with deliberate intent. Someone expected choice here, just not this late.",
        },
        "Mirror Alcove": {
            "aliases": ["alcove", "mirror room"],
            "desc": "A tight alcove lined with mirrors forces every glance back on itself. The silvered glass is polished too often to be decorative; this is a place for deciding what people will see before the world has time to decide for you.",
        },
        "Gear Rack Room": {
            "aliases": ["gear room", "rack room"],
            "desc": "Armor stands, folded clothing, and open crates pack the room in orderly rows. It looks less like generosity than triage: wear something useful and move on.",
        },
        "Weapon Cage": {
            "aliases": ["cage", "weapon room"],
            "desc": "Iron latticework separates neat rows of training weapons from the rest of the room. Whatever order once governed this cage is breaking down into urgency, but the choices are still clear enough to matter.",
        },
        "Training Yard": {
            "aliases": ["yard", "combat yard"],
            "desc": "The yard is all churned dust, battered posts, and hard angles meant to teach movement under pressure. It feels like a lesson already half interrupted by the noise rising beyond the compound walls.",
        },
        "Supply Shack": {
            "aliases": ["shack", "supply room"],
            "desc": "Shelves of bandages, salves, waterskins, and rough field kits crowd this cramped shack. It exists for the moment after a mistake, when someone still has time to keep the next one from being fatal.",
        },
        "Vendor Stall": {
            "aliases": ["stall", "vendor room"],
            "desc": "A cramped stall has been thrown together from crates, ledgers, and hanging hooks of practical goods. Even under threat, someone here is still counting what survival costs.",
        },
        "Breach Corridor": {
            "aliases": ["corridor", "breach"],
            "desc": "A long stone corridor runs toward the outer defenses, littered with dropped tools, scrape marks, and the first signs that something small and vicious has already gotten inside.",
        },
        "Outer Gate": {
            "aliases": ["gate", "exit"],
            "desc": "The gate stands open to the road beyond, its timbers splintered but not yet fallen. Beyond it lies The Landing, the wider world, and no more controlled lessons.",
        },
        "Secret Tunnel": {
            "aliases": ["tunnel", "secret"],
            "desc": "A narrow service tunnel twists behind the gate wall, half-hidden by broken crates and old canvas. It smells of dust, damp mortar, and the sort of shortcut people remember only when time runs out.",
        },
    }

    rooms = {}
    for key, spec in room_specs.items():
        room = _ensure_room(key, spec["desc"], aliases=spec["aliases"])
        room.db.area = "New Player Tutorial"
        room.db.region_name = "Tutorial"
        room.db.is_tutorial = True
        rooms[key] = room

    links = [
        ("Wake Room", "east", "Intake Hall", "west"),
        ("Intake Hall", "east", "Lineup Platform", "west"),
        ("Lineup Platform", "east", "Mirror Alcove", "west"),
        ("Mirror Alcove", "east", "Gear Rack Room", "west"),
        ("Gear Rack Room", "east", "Weapon Cage", "west"),
        ("Weapon Cage", "east", "Training Yard", "west"),
        ("Training Yard", "east", "Supply Shack", "west"),
        ("Supply Shack", "east", "Vendor Stall", "west"),
        ("Vendor Stall", "east", "Breach Corridor", "west"),
        ("Breach Corridor", "east", "Outer Gate", "west"),
    ]
    for src, direction, dest, reverse in links:
        _ensure_exit(rooms[src], direction, rooms[dest])
        _ensure_exit(rooms[dest], reverse, rooms[src])
    _ensure_exit(rooms["Outer Gate"], "down", rooms["Secret Tunnel"])
    _ensure_exit(rooms["Secret Tunnel"], "up", rooms["Outer Gate"])

    mentor = ObjectDB.objects.filter(db_key__iexact="Marshal Vey", db_location=rooms["Wake Room"]).first()
    if not mentor:
        mentor = create_object(
            "typeclasses.npcs.NPC",
            key="Marshal Vey",
            location=rooms["Wake Room"],
            home=rooms["Wake Room"],
        )
    mentor.db.desc = "Marshal Vey has the clipped focus of someone running out of time but not out of control. Nothing about the veteran suggests warmth, only competence and the expectation that you will keep up."
    for alias in ["mentor", "marshal", "vey"]:
        mentor.aliases.add(alias)
    mentor.db.onboarding_role = "mentor"
    if not mentor.scripts.get("onboarding_roleplay"):
        mentor.scripts.add("typeclasses.onboarding_scripts.OnboardingRoleplayScript")

    gremlin = ObjectDB.objects.filter(db_key__iexact="Pip the Gremlin", db_location=rooms["Intake Hall"]).first()
    if not gremlin:
        gremlin = create_object(
            "typeclasses.npcs.NPC",
            key="Pip the Gremlin",
            location=rooms["Intake Hall"],
            home=rooms["Intake Hall"],
        )
    gremlin.db.desc = "Pip moves too quickly for the amount of confidence involved, arms full of forms, straps, and badly timed enthusiasm. The gremlin looks useful only in the way sparks are useful near dry straw."
    for alias in ["gremlin", "pip"]:
        gremlin.aliases.add(alias)
    gremlin.db.onboarding_role = "gremlin"
    if not gremlin.scripts.get("onboarding_roleplay"):
        gremlin.scripts.add("typeclasses.onboarding_scripts.OnboardingRoleplayScript")

    _cleanup_tutorial_helper_characters(rooms)

    _ensure_named_object(
        "silvered mirror",
        rooms["Mirror Alcove"],
        "A flawless standing mirror gleams here. Its frame is worn smooth where generations of nervous fingers have tapped and rubbed at it while deciding how they wish to appear.",
        aliases=["mirror"],
    )
    _ensure_named_object(
        "clothing rack",
        rooms["Gear Rack Room"],
        "A broad rack displays simple shirts, trousers, skirts, cloaks, and boots sized for new travelers.",
        aliases=["rack"],
    )
    _ensure_named_object(
        "weapon rack",
        rooms["Weapon Cage"],
        "A sturdy rack holds plain training weapons ready for first choices and first mistakes.",
        aliases=["rack"],
    )
    _ensure_named_object(
        "supply table",
        rooms["Supply Shack"],
        "Bundled travel items sit here in careful stacks: maps, charms, satchels, and other necessities for a new arrival.",
        aliases=["table"],
    )
    for race_name, desc in [
        ("human station", "A balanced set of practical gear rests here, built for adaptability rather than spectacle."),
        ("elf station", "Long-fingered gloves and narrow-cut kit suggest reach, precision, and a little impatience with cramped design."),
        ("dwarf station", "Stockier gear and reinforced fittings wait here, plain in shape and unapologetic in purpose."),
    ]:
        _ensure_named_object(race_name, rooms["Lineup Platform"], desc, aliases=[race_name.split()[0]])
    _ensure_tutorial_vendor(rooms["Vendor Stall"])
    training_goblin = _ensure_tutorial_goblin(rooms["Training Yard"])
    training_goblin.db.is_tutorial_enemy = True
    training_goblin.db.onboarding_enemy_role = "training"
    if not rooms["Breach Corridor"].scripts.get("onboarding_invasion"):
        rooms["Breach Corridor"].scripts.add("typeclasses.onboarding_scripts.OnboardingInvasionScript")

    from typeclasses.objects import Object
    from typeclasses.wearables import Wearable

    clothing_room = rooms["Gear Rack Room"]
    for key, slot, desc in [
        ("plain shirt", "torso", "A simple shirt meant for a new traveler."),
        ("traveler's trousers", "legs", "A practical pair of trousers with room to move."),
        ("simple boots", "feet", "Serviceable boots made for long roads rather than style."),
    ]:
        item = ObjectDB.objects.filter(db_key=key, db_location=clothing_room).first()
        if not item:
            item = create_object(Wearable, key=key, location=clothing_room, home=clothing_room)
        item.db.slot = slot
        item.db.weight = 1.0
        item.db.desc = desc
        if key == "plain shirt":
            item.aliases.add("shirt")
        elif key == "traveler's trousers":
            for alias in ["trousers", "pants"]:
                item.aliases.add(alias)
        elif key == "simple boots":
            for alias in ["boots", "boot"]:
                item.aliases.add(alias)

    armory = rooms["Weapon Cage"]
    starter_weapons = {
        "training sword": {"weapon_type": "light_edge", "skill": "light_edge", "damage_type": "slice"},
        "training mace": {"weapon_type": "blunt", "skill": "blunt", "damage_type": "impact"},
        "training spear": {"weapon_type": "polearm", "skill": "polearm", "damage_type": "puncture"},
    }
    for key, profile in starter_weapons.items():
        weapon = ObjectDB.objects.filter(db_key=key, db_location=armory).first()
        if not weapon:
            weapon = create_object(Object, key=key, location=armory, home=armory)
        weapon.db.item_type = "weapon"
        weapon.db.weight = 3.0
        weapon.db.weapon_type = profile["weapon_type"]
        weapon.db.skill = profile["skill"]
        weapon.db.damage_type = profile["damage_type"]
        weapon.db.damage_types = {"slice": 0.0, "impact": 0.0, "puncture": 0.0}
        weapon.db.damage_types[profile["damage_type"]] = 1.0
        weapon.db.damage = 4
        weapon.db.damage_min = 2
        weapon.db.damage_max = 5
        weapon.db.roundtime = 3.0
        weapon.db.weapon_profile = {
            "type": profile["weapon_type"],
            "skill": profile["skill"],
            "damage": 4,
            "damage_min": 2,
            "damage_max": 5,
            "roundtime": 3.0,
        }
        weapon.db.desc = f"A plain {key.replace('training ', '')} intended for first lessons and little else."
        weapon.aliases.add(key.replace("training ", ""))

    outer_gate = rooms["Outer Gate"]
    landing_room = _resolve_landing_arrival_room()
    if landing_room:
        _ensure_exit(outer_gate, "out", landing_room)
        _ensure_exit(outer_gate, "leave", landing_room)
        _ensure_exit(rooms["Secret Tunnel"], "crawl", landing_room)

    return rooms["Wake Room"]


def _log_slow_tick(name, started_at, threshold):
    duration = time.perf_counter() - started_at
    from tools.diretest.core.runtime import record_script_delay

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
            or active_cyclic
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

    if now >= _TRAP_TICK_STATE["next_sweep_at"]:
        for trap in ObjectDB.objects.filter(db_typeclass_path="typeclasses.trap_device.TrapDevice"):
            if hasattr(trap, "at_tick"):
                trap.at_tick()
        _TRAP_TICK_STATE["next_sweep_at"] = now + TRAP_SWEEP_INTERVAL

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

    try:
        from world.systems.tick_audit import scan_for_tick_violations

        for warning in scan_for_tick_violations()[:25]:
            logger.log_warn(
                f"[TickAudit] {warning.get('kind')}: {warning.get('path')}:{int(warning.get('line', 0) or 0)} - {warning.get('message', '')}"
            )
    except Exception:
        logger.log_warn("[TickAudit] Soft timing audit failed during server start.")

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
    logger.log_info("Ensuring new player tutorial bootstrap.")
    tutorial_entry = _ensure_new_player_tutorial()
    if tutorial_entry:
        logger.log_info(f"New player tutorial ready at {tutorial_entry.key}(#{tutorial_entry.id}).")
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
