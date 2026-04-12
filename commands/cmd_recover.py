from commands.command import Command


class CmdRecover(Command):
    """
    Recover grave goods or steady yourself as a Warrior.

    Examples:
        recover
        recover grave
    """

    key = "recover"
    locks = "cmd:all()"
    help_category = "Combat"

    def func(self):
        caller = self.caller
        if hasattr(caller, "recover_grave_items"):
            target_grave = None
            raw_args = str(self.args or "").strip()
            visible_graves = [obj for obj in list(getattr(getattr(caller, "location", None), "contents", []) or []) if getattr(getattr(obj, "db", None), "is_grave", False)]
            if raw_args and getattr(caller, "location", None):
                normalized = raw_args.lower()
                for candidate in visible_graves:
                    candidate_key = str(getattr(candidate, "key", "") or "").strip().lower()
                    owner_name = str(getattr(candidate.db, "owner_name", "") or "").strip().lower()
                    if normalized in {candidate_key, "grave", f"grave of {owner_name}"}:
                        target_grave = candidate
                        break
                if not target_grave:
                    caller.msg("You see no such grave here.")
                    return
            ok, message = caller.recover_grave_items(grave=target_grave)
            if ok:
                caller.msg(message)
                if getattr(caller, "location", None):
                    caller.location.msg_contents(f"{caller.key} gathers what remains from the grave.", exclude=[caller])
                return
            if target_grave is not None or visible_graves:
                caller.msg(message)
                return

        if not hasattr(caller, "is_profession") or not caller.is_profession("warrior"):
            caller.msg("You have nothing here to recover.")
            return

        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        if hasattr(caller, "get_pressure_state") and getattr(caller.db, "in_combat", False):
            if caller.get_pressure_state() in {"high", "extreme"}:
                caller.msg("The pressure is too intense for you to recover right now.")
                return

        ok, message = caller.recover_warrior_exhaustion()
        caller.msg(message)
        if ok:
            caller.set_roundtime(3)