def assert_roundtime_blocks(ctx, command, expected_text="before acting"):
    actor = getattr(ctx, "character", None)
    if actor is not None and hasattr(actor, "get_remaining_roundtime"):
        remaining = float(actor.get_remaining_roundtime() or 0)
        if remaining <= 0:
            raise AssertionError(f"Expected active roundtime before repeating '{command}', found remaining={remaining}")
    output_start = len(ctx.output_log)
    ctx.cmd(command)
    messages = ctx.output_log[output_start:]
    blocked = any("wait" in entry.lower() and expected_text in entry.lower() for entry in messages)
    if not blocked:
        raise AssertionError(f"Immediate repeat should be blocked by roundtime for '{command}', saw: {messages}")
    return messages