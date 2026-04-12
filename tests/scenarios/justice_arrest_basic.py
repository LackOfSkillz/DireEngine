import time
from evennia.utils.create import create_object

from world.systems import guards, justice


def _clear_inventory(actor):
    for item in list(getattr(actor, "contents", []) or []):
        try:
            item.delete()
        except Exception:
            continue


def scenario(ctx):
    lawful_room = ctx.harness.create_test_room(key="TEST_JUSTICE_LAWFUL")
    lawful_room.db.zone = "landing"
    lawful_room.db.guard_patrol = True
    lawful_room.db.is_lawful = True
    lawless_room = ctx.harness.create_test_room(key="TEST_JUSTICE_LAWLESS")
    lawless_room.db.law_type = "none"
    lawless_room.db.no_guard = True
    chase_room = ctx.harness.create_test_room(key="TEST_JUSTICE_CHASE")
    chase_room.db.zone = "landing"
    chase_room.db.guard_patrol = True
    chase_room.db.is_lawful = True
    ctx.harness.create_test_exit(lawful_room, chase_room, "east", aliases=["e"])
    ctx.harness.create_test_exit(chase_room, lawful_room, "west", aliases=["w"])

    primary_guard = create_object("typeclasses.npcs.GuardNPC", key="TEST_JUSTICE_GUARD", location=lawful_room, home=lawful_room)
    secondary_guard = create_object("typeclasses.npcs.GuardNPC", key="TEST_JUSTICE_GUARD_2", location=lawful_room, home=lawful_room)
    for guard in (primary_guard, secondary_guard):
        ctx.harness.track_object(guard)
        guard.db.is_guard = True
        guard.db.is_npc = True
        guard.db.zone = "landing"
        guard.db.patrol_anchor = lawful_room
        guard.db.patrol_radius = 2
        guard.db.last_move_time = time.time() - 30.0
        guard.db.last_idle_time = time.time() - 120.0

    accused = ctx.harness.create_test_character(room=lawful_room, key="TEST_JUSTICE_ACCUSED")
    ctx.character = accused
    ctx.room = lawful_room
    accused.db.profession = "thief"
    accused.db.thief_reputation = 5
    accused.db.justice_release_room_id = int(lawful_room.id or 0)
    accused.db.justice_jail_room_id = int(lawful_room.id or 0)
    accused.db.justice_pillory_room_id = int(lawful_room.id or 0)
    accused.db.justice_guardhouse_exterior_room_id = int(lawful_room.id or 0)
    accused.db.justice_guardhouse_room_id = int(lawful_room.id or 0)
    _clear_inventory(accused)

    tier_clear = justice.get_wanted_tier(accused)
    if tier_clear != "clear":
        raise AssertionError(f"Expected clear tier for fresh actor, saw {tier_clear}")

    for severity, action in ((2, "theft"), (2, "burglary")):
        justice.trigger_justice_response(accused, target=lawful_room, action_type=action, severity=severity)

    wanted_tier = justice.get_wanted_tier(accused)
    if wanted_tier != "arrest_eligible":
        raise AssertionError(f"Wanted tier should reach arrest_eligible, saw {wanted_tier}")

    can_arrest, arrest_reason = justice.can_be_arrested(accused)
    if not can_arrest:
        raise AssertionError(f"Arrest should be allowed in lawful room, saw: {arrest_reason}")

    response = justice.evaluate_guard_response(accused)
    if not response.get("should_respond"):
        raise AssertionError(f"Guard response should be active at arrest threshold, saw: {response}")

    guard_attention = bool(getattr(accused.db, "guard_attention", False))
    if not guard_attention:
        raise AssertionError("Triggering arrest-eligible crime should turn on guard attention.")

    guards.scan_room_for_suspicion(primary_guard)
    if int(getattr(accused.db, "active_guard_id", 0) or 0) != int(primary_guard.id or 0):
        raise AssertionError("Primary guard should claim ownership when confrontation begins.")
    if str(getattr(primary_guard.db, "enforcement_state", "") or "") not in {"confronting", "warning"}:
        raise AssertionError("Primary guard should enter visible enforcement flow.")
    if int(getattr(primary_guard.db, "warning_count", 0) or 0) <= 0:
        raise AssertionError("Visible confrontation should start the warning ladder.")
    if int(getattr(accused.db, "justice_warning_level", 0) or 0) <= 0:
        raise AssertionError("Visible confrontation should raise the actor warning level.")

    guards.scan_room_for_suspicion(secondary_guard)
    if int(getattr(accused.db, "active_guard_id", 0) or 0) != int(primary_guard.id or 0):
        raise AssertionError("Secondary guard should not steal ownership from the active guard.")
    if int(getattr(secondary_guard.db, "warning_count", 0) or 0) > 0:
        raise AssertionError("Non-owning guards should not escalate warning speech.")

    justice_output_start = len(ctx.output_log)
    ctx.cmd("justice")
    justice_messages = ctx.output_log[justice_output_start:]
    if not any("active guard" in entry.lower() for entry in justice_messages):
        raise AssertionError(f"Justice command should report the active guard, saw: {justice_messages}")
    if not any("pending arrest" in entry.lower() for entry in justice_messages):
        raise AssertionError(f"Justice command should report pending arrest state, saw: {justice_messages}")

    laylow_output_start = len(ctx.output_log)
    ctx.cmd("laylow")
    laylow_messages = ctx.output_log[laylow_output_start:]
    if not any("cannot lay low" in entry.lower() for entry in laylow_messages):
        raise AssertionError(f"Laylow should be blocked during confrontation, saw: {laylow_messages}")

    lawful_room.db.is_stocks = True
    lawful_room.db.is_jail = True

    accused.db.justice_flee_flag = True
    forced_penalty = justice.calculate_justice_penalty(accused, voluntary=False)
    surrender_penalty_preview = justice.calculate_justice_penalty(accused, voluntary=True)
    if surrender_penalty_preview["fine"] >= forced_penalty["fine"]:
        raise AssertionError("Voluntary surrender should preview a lower fine than forced arrest.")

    accused.db.justice_flee_flag = False
    surrender_output_start = len(ctx.output_log)
    ctx.cmd("surrender")
    surrender_messages = ctx.output_log[surrender_output_start:]
    if not any("accepts your surrender" in entry.lower() or "surrender" in entry.lower() for entry in surrender_messages):
        raise AssertionError(f"Surrender command should produce surrender messaging, saw: {surrender_messages}")

    if not justice.is_detained(accused):
        raise AssertionError("Surrender should end in detention.")
    if int(getattr(accused.db, "active_guard_id", 0) or 0) != 0:
        raise AssertionError("Surrender should clear active guard ownership.")
    if str(getattr(primary_guard.db, "enforcement_state", "") or "") != "idle":
        raise AssertionError("Surrender should reset the enforcing guard state.")

    detained_output_start = len(ctx.output_log)
    ctx.cmd("steal nobody")
    detained_messages = ctx.output_log[detained_output_start:]
    if not any("detained" in entry.lower() for entry in detained_messages):
        raise AssertionError(f"Detention should block thief actions, saw: {detained_messages}")

    wanted_after = int(getattr(accused.db, "wanted_level", 0) or 0)
    reputation_after = int(getattr(accused.db, "thief_reputation", 0) or 0)
    fine_after = int(getattr(accused.db, "outstanding_fine", 0) or 0)
    if wanted_after >= 6:
        raise AssertionError(f"Resolution should reduce wanted pressure, saw wanted={wanted_after}")
    if reputation_after >= 5:
        raise AssertionError(f"Arrest should reduce thief reputation, saw reputation={reputation_after}")
    if fine_after <= 0:
        raise AssertionError("Arrest resolution should assign a fine.")

    accused.db.detained_until = time.time() - 1
    if justice.is_detained(accused):
        raise AssertionError("Expired detention should auto-clear.")

    fugitive = ctx.harness.create_test_character(room=lawful_room, key="TEST_JUSTICE_FUGITIVE")
    fugitive.db.profession = "thief"
    fugitive.db.thief_reputation = 4
    fugitive.db.justice_release_room_id = int(lawful_room.id or 0)
    fugitive.db.justice_jail_room_id = int(lawful_room.id or 0)
    fugitive.db.justice_pillory_room_id = int(lawful_room.id or 0)
    fugitive.db.justice_guardhouse_exterior_room_id = int(lawful_room.id or 0)
    fugitive.db.justice_guardhouse_room_id = int(lawful_room.id or 0)
    _clear_inventory(fugitive)
    justice.trigger_justice_response(fugitive, target=lawful_room, action_type="burglary", severity=3)
    guards.scan_room_for_suspicion(primary_guard)
    fugitive_penalty_before_flee = justice.calculate_justice_penalty(fugitive, voluntary=False)
    pre_flee_wanted = int(getattr(fugitive.db, "wanted_level", 0) or 0)
    ctx.character = fugitive
    flee_output_start = len(ctx.output_log)
    ctx.cmd("passage")
    flee_messages = ctx.output_log[flee_output_start:]
    flee_flag = bool(getattr(fugitive.db, "justice_flee_flag", False))
    if not flee_flag:
        raise AssertionError(f"Refusing surrender under guard attention should set flee flag, saw messages: {flee_messages}")
    if int(getattr(fugitive.db, "wanted_level", 0) or 0) <= pre_flee_wanted:
        raise AssertionError("Fleeing justice pressure should worsen wanted level.")
    fugitive_penalty = justice.calculate_justice_penalty(fugitive, voluntary=False)
    if fugitive_penalty["fine"] <= fugitive_penalty_before_flee["fine"]:
        raise AssertionError("Flee flag should worsen the eventual forced-arrest penalty.")

    fugitive.move_to(chase_room, quiet=True, move_type="test")
    primary_guard.db.last_move_time = time.time() - 30.0
    primary_guard.db.last_idle_time = time.time() - 120.0
    followed = guards.guard_movement_tick(primary_guard)
    if not followed or primary_guard.location != chase_room:
        raise AssertionError("Owning guard should briefly follow a fleeing target.")

    primary_guard.db.last_warning_time = time.time() - 11.0
    guards.process_guard_tick()
    primary_guard.db.warning_count = max(3, int(getattr(primary_guard.db, "warning_count", 0) or 0))
    arrest_result = guards.attempt_visible_arrest(primary_guard, fugitive)
    if not arrest_result.get("started"):
        raise AssertionError(f"Visible arrest attempt should succeed after flee escalation, saw: {arrest_result}")
    if not justice.is_detained(fugitive):
        raise AssertionError("Visible enforcement should end in arrest after flee escalation.")
    if int(getattr(fugitive.db, "active_guard_id", 0) or 0) != 0:
        raise AssertionError("Arrest should clear guard ownership on the actor.")
    if str(getattr(primary_guard.db, "enforcement_state", "") or "") != "idle":
        raise AssertionError("Arrest should reset the guard to idle.")

    fugitive.move_to(lawless_room, quiet=True)
    lawless_response = justice.evaluate_guard_response(fugitive)
    if lawless_response.get("should_respond"):
        raise AssertionError(f"Lawless rooms should suppress arrest response, saw: {lawless_response}")

    ctx.log(
        {
            "wanted_tier": wanted_tier,
            "guard_attention": guard_attention,
            "surrendered": True,
            "detained": True,
            "fine": fine_after,
            "wanted_after": wanted_after,
            "reputation_after": reputation_after,
            "flee_flag": flee_flag,
            "active_guard_id": int(getattr(fugitive.db, "active_guard_id", 0) or 0),
        }
    )

    return {
        "wanted_tier": wanted_tier,
        "guard_attention": guard_attention,
        "surrendered": True,
        "detained": True,
        "fine": fine_after,
        "wanted_after": wanted_after,
        "reputation_after": reputation_after,
        "flee_flag": flee_flag,
        "forced_penalty": forced_penalty,
        "surrender_penalty": surrender_penalty_preview,
        "fugitive_penalty_before_flee": fugitive_penalty_before_flee,
        "fugitive_penalty": fugitive_penalty,
    }