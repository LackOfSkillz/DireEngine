import logging
import random
import time
import uuid

from evennia.utils.create import create_object

from engine.services.skill_service import SkillService
from typeclasses.rooms import is_fishable
from world.systems import fishing_economy


LOGGER = logging.getLogger(__name__)

BORROWED_GEAR_SOURCE = "maren"
BORROWED_GEAR_RETURN_ROOM_ID = 4305

NOTHING_MESSAGES = [
    "Nothing bites.",
    "The water stays still and nothing takes the line.",
    "You wait a while, but the line comes back empty.",
]
LINE_BREAK_MESSAGES = [
    "The line snaps under the strain!",
    "A sharp surge tears the line apart.",
]
SLIP_HOOK_MESSAGES = [
    "The fish twists free and spits the hook.",
    "The hook slips loose and the fish is gone.",
]
TANGLE_MESSAGES = [
    "The slack line snarls into a nasty tangle.",
    "Your timing fouls the line into a knot.",
]

BAIT_FAMILY_REGISTRY = {
    "artificial_simple": {"quality": 10, "lore_requirement": 0, "match_bonus": 0, "tags": ["artificial", "shiny", "starter"]},
    "worm_cutbait": {"quality": 14, "lore_requirement": 10, "match_bonus": 2, "tags": ["worm", "cutbait", "freshwater"]},
    "live_bait": {"quality": 18, "lore_requirement": 25, "match_bonus": 4, "tags": ["live", "river_predator", "ocean_predator"]},
    "specialty_lure": {"quality": 16, "lore_requirement": 20, "match_bonus": 6, "tags": ["specialty", "saltwater", "deepwater"]},
}

FISH_GROUP_DEFAULTS = {
    "river 1": {"label": "River 1", "difficulty_band": (20, 40), "room_density": 0.55, "junk_density": 0.08},
    "river 2": {"label": "River 2", "difficulty_band": (40, 60), "room_density": 0.48, "junk_density": 0.10},
    "river 3": {"label": "River 3", "difficulty_band": (60, 85), "room_density": 0.42, "junk_density": 0.12},
    "ocean": {"label": "Ocean", "difficulty_band": (45, 75), "room_density": 0.46, "junk_density": 0.14},
}

FIGHT_PROFILE_DATA = {
    "steady": {"pressure": 4, "escape_risk": 0.12, "break_risk": 0.04},
    "stubborn": {"pressure": 7, "escape_risk": 0.16, "break_risk": 0.06},
    "darting": {"pressure": 9, "escape_risk": 0.22, "break_risk": 0.05},
    "diving": {"pressure": 12, "escape_risk": 0.14, "break_risk": 0.10},
}

FISH_PROFILES = {
    "silver_trout": {
        "key": "silver_trout",
        "name": "silver trout",
        "fish_group": "river 1",
        "difficulty": 26,
        "weight_min": 1,
        "weight_max": 4,
        "fight_profile": "steady",
        "value_modifier": 1.0,
        "preferred_bait_families": ["worm_cutbait", "artificial_simple"],
        "preferred_bait_tags": ["worm", "shiny", "freshwater"],
    },
    "mud_carp": {
        "key": "mud_carp",
        "name": "mud carp",
        "fish_group": "river 1",
        "difficulty": 34,
        "weight_min": 2,
        "weight_max": 6,
        "fight_profile": "stubborn",
        "value_modifier": 1.1,
        "preferred_bait_families": ["worm_cutbait", "live_bait"],
        "preferred_bait_tags": ["cutbait", "live", "freshwater"],
    },
    "stone_perch": {
        "key": "stone_perch",
        "name": "stone perch",
        "fish_group": "river 2",
        "difficulty": 46,
        "weight_min": 2,
        "weight_max": 5,
        "fight_profile": "steady",
        "value_modifier": 1.25,
        "preferred_bait_families": ["worm_cutbait", "artificial_simple"],
        "preferred_bait_tags": ["worm", "shiny", "freshwater"],
    },
    "swift_pike": {
        "key": "swift_pike",
        "name": "swift pike",
        "fish_group": "river 2",
        "difficulty": 58,
        "weight_min": 3,
        "weight_max": 8,
        "fight_profile": "darting",
        "value_modifier": 1.45,
        "preferred_bait_families": ["live_bait", "specialty_lure"],
        "preferred_bait_tags": ["live", "river_predator", "shiny"],
    },
    "shadow_eel": {
        "key": "shadow_eel",
        "name": "shadow eel",
        "fish_group": "river 3",
        "difficulty": 68,
        "weight_min": 2,
        "weight_max": 7,
        "fight_profile": "darting",
        "value_modifier": 1.6,
        "preferred_bait_families": ["live_bait", "worm_cutbait"],
        "preferred_bait_tags": ["live", "cutbait", "deepwater"],
    },
    "glass_sturgeon": {
        "key": "glass_sturgeon",
        "name": "glass sturgeon",
        "fish_group": "river 3",
        "difficulty": 82,
        "weight_min": 6,
        "weight_max": 14,
        "fight_profile": "diving",
        "value_modifier": 2.1,
        "preferred_bait_families": ["specialty_lure", "live_bait"],
        "preferred_bait_tags": ["deepwater", "live", "specialty"],
    },
    "brine_mackerel": {
        "key": "brine_mackerel",
        "name": "brine mackerel",
        "fish_group": "ocean",
        "difficulty": 54,
        "weight_min": 2,
        "weight_max": 6,
        "fight_profile": "steady",
        "value_modifier": 1.35,
        "preferred_bait_families": ["specialty_lure", "artificial_simple"],
        "preferred_bait_tags": ["saltwater", "shiny", "specialty"],
    },
    "storm_ray": {
        "key": "storm_ray",
        "name": "storm ray",
        "fish_group": "ocean",
        "difficulty": 74,
        "weight_min": 5,
        "weight_max": 12,
        "fight_profile": "diving",
        "value_modifier": 1.9,
        "preferred_bait_families": ["specialty_lure", "live_bait"],
        "preferred_bait_tags": ["saltwater", "deepwater", "ocean_predator"],
    },
}

FISH_GROUP_CATCH_TABLES = {
    "river 1": [("silver_trout", 70), ("mud_carp", 30)],
    "river 2": [("stone_perch", 65), ("swift_pike", 35)],
    "river 3": [("shadow_eel", 60), ("glass_sturgeon", 40)],
    "ocean": [("brine_mackerel", 68), ("storm_ray", 32)],
}

DEFAULT_GEAR_RATINGS = {"rod_rating": 12.0, "hook_rating": 10.0, "line_rating": 10.0}

OUTCOME_WEIGHTS = {
    "river 1": [("fish", 64), ("junk_common", 28), ("junk_interesting", 6), ("event", 2)],
    "river 2": [("fish", 64), ("junk_common", 27), ("junk_interesting", 7), ("event", 2)],
    "river 3": [("fish", 62), ("junk_common", 29), ("junk_interesting", 6), ("event", 3)],
    "ocean": [("fish", 65), ("junk_common", 26), ("junk_interesting", 7), ("event", 2)],
}

JUNK_TABLES = {
    "River 1": {
        "common": [
            {"key": "weeds", "name": "weeds", "weight": 32, "value": 1, "desc": "A dripping mass of pond weeds and silt.", "pull_message": "You drag up a dripping tangle of weeds."},
            {"key": "broken_branch", "name": "broken branch", "weight": 24, "value": 1, "desc": "A snapped branch gone soft from the water.", "pull_message": "A broken branch scrapes over the rail as you haul it in."},
            {"key": "old_boot", "name": "old boot", "weight": 18, "value": 2, "desc": "An old boot swollen with muddy water.", "pull_message": "An old boot swings from the line, dripping pond water."},
            {"key": "tangled_line", "name": "tangled line", "weight": 26, "value": 1, "desc": "A knot of discarded line wrapped around a bent swivel.", "pull_message": "You pull in a foul tangle of abandoned line."},
        ],
        "interesting": [
            {"key": "coin_pouch", "name": "coin pouch", "weight": 34, "value": 14, "desc": "A water-darkened pouch with a few forgotten coins inside.", "pull_message": "A small coin pouch knocks against the stones as it comes free."},
            {"key": "rusted_dagger", "name": "rusted dagger", "weight": 22, "value": 11, "desc": "A rusted dagger with a warped grip.", "pull_message": "You haul up a rusted dagger slick with algae."},
            {"key": "trinket", "name": "trinket", "weight": 20, "value": 9, "desc": "A little trinket dulled by silt and time.", "pull_message": "A little trinket flashes once beneath the water before you land it."},
            {"key": "lost_charm", "name": "lost charm", "weight": 24, "value": 16, "desc": "A lost charm on a broken cord, still oddly bright.", "pull_message": "A lost charm comes up glittering through the reeds."},
        ],
        "event": [
            {
                "key": "violent_tug",
                "name": "violent tug",
                "weight": 100,
                "hook_message": "Your line jerks violently -- this is no fish.",
                "resolution_message": "Whatever it was tears free, snapping your line.",
                "choice_prompt": "Pull harder or release?",
                "encounter_enabled": False,
            }
        ],
    },
    "River 2": {
        "common": [
            {"key": "silt_bundle", "name": "silt bundle", "weight": 30, "value": 1, "desc": "A sodden clump of reeds packed with silt.", "pull_message": "A heavy bundle of reeds and silt drags in on the line."},
            {"key": "snapped_float", "name": "snapped float", "weight": 24, "value": 2, "desc": "Half a cracked float painted in faded red.", "pull_message": "You drag up a snapped float from some older angler's loss."},
            {"key": "broken_branch", "name": "broken branch", "weight": 20, "value": 1, "desc": "A slick branch stripped bare by current.", "pull_message": "A stripped branch comes skidding over the bank."},
            {"key": "snagged_leader", "name": "snagged leader", "weight": 26, "value": 1, "desc": "A snagged leader with corroded swivels.", "pull_message": "A snagged leader and old swivels come up in a knot."},
        ],
        "interesting": [
            {"key": "coin_pouch", "name": "coin pouch", "weight": 28, "value": 13, "desc": "A soaked pouch with a few coins still trapped inside.", "pull_message": "A soaked coin pouch thumps against the bank."},
            {"key": "rusted_dagger", "name": "rusted dagger", "weight": 24, "value": 10, "desc": "A river-rusted dagger with a chipped edge.", "pull_message": "You lift a rusted dagger out of the current."},
            {"key": "lost_charm", "name": "lost charm", "weight": 22, "value": 15, "desc": "A lost charm worked in tarnished silver.", "pull_message": "A tarnished charm swings free of the water."},
            {"key": "carved_token", "name": "carved token", "weight": 26, "value": 12, "desc": "A carved token worn smooth by the river.", "pull_message": "A carved token spins from the line as you lift it free."},
        ],
        "event": [
            {
                "key": "violent_tug",
                "name": "violent tug",
                "weight": 100,
                "hook_message": "Your line jerks violently -- this is no fish.",
                "resolution_message": "Whatever it was tears free, snapping your line.",
                "choice_prompt": "Pull harder or release?",
                "encounter_enabled": False,
            }
        ],
    },
    "River 3": {
        "common": [
            {"key": "black_weeds", "name": "black weeds", "weight": 28, "value": 1, "desc": "A black rope of deep weeds slimed with river muck.", "pull_message": "A rope of black weeds drags up from the darker channel."},
            {"key": "splintered_pole_tip", "name": "splintered pole tip", "weight": 22, "value": 2, "desc": "The splintered tip of a ruined fishing pole.", "pull_message": "You drag up the splintered tip of a ruined pole."},
            {"key": "river_boot", "name": "river boot", "weight": 20, "value": 2, "desc": "A heavy boot packed with dark river clay.", "pull_message": "A clay-heavy river boot breaks the surface."},
            {"key": "snarled_leader", "name": "snarled leader", "weight": 30, "value": 1, "desc": "A snarled leader wrapped around a snapped hook.", "pull_message": "A snarled leader comes up twisting around itself."},
        ],
        "interesting": [
            {"key": "coin_pouch", "name": "coin pouch", "weight": 26, "value": 15, "desc": "A waterlogged pouch that still clinks faintly.", "pull_message": "A heavy coin pouch comes loose from the depths."},
            {"key": "rusted_dagger", "name": "rusted dagger", "weight": 24, "value": 12, "desc": "A broad dagger eaten by rust but still saleable.", "pull_message": "A broad rusted dagger drags over the stones."},
            {"key": "trinket", "name": "trinket", "weight": 18, "value": 10, "desc": "A dark little trinket with bits of inlay still visible.", "pull_message": "A dark trinket glints once before it clears the water."},
            {"key": "lost_charm", "name": "lost charm", "weight": 32, "value": 17, "desc": "A lost charm chased with worn river patterns.", "pull_message": "A lost charm rises from the current on a strip of cord."},
        ],
        "event": [
            {
                "key": "violent_tug",
                "name": "violent tug",
                "weight": 100,
                "hook_message": "Your line jerks violently -- this is no fish.",
                "resolution_message": "Whatever it was tears free, snapping your line.",
                "choice_prompt": "Pull harder or release?",
                "encounter_enabled": False,
            }
        ],
    },
    "Ocean": {
        "common": [
            {"key": "kelp_wad", "name": "kelp wad", "weight": 32, "value": 1, "desc": "A cold wad of kelp and shell grit.", "pull_message": "A dripping wad of kelp slaps against the bank."},
            {"key": "barnacled_boot", "name": "barnacled boot", "weight": 18, "value": 2, "desc": "A barnacled boot with the leather nearly gone.", "pull_message": "A barnacled boot swings from the line."},
            {"key": "shattered_float", "name": "shattered float", "weight": 22, "value": 2, "desc": "A shattered float salt-stiffened by spray.", "pull_message": "A shattered float bounces across the stones as you lift it in."},
            {"key": "salt_tangled_line", "name": "salt-tangled line", "weight": 28, "value": 1, "desc": "A crusted knot of salt-stiff line and bent wire.", "pull_message": "You drag up a crusted tangle of salt-stiff line."},
        ],
        "interesting": [
            {"key": "coin_pouch", "name": "coin pouch", "weight": 24, "value": 15, "desc": "A leather pouch with seawater-darkened coins inside.", "pull_message": "A seawater-darkened coin pouch comes in with the line."},
            {"key": "rusted_dagger", "name": "rusted dagger", "weight": 26, "value": 11, "desc": "A salt-eaten dagger still worth a little salvage.", "pull_message": "You lift a salt-eaten dagger from the wash."},
            {"key": "sailor_trinket", "name": "sailor trinket", "weight": 22, "value": 13, "desc": "A sailor's trinket hung from a corroded ring.", "pull_message": "A sailor's trinket flashes in the sun as you haul it in."},
            {"key": "lost_charm", "name": "lost charm", "weight": 28, "value": 16, "desc": "A lost charm rubbed smooth by brine and grit.", "pull_message": "A lost charm comes up tangled in kelp."},
        ],
        "event": [
            {
                "key": "violent_tug",
                "name": "violent tug",
                "weight": 100,
                "hook_message": "Your line jerks violently -- this is no fish.",
                "resolution_message": "Whatever it was tears free, snapping your line.",
                "choice_prompt": "Pull harder or release?",
                "encounter_enabled": False,
            }
        ],
    },
}


class FishingSession:
    def __init__(self, actor):
        self.actor = actor
        self.state = "idle"
        self.baited = False
        self.hooked_fish = None
        self.active_fish_profile = None
        self.bait_item_id = None
        self.bait_family = None
        self.bait_quality = 0.0
        self.bait_match_tags = []
        self.attempt_token = None
        self.room_id = None
        self.nibble_time = None
        self.last_pull_time = None
        self.pending_pull = False
        self.struggle_round = 0
        self.rod_rating = float(DEFAULT_GEAR_RATINGS["rod_rating"])
        self.hook_rating = float(DEFAULT_GEAR_RATINGS["hook_rating"])
        self.line_rating = float(DEFAULT_GEAR_RATINGS["line_rating"])
        self.line_broken = False
        self.tangled = False
        self.last_outcome = None
        self.outcome_type = None
        self.active_junk_profile = None
        self.active_event_profile = None
        self.scheduled_callbacks = {}
        self.bite_delay = None
        self.nibble_window_delay = None


def clamp(value, low, high):
    return max(float(low), min(float(high), float(value)))


def _normalize_key(value, default=""):
    normalized = str(value or default).strip().lower().replace("-", " ").replace("_", " ")
    return " ".join(normalized.split())


def _safe_actor_rank(actor, skill_name):
    if actor is None or not hasattr(actor, "get_skill"):
        return 0.0
    return max(0.0, float(actor.get_skill(skill_name) or 0.0))


def _safe_actor_stat(actor, stat_name, default=10.0):
    if actor is None:
        return float(default)
    if hasattr(actor, "get_stat"):
        try:
            value = actor.get_stat(stat_name)
            if value is not None:
                return float(value)
        except Exception:
            pass
    stats = getattr(getattr(actor, "db", None), "stats", None)
    if isinstance(stats, dict):
        try:
            return float(stats.get(stat_name, default) or default)
        except (TypeError, ValueError):
            return float(default)
    return float(default)


def _trace(actor, event, **payload):
    LOGGER.debug("fishing event=%s payload=%s", event, payload)
    if actor is None or not bool(getattr(getattr(actor, "ndb", None), "fishing_debug", False)):
        return
    entries = list(getattr(actor.ndb, "fishing_debug_trace", []) or [])
    entries.append({"event": str(event), "payload": dict(payload), "timestamp": float(time.time())})
    actor.ndb.fishing_debug_trace = entries[-100:]


def resolve_bait_family(family_name):
    normalized = _normalize_key(family_name)
    family_key = normalized.replace(" ", "_")
    return family_key if family_key in BAIT_FAMILY_REGISTRY else None


def is_valid_bait_item(item):
    if not item:
        return False
    if not bool(getattr(getattr(item, "db", None), "is_bait", False)):
        return False
    family_name = getattr(getattr(item, "db", None), "bait_family", None) or getattr(getattr(item, "db", None), "bait_type", None)
    return resolve_bait_family(family_name) is not None


def resolve_bait_profile(bait_item):
    if not is_valid_bait_item(bait_item):
        return None
    family_name = resolve_bait_family(getattr(getattr(bait_item, "db", None), "bait_family", None) or getattr(getattr(bait_item, "db", None), "bait_type", None)) or "worm_cutbait"
    family = dict(BAIT_FAMILY_REGISTRY.get(family_name, BAIT_FAMILY_REGISTRY["worm_cutbait"]))
    quality_override = getattr(getattr(bait_item, "db", None), "bait_quality", None)
    if quality_override is None:
        quality_override = getattr(getattr(bait_item, "db", None), "quality", None)
    try:
        quality = float(quality_override if quality_override is not None else family["quality"])
    except (TypeError, ValueError):
        quality = float(family["quality"])
    raw_tags = getattr(getattr(bait_item, "db", None), "bait_match_tags", None)
    if isinstance(raw_tags, (list, tuple, set)):
        match_tags = [_normalize_key(tag) for tag in list(raw_tags or []) if str(tag or "").strip()]
    else:
        match_tags = []
    if not match_tags:
        match_tags = [_normalize_key(tag) for tag in list(family.get("tags", []) or [])]
    return {
        "family": family_name,
        "quality": quality,
        "lore_requirement": float(family.get("lore_requirement", 0.0) or 0.0),
        "match_bonus": float(family.get("match_bonus", 0.0) or 0.0),
        "match_tags": match_tags,
    }


def resolve_fish_group_data(room_or_group):
    source_name = getattr(getattr(room_or_group, "db", None), "fish_group", None) if hasattr(room_or_group, "db") else room_or_group
    normalized = _normalize_key(source_name, default="river 1")
    is_fallback = normalized not in FISH_GROUP_DEFAULTS
    group_key = normalized if normalized in FISH_GROUP_DEFAULTS else "river 1"
    data = dict(FISH_GROUP_DEFAULTS[group_key])
    data["key"] = group_key
    data["is_fallback"] = is_fallback
    data["source_name"] = str(source_name or data.get("label", "River 1"))
    return data


def get_fish_profile(profile_key):
    normalized = _normalize_key(profile_key).replace(" ", "_")
    if normalized not in FISH_PROFILES:
        return None
    return dict(FISH_PROFILES[normalized])


def get_fish_profiles_for_group(room_or_group):
    group_data = resolve_fish_group_data(room_or_group)
    return [dict(FISH_PROFILES[key]) for key, _weight in list(FISH_GROUP_CATCH_TABLES.get(group_data["key"], []) or []) if key in FISH_PROFILES]


def choose_weighted_fish_profile(room_or_group, rng=None):
    rng = rng or random
    group_data = resolve_fish_group_data(room_or_group)
    table = list(FISH_GROUP_CATCH_TABLES.get(group_data["key"], []) or [])
    if not table:
        table = list(FISH_GROUP_CATCH_TABLES["river 1"])
    total = sum(max(1, int(weight or 0)) for _key, weight in table)
    pick = float(rng.random()) * float(total)
    running = 0.0
    for profile_key, weight in table:
        running += float(max(1, int(weight or 0)))
        if pick <= running:
            return dict(FISH_PROFILES[profile_key])
    return dict(FISH_PROFILES[table[-1][0]])


def choose_weighted_entry(table, rng=None):
    rng = rng or random
    entries = list(table or [])
    if not entries:
        return None
    total = sum(max(1, int(entry[1] if isinstance(entry, tuple) else entry.get("weight", 0) or 0)) for entry in entries)
    pick = float(rng.random()) * float(total)
    running = 0.0
    for entry in entries:
        if isinstance(entry, tuple):
            payload, weight = entry
        else:
            payload = entry
            weight = entry.get("weight", 0)
        running += float(max(1, int(weight or 0)))
        if pick <= running:
            return payload
    return entries[-1][0] if isinstance(entries[-1], tuple) else entries[-1]


def get_junk_table(room_or_group):
    group_data = resolve_fish_group_data(room_or_group)
    return dict(JUNK_TABLES.get(str(group_data.get("label", "River 1") or "River 1"), JUNK_TABLES["River 1"]))


def choose_weighted_junk_profile(room_or_group, tier, rng=None):
    table = list(get_junk_table(room_or_group).get(str(tier or "common"), []) or [])
    choice = choose_weighted_entry(table, rng=rng)
    if choice is None:
        return None
    profile = dict(choice)
    profile["tier"] = str(tier or "common")
    profile["group"] = str(resolve_fish_group_data(room_or_group).get("label", "River 1") or "River 1")
    return profile


def roll_fishing_outcome(room_or_group, rng=None):
    rng = rng or random
    group_data = resolve_fish_group_data(room_or_group)
    weights = list(OUTCOME_WEIGHTS.get(group_data["key"], OUTCOME_WEIGHTS["river 1"]))
    category = str(choose_weighted_entry(weights, rng=rng) or "fish")
    if category == "fish":
        return {"category": "fish", "profile": choose_weighted_fish_profile(room_or_group, rng=rng)}
    if category == "junk_common":
        return {"category": "junk", "profile": choose_weighted_junk_profile(room_or_group, "common", rng=rng)}
    if category == "junk_interesting":
        return {"category": "junk", "profile": choose_weighted_junk_profile(room_or_group, "interesting", rng=rng)}
    return {"category": "event", "profile": choose_weighted_junk_profile(room_or_group, "event", rng=rng)}


def calculate_lore_efficiency(actor, bait_profile):
    scholarship = _safe_actor_rank(actor, "scholarship")
    requirement = max(0.0, float((bait_profile or {}).get("lore_requirement", 0.0) or 0.0))
    if requirement <= 0.0 or scholarship >= requirement:
        return 1.0
    deficit = requirement - scholarship
    return clamp(1.0 - (deficit / max(requirement + 20.0, 25.0)) * 0.35, 0.65, 1.0)


def calculate_fishing_rating(actor):
    outdoorsmanship = _safe_actor_rank(actor, "outdoorsmanship")
    reflex = _safe_actor_stat(actor, "reflex", default=10.0)
    discipline = _safe_actor_stat(actor, "discipline", default=10.0)
    base_rating = (outdoorsmanship * 0.65) + (reflex * 0.20) + (discipline * 0.15)
    if actor is not None and hasattr(actor, "get_empath_strain_fishing_modifier"):
        base_rating *= float(actor.get_empath_strain_fishing_modifier() or 1.0)
    return base_rating


def _apply_empath_strain(actor, event_key, amount=0, fish_profile=None):
    if actor is None or not hasattr(actor, "apply_fishing_empath_strain"):
        return 0
    return actor.apply_fishing_empath_strain(event_key, amount=amount, fish_profile=fish_profile)


def calculate_bait_match_bonus(bait_profile, fish_profile):
    bait_profile = dict(bait_profile or {})
    fish_profile = dict(fish_profile or {})
    family = str(bait_profile.get("family", "") or "")
    tags = set(_normalize_key(tag) for tag in list(bait_profile.get("match_tags", []) or []) if str(tag or "").strip())
    preferred_families = set(str(name or "") for name in list(fish_profile.get("preferred_bait_families", []) or []))
    preferred_tags = set(_normalize_key(tag) for tag in list(fish_profile.get("preferred_bait_tags", []) or []) if str(tag or "").strip())
    base_bonus = float(bait_profile.get("match_bonus", 0.0) or 0.0)
    if family in preferred_families:
        return base_bonus
    if tags & preferred_tags:
        return base_bonus * 0.75
    return -max(1.0, base_bonus * 0.5)


def resolve_gear_ratings(actor, session=None):
    if session is not None and all(float(getattr(session, key, 0.0) or 0.0) > 0.0 for key in ("rod_rating", "hook_rating", "line_rating")):
        return {
            "rod_rating": float(session.rod_rating),
            "hook_rating": float(session.hook_rating),
            "line_rating": float(session.line_rating),
        }
    ratings = {}
    pole = get_fishing_pole(actor)
    for key, default in DEFAULT_GEAR_RATINGS.items():
        db_value = getattr(getattr(actor, "db", None), key, None)
        if key == "rod_rating" and pole is not None:
            db_value = getattr(getattr(pole, "db", None), "pole_rating", db_value)
        if key == "hook_rating" and pole is not None and bool(getattr(getattr(pole, "db", None), "hook_attached", False)):
            db_value = getattr(getattr(pole, "db", None), "hook_rating", db_value if db_value is not None else DEFAULT_GEAR_RATINGS["hook_rating"])
        if key == "line_rating" and pole is not None and bool(getattr(getattr(pole, "db", None), "line_attached", False)):
            db_value = getattr(getattr(pole, "db", None), "line_rating", db_value if db_value is not None else DEFAULT_GEAR_RATINGS["line_rating"])
        try:
            ratings[key] = float(db_value if db_value is not None else default)
        except (TypeError, ValueError):
            ratings[key] = float(default)
    return ratings


def get_pole_issue(pole):
    if pole is None:
        return "missing"
    pole_db = getattr(pole, "db", None)
    if bool(getattr(pole_db, "line_tangled", False)):
        return "tangled"
    if not bool(getattr(pole_db, "hook_attached", False)) or not bool(getattr(pole_db, "line_attached", False)):
        return "unrigged"
    return None


def calculate_nibble_chance(actor, room_or_group, bait_item, fish_profile):
    bait_profile = resolve_bait_profile(bait_item)
    group_data = resolve_fish_group_data(room_or_group)
    fish_profile = dict(fish_profile or {})
    lore_efficiency = calculate_lore_efficiency(actor, bait_profile)
    quality = float(bait_profile.get("quality", 0.0) or 0.0)
    room_density = float(group_data.get("room_density", 0.45) or 0.45)
    difficulty = float(fish_profile.get("difficulty", 20.0) or 20.0)
    chance = 0.12 + (quality * 0.010) + (room_density * 0.30) + (lore_efficiency * 0.06) - (difficulty * 0.0025)
    if actor is not None and hasattr(actor, "get_empath_strain_fishing_modifier"):
        chance *= float(actor.get_empath_strain_fishing_modifier() or 1.0)
    return clamp(chance, 0.08, 0.78)


def calculate_hookup_chance(actor, session, bait_item, fish_profile):
    bait_profile = resolve_bait_profile(bait_item)
    lore_efficiency = calculate_lore_efficiency(actor, bait_profile)
    fishing_rating = calculate_fishing_rating(actor)
    fish_profile = dict(fish_profile or {})
    match_bonus = calculate_bait_match_bonus(bait_profile, fish_profile)
    chance = 0.18
    chance += fishing_rating * 0.004
    chance += float(getattr(session, "hook_rating", DEFAULT_GEAR_RATINGS["hook_rating"]) or DEFAULT_GEAR_RATINGS["hook_rating"]) * 0.015
    chance += match_bonus * 0.025
    chance += lore_efficiency * 0.04
    chance -= float(fish_profile.get("difficulty", 20.0) or 20.0) * 0.003
    if actor is not None and hasattr(actor, "get_empath_strain_fishing_modifier"):
        chance *= float(actor.get_empath_strain_fishing_modifier() or 1.0)
    return clamp(chance, 0.08, 0.92)


def calculate_timeout_tangle_chance(actor, fish_profile):
    discipline = _safe_actor_stat(actor, "discipline", default=10.0)
    difficulty = float((fish_profile or {}).get("difficulty", 20.0) or 20.0)
    chance = 0.12 + (difficulty * 0.0025) - (discipline * 0.003)
    if actor is not None and hasattr(actor, "get_empath_strain_tangle_modifier"):
        chance *= float(actor.get_empath_strain_tangle_modifier() or 1.0)
    return clamp(chance, 0.08, 0.45)


def calculate_invalid_pull_tangle_chance(actor, session):
    if str(getattr(session, "state", "") or "") != "cast":
        return 0.0
    reflex = _safe_actor_stat(actor, "reflex", default=10.0)
    chance = 0.18 - (reflex * 0.004)
    return clamp(chance, 0.06, 0.18)


def calculate_fish_value(fish_profile, weight):
    fish_profile = dict(fish_profile or {})
    base_value = (float(fish_profile.get("difficulty", 20.0) or 20.0) * 0.45) + (float(weight or 0.0) * 3.0)
    return max(1, int(round(base_value * float(fish_profile.get("value_modifier", 1.0) or 1.0))))


def resolve_struggle_outcome_data(actor, session, fish_profile, bait_item, *, rng=None):
    rng = rng or random
    fish_profile = dict(fish_profile or {})
    bait_profile = resolve_bait_profile(bait_item) if bait_item is not None else {"quality": 0.0}
    fishing_rating = calculate_fishing_rating(actor)
    gear_rating = float(getattr(session, "rod_rating", 0.0) or 0.0) + float(getattr(session, "hook_rating", 0.0) or 0.0) + float(getattr(session, "line_rating", 0.0) or 0.0)
    fight_profile = dict(FIGHT_PROFILE_DATA.get(str(fish_profile.get("fight_profile", "steady") or "steady"), FIGHT_PROFILE_DATA["steady"]))
    pressure = float(fish_profile.get("difficulty", 20.0) or 20.0) + float(fight_profile.get("pressure", 0.0) or 0.0) + (float(rng.random()) * 10.0)
    round_bonus = min(0.18, max(0, int(getattr(session, "struggle_round", 0) or 0)) * 0.05)
    reaction_bonus = 0.08 if bool(getattr(session, "pending_pull", False)) else -0.06
    lore_efficiency = calculate_lore_efficiency(actor, bait_profile)
    landed_score = 0.22 + ((fishing_rating + gear_rating - pressure) / 160.0) + round_bonus + reaction_bonus + ((lore_efficiency - 0.65) * 0.10)
    lost_score = 0.16 + ((pressure - (fishing_rating * 0.55 + float(getattr(session, "hook_rating", 0.0) or 0.0))) / 150.0)
    break_score = float(fight_profile.get("break_risk", 0.04) or 0.04)
    break_score += max(0.0, pressure - (float(getattr(session, "line_rating", 0.0) or 0.0) + float(getattr(session, "rod_rating", 0.0) or 0.0))) / 90.0
    break_score = clamp(break_score, 0.02, 0.55)
    lost_score = clamp(lost_score, 0.08, 0.45)
    landed_score = clamp(landed_score, 0.10, 0.80)
    if actor is not None and hasattr(actor, "get_empath_strain_fishing_modifier"):
        strain_modifier = float(actor.get_empath_strain_fishing_modifier() or 1.0)
        landed_score = clamp(landed_score * strain_modifier, 0.08, 0.80)
        break_score = clamp(break_score * (2.0 - strain_modifier), 0.02, 0.55)

    break_roll = float(rng.random())
    outcome_roll = float(rng.random())
    if pressure > gear_rating + 10.0 and break_roll < break_score:
        return {"outcome": "line_break", "pressure": pressure, "break_score": break_score, "landed_score": landed_score, "lost_score": lost_score}
    if outcome_roll < landed_score:
        return {"outcome": "landed", "pressure": pressure, "break_score": break_score, "landed_score": landed_score, "lost_score": lost_score}
    if outcome_roll < landed_score + lost_score:
        return {"outcome": "lost_fish", "pressure": pressure, "break_score": break_score, "landed_score": landed_score, "lost_score": lost_score}
    return {"outcome": "still_fighting", "pressure": pressure, "break_score": break_score, "landed_score": landed_score, "lost_score": lost_score}


def get_fishing_session(actor, create=False):
    session = getattr(actor.ndb, "fishing_session", None)
    if session is None and create:
        session = FishingSession(actor)
        actor.ndb.fishing_session = session
    return session


def has_fishing_session(actor):
    return get_fishing_session(actor, create=False) is not None


def _get_expected_session(actor, *, expected_state=None, token=None):
    session = get_fishing_session(actor, create=False)
    if session is None:
        return None
    if expected_state is not None and str(getattr(session, "state", "") or "") != str(expected_state):
        return None
    if token is not None and str(getattr(session, "attempt_token", "") or "") != str(token):
        return None
    return session


def _sync_runtime_flags(actor, session):
    active = bool(session and str(getattr(session, "state", "") or "") in {"cast", "nibble", "hooked"})
    actor.ndb.is_fishing = active
    actor.ndb.fishing_attempt_token = getattr(session, "attempt_token", None) if session else None
    actor.ndb.fishing_room_id = getattr(session, "room_id", None) if session else None


def _cancel_scheduled_task(task):
    if task is None:
        return
    cancel = getattr(task, "cancel", None)
    if callable(cancel):
        try:
            cancel()
            return
        except Exception:
            pass
    stop = getattr(task, "stop", None)
    if callable(stop):
        try:
            stop()
        except Exception:
            pass


def _clear_session_callbacks(session, callback_key=None):
    if session is None:
        return
    callbacks = dict(getattr(session, "scheduled_callbacks", {}) or {})
    if callback_key is None:
        for task in callbacks.values():
            _cancel_scheduled_task(task)
        session.scheduled_callbacks = {}
        return
    _cancel_scheduled_task(callbacks.pop(callback_key, None))
    session.scheduled_callbacks = callbacks


def _schedule_session_callback(actor, session, callback_key, seconds, callback, *callback_args):
    from world.systems.scheduler import schedule_event

    if actor is None or session is None:
        return None
    callbacks = dict(getattr(session, "scheduled_callbacks", {}) or {})
    _cancel_scheduled_task(callbacks.get(callback_key))
    task = schedule_event(
        key=f"fishing_{callback_key}",
        owner=actor,
        delay=float(seconds),
        callback=callback,
        payload={"args": [actor, *callback_args]},
        metadata={"system": "fishing", "type": "delayed_effect"},
    )
    callbacks[callback_key] = task
    session.scheduled_callbacks = callbacks
    return task


def _get_group_bite_delay_range(room_or_group):
    group_key = str(resolve_fish_group_data(room_or_group).get("key", "river 1") or "river 1")
    if group_key == "river 1":
        return 4.0, 10.0
    if group_key == "river 2":
        return 5.0, 13.0
    if group_key == "river 3":
        return 6.0, 18.0
    if group_key == "ocean":
        return 5.0, 16.0
    return 5.0, 15.0


def calculate_bite_delay(room_or_group, rng=None):
    rng = rng or random
    low, high = _get_group_bite_delay_range(room_or_group)
    return float(rng.uniform(float(low), float(high)))


def calculate_nibble_window_delay(rng=None):
    rng = rng or random
    return max(1.5, 3.0 + float(rng.uniform(-0.5, 1.5)))


def reset_fishing_session(actor):
    if actor is None:
        return
    session = getattr(actor.ndb, "fishing_session", None)
    _clear_session_callbacks(session)
    actor.ndb.fishing_session = None
    actor.ndb.is_fishing = False
    actor.ndb.fishing_attempt_token = None
    actor.ndb.fishing_room_id = None


def get_event_choice_prompt(event_profile=None):
    profile = dict(event_profile or {})
    return {
        "prompt": str(profile.get("choice_prompt", "Pull harder or release?") or "Pull harder or release?"),
        "options": ["pull_harder", "release"],
    }


def maybe_spawn_encounter(actor, room, event_profile=None):
    profile = dict(event_profile or {})
    if bool(getattr(getattr(room, "db", None), "safe_zone", False)):
        return None
    if not bool(profile.get("encounter_enabled", False)):
        return None
    return None


def cancel_fishing_session(actor, message=None):
    session = get_fishing_session(actor, create=False)
    if actor is not None and message:
        actor.msg(message)
    if session is not None:
        _clear_session_callbacks(session)
        session.state = "idle"
        session.last_outcome = "canceled"
    reset_fishing_session(actor)


def mark_borrowed_item(item, source=BORROWED_GEAR_SOURCE):
    if not item:
        return item
    item.db.borrowed = True
    item.db.borrowed_source = str(source or BORROWED_GEAR_SOURCE)
    return item


def is_borrowed(item):
    if not item:
        return False
    return getattr(getattr(item, "db", None), "borrowed", False) is True


def is_borrowed_return_room(room):
    if room is None:
        return False
    if int(getattr(room, "id", 0) or 0) == BORROWED_GEAR_RETURN_ROOM_ID:
        return True
    return bool(getattr(getattr(room, "db", None), "borrowed_gear_return_room", False))


def get_borrowed_items(actor):
    if actor is None:
        return []
    return [item for item in list(getattr(actor, "contents", []) or []) if is_borrowed(item)]


def format_borrowed_return_message(direction, paused=False):
    travel_direction = str(direction or "away").strip().lower()
    if paused:
        return f"You pause long enough to return the borrowed fishing gear before heading {travel_direction}."
    return f"You return the borrowed fishing gear and head {travel_direction}."


def _finalize_borrowed_return_cleanup(actor, borrowed_item_ids, fallback_location=None):
    if actor is None:
        return
    borrowed_id_set = {int(item_id or 0) for item_id in list(borrowed_item_ids or []) if int(item_id or 0) > 0}
    if not borrowed_id_set:
        return

    carried_items = list(getattr(actor, "contents", []) or [])
    for item in carried_items:
        if int(getattr(item, "id", 0) or 0) not in borrowed_id_set:
            continue
        for carried in list(getattr(item, "contents", []) or []):
            if is_borrowed(carried):
                continue
            carried.move_to(actor, quiet=True, use_destination=False)
        try:
            item.delete()
        except Exception:
            LOGGER.warning("Borrowed gear delete fallback engaged for %s", getattr(item, "key", item))
            if fallback_location is not None:
                item.move_to(fallback_location, quiet=True, use_destination=False, move_hooks=False)


def return_borrowed_gear(actor, source_location=None, direction=None):
    from world.systems.scheduler import schedule_event

    if actor is None or source_location is None or not is_borrowed_return_room(source_location):
        return False
    destination = getattr(actor, "location", None)
    if destination is None or destination == source_location:
        return False

    borrowed_items = get_borrowed_items(actor)
    if not borrowed_items:
        return False

    travel_direction = str(direction or getattr(getattr(actor, "ndb", None), "last_traverse_direction", None) or "away").strip().lower()
    paused_flavor = bool(getattr(getattr(source_location, "db", None), "borrowed_gear_return_pause_flavor", False))
    actor.msg(format_borrowed_return_message(travel_direction, paused=paused_flavor))
    schedule_event(
        key="borrowed_return_cleanup",
        owner=actor,
        delay=0,
        callback=_finalize_borrowed_return_cleanup,
        payload={"args": [actor, [int(getattr(item, "id", 0) or 0) for item in borrowed_items], source_location]},
        metadata={"system": "fishing", "type": "delayed_effect"},
    )
    return True


def _get_fishing_difficulty(room_or_group):
    group_data = resolve_fish_group_data(room_or_group)
    lower, upper = group_data.get("difficulty_band", (20, 40))
    return int(round((float(lower) + float(upper)) / 2.0))


def _award_outdoorsmanship(actor, room_or_group, *, success, outcome, multiplier):
    if actor is None:
        return
    difficulty = _get_fishing_difficulty(room_or_group)
    SkillService.award_xp(actor, "outdoorsmanship", difficulty, source={"mode": "difficulty"}, success=success, outcome=outcome, event_key="fishing", context_multiplier=multiplier)


def _spawn_junk_item(actor, junk_profile):
    junk_profile = dict(junk_profile or {})
    junk = create_object("typeclasses.items.junk.Junk", key=str(junk_profile.get("name", "junk") or "junk"), location=actor, home=actor)
    junk.db.item_type = "junk"
    junk.db.is_junk = True
    junk.db.junk_key = str(junk_profile.get("key", junk.key) or junk.key)
    junk.db.junk_tier = str(junk_profile.get("tier", "common") or "common")
    junk.db.junk_group = str(junk_profile.get("group", "River 1") or "River 1")
    junk.db.value = max(1, int(junk_profile.get("value", 1) or 1))
    junk.db.item_value = junk.db.value
    junk.db.weight = float(junk_profile.get("item_weight", 0.5) or 0.5)
    junk.db.desc = str(junk_profile.get("desc", "A waterlogged bit of salvage.") or "A waterlogged bit of salvage.")
    return junk


def _resolve_junk_pull(actor):
    session = get_fishing_session(actor, create=False)
    if session is None or session.state != "junk":
        actor.msg("There's nothing on the line anymore.")
        return False

    room = getattr(actor, "location", None)
    junk_profile = dict(getattr(session, "active_junk_profile", None) or {})
    junk = _spawn_junk_item(actor, junk_profile)
    if str(junk_profile.get("tier", "common") or "common") == "interesting":
        actor.msg("You pull something unexpected from the water...")
    actor.msg(str(junk_profile.get("pull_message", "You drag some waterlogged junk up onto the bank.") or "You drag some waterlogged junk up onto the bank."))
    _award_outdoorsmanship(actor, room, success=True, outcome="partial", multiplier=0.85)
    session.last_outcome = str(junk_profile.get("tier", "common") or "common")
    session.outcome_type = "junk"
    _trace(actor, "junk_landed", junk_key=str(getattr(junk.db, "junk_key", junk.key) or junk.key), junk_tier=str(getattr(junk.db, "junk_tier", "common") or "common"))
    reset_fishing_session(actor)
    return junk


def _resolve_event_pull(actor):
    session = get_fishing_session(actor, create=False)
    if session is None or session.state != "event":
        actor.msg("There's nothing on the line anymore.")
        return False

    room = getattr(actor, "location", None)
    event_profile = dict(getattr(session, "active_event_profile", None) or {})
    maybe_spawn_encounter(actor, room, event_profile=event_profile)
    pole = get_fishing_pole(actor)
    if pole is not None:
        pole.db.line_attached = False
        pole.db.line_tangled = False
    actor.msg(str(event_profile.get("resolution_message", "Whatever it was tears free, snapping your line.") or "Whatever it was tears free, snapping your line."))
    _award_outdoorsmanship(actor, room, success=False, outcome="failure", multiplier=0.75)
    _trace(
        actor,
        "event_resolved",
        event_key=str(event_profile.get("key", "violent_tug") or "violent_tug"),
        safe_zone=bool(getattr(getattr(room, "db", None), "safe_zone", False)),
        line_attached=bool(getattr(getattr(pole, "db", None), "line_attached", False)) if pole is not None else False,
    )
    reset_fishing_session(actor)
    return True


def _get_inventory_bait_items(actor):
    return [obj for obj in list(getattr(actor, "contents", []) or []) if is_valid_bait_item(obj)]


def _get_inventory_items_with_flag(actor, flag_name):
    if actor is None:
        return []
    return [obj for obj in list(getattr(actor, "contents", []) or []) if bool(getattr(getattr(obj, "db", None), flag_name, False))]


def has_fishing_pole(actor):
    return bool(_get_inventory_items_with_flag(actor, "is_fishing_pole"))


def has_fishing_hook(actor):
    return bool(_get_inventory_items_with_flag(actor, "is_hook"))


def has_fishing_line(actor):
    return bool(_get_inventory_items_with_flag(actor, "is_line"))


def get_fishing_pole(actor):
    poles = _get_inventory_items_with_flag(actor, "is_fishing_pole")
    return poles[0] if poles else None


def has_ready_hook_and_line(actor, pole=None):
    pole = pole or get_fishing_pole(actor)
    if pole and get_pole_issue(pole) is None and bool(getattr(getattr(pole, "db", None), "hook_attached", False)) and bool(getattr(getattr(pole, "db", None), "line_attached", False)):
        return True
    return has_fishing_hook(actor) and has_fishing_line(actor)


def ensure_minimum_fishing_gear(actor):
    pole = get_fishing_pole(actor)
    if not has_fishing_pole(actor) or pole is None:
        return False, "You need a fishing pole before you can fish."
    pole_issue = get_pole_issue(pole)
    if pole_issue == "tangled":
        return False, "Your pole is tangled. Untangle it before you fish."
    if pole_issue == "unrigged":
        return False, "Your pole is not fully rigged. Rig it before you fish."
    if not has_ready_hook_and_line(actor, pole=pole):
        return False, "You need a hook and line ready before you can fish."
    return True, ""


def rig_fishing_pole(actor):
    pole = get_fishing_pole(actor)
    if pole is None:
        return False, "You need a fishing pole before you can rig anything."
    if bool(getattr(getattr(pole, "db", None), "line_tangled", False)):
        return False, "Untangle the pole before you try to rig it."
    if bool(getattr(getattr(pole, "db", None), "hook_attached", False)) and bool(getattr(getattr(pole, "db", None), "line_attached", False)):
        return False, "Your fishing pole is already rigged."
    if not has_fishing_hook(actor) or not has_fishing_line(actor):
        return False, "You need both a hook and a line to rig the pole."
    skill = _safe_actor_rank(actor, "mechanical_lore") + (_safe_actor_stat(actor, "discipline", 10.0) * 0.5)
    success_chance = clamp(0.40 + (skill * 0.01), 0.40, 0.92)
    if float(random.random()) > success_chance:
        pole.db.line_tangled = True
        SkillService.award_xp(actor, "mechanical_lore", 8, source={"mode": "difficulty"}, success=False, outcome="failure", event_key="fishing_rig", context_multiplier=0.20)
        return False, "You fumble the rigging and snarl the line."
    pole.db.hook_attached = True
    pole.db.line_attached = True
    pole.db.line_tangled = False
    SkillService.award_xp(actor, "mechanical_lore", 10, source={"mode": "difficulty"}, success=True, outcome="success", event_key="fishing_rig", context_multiplier=0.22)
    session = get_fishing_session(actor, create=False)
    if session is not None and session.state == "broken":
        session.state = "baited" if bool(getattr(session, "baited", False)) else "idle"
        session.line_broken = False
        _sync_runtime_flags(actor, session)
    return True, "You rig the pole and set the hook and line in order."


def untangle_fishing_pole(actor):
    pole = get_fishing_pole(actor)
    if pole is None:
        return False, "You need a fishing pole before you can untangle it."
    if not bool(getattr(getattr(pole, "db", None), "line_tangled", False)):
        return False, "Your pole is not tangled."
    skill = _safe_actor_rank(actor, "mechanical_lore") + (_safe_actor_stat(actor, "discipline", 10.0) * 0.4)
    success_chance = clamp(0.45 + (skill * 0.01), 0.45, 0.94)
    if float(random.random()) > success_chance:
        SkillService.award_xp(actor, "mechanical_lore", 8, source={"mode": "difficulty"}, success=False, outcome="failure", event_key="fishing_untangle", context_multiplier=0.20)
        return False, "You work at the knot, but only tighten it."
    pole.db.line_tangled = False
    SkillService.award_xp(actor, "mechanical_lore", 10, source={"mode": "difficulty"}, success=True, outcome="success", event_key="fishing_untangle", context_multiplier=0.22)
    session = get_fishing_session(actor, create=False)
    if session is not None and session.state == "tangled":
        session.state = "baited" if bool(getattr(session, "baited", False)) else "idle"
        session.tangled = False
        _sync_runtime_flags(actor, session)
    return True, "You patiently work the knots free until the line hangs clean again."


def find_bait_item(actor, query=None):
    bait_items = _get_inventory_bait_items(actor)
    if not bait_items:
        if not query:
            return None, [], "", None, False
    if query:
        carried_items = list(getattr(actor, "contents", []) or [])
        item, matches, base_query, index = actor.resolve_numbered_candidate(query, carried_items, default_first=True)
        if item is None:
            return None, matches, base_query, index, False
        if not is_valid_bait_item(item):
            return None, matches, base_query, index, True
        return item, matches, base_query, index, False
    if not bait_items:
        return None, [], "", None, False
    return bait_items[0], bait_items, getattr(bait_items[0], "key", ""), 1, False


def bait_item_still_available(actor, session):
    bait_item_id = int(getattr(session, "bait_item_id", 0) or 0)
    if bait_item_id <= 0:
        return None
    for item in _get_inventory_bait_items(actor):
        if int(getattr(item, "id", 0) or 0) == bait_item_id:
            return item
    return None


def attach_bait(actor, bait_item):
    if not is_valid_bait_item(bait_item):
        return False, "You can't use that as bait.", None
    pole = get_fishing_pole(actor)
    pole_issue = get_pole_issue(pole)
    if pole_issue == "tangled":
        return False, "Untangle your pole before baiting it.", None
    if pole_issue == "unrigged":
        return False, "You need to rig your pole before baiting it.", None
    session = get_fishing_session(actor, create=True)
    bait_profile = resolve_bait_profile(bait_item)
    if bait_profile is None:
        return False, "You can't use that as bait.", None
    fishing_economy.award_bait_usage_xp(actor)
    session.baited = True
    session.bait_item_id = int(getattr(bait_item, "id", 0) or 0)
    session.bait_family = bait_profile["family"]
    session.bait_quality = float(bait_profile["quality"])
    session.bait_match_tags = list(bait_profile["match_tags"])
    session.state = "baited"
    session.hooked_fish = None
    session.active_fish_profile = None
    session.nibble_time = None
    session.last_pull_time = None
    session.pending_pull = False
    session.struggle_round = 0
    session.line_broken = False
    session.tangled = False
    session.last_outcome = "baited"
    session.outcome_type = None
    session.active_junk_profile = None
    session.active_event_profile = None
    _clear_session_callbacks(session)
    ratings = resolve_gear_ratings(actor, session=None)
    session.rod_rating = float(ratings["rod_rating"])
    session.hook_rating = float(ratings["hook_rating"])
    session.line_rating = float(ratings["line_rating"])
    _sync_runtime_flags(actor, session)
    _trace(actor, "bait_attached", bait_family=session.bait_family, bait_quality=session.bait_quality, bait_tags=list(session.bait_match_tags))
    return True, f"You bait your hook with {bait_item.key}.", session


def _mark_tangled(actor, session, message):
    pole = get_fishing_pole(actor)
    if pole is not None:
        pole.db.line_tangled = True
    _clear_session_callbacks(session)
    session.state = "tangled"
    session.tangled = True
    session.pending_pull = False
    session.last_outcome = "tangled"
    _sync_runtime_flags(actor, session)
    actor.msg(message)
    _trace(actor, "session_tangled", message=message)


def _mark_line_broken(actor, session, message):
    pole = get_fishing_pole(actor)
    if pole is not None:
        pole.db.line_attached = False
        pole.db.line_tangled = False
    _clear_session_callbacks(session)
    session.state = "broken"
    session.line_broken = True
    session.pending_pull = False
    session.last_outcome = "line_break"
    _sync_runtime_flags(actor, session)
    actor.msg(message)
    _trace(actor, "line_break", message=message)


def ensure_can_cast(actor):
    room = getattr(actor, "location", None)
    session = get_fishing_session(actor, create=False)

    if room is None or not is_fishable(room):
        return False, "You can't fish here.", None, room
    if session and session.state in {"cast", "nibble", "hooked"}:
        return False, "You are already fishing.", session, room
    if session and session.state == "tangled":
        return False, "Your line is tangled. Re-bait before casting again.", session, room
    if session and session.state == "broken":
        return False, "Your line is broken. You need to rig your pole before fishing again.", session, room
    gear_ready, gear_message = ensure_minimum_fishing_gear(actor)
    if not gear_ready:
        return False, gear_message, session, room
    if not _get_inventory_bait_items(actor):
        return False, "You need bait before you can fish.", session, room
    if session is None or not session.baited:
        return False, "You need to bait your hook first.", session, room
    bait_item = bait_item_still_available(actor, session)
    if bait_item is None:
        session.baited = False
        session.bait_item_id = None
        session.state = "idle"
        _sync_runtime_flags(actor, session)
        return False, "Your bait is no longer ready. Bait your hook again.", session, room
    return True, "", session, room


def start_fishing_cast(actor):
    ok, message, session, room = ensure_can_cast(actor)
    if not ok:
        actor.msg(message)
        return False

    session.state = "cast"
    session.attempt_token = str(uuid.uuid4())
    session.room_id = int(getattr(room, "id", 0) or 0)
    session.nibble_time = None
    session.last_pull_time = None
    session.pending_pull = False
    session.hooked_fish = None
    session.active_fish_profile = None
    session.active_junk_profile = None
    session.active_event_profile = None
    session.outcome_type = None
    session.struggle_round = 0
    ratings = resolve_gear_ratings(actor, session=None)
    session.rod_rating = float(ratings["rod_rating"])
    session.hook_rating = float(ratings["hook_rating"])
    session.line_rating = float(ratings["line_rating"])
    _sync_runtime_flags(actor, session)

    actor.msg("You cast your line into the water.")
    actor.msg("You wait for a bite...")
    _apply_empath_strain(actor, "cast", amount=2, fish_profile=None)
    room.msg_contents(f"{actor.key} casts a line into the water.", exclude=[actor])
    _trace(actor, "cast_started", bait_family=session.bait_family, rod_rating=session.rod_rating, hook_rating=session.hook_rating, line_rating=session.line_rating)
    bite_delay = calculate_bite_delay(room)
    session.bite_delay = float(bite_delay)
    session.nibble_window_delay = None
    _schedule_session_callback(actor, session, "bite", bite_delay, _begin_nibble, session.attempt_token)
    return True


def _begin_nibble(actor, token):
    session = _get_expected_session(actor, expected_state="cast", token=token)
    if session is None:
        return
    _clear_session_callbacks(session, "bite")

    room = getattr(actor, "location", None)
    if room is None or int(getattr(room, "id", 0) or 0) != int(session.room_id or 0) or not is_fishable(room):
        cancel_fishing_session(actor)
        return

    outcome = roll_fishing_outcome(room)
    outcome_category = str((outcome or {}).get("category", "fish") or "fish")
    outcome_profile = dict((outcome or {}).get("profile", {}) or {})
    session.outcome_type = outcome_category
    session.pending_pull = False
    session.nibble_time = float(time.time())

    if outcome_category == "fish":
        session.state = "nibble"
        session.active_fish_profile = str(outcome_profile.get("key", "") or "")
        session.active_junk_profile = None
        session.active_event_profile = None
        _sync_runtime_flags(actor, session)
        actor.msg("You feel a slight tug on the line...")
        _trace(actor, "nibble_check", fish_profile=session.active_fish_profile, bait_family=session.bait_family, outcome="fish")
        nibble_window_delay = calculate_nibble_window_delay()
        session.nibble_window_delay = float(nibble_window_delay)
        _schedule_session_callback(actor, session, "nibble_timeout", nibble_window_delay, _expire_nibble_window, token, session.nibble_time)
        return

    if outcome_category == "junk":
        session.state = "junk"
        session.active_fish_profile = None
        session.active_junk_profile = dict(outcome_profile)
        session.active_event_profile = None
        _sync_runtime_flags(actor, session)
        actor.msg("There is a sodden drag on the line, like something dead and heavy below the surface.")
        _trace(actor, "cast_outcome", outcome="junk", junk_key=str(outcome_profile.get("key", "") or ""), junk_tier=str(outcome_profile.get("tier", "common") or "common"))
        return

    session.state = "event"
    session.active_fish_profile = None
    session.active_junk_profile = None
    session.active_event_profile = dict(outcome_profile)
    _sync_runtime_flags(actor, session)
    actor.msg(str(outcome_profile.get("hook_message", "Your line jerks violently -- this is no fish.") or "Your line jerks violently -- this is no fish."))
    _trace(actor, "cast_outcome", outcome="event", event_key=str(outcome_profile.get("key", "violent_tug") or "violent_tug"))


def _resolve_hook_attempt(actor):
    session = get_fishing_session(actor, create=False)
    if session is None or session.state != "nibble":
        actor.msg("There's nothing on the line anymore.")
        return False

    bait_item = bait_item_still_available(actor, session)
    room = getattr(actor, "location", None)
    fish_profile = get_fish_profile(session.active_fish_profile) or choose_weighted_fish_profile(room)
    hook_roll = float(random.random())
    hookup_chance = calculate_hookup_chance(actor, session, bait_item, fish_profile) if bait_item is not None else 0.0
    _trace(actor, "hook_check", fish_profile=str(fish_profile.get("key", "") or ""), bait_family=session.bait_family, hookup_chance=hookup_chance, hook_roll=hook_roll)
    if bait_item is not None and hook_roll < hookup_chance:
        session.state = "hooked"
        session.hooked_fish = str(fish_profile.get("key", "") or fish_profile.get("name", "fish"))
        session.nibble_time = None
        session.last_pull_time = None
        session.pending_pull = False
        session.struggle_round = 0
        session.last_outcome = "hooked"
        _clear_session_callbacks(session, "nibble_timeout")
        _sync_runtime_flags(actor, session)
        actor.msg("The line jerks violently!")
        _apply_empath_strain(actor, "hook", amount=max(2, int(float(fish_profile.get("difficulty", 20) or 20) * 0.08)), fish_profile=fish_profile)
        _award_outdoorsmanship(actor, room, success=True, outcome="partial", multiplier=0.95)
        _schedule_session_callback(actor, session, "struggle", 2.0, _resolve_struggle_round, session.attempt_token)
        return True

    actor.msg(random.choice(SLIP_HOOK_MESSAGES))
    _award_outdoorsmanship(actor, room, success=False, outcome="failure", multiplier=0.8)
    _trace(actor, "hook_result", outcome="lost_fish")
    reset_fishing_session(actor)
    return False


def _expire_nibble_window(actor, token, nibble_time):
    session = _get_expected_session(actor, expected_state="nibble", token=token)
    if session is None:
        return
    _clear_session_callbacks(session, "nibble_timeout")
    if float(session.nibble_time or 0.0) != float(nibble_time or 0.0):
        return

    room = getattr(actor, "location", None)
    fish_profile = get_fish_profile(session.active_fish_profile) or choose_weighted_fish_profile(room)
    actor.msg("The line goes still...")
    tangle_chance = calculate_timeout_tangle_chance(actor, fish_profile)
    tangle_roll = float(random.random())
    _trace(actor, "nibble_timeout", fish_profile=str(fish_profile.get("key", "") or ""), tangle_chance=tangle_chance, tangle_roll=tangle_roll)
    if tangle_roll < tangle_chance:
        _award_outdoorsmanship(actor, room, success=False, outcome="failure", multiplier=0.65)
        _mark_tangled(actor, session, random.choice(TANGLE_MESSAGES))
        return

    actor.msg("Whatever was there is gone.")
    _award_outdoorsmanship(actor, room, success=False, outcome="failure", multiplier=0.7)
    reset_fishing_session(actor)


def register_hooked_pull(actor):
    session = get_fishing_session(actor, create=False)
    if session is None or session.state != "hooked":
        actor.msg("There's nothing on the line anymore.")
        return False
    session.last_pull_time = float(time.time())
    session.pending_pull = True
    actor.msg("You haul back and keep tension on the line.")
    return True


def _spawn_fish(actor, fish_profile):
    fish_profile = dict(fish_profile or {})
    weight_min = int(fish_profile.get("weight_min", 1) or 1)
    weight_max = int(fish_profile.get("weight_max", max(weight_min, 1)) or max(weight_min, 1))
    weight = random.randint(min(weight_min, weight_max), max(weight_min, weight_max))
    value = calculate_fish_value(fish_profile, weight)
    fish = create_object("typeclasses.items.fish.Fish", key=str(fish_profile.get("name", "fish") or "fish"), location=actor, home=actor)
    fish.db.species = str(fish_profile.get("name", "fish") or "fish")
    fish.db.fish_profile_key = str(fish_profile.get("key", "") or "")
    fish.db.fish_group = str(fish_profile.get("fish_group", "") or "")
    fish.db.fish_difficulty = int(fish_profile.get("difficulty", 0) or 0)
    fish.db.weight = int(weight)
    fish.db.value = int(value)
    fish.db.fight_profile = str(fish_profile.get("fight_profile", "steady") or "steady")
    fishing_economy.set_fish_economy_metadata(fish, fish_profile)
    fishing_economy.update_heaviest_fish_record(actor, fish)
    placed, fish_string, _message = fishing_economy.place_fish_on_string(actor, fish)
    if placed:
        return fish, fish_string
    if fishing_economy.can_receive_caught_fish(actor, fish):
        return fish, None

    fish.delete()
    return None, None
    return fish


def _resolve_struggle_round(actor, token):
    session = _get_expected_session(actor, expected_state="hooked", token=token)
    if session is None:
        return
    _clear_session_callbacks(session, "struggle")

    room = getattr(actor, "location", None)
    session.struggle_round += 1
    bait_item = bait_item_still_available(actor, session)
    fish_profile = get_fish_profile(session.hooked_fish or session.active_fish_profile) or choose_weighted_fish_profile(room)
    outcome_data = resolve_struggle_outcome_data(actor, session, fish_profile, bait_item)
    outcome = str(outcome_data.get("outcome", "still_fighting") or "still_fighting")
    _trace(actor, "struggle_round", fish_profile=str(fish_profile.get("key", "") or ""), round=int(session.struggle_round or 0), bait_family=session.bait_family, outcome=outcome, pressure=float(outcome_data.get("pressure", 0.0) or 0.0), landed_score=float(outcome_data.get("landed_score", 0.0) or 0.0), lost_score=float(outcome_data.get("lost_score", 0.0) or 0.0), break_score=float(outcome_data.get("break_score", 0.0) or 0.0))
    session.pending_pull = False

    if outcome == "landed":
        fish, fish_string = _spawn_fish(actor, fish_profile)
        if fish is None:
            actor.msg("You land the fish, but you have nowhere to secure it and it slips away.")
            _award_outdoorsmanship(actor, room, success=False, outcome="failure", multiplier=0.9)
            reset_fishing_session(actor)
            return
        actor.msg(fishing_economy.get_fish_catch_message(fish))
        trophy_message = fishing_economy.get_trophy_message(fish)
        if trophy_message:
            actor.msg(trophy_message)
        if fish_string is not None:
            actor.msg(f"You secure {fish.key} to your fish string.")
        _apply_empath_strain(actor, "landed", amount=max(3, int(float(fish_profile.get("difficulty", 20) or 20) * 0.10)), fish_profile=fish_profile)
        _award_outdoorsmanship(actor, room, success=True, outcome="success", multiplier=1.1)
        reset_fishing_session(actor)
        return

    if outcome == "line_break":
        _award_outdoorsmanship(actor, room, success=False, outcome="failure", multiplier=0.75)
        _mark_line_broken(actor, session, random.choice(LINE_BREAK_MESSAGES))
        return

    if outcome == "lost_fish":
        actor.msg(random.choice(SLIP_HOOK_MESSAGES))
        _award_outdoorsmanship(actor, room, success=False, outcome="failure", multiplier=0.85)
        reset_fishing_session(actor)
        return

    actor.msg("The fish keeps fighting against the line.")
    _apply_empath_strain(actor, "struggle", amount=max(1, int(float(fish_profile.get("difficulty", 20) or 20) * 0.05)), fish_profile=fish_profile)
    _schedule_session_callback(actor, session, "struggle", 2.0, _resolve_struggle_round, token)


def resolve_pull(actor):
    session = get_fishing_session(actor, create=False)
    if session is None:
        actor.msg("There's nothing on the line anymore.")
        return False
    if session.state == "nibble":
        return _resolve_hook_attempt(actor)
    if session.state == "junk":
        return _resolve_junk_pull(actor)
    if session.state == "event":
        return _resolve_event_pull(actor)
    if session.state == "hooked":
        return register_hooked_pull(actor)
    if session.state == "tangled":
        actor.msg("Your line is tangled. Re-bait before you cast again.")
        return False
    if session.state == "broken":
        actor.msg("Your line is broken. You need to rig your pole before fishing again.")
        return False
    if session.state == "cast":
        actor.msg("You yank too early and spoil the tension.")
        tangle_chance = calculate_invalid_pull_tangle_chance(actor, session)
        _trace(actor, "invalid_pull", state=session.state, tangle_chance=tangle_chance)
        if float(random.random()) < tangle_chance:
            _mark_tangled(actor, session, random.choice(TANGLE_MESSAGES))
        return False
    actor.msg("There's nothing on the line anymore.")
    return False