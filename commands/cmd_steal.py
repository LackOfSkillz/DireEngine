import random
import time

from evennia import Command

from utils.crime import call_guards


SOFT_FAIL_MARGIN = -5

STATE_AWARENESS_SCORES = {
    "unaware": 10,
    "normal": 30,
    "alert": 50,
    "searching": 65,
}


class CmdSteal(Command):
        """
        Attempt to steal from a target's belongings.

        Examples:
            steal pouch from guard
        """

    key = "steal"
    locks = "cmd:all()"
    help_category = "Stealth"

    def get_target_memory(self, target, caller):
        return dict(getattr(target.db, "theft_memory", None) or {}).get(caller.id)

    def record_attempt(self, target, caller, now):
        theft_memory = dict(getattr(target.db, "theft_memory", None) or {})
        memory = dict(theft_memory.get(caller.id) or {"count": 0, "last_attempt": 0})
        memory["count"] = int(memory.get("count", 0) or 0) + 1
        memory["last_attempt"] = now
        theft_memory[caller.id] = memory
        target.db.theft_memory = theft_memory
        return memory

    def get_theft_difficulty_mod(self, caller, target):
        modifier = 0
        memory = self.get_target_memory(target, caller)
        if memory:
            modifier += min(25, int(memory.get("count", 0) or 0) * 5)

        if getattr(caller.db, "marked_target", None) == getattr(target, "id", None):
            modifier -= 10

        if "cunning" in (getattr(caller.db, "khri_active", None) or {}):
            modifier -= 5

        if getattr(target.db, "intimidated", False):
            modifier -= 10

        attention_state = str(getattr(target.db, "attention_state", "idle") or "idle")
        if attention_state == "distracted":
            modifier -= 10
        elif attention_state == "alert":
            modifier += 15

        position_state = str(getattr(caller.db, "position_state", "neutral") or "neutral")
        if position_state == "advantaged":
            modifier -= 10
        elif position_state == "exposed":
            modifier += 10

        if hasattr(caller, "has_recent_action_risk") and caller.has_recent_action_risk():
            modifier += 5

        return modifier

    def get_theft_roundtime(self, caller, base_rt, failed=False):
        roundtime = float(base_rt)
        if getattr(caller.db, "position_state", "neutral") == "advantaged":
            roundtime -= 1
        if failed:
            roundtime += 1
        return max(1, min(roundtime, 5))

    def get_awareness_score(self, target, extra_bonus=0):
        if hasattr(target, "get_awareness_score"):
            return int(target.get_awareness_score(extra_bonus=extra_bonus))
        awareness = target.get_awareness() if hasattr(target, "get_awareness") else "normal"
        base = STATE_AWARENESS_SCORES.get(str(awareness).lower(), 30)
        return int(base + extra_bonus)

    def pick_target_item(self, owner, query):
        items = [item for item in owner.contents if getattr(item.db, "stealable", True)]
        if not items:
            return None, items

        if hasattr(self.caller, "resolve_numbered_candidate"):
            selected, matches, _, _ = self.caller.resolve_numbered_candidate(query, items)
            if selected:
                return selected, items
            if matches:
                if len(matches) > 1 and hasattr(self.caller, "msg_numbered_matches"):
                    self.caller.msg_numbered_matches(query, matches)
                return None, items

        lowered = str(query or "").strip().lower()
        if lowered == str(owner.key).strip().lower():
            return random.choice(items), items

        for item in items:
            if str(item.key).strip().lower() == lowered:
                return item, items

        return None, items

    def handle_shoplifting(self, caller, room):
        shopkeeper = room.get_shopkeeper() if hasattr(room, "get_shopkeeper") else None
        if not shopkeeper:
            caller.msg("There is no shopkeeper here to steal from.")
            return

        is_lawless = bool(hasattr(room, "is_lawless") and room.is_lawless())

        if not caller.is_hidden():
            caller.msg("You must be hidden to do that.")
            return

        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("steal", 0) or 0):
            caller.msg("You need a moment before trying that again.")
            return

        item, items = self.pick_target_item(shopkeeper, self.args.strip())
        if not items:
            caller.msg("There is nothing here you can steal.")
            return
        if not item:
            caller.msg("You do not see that among the shop's stock.")
            return

        roll = random.randint(1, 100)
        stealth = 50
        if caller.is_profession("thief"):
            stealth += 20

        difficulty_mod = self.get_theft_difficulty_mod(caller, shopkeeper)
        suspicion = shopkeeper.get_suspicion_for(caller) if hasattr(shopkeeper, "get_suspicion_for") else 0
        awareness = self.get_awareness_score(shopkeeper, extra_bonus=0 if is_lawless else 30)
        if hasattr(shopkeeper, "is_shopkeeper") and shopkeeper.is_shopkeeper():
            awareness += 20
        awareness += suspicion

        cooldowns["steal"] = now + 3
        caller.ndb.cooldowns = cooldowns

        caller.db.recent_action = True
        caller.db.recent_action_timer = now
        self.record_attempt(shopkeeper, caller, now)

        threshold = awareness + 50 + difficulty_mod
        margin = (roll + stealth) - threshold
        success = margin > 0

        if getattr(caller.db, "debug_mode", False):
            result = "success" if success else "failed"
            if SOFT_FAIL_MARGIN - 4 <= margin <= 0:
                result = "soft-fail"
            caller.msg(f"[Stealth check: {result}]")
            caller.debug_log(
                f"[SHOPLIFT] roll={roll} stealth={stealth} awareness={awareness} suspicion={suspicion} difficulty={difficulty_mod} margin={margin}"
            )

        if success:
            if not item.move_to(caller, quiet=True, move_type="shoplift"):
                caller.msg("You are caught trying to steal!")
                caller.reveal()
                return
            caller.msg(f"You discreetly pocket {item.key}.")
            if hasattr(shopkeeper, "adjust_suspicion_for"):
                shopkeeper.adjust_suspicion_for(caller, 3)
            caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2))
            return

        if margin >= -9:
            caller.msg("You falter but recover before being noticed.")
            caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2))
            return

        caller.msg("You are caught trying to steal!")
        room.msg_contents(f"{caller.key} is trying to steal!", exclude=[])
        if hasattr(shopkeeper, "adjust_suspicion_for"):
            shopkeeper.adjust_suspicion_for(caller, 6)
        if not is_lawless and hasattr(caller, "add_crime"):
            caller.add_crime(2)
        elif not is_lawless:
            caller.db.crime_flag = True
            caller.db.crime_severity = int(getattr(caller.db, "crime_severity", 0) or 0) + 2
        shopkeeper.db.witnessed_crime = True
        if not is_lawless:
            room.db.alert_level = int(getattr(room.db, "alert_level", 0) or 0) + 2
        if not is_lawless and hasattr(shopkeeper, "set_awareness"):
            shopkeeper.set_awareness("alert")
        if hasattr(shopkeeper, "set_attention_state"):
            shopkeeper.set_attention_state("alert")
        if not is_lawless:
            call_guards(room, caller)
        if hasattr(caller, "set_position_state"):
            caller.set_position_state("exposed")
        caller.reveal()
        caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2, failed=True))

    def func(self):
        caller = self.caller
        if not self.args:
            caller.msg("Steal from whom?")
            return

        room = caller.location
        if not room:
            caller.msg("There is no one here to steal from.")
            return

        if hasattr(room, "is_shop") and room.is_shop():
            self.handle_shoplifting(caller, room)
            return

        target = caller.search(self.args.strip(), location=room)
        if not target:
            return

        if target == caller:
            caller.msg("You cannot steal from yourself.")
            return

        if getattr(target.db, "is_npc", False):
            caller.msg("You cannot steal from NPCs yet.")
            return

        if not caller.is_hidden():
            caller.msg("You must be hidden to do that.")
            return

        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        cooldowns = caller.get_ability_cooldowns() if hasattr(caller, "get_ability_cooldowns") else {}
        now = time.time()
        if now < float(cooldowns.get("steal", 0) or 0):
            caller.msg("You need a moment before trying that again.")
            return

        items = [
            item for item in target.contents
            if item != caller and not getattr(item.db, "steal_protected", False)
        ]
        if not items:
            caller.msg("They have nothing you can steal.")
            return

        item = random.choice(items) if items else None
        if not item:
            caller.msg("They have nothing you can steal.")
            return

        roll = random.randint(1, 100)
        stealth = 50
        if caller.is_profession("thief"):
            stealth += 20

        difficulty_mod = self.get_theft_difficulty_mod(caller, target)
        awareness_score = self.get_awareness_score(target)

        total = roll + stealth
        threshold = awareness_score + 50 + difficulty_mod
        margin = total - threshold

        caller.ndb.cooldowns = cooldowns
        caller.ndb.cooldowns["steal"] = now + 3
        caller.db.recent_action = True
        caller.db.recent_action_timer = now
        self.record_attempt(target, caller, now)

        if getattr(caller.db, "debug_mode", False):
            result = "success" if margin > 0 else "failed"
            if margin >= -9:
                result = "soft-fail"
            caller.msg(f"[Stealth check: {result}]")
            caller.debug_log(
                f"[STEAL] roll={roll} stealth={stealth} awareness={awareness_score} difficulty={difficulty_mod} margin={margin}"
            )

        if margin > 0:
            if not item.move_to(caller, quiet=True, move_type="steal"):
                caller.msg("You fail to steal anything.")
                caller.reveal()
                return
            caller.msg(f"You successfully steal {item.key}.")
            caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2))
            return

        if margin >= -9:
            caller.msg("You falter but recover before being noticed.")
            caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2))
            return

        caller.msg("You fail to steal anything.")
        target.msg("You feel someone fumbling with your belongings!")
        caller.reveal()
        if hasattr(target, "set_awareness"):
            target.set_awareness("alert")
        if hasattr(target, "set_attention_state"):
            target.set_attention_state("alert")
        if hasattr(caller, "set_position_state"):
            caller.set_position_state("exposed")
        if hasattr(caller, "add_crime"):
            caller.add_crime(1)
        room.msg_contents(f"{target.key} reacts suddenly!", exclude=[caller, target])
        if not (hasattr(room, "is_lawless") and room.is_lawless()):
            call_guards(room, caller)
        caller.apply_thief_roundtime(self.get_theft_roundtime(caller, 2, failed=True))