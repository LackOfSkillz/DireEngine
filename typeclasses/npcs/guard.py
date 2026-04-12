import time

from typeclasses.npcs import NPC


class GuardNPC(NPC):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_guard = True
        self.db.patrol_anchor = None
        self.db.patrol_radius = 5
        self.db.last_move_time = 0.0
        self.db.last_idle_time = time.time()
        self.db.recent_rooms = []
        self.db.suspicion_targets = {}
        self.db.guard_id = None
        self.db.template_id = None
        self.db.zone = "landing"
        self.db.current_target_id = None
        self.db.current_target_name = None
        self.db.current_target_score = 0
        self.db.current_target_room_id = None
        self.db.last_seen_time = 0.0
        self.db.follow_steps_remaining = 0
        self.db.previous_room_id = 0
        self.db.enforcement_state = "idle"
        self.db.warning_count = 0
        self.db.last_warning_time = 0.0
        self.db.enforcement_started_at = 0.0

    def at_after_move(self, source_location, **kwargs):
        super().at_after_move(source_location, **kwargs)
        from world.systems.guards import handle_guard_room_entry

        handle_guard_room_entry(self, source_location=source_location)