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
    key = "steal"
    locks = "cmd:all()"
    help_category = "Stealth"

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

        suspicion = shopkeeper.get_suspicion_for(caller) if hasattr(shopkeeper, "get_suspicion_for") else 0
        awareness = self.get_awareness_score(shopkeeper, extra_bonus=0 if is_lawless else 30)
        if hasattr(shopkeeper, "is_shopkeeper") and shopkeeper.is_shopkeeper():
            awareness += 20
        awareness += suspicion

        cooldowns["steal"] = now + 3
        caller.ndb.cooldowns = cooldowns

        success = roll + stealth > awareness + 50

        if getattr(caller.db, "debug_mode", False):
            result = "success" if success else "failed"
            caller.msg(f"[Stealth check: {result}]")
            caller.debug_log(f"[SHOPLIFT] roll={roll} stealth={stealth} awareness={awareness} suspicion={suspicion}")

        if success:
            if not item.move_to(caller, quiet=True, move_type="shoplift"):
                caller.msg("You are caught trying to steal!")
                caller.reveal()
                return
            caller.msg(f"You discreetly pocket {item.key}.")
            if hasattr(shopkeeper, "adjust_suspicion_for"):
                shopkeeper.adjust_suspicion_for(caller, 3)
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
        if not is_lawless:
            call_guards(room, caller)
        caller.reveal()

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

        awareness_score = self.get_awareness_score(target)

        total = roll + stealth
        threshold = awareness_score + 50
        margin = total - threshold

        caller.ndb.cooldowns = cooldowns
        caller.ndb.cooldowns["steal"] = now + 3

        if getattr(caller.db, "debug_mode", False):
            result = "success" if margin > 0 else "failed"
            if SOFT_FAIL_MARGIN <= margin <= 0:
                result = "soft-fail"
            caller.msg(f"[Stealth check: {result}]")
            caller.debug_log(f"[STEAL] roll={roll} stealth={stealth} awareness={awareness_score} margin={margin}")

        if margin > 0:
            if not item.move_to(caller, quiet=True, move_type="steal"):
                caller.msg("You fail to steal anything.")
                caller.reveal()
                return
            caller.msg(f"You successfully steal {item.key}.")
            caller.reveal()
            return

        if margin >= SOFT_FAIL_MARGIN:
            caller.msg("You hesitate and withdraw unnoticed.")
            return

        caller.msg("You fail to steal anything.")
        target.msg("You feel someone fumbling with your belongings!")
        caller.reveal()
        if hasattr(target, "set_awareness"):
            target.set_awareness("alert")
        room.msg_contents(f"{target.key} reacts suddenly!", exclude=[caller, target])