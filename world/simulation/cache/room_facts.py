import time


class RoomFacts:
    def __init__(self, room_id):
        self.room_id = room_id
        self.player_count = 0
        self.guard_count = 0
        self.npc_count = 0
        self.crime_flag = False
        self.last_updated = 0
        self.version = 0

    def invalidate(self):
        self.last_updated = 0

    def touch(self):
        self.last_updated = time.time()

    def debug_summary(self):
        return {
            "players": self.player_count,
            "guards": self.guard_count,
            "npcs": self.npc_count,
            "crime": self.crime_flag,
        }

    def _increment_version(self):
        self.version += 1

    def _clamp_counts(self):
        self.player_count = max(0, int(self.player_count or 0))
        self.guard_count = max(0, int(self.guard_count or 0))
        self.npc_count = max(0, int(self.npc_count or 0))

    def inc_players(self):
        self.player_count += 1
        self._clamp_counts()
        self._increment_version()

    def dec_players(self):
        self.player_count -= 1
        self._clamp_counts()
        self._increment_version()

    def inc_guards(self):
        self.guard_count += 1
        self._clamp_counts()
        self._increment_version()

    def dec_guards(self):
        self.guard_count -= 1
        self._clamp_counts()
        self._increment_version()

    def inc_npcs(self):
        self.npc_count += 1
        self._clamp_counts()
        self._increment_version()

    def dec_npcs(self):
        self.npc_count -= 1
        self._clamp_counts()
        self._increment_version()

    def clear_crime(self):
        if self.crime_flag:
            self.crime_flag = False
            self._increment_version()

    def mark_crime(self):
        if not self.crime_flag:
            self.crime_flag = True
            self._increment_version()

    def update_from_scan(self, *, player_count, guard_count, npc_count, crime_flag):
        changed = False
        player_count = max(0, int(player_count or 0))
        guard_count = max(0, int(guard_count or 0))
        npc_count = max(0, int(npc_count or 0))
        crime_flag = bool(crime_flag)
        if self.player_count != player_count:
            self.player_count = player_count
            changed = True
        if self.guard_count != guard_count:
            self.guard_count = guard_count
            changed = True
        if self.npc_count != npc_count:
            self.npc_count = npc_count
            changed = True
        if self.crime_flag != crime_flag:
            self.crime_flag = crime_flag
            changed = True
        self._clamp_counts()
        if changed:
            self._increment_version()
        self.touch()


ROOM_FACTS = {}


def get_room_facts(room_id):
    return ROOM_FACTS.get(room_id)


def get_or_create_room_facts(room_id):
    if room_id not in ROOM_FACTS:
        ROOM_FACTS[room_id] = RoomFacts(room_id)
    return ROOM_FACTS[room_id]
