import time

from tools.diretest.core.runtime import record_payload_timing, suppress_client_payloads
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
        "weapon_range_type": getattr(item.db, "weapon_range_type", None),
        "ammo_loaded": bool(getattr(item.db, "ammo_loaded", False)),
        "ammo_type": getattr(item.db, "ammo_type", None),
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

    if hasattr(character, "get_race_display_name"):
        statuses.append(f"Race: {character.get_race_display_name()}")
    elif getattr(character.db, "race", None):
        statuses.append(f"Race: {str(character.db.race).replace('_', ' ').title()}")

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

    if hasattr(character, "get_favor"):
        statuses.append(f"Favor: {character.get_favor()}")
        if hasattr(character, "get_favor_state_message"):
            message = character.get_favor_state_message()
            if message:
                statuses.append(message)
    if hasattr(character, "get_exp_debt") and character.get_exp_debt() > 0:
        statuses.append(f"Experience Debt: {character.get_exp_debt()}")
    life_state = str(getattr(character.db, "life_state", "ALIVE") or "ALIVE").upper()
    if life_state != "ALIVE":
        statuses.append(f"State: {life_state.title()}")
        if life_state == "DEAD" and hasattr(character, "get_depart_mode"):
            corpse = character.get_death_corpse() if hasattr(character, "get_death_corpse") else None
            statuses.append(f"Depart: {character.get_depart_mode(corpse=corpse).title()}")
        if life_state == "DEAD" and hasattr(character, "get_soul_state"):
            soul_state = character.get_soul_state()
            if isinstance(soul_state, dict):
                if hasattr(character, "get_soul_strength_label"):
                    statuses.append(f"Soul: {character.get_soul_strength_label(soul_state=soul_state).title()}")
                statuses.append(f"Soul Strength: {int(round(float(soul_state.get('strength', 0.0) or 0.0)))}/100")
    if hasattr(character, "is_death_sting_active") and character.is_death_sting_active():
        statuses.append(f"Death's Sting: {character.get_death_sting_label()} ({int(round(character.get_death_sting_severity() * 100))}%)")
    if hasattr(character, "get_state"):
        fragility = character.get_state("resurrection_fragility")
        if fragility:
            statuses.append(f"Recovery: {str(fragility.get('label', 'fragile')).title()}")
        instability = character.get_state("resurrection_instability")
        if instability:
            statuses.append("State: Unstable")
    if hasattr(character, "get_owned_grave") and character.get_owned_grave():
        statuses.append("Grave: Recoverable here")

    if hasattr(character, "is_in_roundtime") and character.is_in_roundtime():
        statuses.append(f"Roundtime {character.get_remaining_roundtime():.1f}s")

    if hasattr(character, "is_profession") and character.is_profession("warrior"):
        if hasattr(character, "get_war_tempo_state"):
            statuses.append(f"Tempo: {character.get_war_tempo_state().title()}")
        if hasattr(character, "get_exhaustion") and hasattr(character, "get_exhaustion_profile"):
            statuses.append(f"Exhaustion: {character.get_exhaustion_profile().get('label', 'Fresh')}")
        if hasattr(character, "get_pressure_level"):
            statuses.append(f"Pressure: {character.get_pressure_level()}")
        if hasattr(character, "get_combat_rhythm_state"):
            statuses.append(f"Rhythm: {character.get_combat_rhythm_state().title()}")
        if hasattr(character, "get_active_warrior_berserk"):
            active_berserk = character.get_active_warrior_berserk()
            if active_berserk:
                statuses.append(f"Berserk: {str(active_berserk.get('name') or active_berserk.get('key') or '').title()}")
    elif hasattr(character, "is_profession") and character.is_profession("ranger"):
        if hasattr(character, "get_wilderness_bond_profile"):
            statuses.append(f"Bond: {character.get_wilderness_bond_profile().get('label', 'Attuned')}")
        if hasattr(character, "get_nature_focus"):
            statuses.append(f"Focus: {character.get_nature_focus()}")
        if getattr(character, "location", None) and hasattr(character.location, "get_environment_type"):
            statuses.append(f"Terrain: {character.location.get_environment_type().title()}")
        if getattr(character, "location", None) and hasattr(character.location, "get_terrain_type"):
            statuses.append(f"Ground: {character.location.get_terrain_type().title()}")
        if hasattr(character, "get_equipped_ammo_state"):
            ammo_state = character.get_equipped_ammo_state()
            if ammo_state:
                statuses.append(f"Ammo: {'Loaded' if ammo_state.get('loaded') else 'Empty'}")
        if hasattr(character, "get_ranger_aim_stacks"):
            aim_stacks = character.get_ranger_aim_stacks()
            if aim_stacks:
                statuses.append(f"Aim: {aim_stacks}")
        if hasattr(character, "has_active_ranger_companion") and character.has_active_ranger_companion():
            statuses.append(f"Companion: {character.get_ranger_companion_label()}")
    elif hasattr(character, "is_profession") and character.is_profession("empath"):
        if hasattr(character, "get_empath_shock"):
            statuses.append(f"Shock: {character.get_empath_shock()}")
        if hasattr(character, "is_empath_overdrawn") and character.is_empath_overdrawn():
            statuses.append("Overdraw")
        if hasattr(character, "get_empath_links"):
            links = character.get_empath_links(require_local=False, include_group=False)
            if links:
                primary = links[0]
                detail = " deep" if primary.get("deepened") else ""
                statuses.append(f"Linked: {primary['target'].key} [{str(primary.get('type', 'touch')).title()} {primary.get('strength_label', 'Weak')}{detail}]")
        if hasattr(character, "get_empath_unity_state"):
            unity = character.get_empath_unity_state()
            if unity:
                statuses.append(f"Unity: {len(unity.get('members', []))}")
        if hasattr(character, "get_empath_wounds"):
            wounds = character.get_empath_wounds()
            statuses.append(f"Wounds V{int(wounds.get('vitality', 0) or 0)}/B{int(wounds.get('bleeding', 0) or 0)}/F{int(wounds.get('fatigue', 0) or 0)}/T{int(wounds.get('trauma', 0) or 0)}/P{int(wounds.get('poison', 0) or 0)}/D{int(wounds.get('disease', 0) or 0)}")
    elif hasattr(character, "is_profession") and character.is_profession("cleric"):
        if hasattr(character, "get_devotion"):
            statuses.append(f"Devotion: {character.get_devotion()}")
        if hasattr(character, "get_devotion_state"):
            statuses.append(f"Connection: {character.get_devotion_state().title()}")

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
        if hasattr(character, "is_hidden_warrior_ability") and character.is_hidden_warrior_ability(ability):
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
                "exhaustion_cost": int(getattr(ability, "exhaustion_cost", 0) or 0),
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
    started_at = time.perf_counter()
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

    payload = {
        "name": character.key,
        "race": character.get_race() if hasattr(character, "get_race") else getattr(character.db, "race", None),
        "race_name": character.get_race_display_name() if hasattr(character, "get_race_display_name") else None,
        "race_size": character.get_race_size() if hasattr(character, "get_race_size") else getattr(character.db, "size", None),
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
        "war_tempo": int(character.get_war_tempo() if hasattr(character, "get_war_tempo") else 0),
        "max_war_tempo": int(character.get_max_war_tempo() if hasattr(character, "get_max_war_tempo") else 0),
        "war_tempo_state": character.get_war_tempo_state() if hasattr(character, "get_war_tempo_state") else None,
        "wilderness_bond": int(character.get_wilderness_bond() if hasattr(character, "get_wilderness_bond") else 0),
        "wilderness_bond_state": character.get_wilderness_bond_state() if hasattr(character, "get_wilderness_bond_state") else None,
        "ranger_instinct": int(character.get_ranger_instinct() if hasattr(character, "get_ranger_instinct") else 0),
        "nature_focus": int(character.get_nature_focus() if hasattr(character, "get_nature_focus") else 0),
        "ranger_terrain": character.get_ranger_terrain_type() if hasattr(character, "get_ranger_terrain_type") else None,
        "ranger_companion": character.get_ranger_companion() if hasattr(character, "get_ranger_companion") else None,
        "empath_shock": int(character.get_empath_shock() if hasattr(character, "get_empath_shock") else 0),
        "empath_wounds": character.get_empath_wounds() if hasattr(character, "get_empath_wounds") else None,
        "empath_link": getattr(character.get_linked_target(), "key", None) if hasattr(character, "get_linked_target") and character.get_linked_target() else None,
        "empath_links": [
            {
                "target": getattr(entry.get("target"), "key", None),
                "type": entry.get("type"),
                "priority": int(entry.get("priority", 0) or 0),
                "strength": int(entry.get("strength", 0) or 0),
                "strength_label": entry.get("strength_label"),
                "deepened": bool(entry.get("deepened", False)),
                "remaining": int(entry.get("remaining", 0) or 0),
            }
            for entry in (character.get_empath_links(require_local=False, include_group=False) if hasattr(character, "get_empath_links") else [])
        ],
        "empath_unity": [member.key for member in ((character.get_empath_unity_state() or {}).get("members", []) if hasattr(character, "get_empath_unity_state") else [])],
        "empath_overdraw": bool(character.is_empath_overdrawn() if hasattr(character, "is_empath_overdrawn") else False),
        "exhaustion": int(character.get_exhaustion() if hasattr(character, "get_exhaustion") else 0),
        "exhaustion_state": character.get_exhaustion_stage() if hasattr(character, "get_exhaustion_stage") else None,
        "pressure_level": int(character.get_pressure_level() if hasattr(character, "get_pressure_level") else 0),
        "combat_rhythm": character.get_combat_rhythm_state() if hasattr(character, "get_combat_rhythm_state") else None,
        "active_berserk": (character.get_active_warrior_berserk() or {}).get("key") if hasattr(character, "get_active_warrior_berserk") else None,
        "coins": int(getattr(character.db, "coins", 0) or 0),
        "carry_modifier": float(character.get_race_carry_modifier() if hasattr(character, "get_race_carry_modifier") else getattr(character.db, "carry_modifier", 1.0) or 1.0),
        "max_carry_weight": float(character.get_max_carry_weight() if hasattr(character, "get_max_carry_weight") else getattr(character.db, "max_carry_weight", 100.0) or 100.0),
        "life_state": str(getattr(character.db, "life_state", "ALIVE") or "ALIVE").upper(),
        "favor": int(character.get_favor() if hasattr(character, "get_favor") else 0),
        "favor_state": character.get_favor_state() if hasattr(character, "get_favor_state") else None,
        "unabsorbed_xp": int(character.get_unabsorbed_xp() if hasattr(character, "get_unabsorbed_xp") else 0),
        "exp_debt": int(character.get_exp_debt() if hasattr(character, "get_exp_debt") else 0),
        "death_favor_snapshot": character.get_favor_death_snapshot() if hasattr(character, "get_favor_death_snapshot") else None,
        "depart_mode": character.get_depart_mode(corpse=character.get_death_corpse()) if hasattr(character, "get_depart_mode") and hasattr(character, "is_dead") and character.is_dead() else None,
        "death_sting_active": bool(character.is_death_sting_active() if hasattr(character, "is_death_sting_active") else False),
        "death_sting_severity": float(character.get_death_sting_severity() if hasattr(character, "get_death_sting_severity") else 0.0),
        "death_sting_label": character.get_death_sting_label() if hasattr(character, "get_death_sting_label") else None,
        "death_sting_remaining": int(character.get_death_sting_time_remaining() if hasattr(character, "get_death_sting_time_remaining") else 0),
        "grave_present": bool(character.get_owned_grave() if hasattr(character, "get_owned_grave") else False),
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
    record_payload_timing((time.perf_counter() - started_at) * 1000.0)
    return payload


def send_character_update(character, session=None):
    payload = get_character_payload(character)
    if not suppress_client_payloads():
        send_structured(character, "character", payload, session=session)
    return payload


def get_subsystem_payload(character):
    started_at = time.perf_counter()
    subsystem = character.get_subsystem() if hasattr(character, "get_subsystem") else None
    if isinstance(subsystem, dict):
        payload = dict(subsystem)
        record_payload_timing((time.perf_counter() - started_at) * 1000.0)
        return payload
    payload = {
        "key": getattr(character.db, "profession", None),
        "profession": getattr(character.db, "profession", None),
        "guild_tag": None,
        "label": None,
    }
    record_payload_timing((time.perf_counter() - started_at) * 1000.0)
    return payload


def send_subsystem_update(character, session=None):
    payload = get_subsystem_payload(character)
    if not suppress_client_payloads():
        send_structured(character, "subsystem", payload, session=session)
    return payload