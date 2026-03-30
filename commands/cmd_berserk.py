from evennia import Command

from world.systems.warrior import BERSERK_DATA, format_berserk_name


class CmdBerserk(Command):
    """
    Enter a warrior berserk state.

    Examples:
      berserk power
      berserk stone
      berserk speed
      berserk stop
    """

    key = "berserk"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("warrior"):
            caller.msg("You are not following the Warrior path.")
            return

        args = str(self.args or "").strip().lower()
        active = caller.get_active_warrior_berserk() if hasattr(caller, "get_active_warrior_berserk") else None

        if not args:
            options = ", ".join(format_berserk_name(key) for key in sorted(BERSERK_DATA))
            if active:
                caller.msg(f"Active berserk: {format_berserk_name(active.get('key'))}. Available: {options}.")
            else:
                caller.msg(f"Available berserks: {options}.")
            return

        if args in {"stop", "cancel", "end"}:
            if hasattr(caller, "clear_warrior_berserk") and caller.clear_warrior_berserk(show_message=True):
                return
            caller.msg("You are not sustaining a berserk.")
            return

        if args not in BERSERK_DATA:
            caller.msg("Unknown berserk. Try power, stone, or speed.")
            return

        ok, message = caller.activate_warrior_berserk(args)
        if not ok:
            caller.msg(message)
            return

        caller.msg(message)