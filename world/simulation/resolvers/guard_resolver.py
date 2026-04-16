from world.simulation.handlers.guard_state import MIN_ARREST_THRESHOLD, MIN_PURSUIT_THRESHOLD, MIN_TARGET_THRESHOLD, MIN_WARN_THRESHOLD
from world.simulation.resolvers.guard_decision import GuardContext, GuardDecision


def can_arrest_target(ctx: GuardContext):
    return bool(ctx.target_present_in_room and not ctx.target_in_custody)


def should_warn(ctx: GuardContext):
    return bool(can_arrest_target(ctx) and int(ctx.target_suspicion_level or 0) >= MIN_WARN_THRESHOLD and ctx.warning_due)


def should_arrest(ctx: GuardContext):
    return bool(
        can_arrest_target(ctx)
        and ctx.arrest_due
        and (
            int(ctx.target_suspicion_level or 0) >= MIN_ARREST_THRESHOLD
            or (int(ctx.warning_stage or 0) >= 1 and int(ctx.target_suspicion_level or 0) >= MIN_WARN_THRESHOLD)
        )
    )


def should_escort(ctx: GuardContext):
    return bool(ctx.target_in_custody and not ctx.target_is_jailed and int(ctx.custody_guard_id or 0) == int(ctx.guard_id or 0) and ctx.escort_due)


def resolve_guard_decision(guard, state, facts: GuardContext):
    if not isinstance(facts, GuardContext):
        return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "missing_context"})

    if not facts.is_valid_guard:
        return GuardDecision(action_type="NOOP", state_updates={"decision_reason": facts.unsupported_reason or "invalid_guard"})

    if facts.room_id is None:
        return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "no_location"})

    if facts.target_is_jailed:
        return GuardDecision(action_type="NOOP", target_id=int(facts.current_target_id or 0) or None, state_updates={"decision_reason": "target_jailed"})

    if facts.target_in_custody and int(facts.custody_guard_id or 0) not in {0, int(facts.guard_id or 0)}:
        return GuardDecision(action_type="NOOP", target_id=int(facts.current_target_id or 0) or None, state_updates={"decision_reason": "target_in_other_guard_custody"})

    if should_escort(facts):
        return GuardDecision(
            action_type="ESCORT",
            target_id=int(facts.current_target_id or 0) or None,
            destination_id=None,
            state_updates={"decision_reason": "target_in_custody"},
        )

    if should_arrest(facts):
        return GuardDecision(
            action_type="ARREST",
            target_id=int(facts.current_target_id or 0) or None,
            state_updates={"decision_reason": "arrest_threshold"},
        )

    if should_warn(facts) and not should_arrest(facts):
        return GuardDecision(
            action_type="WARN",
            target_id=int(facts.current_target_id or 0) or None,
            state_updates={"decision_reason": "warn_threshold"},
        )

    if can_arrest_target(facts) and facts.current_target_id is not None and int(facts.target_suspicion_level or 0) >= MIN_TARGET_THRESHOLD:
        return GuardDecision(
            action_type="OBSERVE",
            target_id=int(facts.current_target_id or 0) or None,
            state_updates={"decision_reason": "target_present_hold"},
        )

    if (
        facts.current_target_id is not None
        and facts.pursuit_target_id is not None
        and facts.pursuit_last_known_room_id is not None
        and int(facts.target_suspicion_level or 0) >= MIN_PURSUIT_THRESHOLD
        and not facts.has_players
        and not facts.has_active_incident
        and bool(facts.pursuit_due)
        and facts.significance_tier != "dormant"
    ):
        destination_id = int(facts.intercept_room_id or facts.pursuit_last_known_room_id or 0) or None
        if destination_id is not None:
            return GuardDecision(
                action_type="PURSUE",
                target_id=int(facts.pursuit_target_id or 0) or None,
                destination_id=destination_id,
                state_updates={
                    "decision_reason": "target_pursuit_due",
                    "intercept_room_id": destination_id,
                },
            )

    if (not facts.target_in_custody) and facts.current_target_id is not None and int(facts.target_suspicion_level or 0) >= MIN_TARGET_THRESHOLD:
        return GuardDecision(
            action_type="OBSERVE",
            target_id=int(facts.current_target_id or 0) or None,
            state_updates={"decision_reason": "target_tracked"},
        )

    if facts.has_players and facts.has_active_incident:
        return GuardDecision(action_type="WARN", state_updates={"decision_reason": "players_present_incident_active"})

    if facts.has_players and not facts.has_active_incident and not facts.movement_due:
        return GuardDecision(action_type="OBSERVE", state_updates={"decision_reason": "players_present_no_incident"})

    if facts.significance_tier == "hot":
        return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "hot_no_patrol"})

    if state is not None and getattr(state, "get_next_patrol_room", None):
        if state.get_next_patrol_room() is None:
            return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "missing_patrol_route"})

    if facts.target_in_custody:
        return GuardDecision(action_type="NOOP", target_id=int(facts.current_target_id or 0) or None, state_updates={"decision_reason": "custody_suppresses_pursuit_patrol"})

    if facts.target_present_in_room or (facts.pursuit_target_id is not None and int(facts.target_suspicion_level or 0) >= MIN_PURSUIT_THRESHOLD):
        return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "pursuit_suppresses_patrol"})

    if not facts.has_players and not facts.has_active_incident and facts.movement_due and facts.significance_tier != "hot":
        return GuardDecision(action_type="MOVE", state_updates={"decision_reason": "movement_due_patrol_route"})

    return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "default_noop"})
