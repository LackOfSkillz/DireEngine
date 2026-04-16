import time


class ZoneFacts:
    def __init__(self, zone_id):
        self.zone_id = zone_id
        self.hot_room_ids = set()
        self.active_incident_room_ids = set()
        self.active_player_room_ids = set()
        self.last_updated = 0
        self.version = 0

    def touch(self):
        self.last_updated = time.time()

    def bump_version(self):
        self.version += 1

    def invalidate(self):
        self.last_updated = 0

    def mark_player_room_active(self, room_id):
        room_id = int(room_id or 0)
        if room_id > 0 and room_id not in self.active_player_room_ids:
            self.active_player_room_ids.add(room_id)
            self.bump_version()
        self.touch()

    def clear_player_room_active(self, room_id):
        room_id = int(room_id or 0)
        if room_id in self.active_player_room_ids:
            self.active_player_room_ids.discard(room_id)
            self.bump_version()
        self.touch()

    def mark_room_hot(self, room_id):
        room_id = int(room_id or 0)
        if room_id > 0 and room_id not in self.hot_room_ids:
            self.hot_room_ids.add(room_id)
            self.bump_version()
        self.touch()

    def clear_room_hot(self, room_id):
        room_id = int(room_id or 0)
        if room_id in self.hot_room_ids:
            self.hot_room_ids.discard(room_id)
            self.bump_version()
        self.touch()

    def mark_incident_room(self, room_id):
        room_id = int(room_id or 0)
        if room_id > 0 and room_id not in self.active_incident_room_ids:
            self.active_incident_room_ids.add(room_id)
            self.bump_version()
        self.touch()

    def clear_incident_room(self, room_id):
        room_id = int(room_id or 0)
        if room_id in self.active_incident_room_ids:
            self.active_incident_room_ids.discard(room_id)
            self.bump_version()
        self.touch()

    def debug_summary(self):
        return {
            "hot_rooms": len(self.hot_room_ids),
            "incident_rooms": len(self.active_incident_room_ids),
            "active_player_rooms": len(self.active_player_room_ids),
        }


ZONE_FACTS = {}


def get_zone_facts(zone_id):
    return ZONE_FACTS.get(zone_id)


def get_or_create_zone_facts(zone_id):
    normalized = str(zone_id or "landing").strip().lower() or "landing"
    if normalized not in ZONE_FACTS:
        ZONE_FACTS[normalized] = ZoneFacts(normalized)
    return ZONE_FACTS[normalized]
