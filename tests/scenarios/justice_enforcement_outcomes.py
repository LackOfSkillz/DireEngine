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

    pillory_room = ctx.harness.create_test_room(key="TEST_PILLORY_SQUARE")
    pillory_room.db.is_lawful = True
    pillory_room.db.no_guard = False
    pillory_room.db.high_traffic = True
    pillory_room.db.pillory = True
    pillory_room.db.guard_patrol = True

    jail_room = ctx.harness.create_test_room(key="TEST_TOWN_JAIL")
    jail_room.db.is_lawful = True
    jail_room.db.no_guard = False
    jail_room.db.is_jail = True
    jail_room.db.guard_patrol = True

    guardhouse_exterior = ctx.harness.create_test_room(key="TEST_GUARDHOUSE_EXTERIOR")
    guardhouse_exterior.db.is_lawful = True
    guardhouse_exterior.db.no_guard = False
    guardhouse_exterior.db.high_traffic = True
    guardhouse_exterior.db.guardhouse_exterior = True

    guardhouse_room = ctx.harness.create_test_room(key="TEST_GUARDHOUSE_INTERIOR")
    guardhouse_room.db.is_lawful = True
    guardhouse_room.db.no_guard = False
    guardhouse_room.db.is_guardhouse = True

    ctx.harness.create_test_exit(pillory_room, release_room, "east", aliases=["e"])
    ctx.harness.create_test_exit(release_room, pillory_room, "west", aliases=["w"])
    ctx.harness.create_test_exit(jail_room, release_room, "out", aliases=[])
    ctx.harness.create_test_exit(guardhouse_exterior, guardhouse_room, "inside", aliases=[])
    ctx.harness.create_test_exit(guardhouse_room, guardhouse_exterior, "outside", aliases=[])

    pillory = create_object("typeclasses.objects.Object", key="wooden pillory", location=pillory_room, home=pillory_room)
    ctx.harness.track_object(pillory)
    pillory.db.is_pillory = True

    evidence_locker = create_object("typeclasses.objects.Object", key="evidence locker", location=guardhouse_room, home=guardhouse_room)
    ctx.harness.track_object(evidence_locker)
    evidence_locker.db.is_evidence_locker = True

    minor = ctx.harness.create_test_character(room=release_room, key="TEST_JUSTICE_MINOR")
    moderate = ctx.harness.create_test_character(room=release_room, key="TEST_JUSTICE_MODERATE")
    severe = ctx.harness.create_test_character(room=release_room, key="TEST_JUSTICE_SEVERE")
    for actor in (minor, moderate, severe):
        actor.db.coins = 2000

    _prime_actor(minor, release_room, pillory_room, jail_room, guardhouse_exterior, guardhouse_room, severity=1, action_type="theft")
    minor_result = justice.complete_arrest(minor, source="test minor arrest", voluntary=False)
    if str(minor_result.get("outcome", "") or "") != "pillory":
        raise AssertionError(f"Minor crime should route to pillory, saw: {minor_result}")
    if not bool(getattr(minor.db, "in_pillory", False)):
        raise AssertionError("Minor outcome should mark the actor as in the pillory.")
    if minor.location != pillory_room:
        raise AssertionError("Minor outcome should move the actor to the pillory room.")

    ctx.character = minor
    pillory_block_start = len(ctx.output_log)
    ctx.cmd("east")
    pillory_block_messages = ctx.output_log[pillory_block_start:]
    if not any("pillory" in entry.lower() or "cannot move" in entry.lower() for entry in pillory_block_messages):
        raise AssertionError(f"Pillory should block movement, saw: {pillory_block_messages}")

    minor.db.pillory_end_time = time.time() - 1
    minor.db.detained_until = time.time() - 1
    justice.process_justice_state_tick(minor)
    if bool(getattr(minor.db, "in_pillory", False)):
        raise AssertionError("Pillory release should clear the in_pillory state.")
    if minor.location != release_room:
        raise AssertionError("Pillory release should return the actor to the release room.")

    _prime_actor(moderate, release_room, pillory_room, jail_room, guardhouse_exterior, guardhouse_room, severity=2, action_type="theft")
    moderate_result = justice.complete_arrest(moderate, source="test moderate arrest", voluntary=False)
    if str(moderate_result.get("outcome", "") or "") != "jail":
        raise AssertionError(f"Moderate crime should route to jail, saw: {moderate_result}")
    if not bool(getattr(moderate.db, "in_jail", False)):
        raise AssertionError("Moderate outcome should mark the actor as in jail.")
    if moderate.location != jail_room:
        raise AssertionError("Moderate outcome should move the actor to the jail room.")
    if int(getattr(moderate.db, "justice_debt", 0) or 0) < 200:
        raise AssertionError("Moderate crime should assign a meaningful debt.")

    ctx.character = moderate
    jail_block_start = len(ctx.output_log)
    ctx.cmd("steal nobody")
    jail_block_messages = ctx.output_log[jail_block_start:]
    if not any("jail" in entry.lower() or "detained" in entry.lower() for entry in jail_block_messages):
        raise AssertionError(f"Jail should block thief actions, saw: {jail_block_messages}")

    moderate.db.jail_end_time = time.time() - 1
    moderate.db.detained_until = time.time() - 1
    justice.process_justice_state_tick(moderate)
    if bool(getattr(moderate.db, "in_jail", False)):
        raise AssertionError("Jail release should clear the in_jail state.")
    if moderate.location != guardhouse_exterior:
        raise AssertionError("Jail release should return the actor to the guardhouse exterior.")

    satchel = create_object("typeclasses.objects.Object", key="confiscated satchel", location=severe, home=severe)
    knife = create_object("typeclasses.objects.Object", key="confiscated knife", location=severe, home=severe)
    satchel.db.weight = 1
    knife.db.weight = 1
    ctx.harness.track_object(satchel)
    ctx.harness.track_object(knife)

    _prime_actor(severe, release_room, pillory_room, jail_room, guardhouse_exterior, guardhouse_room, severity=3, action_type="burglary")
    severe_result = justice.complete_arrest(severe, source="test severe arrest", voluntary=False)
    if str(severe_result.get("outcome", "") or "") != "jail":
        raise AssertionError(f"Severe crime should route to jail, saw: {severe_result}")
    if int(severe_result.get("confiscated_count", 0) or 0) < 2:
        raise AssertionError(f"Severe crime should confiscate inventory, saw: {severe_result}")
    if int(getattr(severe.db, "justice_debt", 0) or 0) < 500:
        raise AssertionError("Severe crime should assign severe debt.")
    if satchel.location != evidence_locker or knife.location != evidence_locker:
        raise AssertionError("Confiscated severe-crime items should be moved into the evidence locker.")

    severe.db.jail_end_time = time.time() - 1
    severe.db.detained_until = time.time() - 1
    justice.process_justice_state_tick(severe)
    severe.move_to(guardhouse_room, quiet=True, move_type="test_move")

    ctx.character = severe
    retrieve_block_start = len(ctx.output_log)
    ctx.cmd("retrieve items")
    retrieve_block_messages = ctx.output_log[retrieve_block_start:]
    if not any("debt" in entry.lower() for entry in retrieve_block_messages):
        raise AssertionError(f"Debt should block item retrieval, saw: {retrieve_block_messages}")

    debt_before = int(getattr(severe.db, "justice_debt", 0) or 0)
    overpay_start = len(ctx.output_log)
    ctx.cmd(f"payfine {debt_before + 1}")
    overpay_messages = ctx.output_log[overpay_start:]
    if not any("cannot pay more" in entry.lower() for entry in overpay_messages):
        raise AssertionError(f"Overpay attempts should be rejected, saw: {overpay_messages}")

    partial_payment = 50
    partial_start = len(ctx.output_log)
    ctx.cmd(f"payfine {partial_payment}")
    partial_messages = ctx.output_log[partial_start:]
    if not any("remaining debt" in entry.lower() for entry in partial_messages):
        raise AssertionError(f"Partial payments should confirm remaining debt, saw: {partial_messages}")
    remaining_debt = int(getattr(severe.db, "justice_debt", 0) or 0)
    if remaining_debt != debt_before - partial_payment:
        raise AssertionError(f"Partial payment should reduce debt, saw {remaining_debt} from {debt_before}")

    final_payment_start = len(ctx.output_log)
    ctx.cmd(f"payfine {remaining_debt}")
    final_payment_messages = ctx.output_log[final_payment_start:]
    if not any("remaining debt: 0" in entry.lower() for entry in final_payment_messages):
        raise AssertionError(f"Final payment should clear debt, saw: {final_payment_messages}")
    if int(getattr(severe.db, "justice_debt", 0) or 0) != 0:
        raise AssertionError("Final payment should clear justice debt.")

    retrieve_success_start = len(ctx.output_log)
    ctx.cmd("retrieve items")
    retrieve_success_messages = ctx.output_log[retrieve_success_start:]
    if not any("evidence locker" in entry.lower() or "retrieve your belongings" in entry.lower() for entry in retrieve_success_messages):
        raise AssertionError(f"Retrieval should succeed after debt is cleared, saw: {retrieve_success_messages}")
    if satchel.location != severe or knife.location != severe:
        raise AssertionError("Recovered items should return to the actor inventory.")

    audit = {
        "pillory_used": bool(getattr(minor.db, "pillory_end_time", 0) or minor_result.get("outcome") == "pillory"),
        "jail_used": bool(moderate_result.get("outcome") == "jail" or severe_result.get("outcome") == "jail"),
        "debt_assigned": int(getattr(severe.db, "outstanding_fine", 0) or 0) + debt_before,
        "items_confiscated": int(severe_result.get("confiscated_count", 0) or 0),
        "items_recovered": 2,
    }
    ctx.log(audit)

    return {
        "minor_outcome": minor_result,
        "moderate_outcome": moderate_result,
        "severe_outcome": severe_result,
        "audit": audit,
    }
