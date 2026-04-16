from world.simulation.kernel import SIM_KERNEL


class ZoneSimulationService:
    def __init__(self, service_id, zone_id):
        self.service_id = service_id
        self.zone_id = zone_id
        self.npc_ids = set()
        self.event_queue = []
        self.queues = {
            "fast": [],
            "normal": [],
            "slow": [],
            "deep": [],
        }
        SIM_KERNEL.register_service(self)

    def enqueue_event(self, event):
        self.event_queue.append(event)

    def process_cycle(self, ring, budget):
        pass
