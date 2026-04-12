import random
import time

from world.systems.burglary import add_burgle_heat, attempt_entry, get_burgle_heat
from world.systems.theft import can_use_passage, request_contact_service


class _RollPatch:
    def __init__(self, rolls, fallback=50):
        self._rolls = list(rolls)
        self._fallback = fallback
        self._original_randint = None

    def __enter__(self):
        self._original_randint = random.randint

        def _patched(_a, _b):
            if self._rolls:
                return self._rolls.pop(0)
            return self._fallback

        random.randint = _patched
        return self

    def __exit__(self, exc_type, exc, tb):
        random.randint = self._original_randint
        return False


def _make_lockpick(ctx, owner, key="basic lockpick"):
    pick = ctx.harness.create_test_object(key=key, location=owner, weight=1)
    pick.db.is_lockpick = True
    pick.db.grade = "basic"
    pick.db.quality = 1.0
    pick.db.durability = 20
    return pick


def scenario(ctx):
    street = ctx.harness.create_test_room(key="TEST_BURGLE_STREET")
    interior = ctx.harness.create_test_room(key="TEST_BURGLE_INTERIOR")
    street.db.has_passage = True
    street.db.passage_links = [interior]

    thief = ctx.harness.create_test_character(room=street, key="TEST_BURGLE_THIEF")
    ctx.character = thief
    ctx.room = street

    for skill_name, rank in (("locksmithing", 120), ("stealth", 80), ("perception", 70), ("athletics", 60)):
        thief.learn_skill(skill_name, {"rank": rank, "mindstate": 0})
    thief.db.profession = "thief"
    thief.db.contacts = {
        "whisper": {"role": "runner", "disposition": 1, "base_cost": 2},
    }
    _make_lockpick(ctx, thief)

    window = ctx.harness.create_test_object(key="TEST_BURGLE_WINDOW", location=street, weight=8)
    window.db.burglary_enabled = True
    window.db.burglary_kind = "entry"
    window.db.lock_difficulty = 20
    window.db.trap_difficulty = 0
    window.db.burglary_destination = interior

    locksmithing_before = float(thief.exp_skills.get("locksmithing").pool)
    stealth_before = float(thief.exp_skills.get("stealth").pool)
    athletics_before = float(thief.exp_skills.get("athletics").pool)
    with _RollPatch([95, 5]):
        ctx.cmd("burgle TEST_BURGLE_WINDOW")
    locksmithing_after_success = float(thief.exp_skills.get("locksmithing").pool)
    stealth_after_success = float(thief.exp_skills.get("stealth").pool)
    athletics_after_success = float(thief.exp_skills.get("athletics").pool)
    burgle_success = getattr(thief, "location", None) == interior and bool(getattr(window.db, "entry_open", False))
    if not burgle_success:
        raise AssertionError("Successful burglary should move the thief inside and mark the entry open.")
    if locksmithing_after_success <= locksmithing_before:
        raise AssertionError(
            f"Successful burglary should train locksmithing: before={locksmithing_before}, after={locksmithing_after_success}"
        )
    if stealth_after_success <= stealth_before:
        raise AssertionError(f"Successful burglary should train stealth: before={stealth_before}, after={stealth_after_success}")
    if athletics_after_success <= athletics_before:
        raise AssertionError(f"Successful burglary should train athletics: before={athletics_before}, after={athletics_after_success}")

    thief.move_to(street, quiet=True)
    thief.db.roundtime_end = time.time() - 1
    locked_gate = ctx.harness.create_test_object(key="TEST_LOCKED_GATE", location=street, weight=8)
    locked_gate.db.burglary_enabled = True
    locked_gate.db.burglary_kind = "entry"
    locked_gate.db.lock_difficulty = 25
    locked_gate.db.trap_difficulty = 0
    locked_gate.db.burglary_destination = interior
    for item in list(getattr(thief, "contents", []) or []):
        if bool(getattr(getattr(item, "db", None), "is_lockpick", False)):
            item.delete()
    output_start = len(ctx.output_log)
    ctx.cmd("burgle TEST_LOCKED_GATE")
    missing_tool_messages = ctx.output_log[output_start:]
    missing_tools_blocked = any("need a lockpick" in entry.lower() for entry in missing_tool_messages)
    if not missing_tools_blocked:
        raise AssertionError(f"Missing lockpick should block burglary cleanly, saw: {missing_tool_messages}")
    _make_lockpick(ctx, thief, key="replacement lockpick")

    trapped_entry = ctx.harness.create_test_object(key="TEST_TRAPPED_ENTRY", location=street, weight=8)
    trapped_entry.db.burglary_enabled = True
    trapped_entry.db.burglary_kind = "entry"
    trapped_entry.db.lock_difficulty = 20
    trapped_entry.db.trap_difficulty = 120
    trapped_entry.db.trap_type = "alarm"
    trapped_entry.db.burglary_destination = interior

    thief.db.wanted_level = 0
    thief.db.guard_attention = False
    thief.db.justice_incidents = []
    thief.db.thief_reputation = 0
    with _RollPatch([5, 95]):
        trap_result = attempt_entry(thief, trapped_entry)
    if trap_result.get("trap_result") != "triggered":
        raise AssertionError(f"Trap failure should trigger the trap path, saw: {trap_result}")
    trap_triggered = True
    wanted_level = int(getattr(thief.db, "wanted_level", 0) or 0)
    if wanted_level < 5:
        raise AssertionError(f"Trap-triggered burglary should escalate wanted past the guard threshold, saw wanted={wanted_level}")
    if not bool(getattr(thief.db, "guard_attention", False)):
        raise AssertionError("High-severity burglary should flip guard attention on.")

    add_burgle_heat(trapped_entry, amount=1)
    burgle_heat = get_burgle_heat(trapped_entry)
    if burgle_heat <= 0:
        raise AssertionError("Burglary heat should increase on repeated intrusion pressure.")

    contact_result = request_contact_service(thief, "whisper", request_type="heat")
    if bool(contact_result.get("ok", True)):
        raise AssertionError(f"High wanted state should worsen or deny contact help, saw: {contact_result}")

    thief.db.awareness_state = {"last_detected_at": time.time()}
    passage_allowed, _passage_message = can_use_passage(thief, street)
    if passage_allowed:
        raise AssertionError("Recent exposure or high wanted state should deny passage access.")

    reputation_after = int(getattr(thief.db, "thief_reputation", 0) or 0)
    incidents = list(getattr(thief.db, "justice_incidents", None) or [])
    if not incidents:
        raise AssertionError("Burglary justice flow should record a justice incident.")

    ctx.log(
        {
            "burgle_success": burgle_success,
            "trap_triggered": trap_triggered,
            "wanted_level": wanted_level,
            "guard_attention": bool(getattr(thief.db, "guard_attention", False)),
            "reputation_after": reputation_after,
            "locksmithing_pool_after_success": locksmithing_after_success,
            "stealth_pool_after_success": stealth_after_success,
            "athletics_pool_after_success": athletics_after_success,
            "contact_result": str(contact_result.get("message") or ""),
            "passage_denied": not passage_allowed,
        }
    )

    return {
        "burgle_success": burgle_success,
        "missing_tools_blocked": missing_tools_blocked,
        "trap_triggered": trap_triggered,
        "burgle_heat": burgle_heat,
        "wanted_level": wanted_level,
        "guard_attention": bool(getattr(thief.db, "guard_attention", False)),
        "reputation_after": reputation_after,
        "locksmithing_pool_after_success": locksmithing_after_success,
        "stealth_pool_after_success": stealth_after_success,
        "athletics_pool_after_success": athletics_after_success,
        "contact_result": contact_result,
        "passage_denied": not passage_allowed,
        "justice_incident_count": len(incidents),
    }