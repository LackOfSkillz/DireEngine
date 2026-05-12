"""Combat RNG helpers.

Implements the combat random number generator described in GSL S00265.
"""

from __future__ import annotations

import random


class CombatRng:
    """4d50 open-roll combat RNG from GSL S00265."""

    def __init__(self, rng=None):
        self._rng = rng or random.Random()

    def roll(self) -> int:
        total = 0
        first_die = 100
        while first_die > 49:
            first_die = self._rng.randint(1, 50)
            total += first_die
            total += self._rng.randint(1, 50)
            total += self._rng.randint(1, 50)
            total += self._rng.randint(1, 50)
        return total