import hashlib
import random
import time
from collections.abc import Mapping

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.search import search_tag

from engine.services.skill_service import SkillService
from utils.survival_loot import create_simple_item
from world.area_forge.paths import area_namespace
from world.systems.scheduler import schedule_event


NEW_PLAYER_TAG = "new_player"
NEW_PLAYER_CATEGORY = "state"
NEW_PLAYER_DURATION = 2 * 60 * 60
NEW_PLAYER_CURRENCY_CAP = 50000
COFFER_REWARD_COINS = 100
AMBIENT_SPAWN_CHANCE = 0.04
POI_SPAWN_CHANCE = 0.65
ORDERLY_IDLE_MIN = 3.0
ORDERLY_IDLE_MAX = 5.0
ORDERLY_KEY = "Empath Orderly"
GUILD_ROOM_KEY = "Empath Guild"
GUILD_ACCESS_KEY = "Larkspur Lane, Midway"

POI_TAGS = (
    "poi_bank",
    "poi_town_green",
    "poi_guild_empath",
    "poi_market",
)

CRITICAL_ITEM_ORDER = (
    "rusty weapon",
    "shirt",
    "pants",
    "boots",
)

KIT_ITEM_ORDER = (
    "rusty weapon",
    "shirt",
    "pants",
    "boots",
    "backpack",
    "pouch",
    "skinning knife",
    "lockpicks",
)

ORDERLY_DIALOGUE = (
    "Hold still.",
    "",
    "A quick inspection--efficient, practiced.",
    "",
    '"You\'re fine."',
    "",
    "A glance toward the door.",
    "",
    '"If something\'s been left behind--take it."',
    "",
    '"No one else will."',
)


def _now():
    return time.time()


def _room_id(room):
    return int(getattr(room, "id", 0) or 0)


def _normalize_looted_map(raw_value):
    if isinstance(raw_value, Mapping):
        normalized = {}
        for key, value in dict(raw_value).items():
            try:
                room_id = int(key)
            except (TypeError, ValueError):
                continue
            normalized[str(room_id)] = bool(value)
        return normalized
    return {}


def _normalize_string_set(raw_value):
    if isinstance(raw_value, set):
        return {str(entry) for entry in raw_value if str(entry or "").strip()}
    if isinstance(raw_value, (list, tuple)):
        return {str(entry) for entry in raw_value if str(entry or "").strip()}
    return set()


def _normalize_int_list(raw_value):
    values = []
    for entry in list(raw_value or []):
        try:
            room_id = int(entry)
        except (TypeError, ValueError):
            continue
        if room_id > 0 and room_id not in values:
            values.append(room_id)
    return values


def _state(character):
    if not character:
        return {}
    character.db.aftermath_looted = _normalize_looted_map(getattr(character.db, "aftermath_looted", None))
    character.db.aftermath_currency_total = max(0, int(getattr(character.db, "aftermath_currency_total", 0) or 0))
    character.db.aftermath_currency_cap = max(0, int(getattr(character.db, "aftermath_currency_cap", NEW_PLAYER_CURRENCY_CAP) or NEW_PLAYER_CURRENCY_CAP))
    character.db.aftermath_items_found = set(_normalize_string_set(getattr(character.db, "aftermath_items_found", None) or set()))
    character.db.coffer_looted = bool(getattr(character.db, "coffer_looted", False))
    character.db.aftermath_rooms_seen = _normalize_int_list(getattr(character.db, "aftermath_rooms_seen", None) or [])
    character.db.aftermath_orderly_prompted = bool(getattr(character.db, "aftermath_orderly_prompted", False))
    character.db.aftermath_orderly_idle_token = int(getattr(character.db, "aftermath_orderly_idle_token", 0) or 0)
    character.db.new_player_expires_at = float(getattr(character.db, "new_player_expires_at", 0.0) or 0.0)
    return {
        "looted": character.db.aftermath_looted,
        "currency_total": character.db.aftermath_currency_total,
        "currency_cap": character.db.aftermath_currency_cap,
        "items_found": set(character.db.aftermath_items_found or set()),
        "coffer_room": int(getattr(character.db, "coffer_room", 0) or 0),
        "coffer_looted": bool(character.db.coffer_looted),
        "rooms_seen": list(character.db.aftermath_rooms_seen or []),
        "orderly_prompted": bool(character.db.aftermath_orderly_prompted),
        "new_player_expires_at": float(character.db.new_player_expires_at or 0.0),
    }


def is_new_player(character):
    if not character or not getattr(character, "tags", None):
        return False
    refresh_new_player_state(character)
    try:
        return bool(character.tags.has(NEW_PLAYER_TAG, category=NEW_PLAYER_CATEGORY))
    except Exception:
        return False


def expire_new_player_state(character):
    if not character:
        return False
    try:
        character.tags.remove(NEW_PLAYER_TAG, category=NEW_PLAYER_CATEGORY)
    except Exception:
        pass
    character.db.new_player_expires_at = 0.0
    return True


def refresh_new_player_state(character):
    if not character:
        return False
    expires_at = float(getattr(character.db, "new_player_expires_at", 0.0) or 0.0)
    if expires_at and _now() >= expires_at:
        expire_new_player_state(character)
        return False
    return True


def _landing_rooms():
    namespace = area_namespace("the_landing")
    rooms = []
    for obj in search_tag(namespace["area_tag"][0], category=namespace["area_tag"][1]):
        if getattr(obj, "destination", None) is not None:
            continue
        rooms.append(obj)
    return rooms


def _room_has_any_tag(room, tag_keys):
    if not room or not getattr(room, "tags", None):
        return False
    for tag_key in tag_keys:
        try:
            if room.tags.has(tag_key):
                return True
        except Exception:
            continue
    return False


def is_poi_room(room):
    return _room_has_any_tag(room, POI_TAGS)


def assign_random_room(character):
    candidates = []
    for room in _landing_rooms():
        room_key = str(getattr(room, "key", "") or "")
        if room_key in {GUILD_ROOM_KEY, GUILD_ACCESS_KEY}:
            continue
        if is_poi_room(room):
            continue
        candidates.append(room)
    if not candidates:
        return 0
    digest = hashlib.sha256(f"coffer:{int(getattr(character, 'id', 0) or 0)}".encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(candidates)
    return int(getattr(candidates[index], "id", 0) or 0)


def activate_new_player_state(character):
    if not character:
        return False
    character.tags.add(NEW_PLAYER_TAG, category=NEW_PLAYER_CATEGORY)
    character.db.new_player_expires_at = _now() + NEW_PLAYER_DURATION
    character.db.aftermath_looted = {}
    character.db.aftermath_currency_total = 0
    character.db.aftermath_currency_cap = NEW_PLAYER_CURRENCY_CAP
    character.db.aftermath_items_found = set()
    character.db.coffer_room = assign_random_room(character)
    character.db.coffer_looted = False
    character.db.aftermath_rooms_seen = []
    character.db.aftermath_orderly_prompted = False
    character.db.aftermath_orderly_idle_token = 0
    return True


def _eligible_room_for_guarantee(room):
    if not room:
        return False
    room_key = str(getattr(room, "key", "") or "")
    return room_key not in {GUILD_ROOM_KEY}


def note_room_entry(character, room=None):
    if not is_new_player(character):
        return False
    room = room or getattr(character, "location", None)
    if not room:
        return False
    state = _state(character)
    room_id = _room_id(room)
    if room_id > 0 and room_id not in state["rooms_seen"] and _eligible_room_for_guarantee(room):
        state["rooms_seen"].append(room_id)
        character.db.aftermath_rooms_seen = list(state["rooms_seen"])

    if str(getattr(room, "key", "") or "") != GUILD_ROOM_KEY:
        return True
    if state["orderly_prompted"]:
        return True

    token = int(_now() * 1000)
    character.db.aftermath_orderly_idle_token = token
    schedule_event(
        key="orderly_idle_prompt",
        owner=character,
        delay=random.uniform(ORDERLY_IDLE_MIN, ORDERLY_IDLE_MAX),
        callback=_emit_idle_orderly_prompt,
        payload={"args": [character, room_id, token]},
        metadata={"system": "aftermath", "type": "delayed_effect"},
    )
    return True


def _emit_idle_orderly_prompt(character, expected_room_id, token):
    if not character or not getattr(character, "pk", None):
        return False
    if not is_new_player(character):
        return False
    if bool(getattr(character.db, "aftermath_orderly_prompted", False)):
        return False
    if int(getattr(character.db, "aftermath_orderly_idle_token", 0) or 0) != int(token or 0):
        return False
    room = getattr(character, "location", None)
    if _room_id(room) != int(expected_room_id or 0):
        return False
    return emit_orderly_dialogue(character)


def note_room_look(character, room):
    if not is_new_player(character):
        return False
    if str(getattr(room, "key", "") or "") != GUILD_ROOM_KEY:
        return False
    if bool(getattr(character.db, "aftermath_orderly_prompted", False)):
        return False
    return emit_orderly_dialogue(character)


def emit_orderly_dialogue(character):
    if not character or bool(getattr(character.db, "aftermath_orderly_prompted", False)):
        return False
    character.db.aftermath_orderly_prompted = True
    lines = [line for line in ORDERLY_DIALOGUE]
    character.msg("\n".join(lines))
    return True


def _hash_float(seed_text):
    digest = hashlib.sha256(str(seed_text).encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _has_item_named(character, candidates):
    wanted = {str(entry).strip().lower() for entry in candidates}
    for item in list(getattr(character, "contents", []) or []):
        if str(getattr(item, "key", "") or "").strip().lower() in wanted:
            return True
    if hasattr(character, "get_worn_items"):
        for item in character.get_worn_items():
            if str(getattr(item, "key", "") or "").strip().lower() in wanted:
                return True
    weapon = character.get_wielded_weapon() if hasattr(character, "get_wielded_weapon") else None
    if weapon and str(getattr(weapon, "key", "") or "").strip().lower() in wanted:
        return True
    return False


def _missing_kit_items(character):
    state = _state(character)
    found = {entry.lower() for entry in state["items_found"]}
    missing = []
    for item_key in KIT_ITEM_ORDER:
        aliases = {item_key}
        if item_key == "lockpicks":
            if hasattr(character, "has_lockpick") and character.has_lockpick():
                continue
        elif item_key == "rusty weapon":
            if _has_item_named(character, {"rusty shortsword", "rusty weapon"}):
                continue
        elif item_key == "pouch":
            if _has_item_named(character, {"small belt pouch", "pouch"}):
                continue
        elif item_key == "backpack":
            if _has_item_named(character, {"weathered backpack", "backpack"}):
                continue
        elif item_key == "skinning knife":
            if _has_item_named(character, {"skinning knife"}):
                continue
        elif item_key == "shirt":
            if _has_item_named(character, {"roughspun shirt", "shirt"}):
                continue
        elif item_key == "pants":
            if _has_item_named(character, {"patched trousers", "pants", "trousers"}):
                continue
        elif item_key == "boots":
            if _has_item_named(character, {"stiff leather boots", "boots"}):
                continue
        if item_key.lower() not in found:
            missing.append(item_key)
    return missing


def _guarantee_corpse(character, room):
    missing_critical = [item for item in _missing_kit_items(character) if item in CRITICAL_ITEM_ORDER]
    if not missing_critical:
        return False
    state = _state(character)
    room_sequence = [room_id for room_id in state["rooms_seen"] if room_id > 0]
    if _room_id(room) <= 0:
        return False
    if _room_id(room) not in room_sequence:
        room_sequence.append(_room_id(room))
    try:
        position = room_sequence.index(_room_id(room))
    except ValueError:
        return False
    return position < 4


def get_spawn_chance_for_room(character, room):
    if not room or str(getattr(room, "key", "") or "") == GUILD_ROOM_KEY:
        return 0.0
    if is_poi_room(room):
        return POI_SPAWN_CHANCE
    return AMBIENT_SPAWN_CHANCE


def _corpse_should_render(character, room):
    if not is_new_player(character):
        return False
    state = _state(character)
    room_id = _room_id(room)
    if room_id <= 0 or state["looted"].get(str(room_id), False):
        return False
    if int(state["coffer_room"] or 0) == room_id and not state["coffer_looted"] and not (hasattr(character, "has_lockpick") and character.has_lockpick()):
        return True
    if _guarantee_corpse(character, room):
        return True
    chance = get_spawn_chance_for_room(character, room)
    return _hash_float(f"corpse:{int(getattr(character, 'id', 0) or 0)}:{room_id}") < chance


def _coffer_should_render(character, room):
    if not is_new_player(character):
        return False
    state = _state(character)
    room_id = _room_id(room)
    if room_id <= 0 or room_id != int(state["coffer_room"] or 0) or state["coffer_looted"]:
        return False
    if not (hasattr(character, "has_lockpick") and character.has_lockpick()):
        return False
    return True


def get_room_render_lines(character, room):
    if not character or not room or not is_new_player(character):
        return []
    lines = []
    if _corpse_should_render(character, room):
        lines.append("A |lc__clickmove__ search raider|ltfallen goblin raider|le lies where the rush of the street forgot it.")
    if _coffer_should_render(character, room):
        lines.append("An |lc__clickmove__ pick coffer|ltironbound coffer|le sits half-hidden against the wall.")
    return lines


def get_room_action_entries(character, room):
    if not character or not room or not is_new_player(character):
        return []
    entries = []
    if _corpse_should_render(character, room):
        entries.append({"command": "search raider", "label": "fallen goblin raider"})
    if _coffer_should_render(character, room):
        entries.append({"command": "pick coffer", "label": "ironbound coffer"})
    return entries


def _create_rusty_weapon(character):
    weapon = create_object("typeclasses.objects.Object", key="rusty shortsword", location=character, home=character)
    weapon.db.item_type = "weapon"
    weapon.db.weight = 2.5
    weapon.db.weapon_profile = {"type": "light_edge", "skill": "light_edge", "damage_min": 2, "damage_max": 5, "roundtime": 3.0}
    weapon.db.weapon_type = "light_edge"
    weapon.db.skill = "light_edge"
    weapon.db.damage_min = 2
    weapon.db.damage_max = 5
    weapon.db.roundtime = 3.0
    weapon.db.damage_type = "slice"
    weapon.db.damage_types = {"slice": 0.65, "impact": 0.1, "puncture": 0.25}
    weapon.db.balance = 48
    weapon.db.desc = "A rust-flecked shortsword with enough edge left to matter."
    if hasattr(weapon, "sync_profile_fields"):
        weapon.sync_profile_fields()
    if hasattr(weapon, "normalize_damage_types"):
        weapon.normalize_damage_types()
    return weapon


def _create_shirt(character):
    item = create_object("typeclasses.wearables.Wearable", key="roughspun shirt", location=character, home=character)
    item.db.slot = "torso"
    item.db.weight = 0.8
    item.db.desc = "A roughspun shirt, clean enough to keep and plain enough not to miss."
    return item


def _create_pants(character):
    item = create_object("typeclasses.wearables.Wearable", key="patched trousers", location=character, home=character)
    item.db.slot = "legs"
    item.db.weight = 0.8
    item.db.desc = "Patched trousers, worn thin at the knee but still usable."
    return item


def _create_boots(character):
    item = create_object("typeclasses.wearables.Wearable", key="stiff leather boots", location=character, home=character)
    item.db.slot = "feet"
    item.db.weight = 1.2
    item.db.desc = "A pair of stiff leather boots with enough sole left for city stone."
    return item


def _create_backpack(character):
    return create_simple_item(
        character,
        key="weathered backpack",
        desc="A weathered backpack with a sound strap and room for salvaged necessities.",
        is_container=True,
        capacity=10,
        weight=1.5,
        value=8,
    )


def _create_pouch(character):
    return create_simple_item(
        character,
        key="small belt pouch",
        desc="A small belt pouch with a drawstring and a little grit still caught in the seams.",
        is_container=True,
        capacity=4,
        weight=0.2,
        value=4,
    )


def _create_skinning_knife(character):
    item = create_object("typeclasses.objects.Object", key="skinning knife", location=character, home=character)
    item.db.item_type = "weapon"
    item.db.weight = 0.4
    item.db.weapon_profile = {"type": "light_edge", "skill": "light_edge", "damage_min": 1, "damage_max": 3, "roundtime": 2.0}
    item.db.weapon_type = "light_edge"
    item.db.skill = "light_edge"
    item.db.damage_min = 1
    item.db.damage_max = 3
    item.db.roundtime = 2.0
    item.db.damage_type = "slice"
    item.db.damage_types = {"slice": 0.5, "impact": 0.1, "puncture": 0.4}
    item.db.balance = 58
    item.db.desc = "A narrow skinning knife, better for close work than a fair fight."
    if hasattr(item, "sync_profile_fields"):
        item.sync_profile_fields()
    if hasattr(item, "normalize_damage_types"):
        item.normalize_damage_types()
    return item


def _create_lockpicks(character):
    item = create_object("typeclasses.lockpick.Lockpick", key="basic lockpick", location=character, home=character)
    item.db.item_value = 10
    item.db.value = 10
    item.db.weight = 0.2
    item.db.grade = "standard"
    item.db.durability = max(10, int(getattr(item.db, "durability", 0) or 0))
    return item


def _grant_item(character, item_key):
    if item_key == "rusty weapon":
        return _create_rusty_weapon(character), "rusty weapon"
    if item_key == "shirt":
        return _create_shirt(character), "shirt"
    if item_key == "pants":
        return _create_pants(character), "pants"
    if item_key == "boots":
        return _create_boots(character), "boots"
    if item_key == "backpack":
        return _create_backpack(character), "backpack"
    if item_key == "pouch":
        return _create_pouch(character), "pouch"
    if item_key == "skinning knife":
        return _create_skinning_knife(character), "skinning knife"
    if item_key == "lockpicks":
        return _create_lockpicks(character), "lockpicks"
    return None, None


def _choose_item_drops(character, room):
    missing = _missing_kit_items(character)
    if not missing:
        return []
    room_id = _room_id(room)
    drops = []
    if int(getattr(character.db, "coffer_room", 0) or 0) == room_id and not (hasattr(character, "has_lockpick") and character.has_lockpick()) and "lockpicks" in missing:
        drops.append("lockpicks")
        missing = [item for item in missing if item != "lockpicks"]

    critical = [item for item in missing if item in CRITICAL_ITEM_ORDER]
    if critical:
        drops.extend(critical[:2])
        return drops

    if missing:
        drops.append(missing[0])
    return drops


def _corpse_coin_award(character, room):
    state = _state(character)
    remaining = max(0, int(state["currency_cap"] or 0) - int(state["currency_total"] or 0))
    if remaining <= 0:
        return 0
    room_id = _room_id(room)
    lower = 60 if is_poi_room(room) else 18
    upper = 160 if is_poi_room(room) else 55
    roll = _hash_float(f"coins:{int(getattr(character, 'id', 0) or 0)}:{room_id}")
    amount = lower + int((upper - lower) * roll)
    return min(amount, remaining)


def _mark_room_looted(character, room):
    looted = _normalize_looted_map(getattr(character.db, "aftermath_looted", None))
    looted[str(_room_id(room))] = True
    character.db.aftermath_looted = looted
    return looted


def handle_search(character, query):
    room = getattr(character, "location", None)
    if not room or not is_new_player(character):
        return False
    normalized = str(query or "").strip().lower()
    if normalized not in {"raider", "fallen goblin raider", "body", "corpse", "goblin", "fallen raider"}:
        return False
    if not _corpse_should_render(character, room):
        return False

    item_drops = _choose_item_drops(character, room)
    created_names = []
    state = _state(character)
    items_found = set(state["items_found"])
    for item_key in item_drops:
        created, found_key = _grant_item(character, item_key)
        if created and found_key:
            created_names.append(str(getattr(created, "key", found_key) or found_key))
            items_found.add(found_key)

    coin_amount = _corpse_coin_award(character, room)
    if coin_amount > 0 and hasattr(character, "add_coins"):
        character.add_coins(coin_amount)
        character.db.aftermath_currency_total = int(getattr(character.db, "aftermath_currency_total", 0) or 0) + coin_amount

    character.db.aftermath_items_found = items_found
    _mark_room_looted(character, room)

    lines = ["You go through the fallen raider with quick, practiced hands."]
    if coin_amount > 0 and hasattr(character, "format_coins"):
        lines.append(f"A little weight remains in a hidden fold: {character.format_coins(coin_amount)}.")
    elif coin_amount <= 0 and not created_names:
        lines.append("There is nothing of value left.")
    if created_names:
        lines.append(f"You salvage {', '.join(created_names)}.")
    lines.append("")
    lines.append("The body gives way under your touch.")
    lines.append("")
    lines.append("There is nothing left worth taking.")
    character.msg("\n".join(lines))
    return True


def handle_pick(character, query):
    room = getattr(character, "location", None)
    if not room or not is_new_player(character):
        return False
    normalized = str(query or "").strip().lower()
    if normalized not in {"coffer", "ironbound coffer", "box"}:
        return False
    state = _state(character)
    if _room_id(room) != int(state["coffer_room"] or 0) or state["coffer_looted"]:
        return False

    if not (hasattr(character, "has_lockpick") and character.has_lockpick()):
        character.msg("You try the coffer.\n\nIt doesn't budge.\n\nLocked.")
        return True

    bonus_lines = ["Your fingers brush against the picks at your belt.", "", "You work the picks into the lock.", "", "A soft click.", ""]
    reward = min(COFFER_REWARD_COINS, max(0, int(state["currency_cap"] or 0) - int(state["currency_total"] or 0)))
    if reward > 0 and hasattr(character, "add_coins"):
        character.add_coins(reward)
        character.db.aftermath_currency_total = int(getattr(character.db, "aftermath_currency_total", 0) or 0) + reward
    character.db.coffer_looted = True
    if reward > 0 and hasattr(character, "format_coins"):
        bonus_lines.append(f"Inside, you find more than the rest combined: {character.format_coins(reward)}.")
    else:
        bonus_lines.append("Inside, there is nothing you can still make use of.")
    bonus_lines.append("")
    bonus_lines.append("The coffer's lid slips loose.")
    bonus_lines.append("")
    bonus_lines.append("There is nothing more to take.")
    SkillService.award_xp(character, "locksmithing", 20, source={"mode": "difficulty"}, success=True, outcome="success", event_key="locksmithing")
    character.msg("\n".join(bonus_lines))
    return True


def append_guild_triage_detail(desc):
    base = str(desc or "").rstrip()
    extra = "A narrow section of the room is clearly used for intake. Not for rest--only assessment."
    if extra in base:
        return base
    if not base:
        return extra
    return f"{base}\n\n{extra}"


def ensure_empath_orderly(room):
    if not room:
        return None
    orderly = ObjectDB.objects.filter(db_key__iexact=ORDERLY_KEY, db_location=room).first()
    if not orderly:
        orderly = create_object("typeclasses.npcs.NPC", key=ORDERLY_KEY, location=room, home=room)
    orderly.db.is_npc = True
    orderly.db.desc = "An orderly with rolled sleeves and a quiet economy of motion waits near the intake tables, watching for what matters and ignoring the rest."
    orderly.db.is_passive = True
    orderly.db.no_greeting = True
    orderly.aliases.add("orderly")
    orderly.aliases.add("empath")
    return orderly


def ensure_poi_tags():
    landing_rooms = _landing_rooms()
    guild_room = ObjectDB.objects.filter(db_key__iexact=GUILD_ROOM_KEY, db_typeclass_path="typeclasses.rooms.Room").first()
    managed_rooms = list(landing_rooms)
    if guild_room and guild_room not in managed_rooms:
        managed_rooms.append(guild_room)
    if not managed_rooms:
        return {}

    for room in managed_rooms:
        for tag_key in POI_TAGS:
            try:
                room.tags.remove(tag_key)
            except Exception:
                pass

    tagged = {}
    bank_room = next((room for room in landing_rooms if bool(getattr(room.db, "is_bank", False)) or str(getattr(room, "key", "") or "") == "Bank"), None)
    if bank_room:
        bank_room.tags.add("poi_bank")
        tagged["poi_bank"] = int(bank_room.id)

    market_candidates = [
        room for room in landing_rooms
        if any(token in str(getattr(room, "key", "") or "").lower() for token in ("marrowmarket", "tallowmarket", "market"))
    ]
    if market_candidates:
        for room in market_candidates[:6]:
            room.tags.add("poi_market")
        tagged["poi_market"] = int(market_candidates[0].id)

    town_green = next(
        (
            room for room in landing_rooms
            if str(getattr(room, "key", "") or "").startswith("Central Crossing [")
        ),
        None,
    )
    if town_green:
        town_green.tags.add("poi_town_green")
        tagged["poi_town_green"] = int(town_green.id)

    if guild_room:
        guild_room.tags.add("poi_guild_empath")
        tagged["poi_guild_empath"] = int(guild_room.id)

    return tagged