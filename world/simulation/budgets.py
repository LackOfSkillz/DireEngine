import time


class TickBudget:
    def __init__(self, max_npcs, max_ms):
        self.max_npcs = int(max_npcs)
        self.max_ms = float(max_ms)
        self.start_time = None
        self.processed = 0

    def start(self):
        self.start_time = time.time()

    def exceeded(self):
        if self.processed >= self.max_npcs:
            return True
        if self.start_time is None:
            return False
        elapsed = (time.time() - self.start_time) * 1000.0
        return elapsed >= self.max_ms

    def increment(self):
        self.processed += 1


FAST_BUDGET = TickBudget(4, 3)
NORMAL_BUDGET = TickBudget(6, 5)
SLOW_BUDGET = TickBudget(10, 6)
