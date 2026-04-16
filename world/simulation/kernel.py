import time

from world.simulation.budgets import FAST_BUDGET, NORMAL_BUDGET, SLOW_BUDGET, TickBudget
from world.simulation.metrics import record_service_cycle


class SimulationKernel:
    def __init__(self):
        self.services = {}

    def register_service(self, service):
        self.services[service.service_id] = service

    def unregister_service(self, service_id):
        self.services.pop(service_id, None)

    def _run_ring(self, ring, budget_template):
        for service in list(self.services.values()):
            budget = TickBudget(budget_template.max_npcs, budget_template.max_ms)
            budget.start()
            started = time.perf_counter()
            try:
                service.process_cycle(ring, budget)
            except Exception:
                continue
            elapsed = (time.perf_counter() - started) * 1000.0
            record_service_cycle(service.service_id, ring, budget.processed, elapsed)

    def tick_fast(self):
        self._run_ring("fast", FAST_BUDGET)

    def tick_normal(self):
        self._run_ring("normal", NORMAL_BUDGET)

    def tick_slow(self):
        self._run_ring("slow", SLOW_BUDGET)


SIM_KERNEL = SimulationKernel()
