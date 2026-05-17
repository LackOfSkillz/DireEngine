from commands.command import Command


class CmdCompanion(Command):
    """
    Command your wilderness companion.

    Examples:
        companion
        companion call wolf
        companion follow
        companion stay
        companion whistle
        companion find me
        companion attack goblin
        companion dismiss
    """

    key = "companion"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        args = str(self.args or "").strip().lower()
        tokens = [token for token in args.split() if token]

        if not args:
            if not hasattr(caller, "get_ranger_companion"):
                caller.msg("You have no companion bond to inspect.")
                return
            companion = caller.get_ranger_companion()
            mode = "following" if companion.get("state") == "present" and getattr(getattr(caller, "get_ranger_companion_entity", lambda: None)(), "db", None) and bool(getattr(caller.get_ranger_companion_entity().db, "follow_owner", True)) else "holding"
            posture = "standing"
            entity = caller.get_ranger_companion_entity() if hasattr(caller, "get_ranger_companion_entity") else None
            if entity is not None:
                posture = str(getattr(getattr(entity, "db", None), "posture", "standing") or "standing")
            caller.msg(
                f"Companion: {caller.get_ranger_companion_label()} [{companion.get('state', 'dismissed')}] bond {int(companion.get('bond', 0) or 0)}/100, {mode}, {posture}"
            )
            return

        if tokens and tokens[0] == "call":
            species = tokens[1] if len(tokens) > 1 else None
            ok, message = caller.call_ranger_companion(species=species) if hasattr(caller, "call_ranger_companion") else (False, "You cannot call a companion.")
            caller.msg(message)
            return

        if args == "dismiss":
            ok, message = caller.dismiss_ranger_companion() if hasattr(caller, "dismiss_ranger_companion") else (False, "You cannot dismiss a companion.")
            caller.msg(message)
            return

        if not hasattr(caller, "command_ranger_companion"):
            caller.msg("You cannot command a companion.")
            return

        verb = tokens[0]
        remainder = str(args[len(verb):] or "").strip()

        if verb in {"follow", "stay", "stop", "return", "sit", "stand", "hide", "unhide", "hunt", "whistle", "recall", "tease"}:
            _ok, message = caller.command_ranger_companion(verb)
            caller.msg(message)
            return

        if verb == "find":
            target = None
            if remainder and remainder not in {"me", "master", "owner", "body", "corpse"}:
                target = caller.search(remainder)
                if not target:
                    return
            _ok, message = caller.command_ranger_companion("find", target=target)
            caller.msg(message)
            return

        if verb == "attack":
            if not remainder:
                caller.msg("Usage: companion attack <target>")
                return
            target = caller.search(remainder)
            if not target:
                return
            _ok, message = caller.command_ranger_companion("attack", target=target)
            caller.msg(message)
            return

        if verb == "get":
            if not remainder:
                caller.msg("Usage: companion get <item>")
                return
            _ok, message = caller.command_ranger_companion("get", item_name=remainder)
            caller.msg(message)
            return

        if verb == "drop":
            if not remainder:
                caller.msg("Usage: companion drop <item>")
                return
            _ok, message = caller.command_ranger_companion("drop", item_name=remainder)
            caller.msg(message)
            return

        if verb == "give":
            if not remainder:
                caller.msg("Usage: companion give <item> [to <target>]")
                return
            item_name = remainder
            recipient = None
            if " to " in remainder:
                item_name, _, recipient_query = remainder.partition(" to ")
                recipient = caller.search(recipient_query.strip()) if recipient_query.strip() else None
                if recipient_query.strip() and not recipient:
                    return
            _ok, message = caller.command_ranger_companion("give", item_name=item_name.strip(), recipient=recipient)
            caller.msg(message)
            return

        caller.msg("Usage: companion call [wolf|raccoon], companion dismiss, or companion <follow|stay|return|whistle|find|attack|get|drop|give|sit|stand|hide|unhide|hunt|tease>")