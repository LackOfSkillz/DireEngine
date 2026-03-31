"""Seed handling for deterministic DireTest runs."""

from __future__ import annotations

import os
import random


def set_seed(seed: int):
    """Apply a deterministic seed for Python-level randomness."""

    normalized = int(seed)
    random.seed(normalized)
    os.environ["DIRETEST_SEED"] = str(normalized)
    return normalized