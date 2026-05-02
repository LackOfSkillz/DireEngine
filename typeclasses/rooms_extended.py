import random

from evennia.utils.utils import repeat

from engine.render.state_markup import build_render_context, render_state_markup

from .rooms import Room


class ExtendedDireRoom(Room):
    """
    Project-local extended room implementation using the Evennia extended-room
    storage model without depending on the contrib module import path.
    """

    room_state_tag_category = "room_state"
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
        from world.calendar import get_current_time_of_day

        return get_current_time_of_day()

    def get_season(self):
        from world.calendar import get_current_season

        return get_current_season()

    def _select_stateful_desc(self):
        from world.calendar import SEASONS

        descriptions = self.all_desc()
        room_states = self.room_states
        seasons = set(SEASONS)

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

    def get_stateful_desc(self, looker=None):
        description = self._select_stateful_desc()
        context = build_render_context(self, looker=looker)
        return render_state_markup(description, context)

    def get_display_desc(self, looker, **kwargs):
        return self.get_stateful_desc(looker=looker)

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