from evennia.contrib.grid.slow_exit.slow_exit import MOVE_DELAY
from evennia.utils import utils

from .exits import Exit


class SlowDireExit(Exit):
    """
    Project slow-exit wrapper.

    This preserves the project's custom Exit behavior while allowing authored
    exits to delay traversal. If `db.travel_time` is set, it overrides the
    speed-based contrib delay. Otherwise the exit uses `db.move_speed` or the
    traverser's `db.move_speed`, falling back to walk speed.
    """

    def at_traverse(self, traversing_object, target_location, **kwargs):
        if traversing_object:
            traversing_object.ndb.last_traverse_direction = self.key
            try:
                from systems.onboarding import get_traverse_block

                message = get_traverse_block(self, traversing_object, target_location)
                if message:
                    traversing_object.msg(message)
                    return False
            except Exception:
                pass
            try:
                if bool(getattr(self.db, "climb_contest", False)) and hasattr(traversing_object, "resolve_climb_exit"):
                    return traversing_object.resolve_climb_exit(self, target_location)
            except Exception:
                pass

        move_speed = str(getattr(self.db, "move_speed", "") or getattr(traversing_object.db, "move_speed", "walk") or "walk").strip().lower()
        move_delay = MOVE_DELAY.get(move_speed, MOVE_DELAY["walk"])
        try:
            explicit_delay = int(getattr(self.db, "travel_time", 0) or 0)
        except (TypeError, ValueError):
            explicit_delay = 0
        if explicit_delay > 0:
            move_delay = explicit_delay

        def move_callback():
            source_location = traversing_object.location
            if traversing_object.move_to(target_location, move_type="traverse"):
                self.at_post_traverse(traversing_object, source_location)
            else:
                if self.db.err_traverse:
                    traversing_object.msg(self.db.err_traverse)
                else:
                    self.at_failed_traverse(traversing_object)

        traversing_object.msg(f"You start moving {self.key} at a {move_speed}.")
        deferred = utils.delay(move_delay, move_callback)
        traversing_object.ndb.currently_moving = deferred
        return deferred