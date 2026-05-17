from commands.command import Command
from engine.services.wound_transfer_service import WoundTransferService


class CmdTake(Command):
    """
    Draw a linked patient's wound into yourself.

    Examples:
        take shock jekar
        take vitality 20
        take bleeding all
        take poison
        take disease all
        take arm
        take chest
        take 25%
        take 50% arm
        take slow chest
    """

    key = "take"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        parts = str(self.args or "").strip().split()
        if not parts:
            caller.msg("Usage: take shock <target> | take <vitality|bleeding|poison|disease> [amount|all] | take <arm|leg|chest|head> | take <percent|slow|fast> [selector]")
            return
        wound_type = parts[0]
        if wound_type.lower() == "shock":
            if len(parts) < 2:
                caller.msg("Usage: take shock <target>")
                return
            target_name = " ".join(parts[1:]).strip()
            target, matches, base_query, index, _scope = self.resolve_target(
                target_name,
                scopes=("characters",),
                default_first=True,
            )
            if not target and matches and index is not None:
                self.msg_target_matches(base_query, matches)
                return
            if not target:
                target = caller.search(target_name, location=caller.location)
            if not target:
                return
            result = WoundTransferService.transfer(caller, patient=target, wound_type="shock")
            caller.msg((result.messages or result.errors)[0])
            return
        if wound_type.endswith("%") or wound_type.lower() in {"slow", "fast"}:
            requested_fraction = None
            requested_rate = None
            token = wound_type.lower()
            if token.endswith("%"):
                try:
                    percent_value = int(token[:-1])
                except ValueError:
                    caller.msg("Give a whole percent between 1 and 100.")
                    return
                if percent_value < 1 or percent_value > 100:
                    caller.msg("Give a whole percent between 1 and 100.")
                    return
                requested_fraction = percent_value / 100.0
            else:
                requested_rate = token

            selector = ""
            if len(parts) > 1:
                selector = caller.normalize_empath_take_selector(parts[1]) if hasattr(caller, "normalize_empath_take_selector") else ""
                if not selector:
                    caller.msg("Partial take only supports an optional arm, leg, chest, or head selector in this order.")
                    return
            if len(parts) > 2:
                caller.msg("Partial take only supports one modifier followed by an optional selector.")
                return

            result = WoundTransferService.transfer(
                caller,
                wound_type="",
                selector=selector or None,
                requested_fraction=requested_fraction,
                requested_rate=requested_rate,
            )
            caller.msg((result.messages or result.errors)[0])
            return
        selector = caller.normalize_empath_take_selector(wound_type) if hasattr(caller, "normalize_empath_take_selector") else ""
        if selector:
            if len(parts) > 1:
                caller.msg("Selective take uses your active link and draws the whole injury for now.")
                return
            result = WoundTransferService.transfer(caller, wound_type=wound_type, selector=selector)
            caller.msg((result.messages or result.errors)[0])
            return
        amount = ""
        if len(parts) > 1:
            amount = parts[1]
        result = WoundTransferService.transfer(caller, wound_type=wound_type, amount=amount)
        caller.msg((result.messages or result.errors)[0])
