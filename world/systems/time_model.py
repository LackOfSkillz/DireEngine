"""Shared timing classification constants for engine timing work."""

from __future__ import annotations


ONE_SHOT = "one_shot"
SCHEDULED_EXPIRY = "scheduled_expiry"
CONTROLLER = "controller"
SHARED_TICKER = "shared_ticker"

VALID_TIMING_MODES = {
    ONE_SHOT,
    SCHEDULED_EXPIRY,
    CONTROLLER,
    SHARED_TICKER,
}


__all__ = [
    "ONE_SHOT",
    "SCHEDULED_EXPIRY",
    "CONTROLLER",
    "SHARED_TICKER",
    "VALID_TIMING_MODES",
]