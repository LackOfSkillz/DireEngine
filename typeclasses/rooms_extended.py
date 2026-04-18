import datetime
import random

from evennia import gametime
from evennia.utils.utils import repeat

from .rooms import Room


class ExtendedDireRoom(Room):
    """
    Project-local extended room implementation using the Evennia extended-room
    storage model without depending on the contrib module import path.
    """

    room_state_tag_category = "room_state"
    months_per_year = 12
    hours_per_day = 24
    seasons_per_year = {
        "spring": (3 / months_per_year, 6 / months_per_year),
        "summer": (6 / months_per_year, 9 / months_per_year),
        "autumn": (9 / months_per_year, 12 / months_per_year),
        "winter": (12 / months_per_year, 3 / months_per_year),
    }
    times_of_day = {
        "night": (0, 6 / hours_per_day),
        "morning": (6 / hours_per_day, 12 / hours_per_day),
        "afternoon": (12 / hours_per_day, 18 / hours_per_day),
        "evening": (18 / hours_per_day, 0),
    }
    fallback_desc = "You see nothing special."

    def at_init(self):
        super().at_init()
        self._start_broadcast_repeat_task()

    @property
    def room_states(self):
        states = self.tags.get(category=self.room_state_tag_category, return_list=True) or []
        return sorted({str(state or "").strip().lower() for state in states if str(state or "").strip()})

    def add_room_state(self, *room_states):
        for state in room_states:
            normalized = str(state or "").strip().lower()
            if normalized:
                self.tags.add(normalized, category=self.room_state_tag_category)

    def remove_room_state(self, *room_states):
        for state in room_states:
            normalized = str(state or "").strip().lower()
            if normalized:
                self.tags.remove(normalized, category=self.room_state_tag_category)

    def clear_room_state(self):
        self.tags.clear(category=self.room_state_tag_category)

    def add_desc(self, desc, room_state=None):
        if room_state is None:
            self.attributes.add("desc", desc)
            return
        normalized = str(room_state or "").strip().lower()
        if normalized:
            self.attributes.add(f"desc_{normalized}", desc)

    def remove_desc(self, room_state):
        normalized = str(room_state or "").strip().lower()
        if normalized:
            self.attributes.remove(f"desc_{normalized}")

    def all_desc(self):
        descriptions = {None: str(getattr(self.db, "desc", "") or "")}
        for attr in list(self.db_attributes.filter(db_key__startswith="desc_").order_by("db_key")):
            state = str(getattr(attr, "key", "") or "")[5:].strip().lower()
            if state:
                descriptions[state] = str(getattr(attr, "value", "") or "")
        return descriptions

    def get_time_of_day(self):
        timestamp = gametime.gametime(absolute=True)
        datestamp = datetime.datetime.fromtimestamp(timestamp)
        timeslot = float(datestamp.hour) / self.hours_per_day
        for time_of_day, (start, end) in self.times_of_day.items():
            if start < end and start <= timeslot < end:
                return time_of_day
        return time_of_day

    def get_season(self):
        timestamp = gametime.gametime(absolute=True)
        datestamp = datetime.datetime.fromtimestamp(timestamp)
        timeslot = float(datestamp.month) / self.months_per_year
        for season, (start, end) in self.seasons_per_year.items():
            if start < end and start <= timeslot < end:
                return season
        return season

    def get_stateful_desc(self):
        descriptions = self.all_desc()
        room_states = self.room_states
        seasons = set(self.seasons_per_year.keys())

        for room_state in room_states:
            if room_state not in seasons and descriptions.get(room_state):
                return descriptions[room_state]

        for room_state in room_states:
            if room_state in seasons and descriptions.get(room_state):
                return descriptions[room_state]

        season = self.get_season()
        if descriptions.get(season):
            return descriptions[season]

        return descriptions.get(None) or self.fallback_desc

    def get_display_desc(self, looker, **kwargs):
        return self.get_stateful_desc()

    def get_detail(self, key, looker=None):
        normalized = str(key or "").strip().lower()
        details = dict(getattr(self.db, "details", {}) or {})
        if normalized in details:
            return details[normalized]
        startswith_matches = sorted(
            (detail_key for detail_key in details.keys() if str(detail_key).startswith(normalized)),
            key=len,
        )
        if startswith_matches:
            return details[startswith_matches[0]]
        return None

    def add_detail(self, key, description):
        normalized = str(key or "").strip().lower()
        if not normalized:
            return
        details = dict(getattr(self.db, "details", {}) or {})
        details[normalized] = description
        self.db.details = details

    def remove_detail(self, key, *args):
        normalized = str(key or "").strip().lower()
        details = dict(getattr(self.db, "details", {}) or {})
        details.pop(normalized, None)
        self.db.details = details

    def _start_broadcast_repeat_task(self):
        rate = int(getattr(self.db, "room_message_rate", 0) or 0)
        messages = list(getattr(self.db, "room_messages", []) or [])
        if rate > 0 and messages and not getattr(self.ndb, "broadcast_repeat_task", None):
            self.ndb.broadcast_repeat_task = repeat(rate, self.repeat_broadcast_message_to_room, persistent=False)

    def start_repeat_broadcast_messages(self):
        self._start_broadcast_repeat_task()

    def repeat_broadcast_message_to_room(self):
        messages = list(getattr(self.db, "room_messages", []) or [])
        if messages:
            self.msg_contents(random.choice(messages))