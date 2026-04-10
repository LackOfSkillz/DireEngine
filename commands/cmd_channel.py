from commands.command import Command


class CmdChannel(Command):
    """
    Sustain a transfer through repeated empathic pulses.

    Examples:
        channel vitality
        channel bleeding
        channel stop
        channel status
    """

    key = "channel"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You cannot do that.")
            return
        args = str(self.args or "").strip().lower()
        if not args:
            caller.msg("Channel what, or 'channel stop'?")
            return
        if args == "stop":
            if hasattr(caller, "stop_empath_channel") and caller.stop_empath_channel(reason="manual", emit_message=False):
                caller.msg("You let the sustained channel go.")
            else:
                caller.msg("You are not sustaining a channel.")
            return
        if args == "status":
            state = caller.get_state("empath_channel") if hasattr(caller, "get_state") else None
            if not state:
                caller.msg("You are not sustaining a channel.")
                return
            caller.msg(f"Channel: {str(state.get('wound') or 'unknown').title()}")
            caller.msg(f"Pulses: {int(state.get('pulse_count', 0) or 0)}")
            return
        ok, message = caller.start_empath_channel(args) if hasattr(caller, "start_empath_channel") else (False, "You cannot sustain a transfer that way.")
        caller.msg(message)
