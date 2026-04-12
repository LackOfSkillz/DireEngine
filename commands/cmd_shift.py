from commands.command import Command


VALID_SHIFT_LOCATIONS = ["arm", "leg", "torso"]


class CmdShift(Command):
    """
    Relocate the worst injury on a connected patient.

    Examples:
        shift jekar arm
        shift jekar leg
        shift jekar torso
    """

    key = "shift"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You do not know how to shift injuries that way.")
            return
        raw = str(self.args or "").strip()
        if not raw:
            caller.msg("Usage: shift <target> <arm|leg|torso>")
            return
        parts = raw.split()
        if len(parts) < 2:
            caller.msg("Usage: shift <target> <arm|leg|torso>")
            return
        location = parts[-1].strip().lower()
        if location not in VALID_SHIFT_LOCATIONS:
            caller.msg("You can only shift toward an arm, leg, or torso.")
            return
        target_name = " ".join(parts[:-1]).strip()
        target = caller.search(target_name, location=caller.location)
        if not target:
            return
        ok, message = caller.shift_empath_injury(target, location) if hasattr(caller, "shift_empath_injury") else (False, "You cannot shift that injury right now.")
        caller.msg(message)
