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