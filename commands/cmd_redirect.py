from commands.command import Command


class CmdRedirect(Command):
    """
    Shift a linked wound from one patient to another.

    Examples:
        redirect vitality 10 sera
        redirect bleeding all scout
    """

    key = "redirect"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You do not know how to redirect pain that way.")
            return
        raw = str(self.args or "").strip()
        if not raw:
            caller.msg("Usage: redirect <type> <amount|all> <target>")
            return
        parts = raw.split()
        if len(parts) < 3:
            caller.msg("Usage: redirect <type> <amount|all> <target>")
            return
        wound_type = parts[0]
        amount_spec = parts[1]
        target_name = " ".join(parts[2:]).strip()
        target = caller.search(target_name, location=caller.location)
        if not target:
            return
        ok, message = caller.redirect_empath_wound(wound_type, amount_spec, target) if hasattr(caller, "redirect_empath_wound") else (False, "You cannot redirect that wound right now.")
        caller.msg(message)
        if ok:
            target.msg("A fresh wave of pain settles into you.")
