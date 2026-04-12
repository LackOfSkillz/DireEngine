import time

from commands.command import Command
from world.systems.theft import apply_steal_reward, can_steal_from, can_steal_from_container, resolve_theft_attempt
from utils.crime import call_guards


class CmdSteal(Command):
    """
    Attempt to steal from a target's belongings.

    Examples:
        steal guard
        steal coin
    """

    key = "steal"
    locks = "cmd:all()"
    help_category = "Stealth"

    def get_theft_roundtime(self, caller, base_rt, failed=False):
        roundtime = float(base_rt)
        if getattr(caller.db, "position_state", "neutral") == "advantaged":
            roundtime -= 1
        if failed:
            roundtime += 1
        return max(1, min(roundtime, 5))

    def _resolve_target(self, caller, room, query):
        item_query, container_query = self._split_container_query(query)
        if container_query:
            container = self._find_container(caller, room, container_query)
            if not container:
                caller.msg("You do not see that container here.")
                return None, None
            owner = getattr(container, "location", None)
            awareness_target = owner if owner and owner != room else container
            return awareness_target, {
                "requested_item": item_query,
                "container": container,
                "awareness_target": awareness_target,
                "source_label": getattr(container, "key", "container"),
            }
        if hasattr(room, "is_shop") and room.is_shop():
            direct = caller.search(query, location=room, quiet=True)
            if direct:
                return direct[0], {"requested_item": query}
            shopkeeper = room.get_shopkeeper() if hasattr(room, "get_shopkeeper") else None
            if shopkeeper:
                return shopkeeper, {"requested_item": query}
        target = caller.search(query, location=room)
        if not target:
            return None, None
        return target, {"requested_item": query}

    def _split_container_query(self, query):
        raw = str(query or "").strip()
        marker = " from "
        if marker not in raw.lower():
            return raw, None
        index = raw.lower().rfind(marker)
        return raw[:index].strip(), raw[index + len(marker):].strip()

    def _find_container(self, caller, room, query):
        candidates = []
        for obj in list(getattr(room, "contents", []) or []):
            if bool(getattr(getattr(obj, "db", None), "is_container", False)):
                candidates.append(obj)
            for nested in list(getattr(obj, "contents", []) or []):
                if bool(getattr(getattr(nested, "db", None), "is_container", False)):
                    candidates.append(nested)
        if hasattr(caller, "resolve_numbered_candidate"):
            container, matches, _, _ = caller.resolve_numbered_candidate(query, candidates, default_first=False)
            if container:
                return container
            if matches and len(matches) > 1 and hasattr(caller, "msg_numbered_matches"):
                caller.msg_numbered_matches(query, matches)
                return None
        lowered = str(query or "").strip().lower()
        for candidate in candidates:
            if str(getattr(candidate, "key", "") or "").strip().lower() == lowered:
                return candidate
        return None

    def _apply_detection_effects(self, caller, target):
        room = getattr(caller, "location", None)
        if hasattr(target, "set_awareness"):
            target.set_awareness("alert")
        if hasattr(target, "set_attention_state"):
            target.set_attention_state("alert")
        if hasattr(caller, "set_position_state"):
            caller.set_position_state("exposed")
        if hasattr(target, "db"):
            target.db.witnessed_crime = True
        if room and not (hasattr(room, "is_lawless") and room.is_lawless()):
            room.db.alert_level = int(getattr(room.db, "alert_level", 0) or 0) + 2
            call_guards(room, caller)
        caller.reveal()

    def _message_success(self, caller, target, reward, result):
        summary = (reward or {}).get("summary") if reward else None
        margin = int(result.get("margin", 0) or 0)
        source_label = str(result.get("source_label") or getattr(target, "key", "them") or "them")
        if not summary:
            caller.msg("You find nothing worth stealing.")
            return
        if margin >= 25:
            caller.msg(f"You cleanly steal {summary} from {source_label}.")
            return
        caller.msg(f"You clumsily lift {summary} from {source_label}, but escape notice.")

    def _message_failure(self, caller, target, result):
        if result.get("caught"):
            caller.msg(f"{target.key} catches you reaching for their belongings!")
            target.msg(f"You catch {caller.key} trying to steal from you!")
            room = getattr(caller, "location", None)
            if room:
                room.msg_contents(f"{target.key} reacts sharply as {caller.key} is caught stealing!", exclude=[caller, target])
            return
        caller.msg("You falter, but recover before anyone notices.")

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Steal from whom?")
            return

        room = caller.location
        if not room:
            caller.msg("There is no one here to steal from.")
            return

        target, context = self._resolve_target(caller, room, self.args.strip())
        if not target:
            return

        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        now = time.time()
        if context.get("container") is not None:
            allowed, message = can_steal_from_container(caller, context.get("container"), requested_item=context.get("requested_item"))
        else:
            allowed, message = can_steal_from(caller, target)
        if not allowed:
            caller.msg(message)
            return

        caller.db.recent_action = True
        caller.db.recent_action_timer = now

        result = resolve_theft_attempt(caller, target, context={**context, "room": room})
        reward_source = context.get("container") or target
        reward = apply_steal_reward(caller, reward_source, result.get("item")) if result.get("success") else None
        result["source_label"] = context.get("source_label") or getattr(target, "key", None)

        if result.get("success") and reward:
            self._message_success(caller, target, reward, result)
            caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2))
            return

        if result.get("success") and not reward:
            caller.msg("You come away empty-handed.")
            caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2))
            return

        self._message_failure(caller, target, result)
        if result.get("caught"):
            self._apply_detection_effects(caller, target)
        caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2, failed=bool(result.get("caught"))))
