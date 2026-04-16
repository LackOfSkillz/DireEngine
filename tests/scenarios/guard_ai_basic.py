import time

from world.systems import canon_seed, guards


def scenario(ctx):
    canon_seed.import_controlled_dataset(limit_per_category=20, reset=True)
    guards.reset_guard_runtime(delete_spawned=True, refresh_templates=True)

    rooms = []
    for index in range(18):
        room = ctx.harness.create_test_room(key=f"TEST_GUARD_ROOM_{index}")
        room.db.zone = "landing"
        room.db.zone_id = "landing"
        room.db.is_lawful = True
        room.db.law_type = "standard"
        room.db.guard_patrol = True
        rooms.append(room)

    rooms[3].db.no_guard = True
    rooms[17].db.guard_patrol = False
    for left, right in zip(rooms, rooms[1:]):
        ctx.harness.create_test_exit(left, right, f"east_{left.id}", aliases=["e"])
        ctx.harness.create_test_exit(right, left, f"west_{right.id}", aliases=["w"])

    boundary_room = ctx.harness.create_test_room(key="TEST_GUARD_BOUNDARY")
    boundary_room.db.zone = "landing"
    boundary_room.db.zone_id = "landing"
    boundary_room.db.is_lawful = True
    boundary_room.db.law_type = "standard"
    boundary_room.db.guard_patrol = True
    boundary_room.db.npc_boundary = True

    restricted_room = ctx.harness.create_test_room(key="TEST_GUARD_GUILD")
    restricted_room.db.zone = "landing"
    restricted_room.db.zone_id = "landing"
    restricted_room.db.is_lawful = True
    restricted_room.db.law_type = "standard"
    restricted_room.db.guard_patrol = True
    restricted_room.db.guild_area = True

    foreign_room = ctx.harness.create_test_room(key="TEST_GUARD_FOREIGN")
    foreign_room.db.zone = "foreign"
    foreign_room.db.zone_id = "foreign"
    foreign_room.db.is_lawful = True
    foreign_room.db.law_type = "standard"
    foreign_room.db.guard_patrol = True

    walkway_room = ctx.harness.create_test_room(key="TEST_GUARD_WALKWAY")
    walkway_room.db.zone = "landing"
    walkway_room.db.zone_id = "landing"
    walkway_room.db.is_lawful = True
    walkway_room.db.law_type = "standard"
    walkway_room.db.guard_patrol = True

    ctx.harness.create_test_exit(rooms[0], boundary_room, "path", aliases=[])
    ctx.harness.create_test_exit(boundary_room, walkway_room, "walkway", aliases=[])
    ctx.harness.create_test_exit(boundary_room, restricted_room, "gate", aliases=[])
    ctx.harness.create_test_exit(boundary_room, foreign_room, "archway", aliases=[])

    templates = guards.get_valid_guard_templates(limit=15, refresh=True)
    if len(templates) < 15:
        raise AssertionError(f"Expected at least 15 validated guard templates, saw {len(templates)}")
    if not all("guard_validated" in list(template.get("tags") or []) for template in templates):
        raise AssertionError("Validated guard templates were not tagged with guard_validated.")

    spawned = guards.spawn_guards_in_landing(count=15)
    if len(spawned) != 15:
        raise AssertionError(f"Expected 15 spawned guards, saw {len(spawned)}")
    for guard in spawned:
        ctx.harness.track_object(guard)
    if not all(bool(getattr(getattr(guard, "db", None), "is_guard", False)) for guard in spawned):
        raise AssertionError("Spawned patrol set contains a non-guard actor.")
    if any(bool(getattr(getattr(getattr(guard, "location", None), "db", None), "no_guard", False)) for guard in spawned):
        raise AssertionError("A guard spawned inside a no_guard room.")
    if any(not bool(getattr(getattr(getattr(guard, "location", None), "db", None), "guard_patrol", False)) for guard in spawned):
        raise AssertionError("A guard spawned in a room outside explicit patrol routes.")

    guard_room_counts = {}
    for guard in spawned:
        room_id = int(getattr(getattr(guard, "location", None), "id", 0) or 0)
        guard_room_counts[room_id] = guard_room_counts.get(room_id, 0) + 1
        if str(getattr(getattr(guard, "db", None), "zone", "") or "") != "landing":
            raise AssertionError("Spawned guard did not inherit landing zone.")
        if str(getattr(getattr(guard, "db", None), "zone_id", "") or "") != "landing":
            raise AssertionError("Spawned guard did not inherit landing zone_id.")
        if str(getattr(getattr(guard, "db", None), "template_id", "") or "") == "":
            raise AssertionError("Spawned guard did not receive a guard template id.")
    if max(guard_room_counts.values()) > 1:
        raise AssertionError(f"Initial guard spawn clumped in a single room: {guard_room_counts}")

    patrol_guard = spawned[0]
    patrol_start = patrol_guard.location
    patrol_guard.db.last_move_time = time.time() - 30.0
    patrol_guard.db.last_idle_time = time.time() - 120.0
    patrol_guard.db.recent_rooms = [int(getattr(patrol_start, "id", 0) or 0)]
    moved = guards.guard_movement_tick(patrol_guard)
    if not moved:
        raise AssertionError("Guard movement tick should move an idle guard with available exits.")
    if patrol_guard.location == patrol_start:
        raise AssertionError("Guard movement tick did not change rooms.")

    boundary_guard = spawned[9]
    boundary_guard.move_to(boundary_room, quiet=True, move_type="test")
    boundary_guard.db.patrol_anchor = boundary_room
    boundary_guard.db.patrol_radius = 4
    boundary_guard.db.last_move_time = time.time() - 30.0
    boundary_guard.db.last_idle_time = time.time() - 120.0
    boundary_exits = guards._get_valid_guard_exits(boundary_guard, boundary_room)
    boundary_exit_labels = {str(getattr(exit_obj, "key", "") or "") for exit_obj in boundary_exits}
    if "gate" in boundary_exit_labels or "archway" in boundary_exit_labels:
        raise AssertionError(f"Restricted or foreign exits should not remain patrol-valid: {boundary_exit_labels}")
    if "walkway" not in boundary_exit_labels:
        raise AssertionError(f"Non-standard in-zone exits should remain patrol-valid: {boundary_exit_labels}")
    selected_boundary_exit, _ = guards._select_guard_exit(boundary_guard, boundary_exits, force_move=True)
    if str(getattr(selected_boundary_exit, "key", "") or "") != "walkway":
        raise AssertionError("Boundary guard should select the in-zone walkway instead of blocked exits.")
    if guards.get_exit_label(selected_boundary_exit) != "the walkway":
        raise AssertionError("Non-standard exit labels should normalize for messaging.")

    clump_guard = spawned[1]
    clump_guard.move_to(patrol_guard.location, quiet=True, move_type="test")
    guards.handle_guard_room_entry(clump_guard, source_location=rooms[1])
    pending_exit_at = float(getattr(getattr(clump_guard, "db", None), "pending_clump_exit_at", 0.0) or 0.0)
    if pending_exit_at <= time.time():
        raise AssertionError("Guard clumping did not schedule an immediate follow-up exit.")
    if str(getattr(getattr(clump_guard.location, "db", None), "last_guard_entry_message", "") or "") != "Several guards pass through.":
        raise AssertionError("Guard entry message throttle did not collapse clustered guard messaging.")

    tracking_guard = spawned[4]
    tracking_guard.move_to(rooms[10], quiet=True, move_type="test")
    tracking_guard.db.patrol_anchor = rooms[10]
    tracking_guard.db.patrol_radius = 2
    tracking_guard.db.previous_room_id = int(getattr(rooms[9], "id", 0) or 0)
    watch_target = ctx.harness.create_test_character(room=rooms[10], key="TEST_GUARD_WATCH")
    watch_target.db.wanted_level = 3
    watch_target.db.last_wanted_update = time.time()
    first_watch = guards.scan_room_for_suspicion(tracking_guard)
    second_watch = guards.scan_room_for_suspicion(tracking_guard)
    watch_key = str(watch_target.id)
    first_score = int((first_watch.get(watch_key) or {}).get("score", 0) or 0)
    second_score = int((second_watch.get(watch_key) or {}).get("score", 0) or 0)
    if second_score <= first_score:
        raise AssertionError("Repeated guard scans should escalate suspicion against the same target.")
    if int(getattr(getattr(tracking_guard, "db", None), "current_target_id", 0) or 0) != int(watch_target.id or 0):
        raise AssertionError("Guard did not retain current target state after repeated suspicion scans.")
    if int(getattr(getattr(tracking_guard, "db", None), "follow_steps_remaining", 0) or 0) <= 0:
        raise AssertionError("Guard did not receive bounded follow state after escalating suspicion.")

    watch_target.move_to(rooms[11], quiet=True, move_type="test")
    tracking_guard.db.last_move_time = time.time() - 30.0
    tracking_guard.db.last_idle_time = time.time() - 120.0
    followed = guards.guard_movement_tick(tracking_guard)
    if not followed or tracking_guard.location != rooms[11]:
        raise AssertionError("Guard should follow a recently seen target into a nearby patrol room.")

    decay_guard = spawned[5]
    decayed_target = ctx.harness.create_test_character(room=decay_guard.location, key="TEST_GUARD_DECAY")
    decay_key = str(decayed_target.id)
    decay_guard.db.suspicion_targets = {
        decay_key: {
            "score": 2,
            "sightings": 1,
            "last_seen_time": time.time() - 120.0,
            "last_decay_time": time.time() - 120.0,
            "last_room_id": int(getattr(getattr(decay_guard, "location", None), "id", 0) or 0),
            "wanted_tier": "clear",
            "warned_at": 0.0,
        }
    }
    decay_result = guards.decay_suspicion(decay_guard)
    if decay_key in decay_result:
        raise AssertionError("Guard suspicion decay should clear stale low-suspicion targets.")

    warning_guard = spawned[6]
    warning_target = ctx.harness.create_test_character(room=warning_guard.location, key="TEST_GUARD_WARNING")
    warning_target.db.wanted_level = 5
    warning_target.db.last_wanted_update = time.time()
    warning_target.db.crime_flag = True
    first_warning = guards.scan_room_for_suspicion(warning_guard)
    warning_state = first_warning.get(str(warning_target.id)) or {}
    if int(getattr(getattr(warning_guard, "db", None), "warning_count", 0) or 0) <= 0:
        raise AssertionError("Guard should issue a visible warning before starting arrest.")
    if int(getattr(getattr(warning_target, "db", None), "active_guard_id", 0) or 0) != int(warning_guard.id or 0):
        raise AssertionError("Guard should claim ownership when visible enforcement begins.")
    if bool(getattr(getattr(warning_target, "db", None), "guard_attention", False)):
        raise AssertionError("Guard should not start arrest on the initial warning pass.")
    for _ in range(3):
        warning_guard.db.last_warning_time = time.time() - 11.0
        guards.process_guard_tick()
        if int(getattr(getattr(warning_guard, "db", None), "warning_count", 0) or 0) >= 3:
            break
    if int(getattr(getattr(warning_guard, "db", None), "warning_count", 0) or 0) < 3:
        raise AssertionError("Guard should escalate its warning ladder on repeated arrest-eligible detection.")
    arrest_result = guards.attempt_visible_arrest(warning_guard, warning_target)
    if not arrest_result.get("started") or not bool(getattr(getattr(warning_target, "db", None), "detained", False)):
        raise AssertionError(f"Visible arrest attempt should resolve after the warning ladder, saw: {arrest_result}")

    coordinator_primary = spawned[7]
    coordinator_support = spawned[8]
    shared_room = rooms[12]
    coordinator_primary.move_to(shared_room, quiet=True, move_type="test")
    coordinator_support.move_to(shared_room, quiet=True, move_type="test")
    coordinated_target = ctx.harness.create_test_character(room=shared_room, key="TEST_GUARD_COORDINATED")
    coordinated_target.db.wanted_level = 3
    coordinated_target.db.last_wanted_update = time.time()
    guards.scan_room_for_suspicion(coordinator_primary)
    support_state = dict(getattr(getattr(coordinator_support, "db", None), "suspicion_targets", None) or {})
    support_entry = support_state.get(str(coordinated_target.id)) or {}
    if int((support_entry or {}).get("score", 0) or 0) <= 0:
        raise AssertionError("Nearby guards should inherit a small coordinated suspicion increase.")

    suspect_room = spawned[2].location
    suspect = ctx.harness.create_test_character(room=suspect_room, key="TEST_GUARD_WANTED")
    suspect.db.profession = "thief"
    suspect.db.wanted_level = 5
    suspect.db.last_wanted_update = time.time()
    suspect.db.crime_flag = True
    suspicion_snapshot = guards.scan_room_for_suspicion(spawned[2])
    if int((suspicion_snapshot.get(str(suspect.id)) or {}).get("score", 0) or 0) <= 0:
        raise AssertionError("Guard entry scan did not record suspicion against a wanted suspect.")
    if int(getattr(getattr(spawned[2], "db", None), "warning_count", 0) or 0) <= 0:
        raise AssertionError("Guard should begin visible warning flow for an arrest-eligible suspect.")
    if bool(getattr(getattr(suspect, "db", None), "guard_attention", False)):
        raise AssertionError("Guard should warn before triggering justice attention against an arrest-eligible suspect.")
    spawned[2].db.warning_count = 3
    arrest_result = guards.attempt_visible_arrest(spawned[2], suspect)
    if not arrest_result.get("started") or not bool(getattr(getattr(suspect, "db", None), "detained", False)):
        raise AssertionError(f"Visible arrest gate should hand off to justice after the warning pass, saw: {arrest_result}")

    hidden_room = spawned[3].location
    stealthy = ctx.harness.create_test_character(room=hidden_room, key="TEST_GUARD_HIDDEN")
    stealthy.set_state("hidden", {"strength": 999, "timestamp": time.time()})
    pre_hidden_attention = bool(getattr(getattr(stealthy, "db", None), "guard_attention", False))
    guards.scan_room_for_suspicion(spawned[3])
    post_hidden_attention = bool(getattr(getattr(stealthy, "db", None), "guard_attention", False))
    if pre_hidden_attention != post_hidden_attention:
        raise AssertionError("Guard scan should not break stealth by auto-arresting a non-wanted hidden actor.")

    ctx.log(
        {
            "validated_templates": len(templates),
            "spawned_guards": len(spawned),
            "guard_room_counts": guard_room_counts,
            "patrol_guard_destination": getattr(getattr(patrol_guard, "location", None), "key", None),
            "suspicion_snapshot": suspicion_snapshot,
            "watch_score": second_score,
            "tracking_guard_destination": getattr(getattr(tracking_guard, "location", None), "key", None),
            "coordinated_support_score": int((support_entry or {}).get("score", 0) or 0),
            "scheduled_clump_exit": pending_exit_at,
        }
    )

    return {
        "validated_templates": len(templates),
        "spawned_guards": len(spawned),
        "guard_room_counts": guard_room_counts,
        "patrol_guard_destination": getattr(getattr(patrol_guard, "location", None), "key", None),
        "suspicion_snapshot": suspicion_snapshot,
        "watch_score": second_score,
        "tracking_guard_destination": getattr(getattr(tracking_guard, "location", None), "key", None),
        "coordinated_support_score": int((support_entry or {}).get("score", 0) or 0),
        "scheduled_clump_exit": pending_exit_at,
    }