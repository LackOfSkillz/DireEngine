from collections.abc import Mapping
import time

from evennia.utils import logger

from world.systems import awareness
from world.systems.skills import award_exp_skill


SHOP_HEAT_DECAY_BUCKET = 300.0
PVP_OPEN_SECONDS = 4 * 60 * 60
MARK_SUSPICION_WINDOW = 60.0
OVERMARK_THRESHOLD = 3
WANTED_DECAY_BUCKET = 600.0
GUARD_ATTENTION_THRESHOLD = 5


def _get_skill_rank(character, skill_name):
    if character is None:
        return 0
    if hasattr(character, "get_skill_rank"):
        try:
            return int(character.get_skill_rank(skill_name) or 0)
        except Exception:
            return 0
    if hasattr(character, "get_skill"):
        try:
            return int(character.get_skill(skill_name) or 0)
        except Exception:
            return 0
    return 0


def _ensure_target_state(target):
    if target is None:
        return
    if getattr(getattr(target, "db", None), "shop_heat", None) is None:
        target.db.shop_heat = 0
    if getattr(getattr(target, "db", None), "shop_heat_updated_at", None) is None:
        target.db.shop_heat_updated_at = 0
    theft_attempt_log = getattr(getattr(target, "db", None), "theft_attempt_log", None)
    if not isinstance(theft_attempt_log, dict):
        target.db.theft_attempt_log = {}


def _ensure_actor_state(actor):
    if actor is None:
        return
    if not isinstance(getattr(getattr(actor, "db", None), "contacts", None), Mapping):
        actor.db.contacts = {}
    if getattr(getattr(actor, "db", None), "thief_reputation", None) is None:
        actor.db.thief_reputation = 0
    if getattr(getattr(actor, "db", None), "wanted_level", None) is None:
        actor.db.wanted_level = 0
    if getattr(getattr(actor, "db", None), "last_wanted_update", None) is None:
        actor.db.last_wanted_update = 0
    if getattr(getattr(actor, "db", None), "guard_attention", None) is None:
        actor.db.guard_attention = False
    justice_incidents = getattr(getattr(actor, "db", None), "justice_incidents", None)
    if justice_incidents is None:
        actor.db.justice_incidents = []


def _get_target_key(target):
    if target is None:
        return "unknown"
    target_id = getattr(target, "id", None)
    if target_id is not None:
        return f"id:{target_id}"
    return str(getattr(target, "key", "unknown") or "unknown").strip().lower() or "unknown"


def _is_player_target(target):
    if target is None or bool(getattr(getattr(target, "db", None), "is_npc", False)):
        return False
    if hasattr(target, "is_typeclass"):
        try:
            return bool(target.is_typeclass("typeclasses.characters.Character", exact=False))
        except Exception:
            return False
    return False


def _is_theft_enabled_target(target):
    if target is None:
        return False
    if bool(getattr(getattr(target, "db", None), "is_vendor", False)):
        return True
    if bool(getattr(getattr(target, "db", None), "is_shopkeeper", False)):
        return True
    if bool(getattr(getattr(target, "db", None), "is_npc", False)):
        return True
    return _is_player_target(target)


def _is_shop_target(target):
    return bool(target and (bool(getattr(getattr(target, "db", None), "is_vendor", False)) or bool(getattr(getattr(target, "db", None), "is_shopkeeper", False))))


def _get_container_owner(container):
    location = getattr(container, "location", None)
    return location if _is_theft_enabled_target(location) else None


def _stealable_items(target):
    return [
        item for item in list(getattr(target, "contents", []) or [])
        if not bool(getattr(getattr(item, "db", None), "steal_protected", False))
        and not bool(getattr(getattr(item, "db", None), "is_character", False))
        and not bool(getattr(getattr(item, "db", None), "is_npc", False))
    ]


def _has_stealable_value(target):
    if int(getattr(getattr(target, "db", None), "coins", 0) or 0) > 0:
        return True
    if _stealable_items(target):
        return True
    if _is_shop_target(target) and list(getattr(getattr(target, "db", None), "inventory", []) or []):
        return True
    return False


def record_mark_attempt(actor, target):
    if actor is None or target is None:
        return 0

    _ensure_target_state(target)
    now = time.time()
    actor_key = str(getattr(actor, "id", "unknown") or "unknown")
    theft_log = dict(getattr(target.db, "theft_attempt_log", None) or {})
    mark_history = dict(theft_log.get("mark_history") or {})
    entry = dict(mark_history.get(actor_key) or {"count": 0, "last_mark_at": 0})
    if now - float(entry.get("last_mark_at", 0) or 0) > MARK_SUSPICION_WINDOW:
        entry["count"] = 0
    entry["count"] = int(entry.get("count", 0) or 0) + 1
    entry["last_mark_at"] = now
    mark_history[actor_key] = entry
    theft_log["mark_history"] = mark_history
    target.db.theft_attempt_log = theft_log

    if _is_shop_target(target) and entry["count"] > OVERMARK_THRESHOLD:
        add_shop_heat(target, amount=1)
        awareness_state = dict(getattr(target.db, "awareness_state", None) or {})
        awareness_state["suspicion_bonus"] = int(awareness_state.get("suspicion_bonus", 0) or 0) + 5
        actor_modifiers = dict(awareness_state.get("actor_modifiers") or {})
        actor_modifiers[actor_key] = int(actor_modifiers.get(actor_key, 0) or 0) + 5
        awareness_state["actor_modifiers"] = actor_modifiers
        target.db.awareness_state = awareness_state
        if hasattr(target, "adjust_suspicion_for"):
            target.adjust_suspicion_for(actor, 2)
    return int(entry["count"])


def get_repeat_target_penalty(actor, target_key):
    data = dict(getattr(getattr(actor, "db", None), "repeat_theft_targets", None) or {})
    entry = dict(data.get(target_key) or {})
    attempts = int(entry.get("attempts", 0) or 0)
    return attempts * 10


def record_theft_attempt(actor, target_key, success):
    data = dict(getattr(getattr(actor, "db", None), "repeat_theft_targets", None) or {})
    entry = dict(data.get(target_key) or {"attempts": 0, "successes": 0, "last_attempt_at": 0})
    entry["attempts"] = int(entry.get("attempts", 0) or 0) + 1
    if success:
        entry["successes"] = int(entry.get("successes", 0) or 0) + 1
    entry["last_attempt_at"] = time.time()
    data[target_key] = entry
    actor.db.repeat_theft_targets = data
    return entry


def get_shop_heat(target):
    if target is None:
        return 0
    return int(getattr(getattr(target, "db", None), "shop_heat", 0) or 0)


def add_shop_heat(target, amount=1):
    if target is None:
        return 0
    _ensure_target_state(target)
    target.db.shop_heat = int(getattr(target.db, "shop_heat", 0) or 0) + int(amount or 0)
    target.db.shop_heat_updated_at = time.time()
    return int(target.db.shop_heat or 0)


def get_shop_heat_penalty(target):
    return int(get_shop_heat(target) * 10)


def decay_shop_heat(target):
    if target is None:
        return 0
    _ensure_target_state(target)
    current_heat = int(getattr(target.db, "shop_heat", 0) or 0)
    last_updated = float(getattr(target.db, "shop_heat_updated_at", 0) or 0)
    if current_heat <= 0 or last_updated <= 0:
        return current_heat

    elapsed = max(0.0, time.time() - last_updated)
    decay_steps = int(elapsed // SHOP_HEAT_DECAY_BUCKET)
    if decay_steps <= 0:
        return current_heat

    new_heat = max(0, current_heat - decay_steps)
    target.db.shop_heat = new_heat
    target.db.shop_heat_updated_at = time.time()
    return new_heat


def can_steal_from(actor, target):
    if actor is None or target is None:
        return False, "There is nothing here to steal from."
    if actor == target:
        return False, "You cannot steal from yourself."
    if not _is_theft_enabled_target(target):
        return False, "You cannot steal from that."
    if getattr(actor, "location", None) != getattr(target, "location", None):
        return False, "They are not here."
    if hasattr(actor, "is_hidden") and not actor.is_hidden():
        return False, "You must be hidden to do that."
    if _is_shop_target(target) and get_shop_heat(target) >= 3:
        return False, "They are watching you too closely right now."
    if not _has_stealable_value(target):
        return False, "They have nothing you can steal."
    return True, None


def can_steal_from_container(actor, container, requested_item=None):
    if actor is None or container is None:
        return False, "There is nothing here to steal from."
    if not bool(getattr(getattr(container, "db", None), "is_container", False)):
        return False, "That is not a container."
    owner = _get_container_owner(container)
    if owner is not None and owner == actor:
        return False, "You cannot steal from yourself."
    if hasattr(actor, "is_hidden") and not actor.is_hidden():
        return False, "You must be hidden to do that."
    if requested_item and _find_requested_item(container, requested_item) is None:
        return False, "You do not find that in the container."
    if not _stealable_items(container):
        return False, "You find nothing worth stealing in that container."
    return True, None


def get_theft_skill_total(actor, target, context=None):
    context = dict(context or {})
    source_target = context.get("container") or target
    target_key = context.get("target_key") or _get_target_key(source_target)
    total = _get_skill_rank(actor, "thievery")
    if hasattr(actor, "is_hidden") and actor.is_hidden():
        total += 10
    awareness_target = context.get("awareness_target") or target
    total += awareness.get_mark_bonus(actor, awareness_target, context=context)
    total += int(context.get("theft_bonus", 0) or 0)
    total -= get_repeat_target_penalty(actor, target_key)
    if _is_shop_target(awareness_target):
        total -= get_shop_heat_penalty(awareness_target)
    return int(total)


def _find_requested_item(target, requested_item):
    query = str(requested_item or "").strip().lower()
    if not query:
        return None
    for item in _stealable_items(target):
        if str(getattr(item, "key", "") or "").strip().lower() == query:
            return item
    for entry in list(getattr(getattr(target, "db", None), "inventory", []) or []):
        if str(entry or "").strip().lower() == query:
            return str(entry)
    return None


def select_stolen_item(actor, target, context=None):
    context = dict(context or {})
    requested_item = context.get("requested_item")
    source_target = context.get("container") or target

    if _is_player_target(target) and source_target == target:
        coins = int(getattr(getattr(target, "db", None), "coins", 0) or 0)
        if coins > 0:
            return {"kind": "coins", "amount": max(1, min(10, coins))}

    if _is_shop_target(target) and source_target == target:
        requested_match = _find_requested_item(source_target, requested_item)
        if hasattr(requested_match, "move_to"):
            return {"kind": "object", "item": requested_match}
        if isinstance(requested_match, str):
            return {"kind": "shop_entry", "entry": requested_match}
        items = _stealable_items(source_target)
        if items:
            return {"kind": "object", "item": items[0]}
        inventory = list(getattr(getattr(source_target, "db", None), "inventory", []) or [])
        if inventory:
            return {"kind": "shop_entry", "entry": str(inventory[0])}

    coins = int(getattr(getattr(source_target, "db", None), "coins", 0) or 0)
    if coins > 0 and source_target == target:
        return {"kind": "coins", "amount": max(1, min(10, coins))}
    requested_match = _find_requested_item(source_target, requested_item)
    if hasattr(requested_match, "move_to"):
        return {"kind": "object", "item": requested_match}
    items = _stealable_items(source_target)
    if items:
        return {"kind": "object", "item": items[0]}
    return None


def apply_steal_reward(actor, target, selection):
    if actor is None or target is None or not selection:
        return None

    kind = str(selection.get("kind", "") or "")
    if kind == "coins":
        amount = max(0, int(selection.get("amount", 0) or 0))
        available = max(0, int(getattr(getattr(target, "db", None), "coins", 0) or 0))
        amount = min(amount, available)
        if amount <= 0:
            return None
        target.db.coins = available - amount
        actor.db.coins = int(getattr(getattr(actor, "db", None), "coins", 0) or 0) + amount
        return {"kind": "coins", "amount": amount, "summary": f"{amount} coins"}

    if kind == "object":
        item = selection.get("item")
        if item is None or not hasattr(item, "move_to"):
            return None
        if not item.move_to(actor, quiet=True, move_type="steal"):
            return None
        return {"kind": "object", "item": item, "summary": str(getattr(item, "key", "item") or "item")}

    if kind == "shop_entry":
        entry = str(selection.get("entry", "") or "").strip()
        if not entry:
            return None
        inventory = list(getattr(getattr(target, "db", None), "inventory", []) or [])
        if entry not in inventory:
            return None
        inventory.remove(entry)
        target.db.inventory = inventory
        from evennia.utils.create import create_object

        stolen_item = create_object("typeclasses.objects.Object", key=entry, location=actor, home=actor.location or actor)
        stolen_item.db.stealable = True
        return {"kind": "object", "item": stolen_item, "summary": entry}

    return None


def trigger_justice_response(actor, target, action_type, severity):
    from world.systems.justice import trigger_justice_response as justice_trigger_justice_response

    return justice_trigger_justice_response(actor, target, action_type, severity)


def trigger_guard_reaction(actor, severity=1):
    from world.systems.justice import evaluate_guard_response

    response = evaluate_guard_response(actor)
    if actor is not None:
        actor.db.guard_reaction_stub = {
            "severity": int(severity or 0),
            "timestamp": time.time(),
            "wanted_level": int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0),
            "eligible": bool(response.get("should_respond", False)),
        }
        return dict(actor.db.guard_reaction_stub or {})
    return {}


def adjust_thief_reputation(actor, delta):
    _ensure_actor_state(actor)
    if actor is None:
        return 0
    actor.db.thief_reputation = int(getattr(actor.db, "thief_reputation", 0) or 0) + int(delta or 0)
    return int(actor.db.thief_reputation or 0)


def apply_reputation_influence(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return {}
    reputation = int(getattr(actor.db, "thief_reputation", 0) or 0)
    if reputation <= -5:
        contact_modifier = -2
    elif reputation >= 5:
        contact_modifier = 1
    else:
        contact_modifier = 0
    return {
        "contact_modifier": int(contact_modifier),
        "guard_attention_modifier": int(max(0, -reputation)),
        "shop_suspicion_modifier": int(max(0, -reputation // 2)),
    }


def get_contact_info(actor, name):
    _ensure_actor_state(actor)
    if actor is None:
        return {}
    contacts = dict(getattr(actor.db, "contacts", None) or {})
    return dict(contacts.get(str(name or "").strip().lower()) or {})


def attempt_entry(actor, target):
    from world.systems.burglary import attempt_entry as burglary_attempt_entry

    return burglary_attempt_entry(actor, target)


def _get_room_region(actor):
    room = getattr(actor, "location", None)
    if room and hasattr(room, "get_region"):
        try:
            return room.get_region() or "default_region"
        except Exception:
            return "default_region"
    return "default_region"


def get_wanted_tier(actor):
    from world.systems.justice import get_wanted_tier as justice_get_wanted_tier

    return justice_get_wanted_tier(actor)


def _append_justice_incident(actor, target, action_type, severity):
    _ensure_actor_state(actor)
    if actor is None:
        return []
    incidents = list(getattr(actor.db, "justice_incidents", None) or [])
    room = getattr(actor, "location", None)
    incidents.append(
        {
            "type": str(action_type or "theft"),
            "target": str(getattr(target, "key", "unknown") or "unknown"),
            "severity": int(severity or 0),
            "timestamp": time.time(),
            "room": str(getattr(room, "key", "unknown") or "unknown"),
        }
    )
    actor.db.justice_incidents = incidents[-20:]
    return actor.db.justice_incidents


def _action_severity_modifier(action_type):
    action = str(action_type or "theft").strip().lower()
    if action == "burglary":
        return 2
    if action == "trespass":
        return 1
    return 0


def decay_wanted(actor):
    from world.systems.justice import decay_wanted as justice_decay_wanted

    return justice_decay_wanted(actor)


def request_contact_service(actor, name, request_type="info"):
    _ensure_actor_state(actor)
    if actor is None:
        return {"ok": False, "message": "No contact answers.", "cost": 0, "quality": -99}
    decay_wanted(actor)
    info = get_contact_info(actor, name)
    if not info:
        return {"ok": False, "message": "You have not cultivated that contact yet.", "cost": 0, "quality": -99}

    request_type = str(request_type or "info").strip().lower() or "info"
    if request_type not in {"info", "heat"}:
        request_type = "info"

    disposition = int(info.get("disposition", 0) or 0)
    reputation_modifiers = apply_reputation_influence(actor)
    wanted_level = int(getattr(actor.db, "wanted_level", 0) or 0)
    quality = disposition + int(reputation_modifiers.get("contact_modifier", 0) or 0) - wanted_level
    cost = max(1, int(info.get("base_cost", 1) or 1) + max(0, wanted_level // 2) + max(0, -disposition // 2))

    if quality <= -3:
        return {
            "ok": False,
            "message": f"{name} keeps their distance. Your local heat is too obvious right now.",
            "cost": cost,
            "quality": quality,
            "service": request_type,
        }

    if request_type == "heat":
        if wanted_level >= GUARD_ATTENTION_THRESHOLD:
            message = f"{name} hisses that every bolt-hole is being watched tonight."
        elif wanted_level >= 3:
            message = f"{name} warns that the western routes are under harder eyes than usual."
        else:
            message = f"{name} murmurs that the local routes still look usable."
    else:
        if wanted_level >= GUARD_ATTENTION_THRESHOLD:
            message = f"{name} offers only scraps: the streets are too hot for clean work."
        elif quality >= 2:
            message = f"{name} whispers a useful rumor about a softer target and which blocks are alert."
        else:
            message = f"{name} shares a thin rumor and reminds you not to press your luck."

    return {
        "ok": True,
        "message": message,
        "cost": cost,
        "quality": quality,
        "service": request_type,
        "wanted_level": wanted_level,
    }


def increase_room_suspicion(room, amount=1):
    if room is None:
        return 0
    room.db.suspicion_level = int(getattr(room.db, "suspicion_level", 0) or 0) + int(amount or 0)
    return int(room.db.suspicion_level or 0)


def _mark_detected(actor):
    if actor is None:
        return
    awareness_state = dict(getattr(actor.db, "awareness_state", None) or {})
    awareness_state["last_detected_at"] = time.time()
    actor.db.awareness_state = awareness_state


def can_use_passage(actor, room):
    if actor is None or room is None or not bool(getattr(getattr(room, "db", None), "has_passage", False)):
        return False, "You find no hidden route here."
    decay_wanted(actor)
    detected_at = float((dict(getattr(getattr(actor, "db", None), "awareness_state", None) or {})).get("last_detected_at", 0) or 0)
    if detected_at + 10.0 > time.time():
        return False, "You are too exposed to risk a hidden route right now."
    if bool(getattr(getattr(actor, "db", None), "guard_attention", False)) or int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0) >= GUARD_ATTENTION_THRESHOLD:
        return False, "The passages are too hot for you right now."
    if int(getattr(getattr(room, "db", None), "suspicion_level", 0) or 0) >= 4:
        return False, "The room is under too much scrutiny for a clean escape."
    stealth_rank = _get_skill_rank(actor, "stealth")
    known = list(getattr(getattr(actor, "db", None), "known_passages", None) or [])
    profession = str(getattr(getattr(actor, "db", None), "profession", "") or "").strip().lower()
    if getattr(room, "id", None) in known or stealth_rank >= 20 or profession == "thief":
        return True, None
    return False, "You do not know how to work this passage."


def move_through_passage(actor, room):
    allowed, message = can_use_passage(actor, room)
    if not allowed:
        return False, message
    if hasattr(room, "get_passage_destinations"):
        destinations = room.get_passage_destinations()
    else:
        destinations = list(getattr(getattr(room, "db", None), "passage_links", None) or [])
    if not destinations:
        return False, "The passage seems to end in rubble."
    destination = destinations[0]
    actor.db.in_passage = True
    actor.move_to(destination, quiet=True, move_type="passage")
    actor.db.in_passage = False
    return True, destination


def _increase_suspicion(observer, actor, amount=10):
    if observer is None:
        return
    awareness_state = dict(getattr(getattr(observer, "db", None), "awareness_state", None) or {})
    awareness_state["suspicion_bonus"] = int(awareness_state.get("suspicion_bonus", 0) or 0) + int(amount or 0)
    actor_modifiers = dict(awareness_state.get("actor_modifiers") or {})
    actor_key = str(getattr(actor, "id", "unknown") or "unknown")
    actor_modifiers[actor_key] = int(actor_modifiers.get(actor_key, 0) or 0) + int(amount or 0)
    awareness_state["actor_modifiers"] = actor_modifiers
    observer.db.awareness_state = awareness_state

    _ensure_target_state(observer)
    theft_log = dict(getattr(observer.db, "theft_attempt_log", None) or {})
    recent_suspicion = dict(theft_log.get("recent_suspicion") or {})
    recent_suspicion[actor_key] = int(recent_suspicion.get(actor_key, 0) or 0) + int(amount or 0)
    theft_log["recent_suspicion"] = recent_suspicion
    observer.db.theft_attempt_log = theft_log

    if hasattr(observer, "adjust_suspicion_for"):
        observer.adjust_suspicion_for(actor, int(max(1, amount // 5)))


def resolve_theft_attempt(actor, target, context=None):
    context = dict(context or {})
    observer = context.get("awareness_target") or target
    source_target = context.get("container") or target
    room = context.get("room") or getattr(actor, "location", None)
    if _is_shop_target(observer):
        decay_shop_heat(observer)

    target_key = _get_target_key(source_target)
    theft_total = get_theft_skill_total(actor, observer, context={**context, "target_key": target_key, "container": source_target if source_target != observer else None})
    contest = awareness.resolve_awareness_contest(
        actor,
        observer,
        "steal",
        context={**context, "actor_total": theft_total, "room": room},
    )
    margin = int(contest.get("margin", 0) or 0)
    success = bool(contest.get("success", False))
    caught = not success and margin <= -20
    selection_context = dict(context)
    if source_target != observer:
        selection_context["container"] = source_target
    selection = select_stolen_item(actor, observer, context=selection_context) if success else None

    if success and selection is None:
        success = False
        caught = False

    theft_difficulty = max(10, int(contest.get("observer_total", 0) or 0))
    if success:
        theft_outcome = "success"
    elif caught:
        theft_outcome = "failure"
    else:
        theft_outcome = "partial"
    award_exp_skill(actor, "thievery", theft_difficulty, success=success, outcome=theft_outcome, event_key="theft")

    record_theft_attempt(actor, target_key, success)
    if _is_shop_target(observer):
        add_shop_heat(observer, amount=1)

    adjust_thief_reputation(actor, 1 if success else 0)
    if room is not None:
        increase_room_suspicion(room, amount=1)

    if _is_player_target(observer) and (success or caught):
        actor.db.pvp_open_until = time.time() + PVP_OPEN_SECONDS

    if caught:
        _increase_suspicion(observer, actor, amount=10)
        _mark_detected(actor)
        adjust_thief_reputation(actor, -2)
        if _is_shop_target(observer):
            add_shop_heat(observer, amount=1)
        if room is not None and not (hasattr(room, "is_lawless") and room.is_lawless()):
            trigger_justice_response(actor, observer, action_type="theft", severity=2 if _is_shop_target(observer) else 1)

    payload = {
        "success": success,
        "caught": caught,
        "actor_total": int(contest.get("actor_total", 0) or 0),
        "observer_total": int(contest.get("observer_total", 0) or 0),
        "margin": margin,
        "item": selection,
        "target_key": target_key,
        "repeat_penalty": get_repeat_target_penalty(actor, target_key),
        "shop_heat": get_shop_heat(observer) if _is_shop_target(observer) else 0,
        "thief_reputation": int(getattr(getattr(actor, "db", None), "thief_reputation", 0) or 0),
        "wanted_level": int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0),
    }
    logger.log_info(
        f"[THEFT] actor={actor} target={target} success={success} caught={caught} margin={margin} repeat_penalty={payload['repeat_penalty']} shop_heat={payload['shop_heat']}"
    )
    return payload