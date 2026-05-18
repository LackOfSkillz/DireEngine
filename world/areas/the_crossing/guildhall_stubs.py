import json
import re
from pathlib import Path

from evennia.utils.create import create_object

from .import_canonical import (
    CANONICAL_ID_CATEGORY,
    DEFAULT_MAP_PATH,
    PHASE1_ROOM_IDS,
    PHASE2_ROOM_IDS,
    PHASE3_ROOM_IDS,
    PHASE4_ROOM_IDS,
    PHASE5_ROOM_IDS,
    ROOM_TYPECLASS,
    _collect_imported_rooms,
    _drain_pending_exits,
    _find_room_by_map_id,
    _populate_room_pending_exits,
)


CANONICAL_AREA_TAG_GUILDHALL_STUB = "canonical_crossing_guildhall_stub"
GUILDHALL_STUB_PHASE = "guildhall_stub"
STUB_GUILDLEADER_TYPECLASS = "typeclasses.npcs.StubGuildleaderNPC"
_TITLE_RE = re.compile(r"^\[\[(.+?),\s*(.+?)\]\]$")

GUILDHALL_STUB_ROOM_IDS = [
    7898,
    852,
    5990,
    5713,
    11733,
    7888,
    15122,
    8916,
    823,
    959,
    958,
    9077,
    7900,
    5995,
    5998,
    6016,
    6017,
    850,
    851,
]

GUILDHALL_STUB_ROOM_SPECS = {
    7898: {"area": "Bards' Guild", "title": "Commons", "desc": "The commons feels half rehearsal hall and half common room, with instrument cases, worn tables, and the practiced quiet that settles before someone decides to perform."},
    852: {"area": "Clerics' Guild", "title": "Residential Cloisters", "desc": "Stone walks and sheltered arches give the cloisters the calm order of a place built for devotion, study, and the constant traffic of people serving both duties."},
    5990: {"area": "Clerics' Guild", "title": "Sanctorum", "desc": "The sanctorum carries the hush of a ceremonial chamber used every day, with benches, altar-space, and incense-worn stone keeping the room solemn without making it grand."},
    5713: {"area": "Empaths' Guild", "title": "Courtyard Garden", "desc": "The courtyard garden softens the city into leaf-shadow, herb scents, and careful paths, offering the Empaths a quieter threshold than the surrounding streets allow."},
    11733: {"area": "Paladins' Guild", "title": "Side Lawn", "desc": "A disciplined stretch of lawn and stone borders the guild grounds, more orderly than decorative, with the feel of a place maintained by people who expect purpose from every corner."},
    7888: {"area": "Paladins' Guild", "title": "Meeting Hall", "desc": "The meeting hall feels built for vows, briefings, and difficult decisions, with long tables and chapel severity holding the room between barracks practicality and sacred duty."},
    15122: {"area": "Paladins' Guild", "title": "Holy Warrior's Promenade", "desc": "The promenade runs in a measured line of stone and trimmed grounds, giving the guild an approach that feels ceremonial without slipping into pageantry."},
    8916: {"area": "Traders' Guild", "title": "Shipment Center", "desc": "Crates, tallies, and cart room give the shipment center the brisk feel of a place where trade is counted, routed, and moved before anyone has time to admire it."},
    823: {"area": "Traders' Guild", "title": "Main Hall", "desc": "The main hall balances guild dignity with mercantile traffic, its desks, benches, and ledger space making it clear that commerce here is organized rather than improvised."},
    959: {"area": "Asemath Academy", "title": "Porte-cochere", "desc": "The porte-cochere offers the Academy a sheltered arrival framed by older stonework, its covered space feeling more scholarly threshold than noble display."},
    958: {"area": "Asemath Academy", "title": "Entrance", "desc": "The Academy entrance feels formal but not severe, a learned threshold of polished floors, old masonry, and the quiet expectation that visitors arrive prepared to listen."},
    9077: {"area": "Thieves' Guild", "title": "Foyer", "desc": "The foyer keeps its secrets close in shadowed corners, muted light, and the unnerving sense that everyone here noticed you before you noticed them."},
    7900: {"area": "Ranger Guild", "title": "Main Hall", "desc": "The Ranger hall stands closer to glade shelter than city guildhouse, with timber, field gear, and weathered maps giving the room the patience of a place that serves the wild first."},
    5995: {"area": "The Raven's Court", "title": "Foyer", "desc": "The Raven's Court foyer feels expensive in a guarded way, with polished surfaces, careful lighting, and just enough elegance to make every hidden purpose seem deliberate."},
    5998: {"area": "The Raven's Court", "title": "Ballroom", "desc": "The ballroom holds the memory of music and display, but the scale and finish of the space suggest private alliances matter here at least as much as dancing."},
    6016: {"area": "The Raven's Court", "title": "Terrace", "desc": "The terrace opens the Court onto air and stone balustrades, offering a refined pause that still feels better suited to quiet plotting than to leisure."},
    6017: {"area": "The Raven's Court", "title": "Silver Walk", "desc": "The Silver Walk carries a polished, hush-kept elegance, its narrow run of stone and ornament feeling like the kind of place where doors are hidden on purpose."},
    850: {"area": "Wilds", "title": "Pine Needle Path", "desc": "The path leaves city stone behind for needles, roots, and the resin scent of close pines, a narrow woodland seam that feels immediately less tamed than the Crossing."},
    851: {"area": "Wilds", "title": "Pine Needle Path", "desc": "Farther along, the pine path deepens into shade and softer ground, with the city reduced to a distant pressure behind trees and undergrowth."},
}

GUILDHALL_STUB_NPC_SPECS = [
    {
        "room_id": 7898,
        "key": "Silvyrfrost",
        "aliases": ["guildleader", "bard guildleader", "leader", "silvyrfrost"],
        "canonical_guild": "Bards' Guild",
        "guild_display_name": "Bards' Guild",
        "desc": "Silvyrfrost watches the commons with a performer's poise and a guildleader's selective patience, as though every conversation is being weighed for its worth before it finishes.",
        "is_placeholder": False,
    },
    {
        "room_id": 5990,
        "key": "High Priestess Aelyn",
        "aliases": ["guildleader", "cleric guildleader", "leader", "aelyn"],
        "canonical_guild": "Clerics' Guild",
        "guild_display_name": "Clerics' Guild",
        "desc": "Aelyn carries the still authority of someone accustomed to prayer, triage, and judgment arriving in the same hour.",
        "is_placeholder": True,
    },
    {
        "room_id": 5713,
        "key": "Mirpah",
        "aliases": ["guildleader", "empath guildleader", "leader", "mirpah"],
        "canonical_guild": "Empaths' Guild",
        "guild_display_name": "Empaths' Guild",
        "desc": "Mirpah keeps the garden under a healer's quiet attention, watching with the measured calm of someone used to pain arriving unannounced.",
        "is_placeholder": True,
    },
    {
        "room_id": 7888,
        "key": "Vyrshkana",
        "aliases": ["guildleader", "paladin guildleader", "leader", "vyrshkana"],
        "canonical_guild": "Paladins' Guild",
        "guild_display_name": "Paladins' Guild",
        "desc": "Vyrshkana stands with the composed force of someone who expects discipline to be visible before a single word is spoken.",
        "is_placeholder": True,
    },
    {
        "room_id": 823,
        "key": "Saramar",
        "aliases": ["guildleader", "trader guildleader", "leader", "saramar"],
        "canonical_guild": "Traders' Guild",
        "guild_display_name": "Traders' Guild",
        "desc": "Saramar has the sharp, attentive look of a person who has spent years turning traffic, goods, and promises into something the guild can trust.",
        "is_placeholder": True,
    },
    {
        "room_id": 958,
        "key": "Asemath",
        "aliases": ["headmaster", "leader", "asemath", "academy headmaster"],
        "canonical_guild": "Asemath Academy",
        "guild_display_name": "Asemath Academy",
        "desc": "Asemath carries himself with the settled gravity of a scholar whose authority comes from long use rather than display.",
        "is_placeholder": False,
    },
    {
        "room_id": 9077,
        "key": "A hooded figure",
        "aliases": ["guildleader", "leader", "hooded figure", "figure"],
        "canonical_guild": "Thieves' Guild",
        "guild_display_name": "Thieves' Guild",
        "desc": "The hooded figure stays composed and unreadable, giving away nothing except the impression that very little here happens by accident.",
        "is_placeholder": False,
        "canonical_name": None,
    },
    {
        "room_id": 7900,
        "key": "Akenturi",
        "aliases": ["guildleader", "ranger guildleader", "leader", "akenturi"],
        "canonical_guild": "Ranger Guild",
        "guild_display_name": "Ranger Guild",
        "desc": "Akenturi has the weathered steadiness of someone who trusts the tree line more than the city and sees no need to apologize for it.",
        "is_placeholder": True,
    },
]

_AREA_PREFIXES = {spec["area"] for spec in GUILDHALL_STUB_ROOM_SPECS.values()}


def _canonical_stub_title(room):
    for raw in room.get("title", []) or []:
        text = str(raw or "").strip()
        match = _TITLE_RE.match(text)
        if not match:
            continue
        area_prefix = match.group(1).strip()
        if area_prefix not in _AREA_PREFIXES:
            continue
        return area_prefix, match.group(2).strip()
    return None


def guildhall_stub_entries_from_map(data, room_ids=None):
    wanted_ids = [int(room_id) for room_id in (room_ids or GUILDHALL_STUB_ROOM_IDS)]
    selected = {}
    missing = []
    for room in data:
        canonical = _canonical_stub_title(room)
        if not canonical:
            continue
        room_id = int(room["id"])
        if room_id not in wanted_ids:
            continue
        selected[room_id] = {
            "id": room_id,
            "area_prefix": canonical[0],
            "canonical_title": canonical[1],
            "description": list(room.get("description", []) or []),
            "paths": list(room.get("paths", []) or []),
            "wayto": dict(room.get("wayto", {}) or {}),
            "timeto": dict(room.get("timeto", {}) or {}),
            "tags": list(room.get("tags", []) or []),
            "image": str(room.get("image") or ""),
            "image_coords": list(room.get("image_coords", []) or []),
        }
    ordered = {}
    for room_id in wanted_ids:
        entry = selected.get(room_id)
        if entry is None:
            missing.append(room_id)
            continue
        spec = GUILDHALL_STUB_ROOM_SPECS[room_id]
        if entry["area_prefix"] != spec["area"] or entry["canonical_title"] != spec["title"]:
            raise ValueError(
                f"Canonical room id {room_id} resolved to {entry['area_prefix']!r} / {entry['canonical_title']!r}, expected {spec['area']!r} / {spec['title']!r}."
            )
        ordered[room_id] = entry
    if missing:
        raise ValueError(f"Canonical guildhall stub room ids missing from map JSON: {missing}")
    return ordered


def _ensure_stub_room(entry, spec):
    room = _find_room_by_map_id(entry["id"])
    if room is None:
        room = create_object(ROOM_TYPECLASS, key=spec["title"], nohome=True)
    room.key = spec["title"]
    room.db.desc = spec["desc"]
    room.db.area = spec["area"]
    room.db.region_name = spec["area"]
    room.db.canonical_area = spec["area"]
    room.db.canonical_map_id = int(entry["id"])
    room.db.canonical_title = entry["canonical_title"]
    room.db.canonical_paths = str((entry.get("paths") or [""])[0] or "")
    room.db.canonical_tags = list(entry.get("tags") or [])
    room.db.canonical_timeto = dict(entry.get("timeto") or {})
    room.db.canonical_image = str(entry.get("image") or "")
    room.db.canonical_image_coords = list(entry.get("image_coords") or [])
    room.db.is_canonical_guildhall_stub = True
    room.db.canonical_phase = GUILDHALL_STUB_PHASE
    room.db.canonical_source = "direlore:map-1777858104.json"
    room.tags.add(CANONICAL_AREA_TAG_GUILDHALL_STUB)
    room.tags.add(str(int(entry["id"])), category=CANONICAL_ID_CATEGORY)
    room.aliases.add(str(entry["canonical_title"] or "").lower())
    return room


def _find_stub_guildleader(location, spec):
    for obj in list(getattr(location, "contents", []) or []):
        if getattr(obj, "db_typeclass_path", "") != STUB_GUILDLEADER_TYPECLASS:
            continue
        if str(getattr(getattr(obj, "db", None), "canonical_guild", "") or "").strip() == spec["canonical_guild"]:
            return obj
    return None


def _ensure_stub_guildleader(spec, rooms):
    room = rooms[spec["room_id"]]
    npc = _find_stub_guildleader(room, spec)
    if npc is None:
        npc = create_object(STUB_GUILDLEADER_TYPECLASS, key=spec["key"], location=room, home=room, nohome=True)
    else:
        npc.location = room
        npc.home = room
    npc.key = spec["key"]
    npc.db.desc = spec["desc"]
    npc.db.canonical_guild = spec["canonical_guild"]
    npc.db.guild_display_name = spec["guild_display_name"]
    npc.db.is_placeholder = bool(spec.get("is_placeholder", False))
    npc.db.default_inquiry_response = (
        f"{spec['key']} says, 'The {spec['guild_display_name']} is not yet open to new members. Check back as our recruitment expands.'"
    )
    npc.db.canonical_name = spec.get("canonical_name", spec["key"])
    for alias in spec.get("aliases", []):
        npc.aliases.add(alias)
    return npc


def ensure_canonical_guildhall_stubs(map_path=DEFAULT_MAP_PATH, room_ids=None):
    path = Path(map_path)
    if not path.exists():
        raise FileNotFoundError(f"Canonical guildhall stub map JSON not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Canonical guildhall stub map JSON must be a top-level list.")
    stub_ids = [int(room_id) for room_id in (room_ids or GUILDHALL_STUB_ROOM_IDS)]
    entries = guildhall_stub_entries_from_map(data, room_ids=stub_ids)
    rooms = {
        room_id: _ensure_stub_room(entry, GUILDHALL_STUB_ROOM_SPECS[room_id])
        for room_id, entry in entries.items()
    }
    imported_rooms = _collect_imported_rooms(
        PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS + PHASE4_ROOM_IDS + PHASE5_ROOM_IDS + stub_ids
    )
    for room_id, entry in entries.items():
        _populate_room_pending_exits(rooms[room_id], entry, imported_rooms)
    _drain_pending_exits(
        _collect_imported_rooms(PHASE1_ROOM_IDS + PHASE2_ROOM_IDS + PHASE3_ROOM_IDS + PHASE4_ROOM_IDS + PHASE5_ROOM_IDS),
        imported_rooms,
    )
    for spec in GUILDHALL_STUB_NPC_SPECS:
        if spec["room_id"] in rooms:
            _ensure_stub_guildleader(spec, rooms)
    return rooms