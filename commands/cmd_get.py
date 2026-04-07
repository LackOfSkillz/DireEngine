from evennia import Command


class CmdGet(Command):
    """
    Pick up something from the room.

    Examples:
      get bow
      get bow 3
    """

    key = "get"
    aliases = ["grab"]
    help_category = "General"

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Get what?")
            return

        room = caller.location
        if not room:
            caller.msg("There is nothing here to pick up.")
            return

        candidates = [obj for obj in room.contents if obj != caller]
        obj, matches, base_query, index = caller.resolve_numbered_candidate(
            self.args,
            candidates,
            default_first=True,
        )
        if not obj:
            if matches and index is not None:
                caller.msg_numbered_matches(base_query, matches)
            else:
                caller.search(base_query or self.args, location=room)
            return

        if caller == obj:
            caller.msg("You can't get yourself.")
            return

        try:
            from systems import onboarding

            block_message = onboarding.get_pickup_block(caller, obj)
            if block_message:
                caller.msg(block_message)
                return
        except Exception:
            pass

        if not obj.access(caller, "get"):
            caller.msg(obj.db.get_err_msg if obj.db.get_err_msg else "You can't get that.")
            return
        if not obj.at_pre_get(caller):
            return
        if hasattr(caller, "can_pick_up_item") and not caller.can_pick_up_item(obj):
            return

        if not obj.move_to(caller, quiet=True, move_type="get"):
            caller.msg("That can't be picked up.")
            return

        obj.at_get(caller)
        if hasattr(caller, "update_encumbrance_state"):
            caller.update_encumbrance_state()
        try:
            from systems import onboarding

            handled, _message = onboarding.note_item_pickup(caller, obj)
            if not handled:
                try:
                    from systems import first_area

                    handled, _message = first_area.note_item_pickup(caller, obj)
                except Exception:
                    handled = False
            if not handled:
                room.msg_contents(f"$You() $conj(pick) up {obj.key}.", from_obj=caller)
        except Exception:
            room.msg_contents(f"$You() $conj(pick) up {obj.key}.", from_obj=caller)