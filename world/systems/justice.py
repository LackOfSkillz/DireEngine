import time


WANTED_DECAY_BUCKET = 600.0
CRIME_DECAY_BUCKET = 3600.0
LAW_REPUTATION_DECAY_BUCKET = 3600.0
ARREST_ELIGIBLE_THRESHOLD = 5

MINOR_FINE = 50
MODERATE_FINE = 200
SEVERE_FINE = 500
MINOR_PILLORY_SECONDS = 180
MODERATE_JAIL_SECONDS = 300
SEVERE_JAIL_SECONDS = 480

MOVEMENT_COMMANDS = {
    "go",
    "north",
    "south",
    "east",
    "west",
    "northeast",
    "northwest",
    "southeast",
    "southwest",
    "up",
    "down",
    "out",
    "leave",
    "n",
    "s",
    "e",
    "w",
    "ne",
    "nw",
    "se",
    "sw",
    "u",
    "d",
}

STEALTH_COMMANDS = {"hide", "sneak", "stalk", "passage", "blend", "unhide", "khri"}
THEFT_COMMANDS = {"steal", "burgle", "mark", "slip"}
COMBAT_COMMANDS = {
    "advance",
    "ambush",
    "attack",
    "backstab",
    "blindside",
    "disengage",
    "fire",
    "load",
    "pounce",
    "retreat",
    "snipe",
    "target",
    "throw",
}

DETENTION_BLOCKED_COMMANDS = MOVEMENT_COMMANDS | STEALTH_COMMANDS | THEFT_COMMANDS | COMBAT_COMMANDS

FLEE_TRIGGER_COMMANDS = {
    "burgle",
    "steal",
    "passage",
    "go",
    "north",
    "south",
    "east",
    "west",
    "n",
    "s",
    "e",
    "w",
    "ne",
    "nw",
    "se",
    "sw",
    "up",
    "down",
    "u",
    "d",
}


def _ensure_actor_state(actor):
    if actor is None:
        return
    defaults = {
        "wanted_level": 0,
        "last_wanted_update": 0,
        "guard_attention": False,
        "detained": False,
        "detained_until": 0,
        "last_arrest_time": 0,
        "last_surrender_time": 0,
        "justice_hold_reason": None,
        "justice_flee_flag": False,
        "outstanding_fine": 0,
        "fine_due": 0,
        "crime_flag": False,
        "warrants": {},
        "active_guard_id": None,
        "pending_arrest": False,
        "justice_warning_level": 0,
        "justice_confrontation_started_at": 0,
        "justice_incidents": [],
        "confiscated_items": [],
        "confiscation_location": None,
        "justice_debt": 0,
        "crime_count": 0,
        "last_crime_time": 0,
        "last_crime_decay_time": 0,
        "law_reputation": 0,
        "last_law_reputation_decay_time": 0,
        "in_pillory": False,
        "pillory_end_time": 0,
        "in_jail": False,
        "jail_end_time": 0,
        "in_stocks": False,
        "jail_timer": 0,
    }
    for key, value in defaults.items():
        if getattr(getattr(actor, "db", None), key, None) is None:
            setattr(actor.db, key, value)


def _find_room_by_key(*keys):
    try:
        from evennia.utils.search import search_object
    except Exception:
        return None

    for key in [str(entry or "").strip() for entry in keys if str(entry or "").strip()]:
        matches = list(search_object(key, exact=True))
        for match in matches:
            if getattr(match, "destination", None):
                continue
            return match
    return None


def _find_room_by_id(room_id):
    try:
        room_id = int(room_id or 0)
    except (TypeError, ValueError):
        return None
    if room_id <= 0:
        return None
    try:
        from evennia.utils.search import search_object
    except Exception:
        return None
    results = search_object(f"#{room_id}")
    for result in list(results or []):
        if getattr(result, "destination", None):
            continue
        return result
    return None


def _find_room_by_flag(flag_name):
    try:
        from evennia.objects.models import ObjectDB
    except Exception:
        return None

    for room in ObjectDB.objects.filter(db_typeclass_path="typeclasses.rooms.Room"):
        if bool(getattr(getattr(room, "db", None), flag_name, False)):
            return room
    return None


def _get_pillory_room(actor=None):
    override_room = _find_room_by_id(getattr(getattr(actor, "db", None), "justice_pillory_room_id", 0) if actor is not None else 0)
    if override_room:
        return override_room
    room = getattr(actor, "location", None) if actor is not None else None
    if room and bool(getattr(getattr(room, "db", None), "pillory", False)):
        return room
    return _find_room_by_flag("pillory") or _find_room_by_key("Pillory Square", "Town Square")


def _get_jail_room(actor=None):
    override_room = _find_room_by_id(getattr(getattr(actor, "db", None), "justice_jail_room_id", 0) if actor is not None else 0)
    if override_room:
        return override_room
    room = getattr(actor, "location", None) if actor is not None else None
    if room and bool(getattr(getattr(room, "db", None), "is_jail", False)):
        return room
    return _find_room_by_flag("is_jail") or _find_room_by_key("Town Jail")


def _get_guardhouse_exterior(actor=None):
    override_room = _find_room_by_id(getattr(getattr(actor, "db", None), "justice_guardhouse_exterior_room_id", 0) if actor is not None else 0)
    if override_room:
        return override_room
    room = getattr(actor, "location", None) if actor is not None else None
    if room and bool(getattr(getattr(room, "db", None), "guardhouse_exterior", False)):
        return room
    return _find_room_by_flag("guardhouse_exterior") or _find_room_by_key("Guardhouse Exterior")


def _get_guardhouse_room(actor=None):
    override_room = _find_room_by_id(getattr(getattr(actor, "db", None), "justice_guardhouse_room_id", 0) if actor is not None else 0)
    if override_room:
        return override_room
    confiscation_room = _find_room_by_id(getattr(getattr(actor, "db", None), "confiscation_location", 0) if actor is not None else 0)
    if confiscation_room:
        return confiscation_room
    room = getattr(actor, "location", None) if actor is not None else None
    if room and bool(getattr(getattr(room, "db", None), "is_guardhouse", False)):
        return room
    return _find_room_by_flag("is_guardhouse") or _find_room_by_key("Guardhouse Interior", "Guardhouse")


def _get_evidence_locker(actor=None):
    guardhouse_room = _get_guardhouse_room(actor=actor)
    if guardhouse_room is None:
        return None
    for obj in list(getattr(guardhouse_room, "contents", []) or []):
        if bool(getattr(getattr(obj, "db", None), "is_evidence_locker", False)):
            return obj
    return None


def _get_release_room(actor=None):
    override_room = _find_room_by_id(getattr(getattr(actor, "db", None), "justice_release_room_id", 0) if actor is not None else 0)
    if override_room:
        return override_room
    room = getattr(actor, "location", None) if actor is not None else None
    if room and bool(getattr(getattr(room, "db", None), "high_traffic", False)):
        return room
    return _find_room_by_key("Town Green", "Town Green NE", "Town Square") or _find_room_by_flag("high_traffic")


def _is_lawful_room(room):
    if room is None:
        return False
    if hasattr(room, "is_lawless"):
        try:
            return not bool(room.is_lawless())
        except Exception:
            return True
    explicit = getattr(getattr(room, "db", None), "is_lawful", None)
    if explicit is not None:
        return bool(explicit)
    return True


def _get_room_region(actor):
    room = getattr(actor, "location", None)
    if room and hasattr(room, "get_region"):
        try:
            return room.get_region() or "default_region"
        except Exception:
            return "default_region"
    return "default_region"


def _action_severity_modifier(action_type):
    action = str(action_type or "theft").strip().lower()
    if action == "burglary":
        return 2
    if action == "trespass":
        return 1
    return 0


def _latest_incident(actor):
    incidents = list(getattr(getattr(actor, "db", None), "justice_incidents", None) or [])
    return dict(incidents[-1] or {}) if incidents else {}


def _classify_arrest_outcome(actor):
    _ensure_actor_state(actor)
    incident = _latest_incident(actor)
    latest_severity = int(incident.get("severity", 0) or 0)
    latest_type = str(incident.get("type", "") or "").strip().lower()
    wanted_level = int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0)
    crime_count = int(getattr(getattr(actor, "db", None), "crime_count", 0) or 0)
    flee_flag = bool(getattr(getattr(actor, "db", None), "justice_flee_flag", False))

    severity = "minor"
    if latest_type == "burglary" or latest_severity >= 3:
        severity = "severe"
    elif latest_severity >= 2 or wanted_level >= 7:
        severity = "moderate"

    if flee_flag and severity == "minor":
        severity = "moderate"
    if crime_count >= 3 and severity == "minor":
        severity = "moderate"
    if crime_count >= 5 and severity != "severe":
        severity = "severe"
    return severity


def get_wanted_tier(actor):
    _ensure_actor_state(actor)
    wanted = int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0)
    if wanted <= 0:
        return "clear"
    if wanted <= 2:
        return "watched"
    if wanted <= 4:
        return "wanted"
    return "arrest_eligible"


def record_justice_incident(actor, incident):
    _ensure_actor_state(actor)
    if actor is None:
        return []
    incidents = list(getattr(actor.db, "justice_incidents", None) or [])
    incidents.append(dict(incident or {}))
    actor.db.justice_incidents = incidents[-20:]
    return list(actor.db.justice_incidents or [])


def decay_wanted(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return 0
    wanted_level = int(getattr(actor.db, "wanted_level", 0) or 0)
    last_updated = float(getattr(actor.db, "last_wanted_update", 0) or 0)
    if wanted_level <= 0 or last_updated <= 0:
        return wanted_level
    elapsed = max(0.0, time.time() - last_updated)
    decay_steps = int(elapsed // WANTED_DECAY_BUCKET)
    if decay_steps <= 0:
        return wanted_level
    actor.db.wanted_level = max(0, wanted_level - decay_steps)
    actor.db.last_wanted_update = time.time()
    if int(actor.db.wanted_level or 0) < ARREST_ELIGIBLE_THRESHOLD:
        actor.db.guard_attention = False
        clear_active_guard_engagement(actor, clear_attention=True)
    return int(actor.db.wanted_level or 0)


def decay_crime_count(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return 0
    crime_count = int(getattr(actor.db, "crime_count", 0) or 0)
    last_crime_time = float(getattr(actor.db, "last_crime_time", 0) or 0)
    last_decay_time = float(getattr(actor.db, "last_crime_decay_time", 0) or 0)
    if crime_count <= 0 or last_crime_time <= 0:
        return crime_count
    reference_time = last_decay_time if last_decay_time > 0 else last_crime_time
    elapsed = max(0.0, time.time() - reference_time)
    decay_steps = int(elapsed // CRIME_DECAY_BUCKET)
    if decay_steps <= 0:
        return crime_count
    actor.db.crime_count = max(0, crime_count - decay_steps)
    actor.db.last_crime_decay_time = reference_time + (decay_steps * CRIME_DECAY_BUCKET) if int(actor.db.crime_count or 0) > 0 else 0
    return int(actor.db.crime_count or 0)


def decay_law_reputation(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return 0
    law_reputation = int(getattr(actor.db, "law_reputation", 0) or 0)
    last_crime_time = float(getattr(actor.db, "last_crime_time", 0) or 0)
    last_decay_time = float(getattr(actor.db, "last_law_reputation_decay_time", 0) or 0)
    if law_reputation == 0 or last_crime_time <= 0:
        return law_reputation
    reference_time = last_decay_time if last_decay_time > 0 else last_crime_time
    elapsed = max(0.0, time.time() - reference_time)
    decay_steps = int(elapsed // LAW_REPUTATION_DECAY_BUCKET)
    if decay_steps <= 0:
        return law_reputation
    if law_reputation < 0:
        actor.db.law_reputation = min(0, law_reputation + decay_steps)
    else:
        actor.db.law_reputation = max(0, law_reputation - decay_steps)
    actor.db.last_law_reputation_decay_time = reference_time + (decay_steps * LAW_REPUTATION_DECAY_BUCKET) if int(actor.db.law_reputation or 0) != 0 else 0
    return int(actor.db.law_reputation or 0)


def _get_law_reputation_penalty(crime_type, severity):
    action = str(crime_type or "theft").strip().lower()
    penalty = max(1, int(severity or 0))
    if action == "burglary":
        return penalty + 1
    if action == "trespass":
        return max(1, penalty)
    return penalty


def apply_crime_if_caught(actor, crime_type, was_caught, *, severity=1):
    _ensure_actor_state(actor)
    # CRITICAL RULE:
    # Crime is only applied if the actor is CAUGHT, not if the action fails.
    # Failure without detection must NOT increment crime_count.
    if actor is None or not bool(was_caught):
        return {"applied": False, "crime_count": int(getattr(getattr(actor, "db", None), "crime_count", 0) or 0) if actor else 0}

    now = time.time()
    decay_crime_count(actor)
    decay_law_reputation(actor)
    actor.db.crime_count = int(getattr(actor.db, "crime_count", 0) or 0) + 1
    actor.db.last_crime_time = now
    actor.db.last_crime_decay_time = now
    actor.db.law_reputation = int(getattr(actor.db, "law_reputation", 0) or 0) - _get_law_reputation_penalty(crime_type, severity)
    actor.db.last_law_reputation_decay_time = now
    return {
        "applied": True,
        "crime_count": int(getattr(actor.db, "crime_count", 0) or 0),
        "law_reputation": int(getattr(actor.db, "law_reputation", 0) or 0),
    }


def evaluate_guard_response(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return {"should_respond": False, "tier": "clear", "reason": "no actor"}
    if is_detained(actor):
        return {"should_respond": False, "tier": get_wanted_tier(actor), "reason": "already detained"}
    room = getattr(actor, "location", None)
    if not _is_lawful_room(room):
        return {"should_respond": False, "tier": get_wanted_tier(actor), "reason": "lawless area"}
    tier = get_wanted_tier(actor)
    if tier != "arrest_eligible":
        return {"should_respond": False, "tier": tier, "reason": "wanted level below arrest threshold"}
    return {"should_respond": True, "tier": tier, "reason": "lawful area arrest threshold met"}


def can_be_arrested(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return False, "No one is there to arrest."
    if is_detained(actor):
        return False, "You are already detained."
    if get_wanted_tier(actor) != "arrest_eligible":
        return False, "Your wanted level is not high enough for arrest."
    room = getattr(actor, "location", None)
    if not _is_lawful_room(room):
        return False, "No lawful authority can pin you here."
    if bool(getattr(getattr(actor, "db", None), "justice_exempt", False)):
        return False, "You are exempt from local justice response."
    return True, None


def begin_arrest(actor, source=None, quiet=False):
    _ensure_actor_state(actor)
    allowed, reason = can_be_arrested(actor)
    if not allowed:
        return {"started": False, "reason": str(reason or "arrest unavailable")}
    actor.db.guard_attention = True
    actor.db.pending_arrest = True
    actor.db.justice_hold_reason = str(source or "local authorities")
    if not quiet:
        actor.msg("Authorities close in to detain you. You may SURRENDER now or risk a harder arrest.")
        room = getattr(actor, "location", None)
        if room and hasattr(room, "msg_contents"):
            room.msg_contents(f"The local authorities move to detain {actor.key}.", exclude=[actor])
    return {"started": True, "reason": "arrest initiated", "tier": get_wanted_tier(actor)}


def calculate_justice_penalty(actor, *, voluntary=False):
    _ensure_actor_state(actor)
    decay_crime_count(actor)
    decay_law_reputation(actor)
    wanted_level = int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0)
    incidents = list(getattr(getattr(actor, "db", None), "justice_incidents", None) or [])
    incident_count = len(incidents)
    crime_count = int(getattr(getattr(actor, "db", None), "crime_count", 0) or 0)
    burglary_count = sum(1 for incident in incidents if str((incident or {}).get("type", "")).lower() == "burglary")
    flee_modifier = 1 if bool(getattr(getattr(actor, "db", None), "justice_flee_flag", False)) else 0
    severity = _classify_arrest_outcome(actor)

    if severity == "minor":
        base_fine = MINOR_FINE
        base_detain_seconds = MINOR_PILLORY_SECONDS
        wanted_reduction = max(2, min(wanted_level, 2))
        reputation_loss = 1
        outcome = "pillory"
        confiscate = False
    elif severity == "moderate":
        base_fine = MODERATE_FINE
        base_detain_seconds = MODERATE_JAIL_SECONDS
        wanted_reduction = max(2, min(wanted_level, 3))
        reputation_loss = 2
        outcome = "jail"
        confiscate = False
    else:
        base_fine = SEVERE_FINE
        base_detain_seconds = SEVERE_JAIL_SECONDS
        wanted_reduction = max(3, min(wanted_level, 4))
        reputation_loss = 3 + max(0, burglary_count)
        outcome = "jail"
        confiscate = True

    fine = int(round(base_fine * (1 + (crime_count * 0.5))))
    detain_seconds = int(round(base_detain_seconds * (1 + (crime_count * 0.3))))
    fine += flee_modifier * 50
    detain_seconds += flee_modifier * 60
    detain_seconds += max(0, incident_count - 1) * 10

    if voluntary:
        fine = max(0, int(fine * 0.75))
        detain_seconds = max(60, int(detain_seconds * 0.75))
        wanted_reduction += 1
        reputation_loss = max(1, reputation_loss - 1)

    return {
        "fine": int(fine),
        "wanted_reduction": int(max(1, wanted_reduction)),
        "detain_seconds": int(max(30, detain_seconds)),
        "reputation_loss": int(max(1, reputation_loss)),
        "severity": severity,
        "outcome": outcome,
        "confiscate": bool(confiscate),
    }


def confiscate_items(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return 0
    guardhouse_room = _get_guardhouse_room(actor=actor)
    evidence_locker = _get_evidence_locker(actor=actor)
    item_ids = []
    for item in list(getattr(actor, "contents", []) or []):
        if getattr(item, "destination", None):
            continue
        if evidence_locker is not None:
            item.move_to(evidence_locker, quiet=True, move_type="justice_confiscation")
        elif guardhouse_room is not None:
            item.move_to(guardhouse_room, quiet=True, move_type="justice_confiscation")
        else:
            item.location = None
        item.db.justice_confiscated_owner_id = int(getattr(actor, "id", 0) or 0)
        item_ids.append(int(getattr(item, "id", 0) or 0))
    actor.db.confiscated_items = item_ids
    actor.db.confiscation_location = int(getattr(guardhouse_room, "id", 0) or 0) or None
    if hasattr(actor, "update_encumbrance_state"):
        actor.update_encumbrance_state()
    actor.msg("The guard confiscates your belongings and sends them to the guardhouse evidence locker.")
    room = getattr(actor, "location", None)
    if room and hasattr(room, "msg_contents"):
        room.msg_contents(f"The guard takes {actor.key}'s belongings into custody for the guardhouse.", exclude=[actor])
    return len(item_ids)


def retrieve_confiscated_items(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return {"ok": False, "reason": "no actor"}
    confiscated_items = list(getattr(actor.db, "confiscated_items", None) or [])
    if not confiscated_items:
        return {"ok": False, "reason": "You have no confiscated items."}
    guardhouse_room = _get_guardhouse_room(actor=actor)
    current_room = getattr(actor, "location", None)
    if current_room is None or not bool(getattr(getattr(current_room, "db", None), "is_guardhouse", False)):
        return {"ok": False, "reason": "You must go to the guardhouse to reclaim your belongings."}
    if guardhouse_room is not None and int(getattr(current_room, "id", 0) or 0) != int(getattr(guardhouse_room, "id", 0) or 0):
        return {"ok": False, "reason": "You must go to the guardhouse to reclaim your belongings."}
    if int(getattr(actor.db, "justice_debt", 0) or 0) > 0:
        return {"ok": False, "reason": "You must clear your debt before reclaiming your belongings."}

    try:
        from evennia.utils.search import search_object
    except Exception:
        return {"ok": False, "reason": "Item lookup unavailable."}

    restored = 0
    for item_id in confiscated_items:
        results = search_object(f"#{int(item_id)}")
        if not results:
            continue
        item = results[0]
        item.db.justice_confiscated_owner_id = None
        if item.move_to(actor, quiet=True):
            restored += 1
    if restored <= 0:
        return {"ok": False, "reason": "You have no confiscated items."}
    actor.db.confiscated_items = []
    actor.db.confiscation_location = None
    if hasattr(actor, "update_encumbrance_state"):
        actor.update_encumbrance_state()
    actor.msg("You open the evidence locker and retrieve your belongings.")
    return {"ok": True, "restored": restored}


def pay_fine(actor, amount=None):
    _ensure_actor_state(actor)
    if actor is None:
        return {"ok": False, "reason": "no actor"}
    debt = int(getattr(actor.db, "justice_debt", 0) or 0)
    if debt <= 0:
        return {"ok": False, "reason": "You have no outstanding justice debt."}
    if amount is None:
        amount = debt
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "Payment amount must be a whole number."}
    if amount <= 0:
        return {"ok": False, "reason": "Payment amount must be greater than zero."}
    if amount > debt:
        return {"ok": False, "reason": "You cannot pay more than you owe."}
    coins = int(getattr(actor.db, "coins", 0) or 0)
    if coins < amount:
        return {"ok": False, "reason": "You do not have enough coin."}

    remaining = debt - amount
    actor.db.coins = coins - amount
    actor.db.justice_debt = remaining
    actor.db.outstanding_fine = remaining
    actor.db.fine_due = remaining
    if remaining <= 0:
        actor.db.collateral_locked = False
        actor.db.fine_due_timestamp = None
    return {"ok": True, "paid": amount, "remaining": remaining}


def place_in_pillory(actor, duration=MINOR_PILLORY_SECONDS):
    _ensure_actor_state(actor)
    if actor is None:
        return None
    room = _get_pillory_room(actor=actor)
    if room and getattr(actor, "location", None) != room:
        actor.move_to(room, quiet=True, move_type="justice_pillory")
    ends_at = time.time() + int(max(30, duration or MINOR_PILLORY_SECONDS))
    actor.db.detained = True
    actor.db.detained_until = ends_at
    actor.db.in_pillory = True
    actor.db.pillory_end_time = ends_at
    actor.db.in_jail = False
    actor.db.jail_end_time = 0
    actor.db.in_stocks = False
    actor.msg("You are locked into the pillory. You cannot move.")
    if getattr(actor, "location", None) and hasattr(actor.location, "msg_contents"):
        actor.location.msg_contents(f"{actor.key} is locked in the pillory.", exclude=[actor])
    return room


def release_from_pillory(actor, *, notify=False):
    _ensure_actor_state(actor)
    if actor is None:
        return {"released": False, "reason": "no actor"}
    actor.db.in_pillory = False
    actor.db.pillory_end_time = 0
    actor.db.detained = False
    actor.db.detained_until = 0
    actor.db.justice_hold_reason = None
    destination = _get_release_room(actor=actor)
    if destination and getattr(actor, "location", None) != destination:
        actor.move_to(destination, quiet=True, move_type="pillory_release")
    if notify:
        actor.msg("The pillory unlocks and you are released.")
    return {"released": True}


def send_to_jail(actor, duration):
    _ensure_actor_state(actor)
    if actor is None:
        return None
    room = _get_jail_room(actor=actor)
    if room and getattr(actor, "location", None) != room:
        actor.move_to(room, quiet=True, move_type="justice_jail")
    ends_at = time.time() + int(max(60, duration or MODERATE_JAIL_SECONDS))
    actor.db.detained = True
    actor.db.detained_until = ends_at
    actor.db.in_jail = True
    actor.db.jail_end_time = ends_at
    actor.db.in_pillory = False
    actor.db.pillory_end_time = 0
    actor.db.in_stocks = False
    actor.db.jail_timer = int(max(60, duration or MODERATE_JAIL_SECONDS))
    actor.msg("The authorities lock you in a jail cell.")
    return room


def release_from_jail(actor, *, notify=False):
    _ensure_actor_state(actor)
    if actor is None:
        return {"released": False, "reason": "no actor"}
    actor.db.in_jail = False
    actor.db.jail_end_time = 0
    actor.db.jail_timer = 0
    actor.db.detained = False
    actor.db.detained_until = 0
    actor.db.justice_hold_reason = None
    destination = _get_guardhouse_exterior(actor=actor) or _get_release_room(actor=actor)
    if destination and getattr(actor, "location", None) != destination:
        actor.move_to(destination, quiet=True, move_type="jail_release")
    if notify:
        actor.msg("You are released from custody.")
        if list(getattr(actor.db, "confiscated_items", None) or []):
            actor.msg("You recall your belongings are held at the guardhouse.")
    return {"released": True}


def complete_arrest(actor, *, source=None, voluntary=False):
    _ensure_actor_state(actor)
    if actor is None:
        return {"completed": False, "reason": "no actor"}
    decay_crime_count(actor)
    decay_law_reputation(actor)
    penalty = calculate_justice_penalty(actor, voluntary=voluntary)
    now = time.time()
    actor.db.detained = True
    actor.db.detained_until = now + int(penalty.get("detain_seconds", 0) or 0)
    actor.db.last_arrest_time = now
    actor.db.guard_attention = False
    actor.db.justice_hold_reason = str(source or ("voluntary surrender" if voluntary else "arrested by authorities"))
    actor.db.outstanding_fine = int(getattr(actor.db, "outstanding_fine", 0) or 0) + int(penalty.get("fine", 0) or 0)
    actor.db.fine_due = int(getattr(actor.db, "fine_due", 0) or 0) + int(penalty.get("fine", 0) or 0)
    actor.db.justice_debt = int(getattr(actor.db, "justice_debt", 0) or 0) + int(penalty.get("fine", 0) or 0)
    actor.db.collateral_locked = bool(penalty.get("confiscate", False))
    actor.db.fine_due_timestamp = now if int(getattr(actor.db, "justice_debt", 0) or 0) > 0 else None
    actor.db.wanted_level = max(0, int(getattr(actor.db, "wanted_level", 0) or 0) - int(penalty.get("wanted_reduction", 0) or 0))
    actor.db.last_wanted_update = now
    if int(actor.db.wanted_level or 0) <= 0:
        actor.db.crime_flag = False

    region = _get_room_region(actor)
    warrants = dict(getattr(actor.db, "warrants", None) or {})
    warrant = dict(warrants.get(region, {}) or {})
    warrant["severity"] = max(0, int(warrant.get("severity", 0) or 0) - int(penalty.get("wanted_reduction", 0) or 0))
    warrant["updated_at"] = now
    if warrant.get("severity", 0) <= 0:
        warrants.pop(region, None)
    else:
        warrants[region] = warrant
    actor.db.warrants = warrants

    from world.systems.theft import adjust_thief_reputation

    adjust_thief_reputation(actor, -int(penalty.get("reputation_loss", 0) or 0))

    confiscated_count = 0
    if str(penalty.get("outcome", "jail") or "jail") == "pillory":
        place_in_pillory(actor, duration=int(penalty.get("detain_seconds", 0) or MINOR_PILLORY_SECONDS))
    else:
        if bool(penalty.get("confiscate", False)):
            confiscated_count = confiscate_items(actor)
        else:
            actor.db.confiscation_location = getattr(actor.db, "confiscation_location", None)
        send_to_jail(actor, duration=int(penalty.get("detain_seconds", 0) or MODERATE_JAIL_SECONDS))

    clear_active_guard_engagement(actor, clear_flee=True, clear_attention=True)
    if voluntary:
        actor.db.last_surrender_time = now
        actor.msg("You submit to the authorities and accept the sentence without resistance.")
    else:
        actor.msg("The authorities overpower you and drag you into custody.")
    return {
        "completed": True,
        "penalty": penalty,
        "wanted_after": int(getattr(actor.db, "wanted_level", 0) or 0),
        "detained_until": float(getattr(actor.db, "detained_until", 0) or 0),
        "outstanding_fine": int(getattr(actor.db, "outstanding_fine", 0) or 0),
        "outcome": str(penalty.get("outcome", "jail") or "jail"),
        "confiscated_count": confiscated_count,
        "crime_count": int(getattr(actor.db, "crime_count", 0) or 0),
        "law_reputation": int(getattr(actor.db, "law_reputation", 0) or 0),
    }


def process_surrender(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return {"ok": False, "reason": "no actor"}
    if is_detained(actor):
        return {"ok": False, "reason": "already detained"}
    if (
        not bool(getattr(actor.db, "guard_attention", False))
        and not bool(getattr(actor.db, "pending_arrest", False))
        and int(getattr(actor.db, "active_guard_id", 0) or 0) <= 0
        and get_wanted_tier(actor) != "arrest_eligible"
    ):
        return {"ok": False, "reason": "no active justice pressure"}
    actor.db.last_surrender_time = time.time()
    actor.db.justice_flee_flag = False
    guard_name = _get_active_guard_name(actor)
    begin_arrest(actor, source="voluntary surrender", quiet=True)
    result = complete_arrest(actor, source="voluntary surrender", voluntary=True)
    return {"ok": True, **result, "surrendered": True, "guard_name": guard_name}


def is_detained(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return False
    now = time.time()
    detained_until = float(getattr(actor.db, "detained_until", 0) or 0)
    if bool(getattr(actor.db, "in_pillory", False)):
        pillory_end = float(getattr(actor.db, "pillory_end_time", 0) or 0)
        if (pillory_end > 0 and pillory_end <= now) or (detained_until > 0 and detained_until <= now):
            release_from_pillory(actor, notify=True)
            return False
        return True
    if bool(getattr(actor.db, "in_jail", False)):
        jail_end = float(getattr(actor.db, "jail_end_time", 0) or 0)
        if (jail_end > 0 and jail_end <= now) or (detained_until > 0 and detained_until <= now):
            release_from_jail(actor, notify=True)
            return False
        return True
    if not bool(getattr(actor.db, "detained", False)):
        return False
    if detained_until > 0 and detained_until <= now:
        release_from_detention(actor, notify=True)
        return False
    return True


def release_from_detention(actor, *, notify=False):
    _ensure_actor_state(actor)
    if actor is None:
        return {"released": False, "reason": "no actor"}
    if bool(getattr(actor.db, "in_pillory", False)):
        return release_from_pillory(actor, notify=notify)
    if bool(getattr(actor.db, "in_jail", False)):
        return release_from_jail(actor, notify=notify)
    actor.db.detained = False
    actor.db.detained_until = 0
    actor.db.justice_hold_reason = None
    actor.db.guard_attention = False
    actor.db.justice_flee_flag = False
    actor.db.in_stocks = False
    clear_active_guard_engagement(actor, clear_flee=True, clear_attention=True)
    if notify:
        actor.msg("The local authorities release you from detention.")
    return {"released": True}


def get_justice_command_block_message(actor, command_name):
    if actor is None:
        return None
    command_name = str(command_name or "").strip().lower()
    if not command_name or not is_detained(actor):
        return None
    if command_name not in DETENTION_BLOCKED_COMMANDS:
        return None
    if bool(getattr(actor.db, "in_pillory", False)):
        return "You are locked into the pillory. You cannot move."
    if bool(getattr(actor.db, "in_jail", False)):
        return "You are detained in jail and cannot do that."
    hold_reason = str(getattr(actor.db, "justice_hold_reason", None) or "pending sentence")
    return f"You are detained and cannot do that while held for {hold_reason}."


def should_block_detained_command(actor, command_name):
    return bool(get_justice_command_block_message(actor, command_name))


def note_flee_attempt(actor, command_name):
    _ensure_actor_state(actor)
    if actor is None:
        return {"flagged": False, "reason": "no actor"}
    command_name = str(command_name or "").strip().lower()
    if command_name not in FLEE_TRIGGER_COMMANDS:
        return {"flagged": False, "reason": "command not treated as flight"}
    if not bool(getattr(actor.db, "guard_attention", False)) and not bool(getattr(actor.db, "pending_arrest", False)) and int(getattr(actor.db, "active_guard_id", 0) or 0) <= 0:
        return {"flagged": False, "reason": "no active guard pressure"}
    actor.db.justice_flee_flag = True
    actor.db.pending_arrest = True
    actor.db.wanted_level = int(getattr(actor.db, "wanted_level", 0) or 0) + 1
    actor.db.last_wanted_update = time.time()
    actor.msg("Your refusal to submit will worsen the sentence when they catch you.")
    return {"flagged": True, "wanted_level": int(actor.db.wanted_level or 0)}


def trigger_justice_response(actor, target, action_type, severity, *, was_caught=True):
    _ensure_actor_state(actor)
    if actor is None:
        return {}
    if not bool(was_caught):
        return {
            "wanted_level": int(getattr(getattr(actor, "db", None), "wanted_level", 0) or 0),
            "tier": "clear",
            "wanted_tier": get_wanted_tier(actor),
            "guard_attention": bool(getattr(getattr(actor, "db", None), "guard_attention", False)),
            "incidents": list(getattr(getattr(actor, "db", None), "justice_incidents", None) or []),
            "response": {"should_respond": False, "reason": "uncaught crime does not create justice pressure"},
        }
    severity = max(0, int(severity or 0)) + _action_severity_modifier(action_type)
    tier = "minor"
    if severity >= 3:
        tier = "severe"
    elif severity >= 2:
        tier = "major"

    actor.db.wanted_stub = True
    actor.db.wanted_stub_meta = {
        "target": getattr(target, "key", None),
        "action_type": str(action_type or "theft"),
        "severity": severity,
        "tier": tier,
        "timestamp": time.time(),
    }
    actor.db.crime_flag = True
    actor.db.wanted_level = int(getattr(actor.db, "wanted_level", 0) or 0) + severity
    actor.db.last_wanted_update = time.time()
    crime_result = apply_crime_if_caught(actor, action_type, was_caught, severity=severity)

    room = getattr(actor, "location", None)
    record_justice_incident(
        actor,
        {
            "type": str(action_type or "theft"),
            "target": str(getattr(target, "key", "unknown") or "unknown"),
            "severity": severity,
            "timestamp": time.time(),
            "room": str(getattr(room, "key", "unknown") or "unknown"),
        },
    )

    region = _get_room_region(actor)
    warrants = dict(getattr(actor.db, "warrants", None) or {})
    warrant = dict(warrants.get(region, {}) or {})
    warrant["severity"] = int(warrant.get("severity", 0) or 0) + severity
    warrant["last_action"] = str(action_type or "theft")
    warrant["updated_at"] = time.time()
    warrants[region] = warrant
    actor.db.warrants = warrants

    response = evaluate_guard_response(actor)
    if response.get("should_respond"):
        actor.db.guard_attention = True
        actor.db.pending_arrest = True
    else:
        actor.db.guard_attention = bool(getattr(actor.db, "guard_attention", False) or get_wanted_tier(actor) == "arrest_eligible")

    return {
        "wanted_level": int(getattr(actor.db, "wanted_level", 0) or 0),
        "tier": tier,
        "wanted_tier": get_wanted_tier(actor),
        "guard_attention": bool(getattr(actor.db, "guard_attention", False)),
        "incidents": list(getattr(actor.db, "justice_incidents", None) or []),
        "crime_result": crime_result,
        "response": response,
    }


def clear_active_guard_engagement(actor, *, clear_flee=False, clear_attention=False):
    _ensure_actor_state(actor)
    if actor is None:
        return False
    try:
        from world.systems.guards import get_guard_by_id, release_guard_enforcement

        guard = get_guard_by_id(int(getattr(actor.db, "active_guard_id", 0) or 0))
        release_guard_enforcement(guard=guard, actor=actor, clear_actor=True, clear_attention=clear_attention, clear_flee=clear_flee)
        return True
    except Exception:
        actor.db.active_guard_id = None
        actor.db.pending_arrest = False
        actor.db.justice_warning_level = 0
        actor.db.justice_confrontation_started_at = 0
        if clear_flee:
            actor.db.justice_flee_flag = False
        if clear_attention:
            actor.db.guard_attention = False
        return True


def get_justice_status(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return {}
    decay_crime_count(actor)
    decay_law_reputation(actor)
    room = getattr(actor, "location", None)
    law = room.get_law_type() if room and hasattr(room, "get_law_type") else "standard"
    custody = "free"
    if bool(getattr(actor.db, "in_pillory", False)):
        custody = "pillory"
    elif bool(getattr(actor.db, "in_jail", False)):
        custody = "jail"
    elif bool(getattr(actor.db, "detained", False)):
        custody = "detained"
    return {
        "law": law,
        "wanted_tier": get_wanted_tier(actor),
        "wanted_level": int(getattr(actor.db, "wanted_level", 0) or 0),
        "warning_level": int(getattr(actor.db, "justice_warning_level", 0) or 0),
        "active_guard_id": int(getattr(actor.db, "active_guard_id", 0) or 0),
        "active_guard_name": _get_active_guard_name(actor),
        "pending_arrest": bool(getattr(actor.db, "pending_arrest", False)),
        "guard_attention": bool(getattr(actor.db, "guard_attention", False)),
        "detained": bool(is_detained(actor)),
        "detained_until": float(getattr(actor.db, "detained_until", 0) or 0),
        "outstanding_fine": int(getattr(actor.db, "outstanding_fine", 0) or 0),
        "justice_debt": int(getattr(actor.db, "justice_debt", 0) or 0),
        "confiscated_items": len(list(getattr(actor.db, "confiscated_items", None) or [])),
        "confiscation_location": int(getattr(actor.db, "confiscation_location", 0) or 0),
        "custody": custody,
        "crime_count": int(getattr(actor.db, "crime_count", 0) or 0),
        "law_reputation": int(getattr(actor.db, "law_reputation", 0) or 0),
        "warrants": dict(getattr(actor.db, "warrants", None) or {}),
    }


def can_lay_low(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return False, "No one is there to lie low."
    if is_detained(actor):
        return False, "You cannot lay low while detained."
    if bool(getattr(actor.db, "pending_arrest", False)) or int(getattr(actor.db, "active_guard_id", 0) or 0) > 0:
        return False, "You cannot lay low while a guard is actively confronting you."
    room = getattr(actor, "location", None)
    is_safe = room is not None and (
        not _is_lawful_room(room)
        or bool(getattr(getattr(room, "db", None), "safe", False))
        or bool(getattr(getattr(room, "db", None), "no_guard", False))
    )
    if not is_safe:
        return False, "You need safer ground before you can properly lay low."
    return True, None


def process_lay_low(actor):
    _ensure_actor_state(actor)
    allowed, reason = can_lay_low(actor)
    if not allowed:
        return {"ok": False, "reason": str(reason or "You cannot lay low right now.")}

    decay_wanted(actor)
    warrants = dict(getattr(actor.db, "warrants", None) or {})
    for region, data in list(warrants.items()):
        data["severity"] = max(0, int(data.get("severity", 0) or 0) - 1)
        if data["severity"] <= 0:
            warrants.pop(region, None)
        else:
            warrants[region] = data

    actor.db.warrants = warrants
    actor.db.last_known_region = None
    actor.db.wanted_level = max(0, int(getattr(actor.db, "wanted_level", 0) or 0) - 1)
    if int(getattr(actor.db, "wanted_level", 0) or 0) < ARREST_ELIGIBLE_THRESHOLD:
        actor.db.guard_attention = False
    if not warrants and not getattr(actor.db, "fine_due", 0) and not getattr(actor.db, "outstanding_fine", 0):
        actor.db.crime_flag = False
    clear_active_guard_engagement(actor, clear_attention=False)
    return {"ok": True, "wanted_level": int(getattr(actor.db, "wanted_level", 0) or 0), "warrants": warrants}


def process_justice_state_tick(actor):
    _ensure_actor_state(actor)
    if actor is None:
        return
    now = time.time()
    decay_crime_count(actor)
    decay_law_reputation(actor)
    if bool(getattr(actor.db, "in_pillory", False)):
        if float(getattr(actor.db, "pillory_end_time", 0) or 0) <= now:
            release_from_pillory(actor, notify=True)
            return
        next_msg_at = float(getattr(actor.ndb, "pillory_msg_at", 0) or 0)
        if now >= next_msg_at:
            actor.msg("The crowd watches you from beyond the pillory.")
            actor.ndb.pillory_msg_at = now + 60
    if bool(getattr(actor.db, "in_jail", False)):
        if float(getattr(actor.db, "jail_end_time", 0) or 0) <= now:
            release_from_jail(actor, notify=True)
            return
        actor.db.jail_timer = max(0, int(float(getattr(actor.db, "jail_end_time", 0) or 0) - now))


def _get_active_guard_name(actor):
    guard_id = int(getattr(getattr(actor, "db", None), "active_guard_id", 0) or 0)
    if guard_id <= 0:
        return None
    try:
        from world.systems.guards import get_guard_by_id

        guard = get_guard_by_id(guard_id)
        return str(getattr(guard, "key", "") or "") or None
    except Exception:
        return None
