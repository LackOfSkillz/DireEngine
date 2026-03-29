"""
Room

Rooms are simple containers that has no location of their own.

"""

from django.utils.translation import gettext as _
from evennia.objects.objects import DefaultRoom
from evennia.utils.utils import iter_to_str

from .objects import ObjectParent


class Room(ObjectParent, DefaultRoom):
    """
    Rooms are like any Object, except their location is None
    (which is default). They also use basetype_setup() to
    add locks so they cannot be puppeted or picked up.
    (to change that, use at_object_creation instead)

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Objects.
    """

    def get_display_characters(self, looker, **kwargs):
        visible = []
        for obj in self.contents:
            is_character = False
            if hasattr(obj, "is_typeclass"):
                is_character = obj.is_typeclass("typeclasses.characters.Character", exact=False)
            if obj == looker or not is_character:
                continue
            if hasattr(looker, "can_detect") and not looker.can_detect(obj):
                continue
            visible.append(obj)

        if not visible:
            return ""

        names = ", ".join(obj.get_display_name(looker, **kwargs) for obj in visible)
        return f"Characters: {names}"

    def get_display_exits(self, looker, **kwargs):
        def _sort_exits(exit_objects):
            exit_order = kwargs.get("exit_order")
            if not exit_order:
                return sorted(exit_objects, key=lambda exit_obj: str(exit_obj.key).lower())

            sort_index = {name: index for index, name in enumerate(exit_order)}
            end_pos = len(sort_index)
            return sorted(
                exit_objects,
                key=lambda exit_obj: (
                    sort_index.get(str(exit_obj.key).lower(), end_pos),
                    str(exit_obj.key).lower(),
                ),
            )

        exits = self.filter_visible(self.contents_get(content_type="exit"), looker, **kwargs)
        if not exits:
            return ""

        rendered = []
        for exit_obj in _sort_exits(exits):
            exit_name = str(exit_obj.get_display_name(looker, **kwargs))
            is_hidden = bool(getattr(exit_obj.db, "hidden_exit", False) or getattr(exit_obj.db, "secret", False))
            if is_hidden:
                continue
            rendered.append(f"|lc__clickmove__ {str(exit_obj.key)}|lt|y{exit_name}|n|le")

        exit_names = iter_to_str(rendered, endsep=_(", and"))
        return f"|w{_('Exits')}:|n {exit_names}" if exit_names else ""
