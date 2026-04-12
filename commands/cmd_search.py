import time

from commands.command import Command
from world.systems import awareness, stealth, theft


class CmdSearch(Command):
    """
    Search the room for hidden objects, exits, or clues.

    Examples:
        search
        search chest
    """

    key = "search"
    locks = "cmd:all()"
    help_category = "Perception"

    def _get_detection_bonus(self, caller, target, room):
        base = 0
        if hasattr(caller, "get_skill_rank"):
            try:
                base = int(caller.get_skill_rank("perception") or 0)
            except Exception:
                base = 0
        total = awareness.get_awareness_total(caller, actor=target, context={"room": room, "observe_target": target})
        return max(0, int(total - base))

    def _find_hidden_targets(self, caller, room, args):
        lowered = str(args or "").strip().lower()
        matches = []
        for obj in list(getattr(room, "contents", []) or []):
            if obj == caller or not hasattr(obj, "is_hidden") or not obj.is_hidden():
                continue
            if lowered and lowered not in str(getattr(obj, "key", "") or "").strip().lower():
                continue
            matches.append(obj)
        return matches

    def _search_for_passage(self, caller, room):
        if not room or not hasattr(room, "has_passage") or not room.has_passage():
            return None
        known = list(getattr(getattr(caller, "db", None), "known_passages", None) or [])
        if getattr(room, "id", None) not in known:
            known.append(room.id)
            caller.db.known_passages = known
        return "You uncover the seam of a hidden passage."

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()
        room = getattr(caller, "location", None)
        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return
        if not room:
            caller.msg("There is nothing here to search.")
            return

        try:
            from systems import aftermath

            if args and aftermath.handle_search(caller, args):
                caller.db.last_search_time = time.time()
                caller.apply_thief_roundtime(2)
                return
        except Exception:
            pass

        findings = []
        for target in self._find_hidden_targets(caller, room, args):
            result = stealth.resolve_detection(
                caller,
                target,
                award_xp=True,
                active=True,
                context={"perception_bonus": self._get_detection_bonus(caller, target, room)},
            )
            if result.get("success") and result.get("margin", 0) >= 20:
                target.reveal()
                findings.append(f"You pinpoint {target.key} and drag them out of hiding.")
                continue
            if result.get("hint") == "hint":
                findings.append(f"You catch a flicker of movement from {target.key}'s hiding place.")

        if not args or "passage" in args.lower() or "hidden" in args.lower():
            passage_message = self._search_for_passage(caller, room)
            if passage_message:
                findings.append(passage_message)

        if args:
            target = caller.search(args, location=caller.location)
            if not target:
                if findings:
                    caller.msg("\n".join(findings))
                    caller.db.last_search_time = time.time()
                    theft.increase_room_suspicion(room, amount=1)
                    caller.apply_thief_roundtime(2)
                    return
                caller.msg("You search carefully but uncover nothing new.")
                caller.db.last_search_time = time.time()
                theft.increase_room_suspicion(room, amount=1)
                caller.apply_thief_roundtime(2)
                return
            if hasattr(caller, "search_loot_target") and bool(getattr(getattr(target, "db", None), "is_npc", False)):
                caller.search_loot_target(target)
                caller.db.last_search_time = time.time()
                caller.apply_thief_roundtime(2)
                return

        if findings:
            caller.msg("\n".join(findings))
        else:
            caller.msg("You search carefully but uncover nothing new.")
        caller.db.last_search_time = time.time()
        theft.increase_room_suspicion(room, amount=1)
        caller.apply_thief_roundtime(2)
