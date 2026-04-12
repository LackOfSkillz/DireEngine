from commands.command import Command


class CmdQueue(Command):
    """
    Review local triage pressure.

    Examples:
        queue
    """

    key = "queue"
    aliases = ["triage"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not getattr(caller, "is_empath", lambda: False)():
            caller.msg("You have no sense for a healing queue.")
            return
        if not getattr(caller, "location", None):
            caller.msg("You are nowhere useful for triage.")
            return

        targets = caller.get_empath_perceive_targets(include_adjacent=False) if hasattr(caller, "get_empath_perceive_targets") else []
        if hasattr(caller, "update_empath_triage_context"):
            caller.update_empath_triage_context(targets=targets, source="queue")
        entries = caller.get_empath_queue_entries() if hasattr(caller, "get_empath_queue_entries") else []
        if not entries:
            caller.msg("No one nearby appears to need immediate attention.")
            return

        caller.msg("Triage queue:")
        for index, entry in enumerate(entries, start=1):
            target = entry.get("target")
            severity = str(entry.get("severity", "stable") or "stable").replace("_", " ")
            social = str(entry.get("social", "") or "")
            context_labels = [str(label or "") for label in list(entry.get("context_labels", []) or []) if str(label or "")]
            suffix_parts = []
            if social:
                suffix_parts.append(social)
            suffix_parts.extend(context_labels)
            suffix = f" [{' | '.join(suffix_parts)}]" if suffix_parts else ""
            caller.msg(f"{index}. {getattr(target, 'key', 'Unknown')}: {severity}{suffix}")