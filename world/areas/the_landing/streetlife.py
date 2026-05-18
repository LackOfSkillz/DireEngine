from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from world.area_forge.paths import area_namespace


ROOM_TYPECLASS = "typeclasses.rooms.Room"
NPC_TYPECLASS = "typeclasses.npcs.NPC"
AREA_ID = "new_landing"

STREETLIFE_NPCS = {
    "Crier Pell": {
        "node_id": "new_landing_666_432",
        "aliases": ["pell", "crier", "town crier"],
        "desc": (
            "Pell keeps a rolled proclamation tube under one arm and the alert posture of someone who expects public attention to turn ugly without warning. "
            "His voice looks ready before he uses it."
        ),
        "greeting": "Pell says, 'If you need the pulse of the district, listen for what gets posted and what gets torn down.'",
    },
    "Clerk Ardin": {
        "node_id": "new_landing_444_488",
        "aliases": ["ardin", "clerk", "scribe"],
        "desc": (
            "Ardin carries wax tablets and sealed notes in careful layers, moving with the tight economy of a clerk who has learned that hesitation multiplies paperwork."
        ),
        "greeting": "Ardin says, 'Questions travel faster than answers here. If you want certainty, get it stamped.'",
    },
    "Lamplighter Ves": {
        "node_id": "new_landing_488_538",
        "aliases": ["ves", "lamplighter", "lighter"],
        "desc": (
            "Ves smells faintly of lamp oil and damp wool, with a hook pole slung over one shoulder and the calm patience of someone used to working while the city hurries past."
        ),
        "greeting": "Ves says, 'By dusk this court belongs to shadows unless I stay ahead of them.'",
    },
    "Sergeant Nera": {
        "node_id": "new_landing_92_362",
        "aliases": ["nera", "sergeant", "gate sergeant"],
        "desc": (
            "Nera watches the gateward traffic with a soldier's stillness, one hand never straying far from the baton at her belt. "
            "She has the look of someone who remembers faces longer than names."
        ),
        "greeting": "Nera says, 'If you came through the west road intact, count that as your first good decision today.'",
    },
    "Ropefactor Dema": {
        "node_id": "new_landing_42_920",
        "aliases": ["dema", "ropefactor", "dockworker"],
        "desc": (
            "Dema's coat is stiff with salt and hemp dust, and both hands show the glossy calluses of someone who trusts rope only after testing it personally."
        ),
        "greeting": "Dema says, 'If it frays at the slip, it drowns at the pilings. That's the sort of lesson the river charges for.'",
    },
    "Wharf Runner Tavi": {
        "node_id": "new_landing_92_894",
        "aliases": ["tavi", "runner", "wharf runner"],
        "desc": (
            "Tavi stands in the restless half-crouch of someone who rarely stops moving for long, with damp boots, quick eyes, and a satchel that never seems empty."
        ),
        "greeting": "Tavi says, 'If you're looking for quiet, you're standing too close to the river and too far from sleep.'",
    },
    "Warrant Clerk Iven": {
        "node_id": "new_landing_92_670",
        "aliases": ["iven", "warrant clerk", "warrant"],
        "desc": (
            "Iven keeps his cuffs immaculate despite the quarter around him, peering over a ledger board with the tense politeness of a man who knows bad news by profession."
        ),
        "greeting": "Iven says, 'Most trouble here starts with a name on paper. The rest starts when someone pretends not to recognize it.'",
    },
}


def _room_for_node(node_id):
    namespace = area_namespace(AREA_ID)
    for room in ObjectDB.objects.get_by_tag(node_id, category=namespace["node_category"]):
        if getattr(room, "db_typeclass_path", "") == ROOM_TYPECLASS:
            return room
    return None


def _ensure_npc(key, room, *, aliases=None, desc="", greeting=""):
    npc = ObjectDB.objects.filter(db_key__iexact=key, db_location=room).first()
    if not npc:
        npc = create_object(NPC_TYPECLASS, key=key, location=room, home=room)
    npc.key = key
    npc.home = room
    if getattr(npc, "location", None) != room:
        npc.move_to(room, quiet=True, use_destination=False)
    npc.db.desc = desc
    npc.db.is_npc = True
    npc.db.default_inquiry_response = greeting
    npc.db.landing_streetlife = True
    for alias in aliases or []:
        npc.aliases.add(alias)
    return npc


def ensure_the_landing_streetlife():
    placed = {}
    for key, spec in STREETLIFE_NPCS.items():
        room = _room_for_node(spec["node_id"])
        if not room:
            continue
        placed[key] = _ensure_npc(
            key,
            room,
            aliases=spec.get("aliases", []),
            desc=spec.get("desc", ""),
            greeting=spec.get("greeting", ""),
        )
    return placed