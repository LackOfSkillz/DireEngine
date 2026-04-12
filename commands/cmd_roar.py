from commands.command import Command

from world.systems.warrior import ROAR_DATA, format_roar_name


class CmdRoar(Command):
    """
    Use a warrior roar.

    Examples:
      roar
      roar intimidate
      roar disrupt goblin
      roar challenge raider
      roar rallying
    """

    key = "roar"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("warrior"):
            caller.msg("You are not following the Warrior path.")
            return

        args = str(self.args or "").strip()
        if not args:
            available = []
            if hasattr(caller, "get_available_warrior_roars"):
                available = caller.get_available_warrior_roars()
            if not available:
                caller.msg("You do not yet know any roars.")
                return
            caller.msg(f"Available roars: {', '.join(format_roar_name(name) for name in available)}.")
            return

        roar_name, _, target_name = args.partition(" ")
        roar_name = roar_name.strip().lower()
        target_name = target_name.strip()

        if roar_name not in ROAR_DATA:
            caller.msg("Unknown roar.")
            return

        ok, message = caller.activate_warrior_roar(roar_name, target_name=target_name)
        caller.msg(message)