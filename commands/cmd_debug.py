from commands.command import Command


class CmdDebug(Command):
    """
    Inspect lightweight runtime debug state.

    Usage:
      debug npc <target>
    """

    key = "debug"
    locks = "cmd:perm(Developer) or perm(Admin)"
    help_category = "Admin"

    @staticmethod
    def _format_last_seen_target(target):
        last_seen_target_id = getattr(getattr(target, "db", None), "last_seen_target", None)
        current_target = target.get_target() if hasattr(target, "get_target") else None
        if current_target is not None and getattr(current_target, "id", None) == last_seen_target_id:
            return getattr(current_target, "key", None) or str(last_seen_target_id)
        if last_seen_target_id in (None, ""):
            return "None"
        if getattr(target, "location", None) is not None:
            for obj in getattr(target.location, "contents", []) or []:
                if getattr(obj, "id", None) == last_seen_target_id:
                    return getattr(obj, "key", None) or str(last_seen_target_id)
        return str(last_seen_target_id)

    @staticmethod
    def _format_assist_source(target):
        assist_source = getattr(getattr(target, "db", None), "assist_source", None)
        if assist_source in (None, ""):
            return "None"
        if getattr(target, "location", None) is not None:
            for obj in getattr(target.location, "contents", []) or []:
                if getattr(obj, "id", None) == assist_source:
                    return getattr(obj, "key", None) or str(assist_source)
        return str(assist_source)

    @staticmethod
    def _format_threat_table(target):
        if not hasattr(target, "_get_threat_table"):
            return ["Threat Table: empty"]
        threat_table = dict(target._get_threat_table() or {})
        if not threat_table:
            return ["Threat Table: empty"]
        formatted_lines = ["Threat Table:"]
        for target_id, threat_value in sorted(threat_table.items(), key=lambda item: int(item[1] or 0), reverse=True):
            label = str(target_id)
            if hasattr(target, "_resolve_threat_target"):
                resolved = target._resolve_threat_target(target_id)
                if resolved is not None:
                    label = getattr(resolved, "key", None) or label
            formatted_lines.append(f"{label}: {int(threat_value or 0)}")
        return formatted_lines

    def func(self):
        tokens = [token for token in str(self.args or "").strip().split() if token]
        if len(tokens) < 2 or str(tokens[0] or "").strip().lower() != "npc":
            self.caller.msg("Usage: debug npc <target>")
            return

        room = getattr(self.caller, "location", None)
        if room is None:
            self.caller.msg("You are nowhere.")
            return

        target_name = " ".join(tokens[1:]).strip()
        candidates = [obj for obj in room.contents if bool(getattr(getattr(obj, "db", None), "is_npc", False))]
        target, matches, base_query, index = self.caller.resolve_numbered_candidate(
            target_name,
            candidates,
            default_first=True,
        )
        if not target and matches and index is not None:
            self.caller.msg_numbered_matches(base_query, matches)
            return
        if target is None:
            self.caller.msg("You do not see that NPC here.")
            return

        current_target = target.get_target() if hasattr(target, "get_target") else getattr(getattr(target, "db", None), "target", None)
        current_target_name = getattr(current_target, "key", None) or "None"
        loop_active = target.is_combat_loop_active() if hasattr(target, "is_combat_loop_active") else False
        same_room = current_target is not None and getattr(current_target, "location", None) == getattr(target, "location", None)
        distance = target.get_range(current_target) if current_target is not None and hasattr(target, "get_range") else "not-engaged"
        last_seen_target = self._format_last_seen_target(target)
        assist_source = self._format_assist_source(target)
        top_threat = target.get_highest_threat() if hasattr(target, "get_highest_threat") else None
        top_threat_name = getattr(top_threat, "key", None) or "None"
        npc_type = getattr(getattr(target, "__class__", None), "__name__", "Unknown")
        self.caller.msg(
            "\n".join(
                [
                    f"--- NPC DEBUG: {target.key} ---",
                    f"Target: {current_target_name}",
                    f"Same room: {bool(same_room)}",
                    f"Distance: {distance}",
                    f"In combat: {bool(getattr(getattr(target, 'db', None), 'in_combat', False))}",
                    f"Loop active: {bool(loop_active)}",
                    f"Aggressive: {bool(getattr(getattr(target, 'db', None), 'aggressive', False))}",
                    f"Assist enabled: {bool(getattr(getattr(target, 'db', None), 'assist', False))}",
                    f"Assisting: {assist_source}",
                    f"Top Threat: {top_threat_name}",
                    f"Last seen: {last_seen_target}",
                    f"Typeclass: {npc_type}",
                    *self._format_threat_table(target),
                ]
            )
        )