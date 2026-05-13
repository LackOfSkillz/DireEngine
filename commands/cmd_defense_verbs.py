from __future__ import annotations

from commands.command import Command
from engine.services.defense_verb_service import DefenseVerbService


class _BaseDefenseVerbCommand(Command):
    locks = "cmd:all()"
    help_category = "Combat"
    verb_key = ""

    def func(self):
        execution = DefenseVerbService.execute(self.caller, self.verb_key)
        result = execution.result
        data = dict(getattr(result, "data", {}) or {})

        if data.get("broke_stealth"):
            self.caller.msg("You come out of hiding.")
            if getattr(self.caller, "location", None):
                self.caller.location.msg_contents(f"{self.caller.key} comes out of hiding.", exclude=[self.caller])

        if not result.success:
            if data.get("error_code") == "roundtime" and hasattr(self.caller, "msg_roundtime_block"):
                self.caller.msg_roundtime_block()
                return
            block_message = str(data.get("block_message", "") or "")
            if block_message:
                self.caller.msg(block_message)
            return

        self.caller.msg(str(data.get("message", "") or execution.verb.enter_message))
        self.caller.msg(f"Roundtime: {int(data.get('roundtime', 0) or 0)} sec.")
        if getattr(self.caller, "location", None):
            self.caller.location.msg_contents(
                f"{self.caller.key} moves into a position to {execution.verb.key}.",
                exclude=[self.caller],
            )


class CmdParry(_BaseDefenseVerbCommand):
    """
    Shift into a parrying stance.

    Usage:
        parry

    Parry favors weapon-based defense.
    Roundtime: 3-4 seconds.
    """

    key = "parry"
    aliases = ["par"]
    verb_key = "parry"


class CmdDodge(_BaseDefenseVerbCommand):
    """
    Shift into a dodging stance.

    Usage:
        dodge

    Dodge maximizes evasion against the next exchange.
    Roundtime: 3-4 seconds.
    """

    key = "dodge"
    aliases = ["dod"]
    verb_key = "dodge"