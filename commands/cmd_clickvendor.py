from commands.command import Command


class CmdClickVendor(Command):
    """Internal wrapper for clickable NPC interaction links."""

    key = "__clicknpc__"
    aliases = ["__clickvendor__"]
    locks = "cmd:all()"
    help_category = "System"
    auto_help = False

    def func(self):
        raw_target = (self.args or "").strip()
        if not raw_target:
            return
        caller = self.caller
        if not caller.location:
            return
        try:
            target_id = int(raw_target)
        except (TypeError, ValueError):
            target_id = 0
        target = None
        for obj in list(getattr(caller.location, "contents", []) or []):
            if target_id and int(getattr(obj, "id", 0) or 0) == target_id:
                target = obj
                break
        if not target:
            caller.msg("They are no longer here.")
            return
        if hasattr(target, "at_object_receive_click"):
            target.at_object_receive_click(caller)
            return
        if hasattr(target, "handle_interaction"):
            target.handle_interaction(caller)
