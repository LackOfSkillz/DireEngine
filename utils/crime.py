import random
import time

from evennia import search_object
from evennia.utils.create import create_object

from world.law import LAW_NONE


GUARD_STORAGE_KEY = "Guard Post"
JUDGE_ROOM_KEY = "Town Hall Chamber"
STOCKS_ROOM_KEY = "Town Square"
STOCKS_EXIT_KEY = "Town Square"


def _resolve_room(key):
    if not key:
        return None
    result = search_object(key)
    return result[0] if result else None


def _is_guard(obj):
    role = str(getattr(getattr(obj, "db", None), "role", "") or "").lower()
    if "guard" in role:
        return True
    return False


def _iter_guard_candidates(room):
    if not room:
        return []

    seen_ids = set()
    candidates = []
    rooms = [room]
    exits = [obj for obj in room.contents if getattr(obj, "destination", None)]
    rooms.extend(exit_obj.destination for exit_obj in exits if getattr(exit_obj, "destination", None))

    for candidate_room in rooms:
        if not candidate_room:
            continue
        for obj in candidate_room.contents:
            if getattr(obj, "id", None) in seen_ids:
                continue
            if not _is_guard(obj):
                continue
            seen_ids.add(obj.id)
            candidates.append(obj)
    return candidates


def confiscate_items(character):
    items = list(getattr(character, "contents", []) or [])
    character.db.confiscated_items = []
    storage = _resolve_room(GUARD_STORAGE_KEY)

    for item in items:
        character.db.confiscated_items.append(item.id)
        if storage:
            item.move_to(storage, quiet=True, move_type="confiscate")


def _make_burlap_sack(holder):
    sack = create_object("typeclasses.objects.Object", key="a rough burlap sack", location=holder, home=holder)
    sack.db.desc = "A rough burlap sack holding your returned belongings."
    return sack


def return_confiscated_items(character):
    item_ids = list(getattr(character.db, "confiscated_items", None) or [])
    if not item_ids:
        return None

    sack = _make_burlap_sack(character)
    moved = False
    for item_id in item_ids:
        result = search_object(item_id)
        if not result:
            continue
        result[0].move_to(sack, quiet=True, move_type="return")
        moved = True

    if not moved:
        sack.delete()
        return None

    character.db.confiscated_items = []
    character.msg("The guard returns your belongings in a sack.")
    return sack


def release_from_stocks(character):
    character.db.in_stocks = False
    exit_room = _resolve_room(STOCKS_EXIT_KEY)
    if exit_room:
        character.move_to(exit_room, quiet=True, move_type="stocks_release")
    character.msg("You are released from the stocks.")


def _finalize_sentence(character, sentence, fine, paid):
    character.db.sentence_type = sentence
    character.db.fine_amount = fine
    character.db.is_captured = False
    character.db.awaiting_plea = False

    if not paid:
        character.db.fine_due = fine
        character.db.collateral_locked = True
        character.db.fine_due_timestamp = time.time()
    else:
        character.db.fine_due = 0
        character.db.collateral_locked = False
        character.db.fine_due_timestamp = None
        return_confiscated_items(character)

    if sentence == "stocks":
        stocks_room = _resolve_room(STOCKS_ROOM_KEY)
        if stocks_room:
            character.move_to(stocks_room, quiet=True, move_type="stocks")
        character.db.in_stocks = True
        character.msg("You are locked into the public stocks. All can see your shame.")
    elif sentence == "jail":
        character.db.jail_timer = random.randint(600, 900)

    character.msg(f"The judge passes sentence: {sentence}.")


def resolve_justice_case(character):
    severity = int(getattr(character.db, "crime_severity", 0) or 1)
    severity = max(1, severity + random.randint(-1, 1))
    if getattr(character.db, "surrendered", False):
        severity = max(1, severity - 1)

    if severity <= 2:
        sentence = "stocks"
    elif severity <= 5:
        sentence = "fine"
    else:
        sentence = "jail"

    fine = severity * 20
    plea = getattr(character.db, "plea", None)
    if plea == "guilty":
        fine = int(fine * 0.8)
    elif plea == "innocent":
        roll = random.randint(1, 100)
        if roll > 70:
            character.db.crime_flag = False
            character.db.fine_due = 0
            character.db.awaiting_plea = False
            character.db.plea = None
            character.db.surrendered = False
            character.db.is_captured = False
            warrants = dict(getattr(character.db, "warrants", None) or {})
            current_region = character.location.get_region() if getattr(character, "location", None) and hasattr(character.location, "get_region") else None
            if current_region and current_region in warrants:
                warrants.pop(current_region, None)
                character.db.warrants = warrants
            return_confiscated_items(character)
            character.msg("The judge frowns, then waves you off. 'Insufficient evidence.'")
            return
        fine = int(fine * 1.2)
        character.msg("The judge scowls. 'Your lies cost you more dearly.'")

    coins = int(getattr(character.db, "coins", 0) or 0)
    paid = coins >= fine
    if paid:
        character.db.coins = coins - fine

    _finalize_sentence(character, sentence, fine, paid)
    character.db.plea = None
    character.db.surrendered = False


def capture_criminal(target, guard=None, room=None):
    if not target or getattr(target.db, "is_captured", False):
        return False
    room = room or getattr(target, "location", None)
    if room and hasattr(room, "is_lawless") and room.is_lawless():
        return False

    target.db.is_captured = True
    target.db.in_passage = False
    target.db.in_combat = False
    target.db.pursuers = []
    if hasattr(target, "set_target"):
        target.set_target(None)
    if hasattr(target, "clear_state"):
        target.clear_state("combat_timer")
    target.msg("The guard seizes you and binds your hands!")
    confiscate_items(target)

    judge_room = _resolve_room(JUDGE_ROOM_KEY)
    if judge_room:
        target.move_to(judge_room, quiet=True, move_type="justice")
        target.msg("You are dragged before a judge.")

    target.db.awaiting_plea = True
    target.ndb.plea_deadline = time.time() + 30
    target.msg("The judge looks down at you. 'How do you plead?'")
    return True


def check_liquidation(character):
    if not character.has_unpaid_fine():
        return

    elapsed = time.time() - float(getattr(character.db, "fine_due_timestamp", 0) or 0)
    if elapsed < 172800:
        return

    items = character.get_confiscated_items()
    value = len(items) * 5
    character.db.fine_due = max(0, int(getattr(character.db, "fine_due", 0) or 0) - value)
    for item in items:
        item.delete()
    character.db.confiscated_items = []
    character.db.collateral_locked = False
    if getattr(character, "sessions", None):
        character.msg("Your confiscated belongings have been sold to cover part of your fine.")


def decay_warrants(character):
    warrants = dict(getattr(character.db, "warrants", None) or {})
    if not warrants:
        return False

    changed = False
    now = time.time()
    for region, data in list(warrants.items()):
        elapsed = now - float((data or {}).get("timestamp", 0) or 0)
        if elapsed <= 3600:
            continue
        data["severity"] = max(0, int(data.get("severity", 0) or 0) - 1)
        data["bounty"] = max(0, int(data.get("bounty", 0) or 0) - 5)
        data["timestamp"] = now
        if data["severity"] <= 0:
            warrants.pop(region, None)
        else:
            warrants[region] = data
        changed = True

    if changed:
        character.db.warrants = warrants
        if not warrants and not character.has_unpaid_fine():
            character.db.crime_flag = False
    return changed


def call_guards(room, culprit):
    responders = []
    if not room or not culprit:
        return responders
    if getattr(getattr(culprit, "db", None), "in_passage", False):
        return responders

    if hasattr(room, "get_law_type") and room.get_law_type() == LAW_NONE:
        return responders
    if getattr(getattr(culprit, "location", None), "is_lawless", lambda: False)():
        return responders

    region = room.get_region() if hasattr(room, "get_region") else "default_region"
    warrants = dict(getattr(culprit.db, "warrants", None) or {})
    warrant = dict(warrants.get(region) or {})
    if not warrant and not getattr(culprit.db, "crime_flag", False):
        return responders

    severity = max(1, int(warrant.get("severity", 1) or 1))
    if warrant and "bounty" not in warrant:
        warrant["bounty"] = 10 + (severity * 5)
        warrants[region] = warrant
        culprit.db.warrants = warrants

    disguised = bool(getattr(culprit.db, "disguised", False))
    effective_severity = max(1, severity - 1) if disguised else severity

    for guard in _iter_guard_candidates(room):
        if hasattr(guard, "set_awareness"):
            guard.set_awareness("alert")
        if getattr(guard, "location", None) != room and hasattr(guard, "move_to"):
            guard.move_to(room, quiet=True, move_type="pursuit")
        responders.append(guard)
        if hasattr(guard, "location") and hasattr(guard.location, "msg_contents") and warrant:
            if disguised:
                guard.location.msg_contents(f"{guard.key} squints uncertainly at {culprit.key}.", exclude=[])
            else:
                guard.location.msg_contents(f"{guard.key} recognizes {culprit.key}!", exclude=[])
        if len(responders) >= min(3, effective_severity):
            break

    if responders and (effective_severity < 3 or disguised) and room.db.pending_guard_target != culprit.id:
        room.db.pending_guard_target = culprit.id
        if disguised:
            responders[0].location.msg_contents(f"{responders[0].key} barks, 'You there, stop a moment!'", exclude=[])
        else:
            responders[0].location.msg_contents(f"{responders[0].key} barks, 'Hold there, {culprit.key}!'", exclude=[])
    elif responders:
        room.db.pending_guard_target = None
        capture_criminal(culprit, guard=responders[0], room=room)

    if responders:
        room.msg_contents("The alarm spreads quickly through the area.", exclude=[culprit])
    else:
        room.db.pending_guard_target = culprit.id

    return responders