from collections.abc import Mapping

from django.conf import settings

from evennia.utils.create import create_object
from evennia.objects.models import ObjectDB

from systems.appearance.normalizer import normalize_identity_data
from systems.chargen.state import CharacterBlueprint
from systems.chargen.validators import is_name_available, validate_identity, validate_name
from world.professions.professions import DEFAULT_PROFESSION, PROFESSION_PROFILES, resolve_profession_name
from world.races import DEFAULT_RACE, RACE_DEFINITIONS, RACE_STATS, apply_race, resolve_race_name


BLUEPRINT_FIELDS = (
    "name",
    "race",
    "gender",
    "profession",
    "stats",
    "description",
)

OPTIONAL_BLUEPRINT_FIELDS = (
    "appearance",
    "identity",
)

PROFESSION_STARTER_SKILLS = {
    "barbarian": {"blunt": 2, "combat": 2, "evasion": 1},
    "bard": {"light_edge": 1, "scholarship": 2, "appraisal": 1},
    "cleric": {"theurgy": 2, "warding": 1, "blunt": 1},
    "commoner": {"appraisal": 1, "athletics": 1},
    "empath": {"empathy": 2, "first_aid": 2, "scholarship": 1},
    "moon_mage": {"arcana": 2, "targeted_magic": 1, "utility": 1},
    "necromancer": {"arcana": 2, "targeted_magic": 1, "debilitation": 1},
    "paladin": {"light_edge": 1, "light_armor": 1, "warding": 1},
    "ranger": {"polearm": 2, "outdoorsmanship": 2, "perception": 1},
    "thief": {"light_edge": 1, "stealth": 2, "locksmithing": 2},
    "trader": {"trading": 2, "appraisal": 2, "scholarship": 1},
    "warrior": {"light_edge": 2, "combat": 2, "tactics": 1},
    "warrior_mage": {"arcana": 2, "targeted_magic": 1, "light_edge": 1},
}

PROFESSION_STARTER_WEAPONS = {
    "barbarian": "mace",
    "bard": "sword",
    "cleric": "mace",
    "commoner": "sword",
    "empath": "sword",
    "moon_mage": "sword",
    "necromancer": "sword",
    "paladin": "sword",
    "ranger": "spear",
    "thief": "dagger",
    "trader": "sword",
    "warrior": "sword",
    "warrior_mage": "sword",
}

RACE_STARTER_KIT = {
    "human": {"container": "canvas satchel", "clothing": "plain tunic", "accessory": "bronze ring"},
    "elf": {"container": "soft travel satchel", "clothing": "fitted tunic", "accessory": "silver leaf pin"},
    "dwarf": {"container": "stout field pack", "clothing": "wool tunic", "accessory": "copper torque"},
    "halfling": {"container": "belt pouch", "clothing": "short vest", "accessory": "bright scarf pin"},
    "gnome": {"container": "tool satchel", "clothing": "neat jacket", "accessory": "brass charm"},
    "volgrin": {"container": "broad travel pack", "clothing": "heavy vest", "accessory": "carved wristband"},
    "saurathi": {"container": "scaled satchel", "clothing": "desert wrap", "accessory": "shell bracelet"},
    "valran": {"container": "fur-lined pack", "clothing": "sturdy tunic", "accessory": "iron armlet"},
    "aethari": {"container": "ink-stained satchel", "clothing": "layered robe", "accessory": "etched focus ring"},
    "felari": {"container": "supple shoulder satchel", "clothing": "tailored vest", "accessory": "polished claw charm"},
    "lunari": {"container": "weathered travel satchel", "clothing": "moon-gray tunic", "accessory": "crescent clasp"},
}


class CharacterCreationError(ValueError):
    """Raised when a blueprint or assembly input is invalid."""


def _normalize_text(value):
    text = str(value or "").strip()
    return text or None


def _normalize_race_choice(race_name):
    raw_value = _normalize_text(race_name)
    if not raw_value:
        raise CharacterCreationError("Character creation requires a race.")
    normalized = resolve_race_name(raw_value, default=None)
    if not normalized or normalized not in RACE_DEFINITIONS:
        raise CharacterCreationError(f"Unknown race: {raw_value}")
    return normalized


def _normalize_profession_choice(profession_name):
    raw_value = _normalize_text(profession_name)
    if raw_value is None:
        return DEFAULT_PROFESSION
    normalized = resolve_profession_name(raw_value, default=None)
    if not normalized or normalized not in PROFESSION_PROFILES:
        raise CharacterCreationError(f"Unknown profession: {raw_value}")
    return normalized


def _normalize_stats(stats):
    if not isinstance(stats, Mapping):
        raise CharacterCreationError("Character creation requires a complete stats mapping.")

    provided_keys = set(stats.keys())
    expected_keys = set(RACE_STATS)
    if provided_keys != expected_keys:
        missing = sorted(expected_keys - provided_keys)
        extra = sorted(provided_keys - expected_keys)
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected: {', '.join(extra)}")
        raise CharacterCreationError("Invalid stat payload (" + "; ".join(details) + ").")

    normalized = {}
    for stat_name in RACE_STATS:
        value = stats.get(stat_name)
        if value is None:
            raise CharacterCreationError(f"Character creation requires a value for {stat_name}.")
        try:
            normalized[stat_name] = int(value)
        except (TypeError, ValueError) as exc:
            raise CharacterCreationError(f"Invalid stat value for {stat_name}: {value}") from exc
    return normalized


def _normalize_identity_payload(race, gender, *, appearance=None, identity=None):
    normalized_identity = normalize_identity_data(
        identity,
        fallback_race=race,
        fallback_gender=gender,
        fallback_appearance=appearance,
    )
    ok, error = validate_identity(normalized_identity)
    if not ok:
        raise CharacterCreationError(error)
    return normalized_identity


def normalize_creation_blueprint(blueprint, validate_name_availability=True, allow_reserved_name=False):
    if isinstance(blueprint, CharacterBlueprint):
        raw_blueprint = blueprint.to_dict()
    elif isinstance(blueprint, Mapping):
        raw_blueprint = dict(blueprint)
    else:
        raise CharacterCreationError("Character blueprint must be a mapping or CharacterBlueprint.")

    provided_keys = set(raw_blueprint.keys())
    expected_keys = set(BLUEPRINT_FIELDS)
    optional_keys = set(OPTIONAL_BLUEPRINT_FIELDS)
    missing = sorted(expected_keys - provided_keys)
    extra = sorted(provided_keys - expected_keys - optional_keys)
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if extra:
            details.append(f"unexpected: {', '.join(extra)}")
        raise CharacterCreationError("Blueprint must contain the required creation fields (" + "; ".join(details) + ").")

    name = _normalize_text(raw_blueprint.get("name"))
    ok, error = validate_name(
        name,
        allow_reserved=(not validate_name_availability) or allow_reserved_name,
        check_availability=validate_name_availability,
    )
    if not ok:
        raise CharacterCreationError(error)

    race = _normalize_race_choice(raw_blueprint.get("race"))
    gender = _normalize_text(raw_blueprint.get("gender"))
    if gender is None:
        raise CharacterCreationError("Character creation requires a gender.")
    profession = _normalize_profession_choice(raw_blueprint.get("profession"))
    stats = _normalize_stats(raw_blueprint.get("stats"))
    description = str(raw_blueprint.get("description") or "").strip() or "An unremarkable person."
    appearance = dict(raw_blueprint.get("appearance") or {}) if isinstance(raw_blueprint.get("appearance"), Mapping) else {}
    identity = _normalize_identity_payload(
        race,
        gender.lower(),
        appearance=appearance,
        identity=raw_blueprint.get("identity"),
    )

    return {
        "name": name,
        "race": race,
        "gender": gender.lower(),
        "profession": profession,
        "stats": stats,
        "description": description,
        "appearance": appearance,
        "identity": identity,
    }


def resolve_creation_start_room(start_room=None):
    if start_room:
        return start_room

    tutorial_room = ObjectDB.objects.filter(
        db_key="Intake Chamber",
        db_typeclass_path="typeclasses.rooms.Room",
    ).first()
    if tutorial_room:
        return tutorial_room

    configured_room = ObjectDB.objects.get_id(getattr(settings, "START_LOCATION", None))
    if configured_room:
        return configured_room

    return ObjectDB.objects.filter(id=2).first()


def is_onboarding_start_room(room):
    return bool(room and (getattr(getattr(room, "db", None), "is_onboarding", False) or getattr(getattr(room, "db", None), "is_tutorial", False)))


def apply_character_stats(character, stats):
    normalized = _normalize_stats(stats)
    if hasattr(character, "ensure_core_defaults"):
        character.ensure_core_defaults()

    if hasattr(character, "set_stat"):
        for stat_name, value in normalized.items():
            character.set_stat(stat_name, value, emit_cap_message=False)
    else:
        character.db.stats = dict(normalized)

    return normalized


def _create_training_weapon(holder, weapon_type):
    from typeclasses.objects import Object

    profiles = {
        "dagger": {
            "key": "training dagger",
            "profile": {"type": "light_edge", "skill": "light_edge", "damage_min": 2, "damage_max": 5, "roundtime": 2.0},
            "damage_type": "slice",
            "damage_types": {"slice": 0.6, "impact": 0.1, "puncture": 0.3},
            "balance": 60,
        },
        "sword": {
            "key": "training sword",
            "profile": {"type": "light_edge", "skill": "light_edge", "damage_min": 3, "damage_max": 6, "roundtime": 3.0},
            "damage_type": "slice",
            "damage_types": {"slice": 0.7, "impact": 0.1, "puncture": 0.2},
            "balance": 55,
        },
        "mace": {
            "key": "training mace",
            "profile": {"type": "blunt", "skill": "blunt", "damage_min": 4, "damage_max": 8, "roundtime": 4.0},
            "damage_type": "impact",
            "damage_types": {"slice": 0.0, "impact": 0.9, "puncture": 0.1},
            "balance": 45,
        },
        "spear": {
            "key": "training spear",
            "profile": {"type": "polearm", "skill": "polearm", "damage_min": 3, "damage_max": 7, "roundtime": 4.0},
            "damage_type": "puncture",
            "damage_types": {"slice": 0.1, "impact": 0.1, "puncture": 0.8},
            "balance": 52,
        },
    }
    profile = profiles[weapon_type]
    weapon = create_object(Object, key=profile["key"], location=holder, home=holder)
    weapon.db.item_type = "weapon"
    weapon.db.weight = 3.0
    weapon.db.weapon_profile = dict(profile["profile"])
    weapon.db.weapon_type = profile["profile"]["type"]
    weapon.db.skill = profile["profile"]["skill"]
    weapon.db.damage_min = profile["profile"]["damage_min"]
    weapon.db.damage_max = profile["profile"]["damage_max"]
    weapon.db.roundtime = profile["profile"]["roundtime"]
    weapon.db.damage_type = profile["damage_type"]
    weapon.db.damage_types = dict(profile["damage_types"])
    weapon.db.balance = profile["balance"]
    if hasattr(weapon, "sync_profile_fields"):
        weapon.sync_profile_fields()
    if hasattr(weapon, "normalize_damage_types"):
        weapon.normalize_damage_types()
    return weapon


def _create_starter_armor(holder):
    from typeclasses.armor import Armor

    armor = create_object(Armor, key="test leather armor", location=holder, home=holder)
    armor.db.slot = "torso"
    armor.db.desc = "A suit of light leather armor fit for a new adventurer."
    armor.db.armor_type = "light_armor"
    armor.db.protection = 2
    armor.db.hindrance = 1
    armor.db.absorption = 0.15
    armor.db.maneuver_hindrance = 4
    armor.db.stealth_hindrance = 3
    armor.db.coverage = ["chest", "abdomen", "back"]
    armor.db.covers = ["chest", "abdomen", "back"]
    if hasattr(armor, "apply_armor_preset"):
        armor.apply_armor_preset()
    return armor


def _create_sheath(holder, sheath_kind):
    from typeclasses.sheaths import BackScabbard, BeltSheath

    sheath_cls = BackScabbard if sheath_kind == "back" else BeltSheath
    key = "back scabbard" if sheath_kind == "back" else "belt sheath"
    return create_object(sheath_cls, key=key, location=holder, home=holder)


def _create_starter_cloak(holder):
    from typeclasses.wearables import Wearable

    cloak = create_object(Wearable, key="traveler's cloak", location=holder, home=holder)
    cloak.db.slot = "torso"
    cloak.db.desc = "A practical cloak suited to rough travel and changing weather."
    return cloak


def _create_simple_container(holder, key, desc):
    from typeclasses.objects import Object

    container = create_object(Object, key=key, location=holder, home=holder)
    container.db.is_container = True
    container.db.capacity = 8
    container.db.weight = 1.5
    container.db.desc = desc
    return container


def _create_simple_wearable(holder, key, slot, desc, weight=0.5):
    from typeclasses.wearables import Wearable

    item = create_object(Wearable, key=key, location=holder, home=holder)
    item.db.slot = slot
    item.db.weight = weight
    item.db.desc = desc
    return item


def _create_divine_charm(holder):
    return _create_simple_wearable(
        holder,
        key="divine charm",
        slot="neck",
        desc="A simple protective charm given to new adventurers.",
        weight=0.1,
    )


def _create_local_map(holder):
    from typeclasses.objects import Object

    item = create_object(Object, key="brookhollow map", location=holder, home=holder)
    item.db.weight = 0.1
    item.db.desc = "A simple starter map marked with the nearby roads and common landmarks."
    return item


def _create_study_book(holder, skill="scholarship"):
    from typeclasses.study_item import StudyItem

    item = create_object(StudyItem, key="study book", location=holder, home=holder)
    item.db.skill = skill
    item.db.difficulty = 10
    item.db.item_value = 10
    item.db.value = 10
    item.db.weight = 1.0
    item.db.desc = "A compact study text full of practical notes and marginalia."
    return item


def _create_lockpick(holder):
    from typeclasses.lockpick import Lockpick

    item = create_object(Lockpick, key="basic lockpick", location=holder, home=holder)
    item.db.item_value = 10
    item.db.value = 10
    item.db.weight = 0.2
    return item


def _create_gem_pouch(holder):
    return create_object("typeclasses.items.gem_pouch.GemPouch", key="gem pouch", location=holder, home=holder)


def apply_starting_gear(character):
    profession = _normalize_profession_choice(getattr(character.db, "profession", None))
    race = _normalize_race_choice(getattr(character.db, "race", None))
    race_kit = dict(RACE_STARTER_KIT.get(race, RACE_STARTER_KIT[DEFAULT_RACE]))
    created = []
    created.append(_create_divine_charm(character))
    created.append(_create_local_map(character))
    created.append(_create_training_weapon(character, PROFESSION_STARTER_WEAPONS.get(profession, "sword")))
    created.append(_create_starter_armor(character))
    created.append(
        _create_simple_container(
            character,
            key=race_kit["container"],
            desc=f"A starter container prepared for a newly arrived {RACE_DEFINITIONS[race]['name']} adventurer.",
        )
    )
    created.append(
        _create_simple_wearable(
            character,
            key=race_kit["clothing"],
            slot="torso",
            desc="A basic piece of starter clothing suited to the road.",
            weight=1.0,
        )
    )
    created.append(
        _create_simple_wearable(
            character,
            key=race_kit["accessory"],
            slot="fingers",
            desc="A small personal accessory included with your starting kit.",
            weight=0.1,
        )
    )

    character.db.coins = int(getattr(character.db, "coins", 0) or 0) + 10
    return created


def apply_starting_skills(character):
    if hasattr(character, "ensure_starter_skills"):
        character.ensure_starter_skills()
    profession = _normalize_profession_choice(getattr(character.db, "profession", None))
    if hasattr(character, "learn_skill"):
        for skill_name, target_rank in PROFESSION_STARTER_SKILLS.get(profession, {}).items():
            current_rank = int(getattr(character, "get_skill", lambda _name: 0)(skill_name) or 0)
            if current_rank < target_rank:
                character.learn_skill(skill_name, {"rank": target_rank, "mindstate": 0})
    return dict(getattr(character.db, "skills", {}) or {}) if getattr(character, "db", None) else {}


def finalize_character_creation(
    character,
    *,
    blueprint=None,
    race=None,
    gender=None,
    profession=None,
    stats=None,
    description=None,
    start_room=None,
    activate_onboarding=True,
    emit_messages=False,
):
    if not character:
        raise CharacterCreationError("Character assembly requires a character object.")

    normalized_blueprint = (
        normalize_creation_blueprint(blueprint, validate_name_availability=False)
        if blueprint is not None
        else None
    )
    selected_race = normalized_blueprint["race"] if normalized_blueprint else (race if race is not None else getattr(character.db, "race", DEFAULT_RACE))
    selected_gender = normalized_blueprint["gender"] if normalized_blueprint else gender
    selected_profession = normalized_blueprint["profession"] if normalized_blueprint else profession
    selected_stats = normalized_blueprint["stats"] if normalized_blueprint else stats
    selected_description = normalized_blueprint["description"] if normalized_blueprint else description
    selected_identity = normalized_blueprint["identity"] if normalized_blueprint else None

    selected_race = _normalize_race_choice(selected_race)
    selected_gender = str(selected_gender or getattr(character.db, "gender", "neutral")).strip().lower()
    selected_profession = _normalize_profession_choice(selected_profession)
    selected_identity = _normalize_identity_payload(selected_race, selected_gender, identity=selected_identity)

    if hasattr(character, "ensure_core_defaults"):
        character.ensure_core_defaults()

    if selected_description is not None:
        character.db.desc = str(selected_description or "").strip() or "An unremarkable person."
    character.db.gender = selected_gender or "neutral"
    character.db.identity = normalize_identity_data(
        selected_identity,
        fallback_race=selected_race,
        fallback_gender=selected_gender,
    )

    if hasattr(character, "set_race"):
        character.set_race(selected_race, sync=False, emit_messages=emit_messages)
    else:
        apply_race(character, selected_race, sync=False, emit_messages=emit_messages)

    if hasattr(character, "set_profession"):
        if character.set_profession(selected_profession) is False:
            raise CharacterCreationError(f"Could not assign profession: {selected_profession}")
    else:
        character.db.profession = selected_profession
        character.db.guild = selected_profession

    if selected_stats is not None:
        apply_character_stats(character, selected_stats)

    if hasattr(character, "get_rendered_desc"):
        character.db.desc = character.get_rendered_desc()

    room = resolve_creation_start_room(start_room=start_room)
    if not is_onboarding_start_room(room):
        apply_starting_gear(character)
    apply_starting_skills(character)

    if room:
        character.home = room
        character.location = room
        if is_onboarding_start_room(room):
            character.db.onboarding_step = "start" if activate_onboarding else None
            character.db.onboarding_complete = False

    if hasattr(character, "update_encumbrance_state"):
        character.update_encumbrance_state()
    if hasattr(character, "sync_client_state"):
        character.sync_client_state(include_map=False)

    return character


def create_character_from_blueprint(account, blueprint, **kwargs):
    allow_reserved_name = bool(kwargs.pop("allow_reserved_name", False))
    normalized_blueprint = normalize_creation_blueprint(
        blueprint,
        validate_name_availability=True,
        allow_reserved_name=allow_reserved_name,
    )
    if not is_name_available(normalized_blueprint["name"], allow_reserved=allow_reserved_name):
        raise CharacterCreationError(f"That name is no longer available: {normalized_blueprint['name']}")

    create_kwargs = {
        "key": normalized_blueprint["name"],
        "race": normalized_blueprint["race"],
        "gender": normalized_blueprint["gender"],
        "profession": normalized_blueprint["profession"],
        "stats": normalized_blueprint["stats"],
        "description": normalized_blueprint["description"],
        "creation_blueprint": normalized_blueprint,
    }
    if kwargs.get("start_room") is not None:
        create_kwargs["start_room"] = kwargs["start_room"]
    if kwargs.get("typeclass") is not None:
        create_kwargs["typeclass"] = kwargs["typeclass"]
    if kwargs.get("permissions") is not None:
        create_kwargs["permissions"] = kwargs["permissions"]
    if kwargs.get("ip") is not None:
        create_kwargs["ip"] = kwargs["ip"]
    if kwargs.get("skip_post_create_setup") is not None:
        create_kwargs["skip_post_create_setup"] = kwargs["skip_post_create_setup"]
    if kwargs.get("activate_onboarding") is not None:
        create_kwargs["activate_onboarding"] = kwargs["activate_onboarding"]

    character, errors = account.create_character(**create_kwargs)
    return character, errors


def assign_profession_in_world(character, profession):
    if not character:
        return False
    normalized = _normalize_profession_choice(profession)
    if hasattr(character, "set_profession"):
        return bool(character.set_profession(normalized))
    character.db.profession = normalized
    character.db.guild = normalized
    return True
