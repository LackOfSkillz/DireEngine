from commands.command import Command


class CmdLink(Command):
    """
    Deepen an empathic bond with a patient.

    Examples:
        link jekar
        link persistent jekar
        link deepen jekar
    """

    key = "link"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You do not know how to deepen an empathic link.")
            return
        args = str(self.args or "").strip()
        if not args:
            caller.msg("Usage: link <target>, link persistent <target>, or link deepen <target>")
            return
        persistent = False
        deepen = False
        target_name = args
        if args.lower().startswith("persistent "):
            persistent = True
            target_name = args[11:].strip()
        elif args.lower().startswith("deepen "):
            deepen = True
            target_name = args[7:].strip()
        if not target_name:
            caller.msg("Link whom?")
            return
        target = caller.search(target_name, location=caller.location)
        if not target:
            return
        ok, lines = caller.link_empath_target(target, persistent=persistent, deepen=deepen) if hasattr(caller, "link_empath_target") else (False, ["You fail to deepen the bond."])
        for line in lines if isinstance(lines, list) else [str(lines)]:
            caller.msg(line)