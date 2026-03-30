from commands.command import Command


class CmdTake(Command):
    """
    Draw a linked patient's wound into yourself.

    Examples:
        take vitality 20
        take bleeding all
        take fatigue
        take trauma 10
        take poison 10
        take disease all
        take vitality 15 from jekar
    """

    key = "take"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        parts = str(self.args or "").strip().split()
        if not parts:
            caller.msg("Usage: take <vitality|bleeding|fatigue|trauma|poison|disease> [amount|all] [from <target>]")
            return
        wound_type = parts[0]
        amount = ""
        target = None
        if len(parts) > 1:
            if "from" in [part.lower() for part in parts[1:]]:
                lowered = [part.lower() for part in parts]
                from_index = lowered.index("from")
                if from_index > 1:
                    amount = parts[1]
                target = " ".join(parts[from_index + 1:]).strip()
            else:
                amount = parts[1]
        ok, message = caller.take_empath_wound(wound_type, amount, target=target) if hasattr(caller, "take_empath_wound") else (False, "You cannot take that wound right now.")
        caller.msg(message)
        if ok:
            patient = target
            if isinstance(patient, str) and hasattr(caller, "resolve_empath_link_target"):
                patient = caller.resolve_empath_link_target(patient, require_local=True)
            if patient is None and hasattr(caller, "get_linked_target"):
                patient = caller.get_linked_target()
            if patient:
                patient.msg("You feel your pain lessen.")
