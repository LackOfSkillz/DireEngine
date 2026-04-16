from world.simulation.resolvers.guard_decision import GuardDecision


def legacy_guard_adapter(guard, context):
    return GuardDecision(action_type="NOOP", state_updates={"decision_reason": "legacy_adapter_noop"})
