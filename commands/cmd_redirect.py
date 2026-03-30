from commands.command import Command


class CmdRedirect(Command):
    """
    Shift a linked wound from one patient to another.

    Examples:
        redirect vitality 10 from jekar to sera
        redirect bleeding all from guard to scout
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
            caller.msg("Usage: redirect <type> <amount|all> from <source> to <target>")
            return
        lowered = raw.lower()
        if " from " not in lowered or " to " not in lowered:
            caller.msg("Usage: redirect <type> <amount|all> from <source> to <target>")
            return
        from_index = lowered.index(" from ")
        to_index = lowered.index(" to ", from_index + 6)
        prefix = raw[:from_index]
        source_name = raw[from_index + 6:to_index]
        target_name = raw[to_index + 4:]
        prefix_parts = prefix.split()
        if len(prefix_parts) < 2:
            caller.msg("Usage: redirect <type> <amount|all> from <source> to <target>")
            return
        wound_type = prefix_parts[0]
        amount_spec = prefix_parts[1]
        source = caller.search(source_name.strip(), location=caller.location)
        if not source:
            return
        target = caller.search(target_name.strip(), location=caller.location)
        if not target:
            return
        ok, message = caller.redirect_empath_wound(wound_type, amount_spec, source, target) if hasattr(caller, "redirect_empath_wound") else (False, "You cannot redirect that wound right now.")
        caller.msg(message)
        if ok:
            source.msg("The pressure eases as part of the wound leaves you.")
            target.msg("A fresh wave of pain settles into you.")
