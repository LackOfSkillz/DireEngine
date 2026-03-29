import time

from typeclasses.abilities import get_ability_map
from world.area_forge.utils.messages import send_structured


def _item_actions(character, item):
    actions = ["look", "drop"]
    is_wielded = bool(hasattr(character, "get_weapon") and character.get_weapon() == item)
    if is_wielded:
        actions.insert(1, "unwield")
    elif getattr(item.db, "item_type", None) == "weapon" or getattr(item.db, "weapon_type", None):
        actions.insert(1, "wield")

    if getattr(item.db, "wearable", False):
        actions.insert(1, "wear")

    deduped = []
    for action in actions:
        if action not in deduped:
            deduped.append(action)
    return deduped


def _serialize_inventory_item(character, item):
    return {
        "name": item.key,
        "type": getattr(item.db, "item_type", None) or "item",
        "slot": getattr(item.db, "slot", None),
        "wearable": bool(getattr(item.db, "wearable", False)),
        "wieldable": bool(getattr(item.db, "item_type", None) == "weapon" or getattr(item.db, "weapon_type", None)),
        "weapon_type": getattr(item.db, "weapon_type", None),
        "is_wielded": bool(hasattr(character, "get_weapon") and character.get_weapon() == item),
        "actions": _item_actions(character, item),
    }


def _get_status_list(character):
    statuses = []

    profession = None
    if hasattr(character, "get_profession"):
        profession = character.get_profession()
    elif getattr(character.db, "profession", None):
        profession = character.db.profession

    if profession and profession != "commoner":
        statuses.append(f"Profession: {str(profession).replace('_', ' ').title()}")

    if getattr(character.db, "guild", None):
        statuses.append(f"Guild: {str(character.db.guild).replace('_', ' ').title()}")

    if getattr(character.db, "stunned", False):
        statuses.append("Stunned")

    bleed_state = getattr(character.db, "bleed_state", None)
    if bleed_state and bleed_state != "none":
        statuses.append(f"Bleeding: {str(bleed_state).title()}")

    if getattr(character.db, "in_combat", False):
        target = getattr(character.db, "target", None)
        target_name = getattr(target, "key", None)
        statuses.append(f"In combat{f' with {target_name}' if target_name else ''}")

    if hasattr(character, "is_in_roundtime") and character.is_in_roundtime():
        statuses.append(f"Roundtime {character.get_remaining_roundtime():.1f}s")

    stance = getattr(character.db, "stance", None) or {}
    if stance:
        statuses.append(f"Stance O{int(stance.get('offense', 50))}/D{int(stance.get('defense', 50))}")

    states = getattr(character.db, "states", None) or {}
    state_labels = {
        "hidden": "Hidden",
        "sneaking": "Sneaking",
        "observing": "Observing",
        "augmentation_buff": "Buffed",
        "debilitated": "Debilitated",
        "warding_barrier": "Barrier Active",
        "utility_light": "Light Spell",
        "exposed_magic": "Magic Exposed",
    }
    for key, label in state_labels.items():
        if states.get(key):
            statuses.append(label)

    if states.get("stalking"):
        statuses.append("Stalking")
    if states.get("ambush_target"):
        statuses.append("Ambush Ready")

    return statuses


def _get_cooldowns(character):
    cooldowns = {}
    for key, value in (getattr(character.db, "states", None) or {}).items():
        key_str = str(key)
        if not key_str.startswith("cooldown_"):
            continue
        cooldown_key = key_str.replace("cooldown_", "", 1)
        duration = 0
        if isinstance(value, dict):
            duration = int(value.get("duration", 0) or 0)
        elif value is not None:
            duration = int(value or 0)
        cooldowns[cooldown_key] = max(0, duration)

    runtime_cooldowns = getattr(getattr(character, "ndb", None), "cooldowns", None)
    now = time.time()
    if isinstance(runtime_cooldowns, dict):
        for cooldown_key, expires_at in runtime_cooldowns.items():
            remaining = max(0, int(float(expires_at or 0) - now))
            if remaining > 0:
                cooldowns[str(cooldown_key)] = max(cooldowns.get(str(cooldown_key), 0), remaining)
    return cooldowns


def _get_ability_payload(character, cooldowns):
    if not hasattr(character, "can_see_ability"):
        return []

    abilities = []
    for ability in get_ability_map(character).values():
        if not character.passes_guild_check(ability):
            continue
        required = getattr(ability, "required", {}) or {}
        visible_if = getattr(ability, "visible_if", {}) or {}
        skill_name = required.get("skill") or visible_if.get("skill")
        is_visible = character.can_see_ability(ability)
        meets_requirements, requirement_message = character.meets_ability_requirements(ability)
        locked_reason = None
        if not is_visible and skill_name:
            locked_reason = f"requires {skill_name} rank {int(visible_if.get('min_rank', 0) or 0)}"
        elif not meets_requirements:
            locked_reason = requirement_message.replace("You need ", "requires ")
        abilities.append(
            {
                "key": ability.key,
                "category": getattr(ability, "category", "general"),
                "roundtime": float(getattr(ability, "roundtime", 0) or 0),
                "required_skill": skill_name,
                "required_rank": int(required.get("rank", 0) or 0),
                "current_rank": int(character.get_skill(skill_name) if skill_name else 0),
                "cooldown": int(cooldowns.get(ability.key, 0) or 0),
                "locked": bool(not is_visible or not meets_requirements),
                "locked_reason": locked_reason,
            }
        )

    return sorted(abilities, key=lambda item: (item["category"], item.get("locked", False), item["key"]))


def _object_name(value):
    if value is None:
        return None
    return getattr(value, "key", str(value))


def get_character_payload(character):
    max_hp = getattr(character.db, "max_hp", None) or 100
    hp = getattr(character.db, "hp", None)
    if hp is None:
        hp = max_hp

    max_stamina = getattr(character.db, "max_fatigue", None) or 100
    fatigue = getattr(character.db, "fatigue", None) or 0
    stamina = max(0, max_stamina - fatigue)
    max_balance = getattr(character.db, "max_balance", None) or 100
    balance = getattr(character.db, "balance", None)
    if balance is None:
        balance = max_balance
    max_attunement = getattr(character.db, "max_attunement", None) or 100
    attunement = getattr(character.db, "attunement", None)
    if attunement is None:
        attunement = max_attunement

    equipment_payload = {}
    equipment = getattr(character.db, "equipment", None) or {}
    if isinstance(equipment, dict):
        for slot, value in equipment.items():
            if isinstance(value, (list, tuple)):
                equipment_payload[slot] = [_object_name(item) for item in value if item]
            else:
                equipment_payload[slot] = _object_name(value)

    inventory = [
        _serialize_inventory_item(character, obj)
        for obj in character.contents
        if getattr(obj, "destination", None) is None and getattr(obj.db, "worn_by", None) != character
    ]

    cooldowns = _get_cooldowns(character)
    target = getattr(character.db, "target", None)
    stance = getattr(character.db, "stance", None) or {"offense": 50, "defense": 50}

    return {
        "name": character.key,
        "profession": character.get_profession() if hasattr(character, "get_profession") else getattr(character.db, "profession", None),
        "profession_rank": character.get_profession_rank() if hasattr(character, "get_profession_rank") else int(getattr(character.db, "profession_rank", 1) or 1),
        "guild": getattr(character.db, "guild", None),
        "hp": hp,
        "max_hp": max_hp,
        "balance": balance,
        "max_balance": max_balance,
        "stamina": stamina,
        "max_stamina": max_stamina,
        "fatigue": fatigue,
        "attunement": attunement,
        "max_attunement": max_attunement,
        "coins": int(getattr(character.db, "coins", 0) or 0),
        "roundtime": float(character.get_remaining_roundtime() if hasattr(character, "get_remaining_roundtime") else 0),
        "in_combat": bool(getattr(character.db, "in_combat", False)),
        "target": getattr(target, "key", None),
        "equipped_weapon": _object_name(character.get_weapon()) if hasattr(character, "get_weapon") else None,
        "stance": {
            "offense": int(stance.get("offense", 50) or 50),
            "defense": int(stance.get("defense", 50) or 50),
        },
        "inventory": inventory,
        "equipment": equipment_payload,
        "status": _get_status_list(character),
        "cooldowns": cooldowns,
        "abilities": _get_ability_payload(character, cooldowns),
    }


def send_character_update(character, session=None):
    payload = get_character_payload(character)
    send_structured(character, "character", payload, session=session)
    return payload


def get_subsystem_payload(character):
    subsystem = character.get_subsystem() if hasattr(character, "get_subsystem") else None
    if isinstance(subsystem, dict):
        return dict(subsystem)
    return {
        "key": getattr(character.db, "profession", None),
        "profession": getattr(character.db, "profession", None),
        "guild_tag": None,
        "label": None,
    }


def send_subsystem_update(character, session=None):
    payload = get_subsystem_payload(character)
    send_structured(character, "subsystem", payload, session=session)
    return payload