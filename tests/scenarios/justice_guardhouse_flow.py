import time

from evennia.utils.create import create_object

from world.systems import justice


def _prime_actor(actor, release_room, pillory_room, jail_room, guardhouse_exterior, guardhouse_room, *, severity, action_type="theft"):
    actor.move_to(release_room, quiet=True, move_type="test_reset")
    actor.db.wanted_level = justice.ARREST_ELIGIBLE_THRESHOLD
    actor.db.last_wanted_update = time.time()
    actor.db.crime_flag = True
    actor.db.justice_flee_flag = False
    actor.db.justice_incidents = [
        {
            "type": action_type,
            "target": "test target",
            "severity": severity,
            "timestamp": time.time(),
            "room": release_room.key,
        }
    ]
    actor.db.warrants = {"test_region": {"severity": severity, "updated_at": time.time()}}
    actor.db.detained = False
    actor.db.detained_until = 0
    actor.db.guard_attention = False
    actor.db.pending_arrest = False
    actor.db.justice_warning_level = 0
    actor.db.active_guard_id = None
    actor.db.in_pillory = False
    actor.db.pillory_end_time = 0
    actor.db.in_jail = False
    actor.db.jail_end_time = 0
    actor.db.jail_timer = 0
    actor.db.justice_hold_reason = None
    actor.db.confiscated_items = []
    actor.db.confiscation_location = None
    actor.db.justice_pillory_room_id = int(pillory_room.id or 0)
    actor.db.justice_jail_room_id = int(jail_room.id or 0)
    actor.db.justice_release_room_id = int(release_room.id or 0)
    actor.db.justice_guardhouse_exterior_room_id = int(guardhouse_exterior.id or 0)
    actor.db.justice_guardhouse_room_id = int(guardhouse_room.id or 0)


def scenario(ctx):
    release_room = ctx.harness.create_test_room(key="TEST_TOWN_GREEN")
    release_room.db.is_lawful = True
    release_room.db.high_traffic = True
    release_room.db.no_guard = False

    guardhouse_exterior = ctx.harness.create_test_room(key="TEST_GUARDHOUSE_EXTERIOR")
    guardhouse_exterior.db.is_lawful = True
    guardhouse_exterior.db.high_traffic = True
    guardhouse_exterior.db.no_guard = False
    guardhouse_exterior.db.guardhouse_exterior = True

    guardhouse_room = ctx.harness.create_test_room(key="TEST_GUARDHOUSE_INTERIOR")
    guardhouse_room.db.is_lawful = True
    guardhouse_room.db.no_guard = False
    guardhouse_room.db.is_guardhouse = True

    pillory_room = ctx.harness.create_test_room(key="TEST_PILLORY_SQUARE")
    pillory_room.db.is_lawful = True
    pillory_room.db.no_guard = False
    pillory_room.db.high_traffic = True
    pillory_room.db.pillory = True

    jail_room = ctx.harness.create_test_room(key="TEST_TOWN_JAIL")
    jail_room.db.is_lawful = True
    jail_room.db.no_guard = False
    jail_room.db.is_jail = True

    ctx.harness.create_test_exit(release_room, guardhouse_exterior, "guardhouse", aliases=[])
    ctx.harness.create_test_exit(guardhouse_exterior, release_room, "green", aliases=[])
    ctx.harness.create_test_exit(guardhouse_exterior, guardhouse_room, "inside", aliases=[])
    ctx.harness.create_test_exit(guardhouse_room, guardhouse_exterior, "outside", aliases=[])
    ctx.harness.create_test_exit(guardhouse_room, jail_room, "jail", aliases=[])
    ctx.harness.create_test_exit(jail_room, guardhouse_exterior, "out", aliases=[])

    evidence_locker = create_object("typeclasses.objects.Object", key="evidence locker", location=guardhouse_room, home=guardhouse_room)
    evidence_locker.db.is_evidence_locker = True
    ctx.harness.track_object(evidence_locker)

    pillory = create_object("typeclasses.objects.Object", key="wooden pillory", location=pillory_room, home=pillory_room)
    pillory.db.is_pillory = True
    ctx.harness.track_object(pillory)

    offender = ctx.harness.create_test_character(room=release_room, key="TEST_GUARDHOUSE_OFFENDER")
    offender.db.coins = 2500
    satchel = create_object("typeclasses.objects.Object", key="confiscated satchel", location=offender, home=offender)
    knife = create_object("typeclasses.objects.Object", key="confiscated knife", location=offender, home=offender)
    satchel.db.weight = 1
    knife.db.weight = 1
    ctx.harness.track_object(satchel)
    ctx.harness.track_object(knife)

    _prime_actor(offender, release_room, pillory_room, jail_room, guardhouse_exterior, guardhouse_room, severity=3, action_type="burglary")
    arrest_result = justice.complete_arrest(offender, source="test severe arrest", voluntary=False)
    if int(arrest_result.get("confiscated_count", 0) or 0) < 2:
        raise AssertionError(f"Expected confiscation during severe arrest, saw: {arrest_result}")
    if int(getattr(offender.db, "confiscation_location", 0) or 0) != int(guardhouse_room.id or 0):
        raise AssertionError("Confiscation should be anchored to the guardhouse interior.")
    if satchel.location != evidence_locker or knife.location != evidence_locker:
        raise AssertionError("Confiscated items should be stored in the evidence locker.")

    offender.db.jail_end_time = time.time() - 1
    offender.db.detained_until = time.time() - 1
    justice.process_justice_state_tick(offender)
    if offender.location != guardhouse_exterior:
        raise AssertionError("Jail release should return the actor to the guardhouse exterior.")

    ctx.character = offender
    retrieve_outside_start = len(ctx.output_log)
    ctx.cmd("retrieve items")
    retrieve_outside_messages = ctx.output_log[retrieve_outside_start:]
    if not any("guardhouse" in entry.lower() for entry in retrieve_outside_messages):
        raise AssertionError(f"Retrieval outside the guardhouse should be blocked, saw: {retrieve_outside_messages}")

    offender.move_to(guardhouse_room, quiet=True, move_type="test_move")
    retrieve_debt_start = len(ctx.output_log)
    ctx.cmd("retrieve items")
    retrieve_debt_messages = ctx.output_log[retrieve_debt_start:]
    if not any("debt" in entry.lower() for entry in retrieve_debt_messages):
        raise AssertionError(f"Debt should block retrieval in the guardhouse, saw: {retrieve_debt_messages}")

    debt_before = int(getattr(offender.db, "justice_debt", 0) or 0)
    ctx.cmd(f"payfine {debt_before}")
    if int(getattr(offender.db, "justice_debt", 0) or 0) != 0:
        raise AssertionError("Paying the full debt should clear the justice debt.")

    retrieve_success_start = len(ctx.output_log)
    ctx.cmd("retrieve items")
    retrieve_success_messages = ctx.output_log[retrieve_success_start:]
    if not any("evidence locker" in entry.lower() or "retrieve your belongings" in entry.lower() for entry in retrieve_success_messages):
        raise AssertionError(f"Retrieval should succeed in the guardhouse after payment, saw: {retrieve_success_messages}")
    if satchel.location != offender or knife.location != offender:
        raise AssertionError("Retrieved items should return to the actor.")
    if list(getattr(offender.db, "confiscated_items", None) or []):
        raise AssertionError("Successful retrieval should clear the confiscated items list.")
    if getattr(offender.db, "confiscation_location", None) is not None:
        raise AssertionError("Successful retrieval should clear the confiscation location.")

    repeat_offender = ctx.harness.create_test_character(room=release_room, key="TEST_REPEAT_OFFENDER")
    repeat_offender.db.coins = 2500
    _prime_actor(repeat_offender, release_room, pillory_room, jail_room, guardhouse_exterior, guardhouse_room, severity=1, action_type="theft")
    base_penalty = justice.calculate_justice_penalty(repeat_offender)
    repeat_offender.db.crime_count = 3
    repeat_offender.db.last_crime_time = time.time()
    scaled_penalty = justice.calculate_justice_penalty(repeat_offender)
    if int(scaled_penalty.get("fine", 0) or 0) <= int(base_penalty.get("fine", 0) or 0):
        raise AssertionError("Repeat offenses should scale fines upward.")
    if int(scaled_penalty.get("detain_seconds", 0) or 0) <= int(base_penalty.get("detain_seconds", 0) or 0):
        raise AssertionError("Repeat offenses should scale jail or pillory time upward.")
    if str(scaled_penalty.get("outcome", "") or "") != "jail":
        raise AssertionError(f"Crime count >= 3 should escalate a minor offense to jail, saw: {scaled_penalty}")

    repeat_offender.db.crime_count = 4
    repeat_offender.db.last_crime_time = time.time() - ((justice.CRIME_DECAY_BUCKET * 2) + 5)
    repeat_offender.db.law_reputation = -4
    decayed_crime_count = justice.decay_crime_count(repeat_offender)
    decayed_law_reputation = justice.decay_law_reputation(repeat_offender)
    if decayed_crime_count != 2:
        raise AssertionError(f"Crime count decay should reduce by elapsed buckets, saw: {decayed_crime_count}")
    if decayed_law_reputation != -2:
        raise AssertionError(f"Law reputation should drift toward zero over time, saw: {decayed_law_reputation}")

    empty_start = len(ctx.output_log)
    ctx.cmd("retrieve items")
    empty_messages = ctx.output_log[empty_start:]
    if not any("no confiscated items" in entry.lower() for entry in empty_messages):
        raise AssertionError(f"Empty locker retrieval should be explicit, saw: {empty_messages}")

    audit = {
        "crime_count": int(getattr(offender.db, "crime_count", 0) or 0),
        "law_reputation": int(getattr(offender.db, "law_reputation", 0) or 0),
        "fine_scaled": int(scaled_penalty.get("fine", 0) or 0),
        "jail_scaled": int(scaled_penalty.get("detain_seconds", 0) or 0),
        "items_confiscated": int(arrest_result.get("confiscated_count", 0) or 0),
        "items_retrieved": 2,
    }
    ctx.log(audit)

    return {
        "arrest_result": arrest_result,
        "base_penalty": base_penalty,
        "scaled_penalty": scaled_penalty,
        "audit": audit,
    }