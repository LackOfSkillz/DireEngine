from commands.command import Command


class CmdFire(Command):
        """
        Fire your loaded ranged weapon at a target.

        Examples:
            fire goblin
            fire
        """

    key = "fire"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if caller.is_stunned():
            caller.msg("You are too stunned to fire.")
            caller.consume_stun()
            return
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return
        args = str(self.args or "").strip()
        if not hasattr(caller, "has_ranged_weapon_equipped") or not caller.has_ranged_weapon_equipped():
            caller.msg("You need a ranged weapon ready before you can fire.")
            return
        ammo_state = caller.get_equipped_ammo_state() if hasattr(caller, "get_equipped_ammo_state") else None
        if not ammo_state or not ammo_state.get("loaded"):
            caller.msg("Your weapon is not loaded.")
            return
        if not args:
            target = caller.get_target() if hasattr(caller, "get_target") else None
            if not target:
                caller.msg("Fire at whom?")
                return
            args = target.key
        caller.execute_cmd(f"attack {args}")
