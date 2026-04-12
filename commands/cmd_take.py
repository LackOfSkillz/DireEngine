from commands.command import Command


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
            target = caller.search(target_name, location=caller.location)
            if not target:
                return
            ok, message = caller.take_empath_shock(target) if hasattr(caller, "take_empath_shock") else (False, "You cannot take that burden right now.")
            caller.msg(message)
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

            ok, message = caller.take_empath_wound(
                "",
                "all",
                selector=selector or None,
                requested_fraction=requested_fraction,
                requested_rate=requested_rate,
            ) if hasattr(caller, "take_empath_wound") else (False, "You cannot take that wound right now.")
            caller.msg(message)
            if ok:
                link_state = caller.get_empath_link_state(require_local=True, emit_break_messages=False) if hasattr(caller, "get_empath_link_state") else None
                patient = link_state.get("target") if isinstance(link_state, dict) else None
                if patient:
                    if requested_fraction is not None:
                        patient.msg("You feel only part of your pain lessen.")
                    elif requested_rate == "slow":
                        patient.msg("You feel your pain ease in a slow, careful draw.")
                    else:
                        patient.msg("You feel your pain wrench sharply away.")
            return
        selector = caller.normalize_empath_take_selector(wound_type) if hasattr(caller, "normalize_empath_take_selector") else ""
        if selector:
            if len(parts) > 1:
                caller.msg("Selective take uses your active link and draws the whole injury for now.")
                return
            ok, message = caller.take_empath_wound(wound_type, "", selector=selector) if hasattr(caller, "take_empath_wound") else (False, "You cannot take that wound right now.")
            caller.msg(message)
            if ok:
                link_state = caller.get_empath_link_state(require_local=True, emit_break_messages=False) if hasattr(caller, "get_empath_link_state") else None
                patient = link_state.get("target") if isinstance(link_state, dict) else None
                if patient:
                    patient.msg("You feel a focused thread of pain lessen.")
            return
        amount = ""
        if len(parts) > 1:
            amount = parts[1]
        ok, message = caller.take_empath_wound(wound_type, amount) if hasattr(caller, "take_empath_wound") else (False, "You cannot take that wound right now.")
        caller.msg(message)
        if ok:
            link_state = caller.get_empath_link_state(require_local=True, emit_break_messages=False) if hasattr(caller, "get_empath_link_state") else None
            patient = link_state.get("target") if isinstance(link_state, dict) else None
            if patient:
                patient.msg("You feel your pain lessen.")
