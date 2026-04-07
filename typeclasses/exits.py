"""
Exits

Exits are connectors between Rooms. An exit always has a destination property
set and has a single command defined on itself with the same name as its key,
for allowing Characters to traverse the exit to its destination.

"""

from evennia.objects.objects import DefaultExit

from .objects import ObjectParent


class Exit(ObjectParent, DefaultExit):
    """
    Exits are connectors between rooms. Exits are normal Objects except
    they defines the `destination` property and overrides some hooks
    and methods to represent the exits.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects child classes like this.

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
        return super().at_traverse(traversing_object, target_location, **kwargs)

    def get_display_name(self, looker=None, **kwargs):
        custom_name = str(getattr(self.db, "exit_display_name", "") or "").strip()
        if custom_name:
            return custom_name
        return super().get_display_name(looker, **kwargs)
