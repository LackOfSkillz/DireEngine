import random

from evennia.utils.create import create_object

from typeclasses.abilities import Ability, register_ability
from typeclasses.objects import Object
from utils.contests import run_contest
from utils.forage_catalog import iter_forage_catalog_entries
from utils.survival_messaging import msg_actor, msg_room
from world.builder.prompting.room_description_prompt import _THRESHOLD_STRUCTURES, determine_applicable_state_groups
from world.builder.schemas.room_tag_schema import normalize_room_tags
from world.calendar import get_current_season, get_current_time_of_day
from world.invasion import get_current_invasion
from world.weather import get_current_weather


LEGACY_RESOURCE_PROFILES = (
    {
        "key": "grass tuft",
        "desc": "A tuft of hardy field grass gathered from the surrounding area.",
        "value": 1,
        "weight": 0.2,
        "kind": "grass",
    },
    {
        "key": "stick bundle",
        "desc": "A tidy bundle of dry sticks suitable for kindling, trade, or camp work.",
        "value": 2,
        "weight": 0.5,
        "kind": "stick",
    },
    {
        "key": "wild herb",
        "desc": "A fragrant wild herb with enough quality to interest a careful buyer.",
        "value": 5,
        "weight": 0.1,
        "kind": "wild herb",
    },
)
QUALITY_ORDER = ("rough", "useful", "high-quality")
QUALITY_VALUE_MULTIPLIERS = {
    "rough": 1,
    "useful": 2,
    "high-quality": 3,
}
FORAGE_FAILURE_XP_MULTIPLIER = 0.25
PRIMARY_TERRAIN_WEIGHT = 0.7
SECONDARY_TERRAIN_WEIGHT = 0.3
RANGER_SKILL_BONUS = 20
RANGER_QUANTITY_BONUS = 1
RANGER_QUALITY_BONUS = 1
INVASION_YIELD_MODIFIER = 0.6
WEATHER_YIELD_MODIFIERS = {
    "clear": 1.0,
    "cloudy": 1.0,
    "light_rain": 1.0,
    "heavy_rain": 0.75,
    "storm": 0.25,
    "fog": 0.85,
    "light_snow": 0.7,
    "heavy_snow": 0.55,
    "blizzard": 0.25,
    "sandstorm": 0.25,
}
WEATHER_WEIGHT_MODIFIERS = {
    "clear": 1.0,
    "cloudy": 1.0,
    "light_rain": 1.0,
    "heavy_rain": 0.75,
    "storm": 0.2,
    "fog": 0.85,
    "light_snow": 0.8,
    "heavy_snow": 0.6,
    "blizzard": 0.2,
    "sandstorm": 0.2,
}
RAIN_AFFINITY_CATEGORIES = {"mushroom", "flora", "healing_herb"}
SNOW_AFFINITY_TERRAINS = {"ice_cap", "highland_mountain", "boreal_forest", "subterranean"}
TERRAIN_ALIASES = {
    "forest": {"forest", "deciduous_forest", "boreal_forest", "rainforest", "outdoor"},
    "plains": {"plains", "steppe", "savannah", "rural_cultivated", "urban_cultivated", "outdoor"},
    "swamp": {"swamp", "freshwater_wetland", "outdoor"},
    "mountain": {"mountain", "highland_mountain", "badland", "outdoor"},
    "urban": {"urban", "urban_cultivated", "outdoor"},
    "coastal": {"coastal", "marine", "outdoor"},
    "underground": {"underground", "subterranean", "photophobic"},
}


def _normalize_text(value):
    return str(value or "").strip().lower()


def _normalize_list(value):
    return [_normalize_text(item) for item in list(value or []) if _normalize_text(item)]


def _is_ranger(user):
    return bool(hasattr(user, "is_profession") and user.is_profession("ranger"))


def _get_user_stat(user, stat_name):
    stats = getattr(getattr(user, "db", None), "stats", None)
    if isinstance(stats, dict):
        normalized = _normalize_text(stat_name).replace("-", "_")
        return int(stats.get(normalized, 0) or 0)
    return int(user.get_stat(stat_name) or 0)


def _get_room_zone_id(room):
    return str(getattr(getattr(room, "db", None), "zone_id", "") or "").strip()


def _get_room_environment(room):
    if room and hasattr(room, "get_environment_type"):
        return _normalize_text(room.get_environment_type() or "urban") or "urban"
    return _normalize_text(getattr(getattr(room, "db", None), "environment_type", "urban") or "urban") or "urban"


def _is_room_indoor(room):
    if not room:
        return False
    room_payload = {
        "environment": _get_room_environment(room),
        "tags": getattr(getattr(room, "db", None), "room_tags", None),
    }
    zone_payload = {"generation_context": {"setting_type": _get_room_environment(room)}}
    tags = normalize_room_tags(room_payload.get("tags"))
    structure = _normalize_text((tags.get("structure") or ""))
    groups = determine_applicable_state_groups(room_payload, zone_payload)
    return not ("weather" in groups or structure in _THRESHOLD_STRUCTURES)


def _resolve_room_terrains(room):
    if not room:
        return None, None
    room_db = getattr(room, "db", None)
    primary = _normalize_text(getattr(room_db, "terrain_primary", None))
    secondary = _normalize_text(getattr(room_db, "terrain_secondary", None))
    if not primary and hasattr(room, "get_terrain_type"):
        primary = _normalize_text(room.get_terrain_type())
    if not primary:
        primary = _normalize_text(getattr(room_db, "terrain_type", None))
    if secondary == primary:
        secondary = ""
    return primary or None, secondary or None


def _terrain_aliases(terrain):
    normalized = _normalize_text(terrain)
    if not normalized:
        return set()
    aliases = set(TERRAIN_ALIASES.get(normalized, set()))
    aliases.add(normalized)
    return aliases


def _entry_matches_terrain(entry, aliases):
    terrain_values = set(_normalize_list(entry.get("terrain") or []))
    return bool(terrain_values & aliases)


def _season_matches(entry, season):
    seasons = _normalize_list(entry.get("seasonal") or ["all"])
    return not seasons or "all" in seasons or season in seasons


def _time_of_day_matches(entry, time_of_day):
    values = _normalize_list(entry.get("time_of_day") or ["all"])
    if not values or "all" in values:
        return True
    if "day" in values and time_of_day in {"morning", "afternoon", "evening"}:
        return True
    if "night" in values and time_of_day == "night":
        return True
    return time_of_day in values


def _filter_catalog_entries(room, *, season, time_of_day, effective_rank):
    primary_terrain, secondary_terrain = _resolve_room_terrains(room)
    if not primary_terrain:
        return {"mode": "legacy", "entries": [], "pre_skill_entries": []}

    primary_aliases = _terrain_aliases(primary_terrain)
    secondary_aliases = _terrain_aliases(secondary_terrain)
    weighted_entries = []
    for entry in iter_forage_catalog_entries():
        weight = 0.0
        if _entry_matches_terrain(entry, primary_aliases):
            weight += PRIMARY_TERRAIN_WEIGHT if secondary_aliases else 1.0
        if secondary_aliases and _entry_matches_terrain(entry, secondary_aliases):
            weight += SECONDARY_TERRAIN_WEIGHT
        if weight <= 0.0:
            continue
        weighted_entries.append({"entry": entry, "terrain_weight": weight})

    if not weighted_entries:
        return {"mode": "legacy", "entries": [], "pre_skill_entries": []}

    indoor = _is_room_indoor(room)
    terrain_entries = []
    for weighted in weighted_entries:
        entry = weighted["entry"]
        if indoor and not bool(entry.get("indoor")):
            continue
        if not _season_matches(entry, season):
            continue
        if not _time_of_day_matches(entry, time_of_day):
            continue
        terrain_entries.append(weighted)

    if not terrain_entries:
        return {"mode": "legacy", "entries": [], "pre_skill_entries": []}

    filtered_entries = [
        weighted for weighted in terrain_entries if int(weighted["entry"].get("skill_ranks") or 0) <= int(effective_rank or 0)
    ]
    return {"mode": "catalog", "entries": filtered_entries, "pre_skill_entries": terrain_entries}


def _apply_weather_weights(weighted_entries, weather_state):
    adjusted = []
    weather_multiplier = float(WEATHER_WEIGHT_MODIFIERS.get(weather_state, 1.0))
    for weighted in weighted_entries:
        entry = weighted["entry"]
        multiplier = weather_multiplier
        category = _normalize_text(entry.get("category"))
        terrain_values = set(_normalize_list(entry.get("terrain") or []))
        if weather_state == "light_rain" and category in RAIN_AFFINITY_CATEGORIES:
            multiplier *= 1.25
        elif weather_state == "heavy_rain" and category in RAIN_AFFINITY_CATEGORIES:
            multiplier *= 1.5
        elif weather_state in {"light_snow", "heavy_snow", "blizzard"} and terrain_values & SNOW_AFFINITY_TERRAINS:
            multiplier *= 1.15
        adjusted.append({**weighted, "weight": max(0.01, float(weighted["terrain_weight"]) * multiplier)})
    return adjusted


def _select_catalog_entry(weighted_entries, rng=None):
    if not weighted_entries:
        return None
    random_source = rng or random
    weights = [float(weighted.get("weight", weighted.get("terrain_weight", 1.0)) or 1.0) for weighted in weighted_entries]
    return random_source.choices(weighted_entries, weights=weights, k=1)[0]["entry"]


def _quality_label(index):
    return QUALITY_ORDER[max(0, min(len(QUALITY_ORDER) - 1, int(index or 0)))]


def _create_foraged_item(user, key, desc, **attributes):
    item = create_object(Object, key=key, nohome=True)
    item.db.desc = desc
    for attr_name, attr_value in attributes.items():
        setattr(item.db, attr_name, attr_value)
    if getattr(item.db, "item_value", None) is None:
        item.db.item_value = int(getattr(item.db, "value", 1) or 1)
    if getattr(item.db, "value", None) is None:
        item.db.value = int(getattr(item.db, "item_value", 1) or 1)
    if getattr(item.db, "weight", None) is None:
        item.db.weight = 1.0
    item.move_to(user, quiet=True, use_destination=False)
    return item


def _build_created_item(user, entry, quality, item_value):
    slug = _normalize_text(entry.get("slug"))
    display_name = str(entry.get("display_name") or slug or "foraged item").strip()
    item_key = f"{quality} {display_name}"
    attributes = {
        "foraged": True,
        "material_quality": quality,
        "forage_kind": slug,
        "catalog_group": _normalize_text(entry.get("group")),
        "catalog_category": _normalize_text(entry.get("category")),
        "item_value": item_value,
        "value": item_value,
        "weight": 0.2,
    }
    if slug in {"grass", "stick"}:
        attributes["ranger_resource_kind"] = slug
        attributes["item_type"] = "raw_resource"
    else:
        attributes["item_type"] = "foraged_material"
    return _create_foraged_item(
        user,
        key=item_key,
        desc=f"A {quality} {display_name} gathered from the surrounding area.",
        **attributes,
    )


def _award_forage_skill(user, difficulty, *, learning_multiplier=1.0):
    user.use_skill(
        "outdoorsmanship",
        apply_roundtime=False,
        emit_placeholder=False,
        require_known=False,
        difficulty=max(1, int(difficulty or 1)),
        learning_multiplier=max(0.0, float(learning_multiplier or 0.0)),
    )


def _award_forage_failure_xp(user, difficulty):
    from engine.services.skill_service import SkillService

    SkillService.award_xp(
        user,
        "outdoorsmanship",
        max(1, int(difficulty or 1)),
        source={"mode": "difficulty"},
        success=False,
        outcome="failure",
        event_key="forage",
        context_multiplier=FORAGE_FAILURE_XP_MULTIPLIER,
    )


def _execute_legacy_forage(user, room, *, rng=None, create_items=True):
    random_source = rng or random
    outdoorsmanship = int(user.get_skill("outdoorsmanship") or 0)
    skill_total = outdoorsmanship + int(user.get_stat("wisdom") or 0) + int(user.get_stat("intelligence") or 0)
    difficulty = int(getattr(getattr(room, "db", None), "forage_difficulty", 35) or 35)
    result = run_contest(skill_total, difficulty, attacker=user)
    outcome = result["outcome"]
    if outcome == "fail":
        return {
            "status": "failure",
            "failure_reason": "generic_no_result",
            "used_legacy": True,
            "message": "You find nothing of value here.",
            "created_items": [],
            "difficulty": difficulty,
        }

    if outcome == "partial":
        quality = "rough"
        yield_amount = 1
        message = "You find a few scraps of usable material."
    elif outcome == "success":
        quality = "useful"
        yield_amount = 2
        message = "You gather some useful natural materials."
    else:
        quality = "high-quality"
        yield_amount = 3
        message = "You expertly gather high-quality natural materials."

    if _is_ranger(user):
        yield_amount += 1
    yield_amount += outdoorsmanship // 10
    created_items = []
    for _index in range(max(1, int(yield_amount or 1))):
        roll = random_source.random()
        if roll < 0.7:
            profile = LEGACY_RESOURCE_PROFILES[0]
        elif roll < 0.95:
            profile = LEGACY_RESOURCE_PROFILES[1]
        else:
            profile = LEGACY_RESOURCE_PROFILES[2]
        item_key = f"{quality} {profile['key']}"
        item_value = int(profile["value"] * QUALITY_VALUE_MULTIPLIERS.get(quality, 1))
        if create_items:
            _create_foraged_item(
                user,
                key=item_key,
                desc=f"A {quality} {profile['desc'].lower()}",
                foraged=True,
                material_quality=quality,
                forage_kind=profile["kind"],
                item_value=item_value,
                value=item_value,
                weight=profile["weight"],
                ranger_resource_kind=profile["kind"] if profile["kind"] in {"grass", "stick"} else None,
                item_type="raw_resource" if profile["kind"] in {"grass", "stick"} else "foraged_material",
            )
        created_items.append(item_key)

    _award_forage_skill(user, difficulty)
    return {
        "status": "success",
        "used_legacy": True,
        "message": message,
        "created_items": created_items,
        "difficulty": difficulty,
        "quality": quality,
        "yield_amount": int(yield_amount),
    }


def forage_attempt(user, room=None, *, rng=None, create_items=True):
    room = room or getattr(user, "location", None)
    if room is None:
        return {
            "status": "failure",
            "failure_reason": "generic_no_result",
            "used_legacy": False,
            "message": "You find nothing of value here.",
            "created_items": [],
            "difficulty": 1,
        }

    base_rank = int(user.get_skill("outdoorsmanship") or 0)
    ranger = _is_ranger(user)
    effective_rank = base_rank + (RANGER_SKILL_BONUS if ranger else 0)
    season = _normalize_text(get_current_season())
    time_of_day = _normalize_text(get_current_time_of_day())
    zone_id = _get_room_zone_id(room)
    weather_state = _normalize_text(get_current_weather(zone_id)) if zone_id else "clear"
    invasion_state = _normalize_text(get_current_invasion(zone_id)) if zone_id else "none"
    filtered = _filter_catalog_entries(room, season=season, time_of_day=time_of_day, effective_rank=effective_rank)
    if filtered["mode"] == "legacy":
        return _execute_legacy_forage(user, room, rng=rng, create_items=create_items)
    if filtered["pre_skill_entries"] and not filtered["entries"]:
        threshold = min(int(weighted["entry"].get("skill_ranks") or 1) for weighted in filtered["pre_skill_entries"])
        _award_forage_failure_xp(user, threshold)
        return {
            "status": "skill_failure",
            "failure_reason": "skill_too_low",
            "used_legacy": False,
            "message": "You search the area but nothing within your skill catches your eye.",
            "created_items": [],
            "difficulty": threshold,
        }

    weighted_entries = _apply_weather_weights(filtered["entries"], weather_state)
    selected_entry = _select_catalog_entry(weighted_entries, rng=rng)
    if not selected_entry:
        return {
            "status": "failure",
            "failure_reason": "generic_no_result",
            "used_legacy": False,
            "message": "You find nothing of value here.",
            "created_items": [],
            "difficulty": 1,
        }

    wisdom = _get_user_stat(user, "wisdom")
    intelligence = _get_user_stat(user, "intelligence")
    skill_total = effective_rank + wisdom + intelligence
    threshold = int(selected_entry.get("skill_ranks") or 0)
    result = run_contest(skill_total, threshold, attacker=user)
    outcome = result["outcome"]
    severe_weather = weather_state in {"heavy_rain", "storm", "heavy_snow", "blizzard", "sandstorm", "fog", "light_snow"}
    if outcome == "fail":
        if severe_weather and skill_total >= (threshold + 30):
            outcome = "partial"
        else:
            if severe_weather:
                return {
                    "status": "weather_failure",
                    "failure_reason": "weather_blocked",
                    "used_legacy": False,
                    "message": f"The {weather_state.replace('_', ' ')} makes foraging nearly impossible.",
                    "created_items": [],
                    "difficulty": threshold,
                    "selected_entry": selected_entry,
                    "weather_state": weather_state,
                }
            return {
                "status": "failure",
                "failure_reason": "generic_no_result",
                "used_legacy": False,
                "message": "You find nothing of value here.",
                "created_items": [],
                "difficulty": threshold,
                "selected_entry": selected_entry,
            }

    if outcome == "partial":
        quality_index = 0
        yield_amount = 1
        message = "You find a few scraps of usable material."
    elif outcome == "success":
        quality_index = 1
        yield_amount = 2
        message = "You gather some useful natural materials."
    else:
        quality_index = 2
        yield_amount = 3
        message = "You expertly gather high-quality natural materials."

    if ranger:
        quality_index = min(len(QUALITY_ORDER) - 1, quality_index + RANGER_QUALITY_BONUS)
        yield_amount += RANGER_QUANTITY_BONUS
    skill_margin = max(0, effective_rank - threshold)
    yield_amount += skill_margin // 40

    weather_yield_modifier = float(WEATHER_YIELD_MODIFIERS.get(weather_state, 1.0))
    invasion_modifier = INVASION_YIELD_MODIFIER if invasion_state != "none" else 1.0
    adjusted_yield = max(1, int(yield_amount * weather_yield_modifier * invasion_modifier))

    quality = _quality_label(quality_index)
    item_value = max(1, int((1 + (threshold // 10)) * QUALITY_VALUE_MULTIPLIERS.get(quality, 1)))
    created_items = []
    for _index in range(adjusted_yield):
        if create_items:
            _build_created_item(user, selected_entry, quality, item_value)
        created_items.append(f"{quality} {str(selected_entry.get('display_name') or selected_entry.get('slug') or 'foraged item').strip()}")

    _award_forage_skill(user, threshold)
    return {
        "status": "success",
        "used_legacy": False,
        "message": message,
        "created_items": created_items,
        "difficulty": threshold,
        "selected_entry": selected_entry,
        "quality": quality,
        "yield_amount": adjusted_yield,
        "weather_state": weather_state,
        "invasion_state": invasion_state,
    }


class ForageAbility(Ability):
    key = "forage"
    roundtime = 3.0
    category = "survival"
    required = {}
    visible_if = {}

    def execute(self, user, target=None):
        msg_room(user, f"{user.key} searches the area carefully.", exclude=[user])
        result = forage_attempt(user, getattr(user, "location", None), rng=random, create_items=True)
        msg_actor(user, str(result.get("message") or "You find nothing of value here."))
        if result.get("status") != "success":
            return

        user.db.forage_uses = int(getattr(user.db, "forage_uses", 0) or 0) + 1
        created_items = list(result.get("created_items") or [])
        if created_items:
            summary = ", ".join(created_items[:3])
            if len(created_items) > 3:
                summary = f"{summary}, and {len(created_items) - 3} more"
            msg_actor(user, f"You recover {summary}.")


register_ability(ForageAbility())