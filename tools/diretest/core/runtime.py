"""Runtime hooks for active DireTest execution context."""

from __future__ import annotations


_ACTIVE_CONTEXT = None


def set_active_context(ctx):
    global _ACTIVE_CONTEXT
    _ACTIVE_CONTEXT = ctx
    return ctx


def clear_active_context(ctx=None):
    global _ACTIVE_CONTEXT
    if ctx is None or _ACTIVE_CONTEXT is ctx:
        _ACTIVE_CONTEXT = None


def get_active_context():
    return _ACTIVE_CONTEXT


def is_diretest_mode():
    ctx = get_active_context()
    return bool(ctx and getattr(ctx, "test_mode", False))


def suppress_client_payloads():
    ctx = get_active_context()
    return bool(ctx and getattr(ctx, "suppress_client_payloads", False))


def record_payload_timing(duration_ms):
    ctx = get_active_context()
    if ctx and hasattr(ctx, "record_payload_timing"):
        return ctx.record_payload_timing(duration_ms)
    return 0.0


def record_script_delay(duration_ms, source=""):
    ctx = get_active_context()
    if ctx and hasattr(ctx, "record_script_delay"):
        return ctx.record_script_delay(duration_ms, source=source)
    return 0.0