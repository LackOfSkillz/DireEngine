from evennia import Command

from world.khri import KHRI


class CmdKhri(Command):
    """
    Activate, list, or dismiss your available khri.

    Examples:
        khri
        khri cunning
    """

    key = "khri"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip().lower()
        active = dict(getattr(caller.db, "khri_active", None) or {})
        pool = int(getattr(caller.db, "khri_pool", 0) or 0)

        if not args:
            active_names = ", ".join(sorted(active)) or "none"
            caller.msg(f"Focus: {pool}. Active khri: {active_names}.")
            return

        if args.startswith("stop "):
            name = args[5:].strip()
            if name not in active:
                caller.msg("You are not sustaining that khri.")
                return
            del active[name]
            caller.db.khri_active = active
            caller.msg(f"You release your focus on {name}.")
            return

        name = args
        data = KHRI.get(name)
        if not data:
            caller.msg("Unknown khri.")
            return

        if name in active:
            caller.msg("You are already sustaining that khri.")
            return

        if len(active) >= int(getattr(caller.db, "khri_limit", 2) or 2):
            caller.msg("You cannot maintain more focus.")
            return

        cost = int(data.get("cost", 0) or 0)
        if pool < cost:
            caller.msg("You lack the focus.")
            return

        active[name] = True
        caller.db.khri_active = active
        caller.db.khri_pool = pool - cost
        caller.msg("You focus inward, sharpening your instincts.")
