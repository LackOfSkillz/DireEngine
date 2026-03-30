import random
import time
from collections.abc import Mapping

from typeclasses.characters import Character


class NPC(Character):
    COMBAT_AI_INTERVAL = 1.0
    IDLE_AI_INTERVAL = 8.0

    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_npc = True
        self.db.is_trainer = False
        self.db.trains_profession = None
        self.db.is_shopkeeper = False
        self.db.coin_min = 0
        self.db.coin_max = 0
        self.db.drops_box = False
        self.db.blocked_professions = []
        self.db.suspects = {}
        self.db.witnessed_crime = False

    def is_shopkeeper(self):
        return bool(getattr(self.db, "is_shopkeeper", False))

    def get_suspects(self):
        suspects = getattr(self.db, "suspects", None)
        if not isinstance(suspects, dict):
            suspects = {}
            self.db.suspects = suspects
        return suspects

    def get_suspicion_for(self, actor):
        if not actor or not getattr(actor, "id", None):
            return 0
        suspects = self.get_suspects()
        return int(suspects.get(str(actor.id), 0) or 0)

    def adjust_suspicion_for(self, actor, amount, maximum=15):
        if not actor or not getattr(actor, "id", None):
            return 0
        suspects = dict(self.get_suspects())
        key = str(actor.id)
        current = int(suspects.get(key, 0) or 0)
        updated = max(0, min(int(maximum or 0), current + int(amount or 0)))
        if updated > 0:
            suspects[key] = updated
        elif key in suspects:
            suspects.pop(key, None)
        self.db.suspects = suspects
        return updated

    def react_to(self, actor, context="presence"):
        if not actor or actor == self or not hasattr(actor, "get_profession_reaction_message"):
            return None
        reaction = actor.get_profession_reaction_message(context=context, observer=self)
        if reaction:
            actor.msg(f"{self.key} {reaction}")
        return reaction

    def can_trade(self, actor):
        if hasattr(actor, "can_trade") and not actor.can_trade():
            return False, "The shopkeeper refuses to deal with you until your debts are settled."

        blocked = {
            str(entry).strip().lower().replace("-", "_").replace(" ", "_")
            for entry in (getattr(self.db, "blocked_professions", None) or [])
            if str(entry or "").strip()
        }
        profession = actor.get_profession() if hasattr(actor, "get_profession") else None
        if profession in blocked:
            return False, f"{self.key} refuses to deal with your kind here."

        location = getattr(self, "location", None)
        alert_level = int(getattr(getattr(location, "db", None), "alert_level", 0) or 0)
        if self.is_shopkeeper() and profession == "thief" and (bool(getattr(actor.db, "crime_flag", False)) or alert_level > 0):
            return False, f"{self.key} narrows their eyes. 'No trade with thieves today.'"

        self.react_to(actor, context="trade")
        return True, ""

    def ai_tick(self):
        if not self.db.is_npc:
            return

        if self.is_dead():
            return

        if self.is_in_roundtime():
            return

        if self.is_surprised():
            self.clear_surprise()
            self.msg("You are too startled to react!")
            return

        target = self.get_target()
        has_pursuit_state = bool(self.get_state("last_seen_target") or self.get_state("empath_manipulated"))
        if not target and not has_pursuit_state:
            return

        now = time.time()
        interval = self.COMBAT_AI_INTERVAL if target else self.IDLE_AI_INTERVAL
        next_tick_at = float(getattr(self.ndb, "next_ai_tick_at", 0.0) or 0.0)
        if now < next_tick_at:
            return
        self.ndb.next_ai_tick_at = now + interval

        combat_timer = int(self.get_state("combat_timer") or 0)
        if target:
            if combat_timer <= 0:
                self.set_state("combat_timer", 5)
        elif combat_timer > 0:
            combat_timer -= 1
            if combat_timer > 0:
                self.set_state("combat_timer", combat_timer)
            else:
                self.clear_state("combat_timer")

        self.process_ai_decision()

    def process_ai_decision(self):
        manipulated = self.get_state("empath_manipulated") if hasattr(self, "get_state") else None
        if isinstance(manipulated, Mapping):
            expires_at = float(manipulated.get("expires_at", 0) or 0)
            if expires_at and time.time() >= expires_at:
                self.clear_state("empath_manipulated")
            else:
                if self.get_target():
                    self.set_target(None)
                self.db.in_combat = False
                return

        target = self.get_target()

        if not target:
            last_seen_target = self.get_state("last_seen_target")
            if last_seen_target and self.location:
                for obj in self.location.contents:
                    if getattr(obj, "id", None) == last_seen_target:
                        self.set_target(obj)
                        target = obj
                        break

        if not target:
            return

        if not target.is_alive():
            self.set_target(None)
            return

        if target.is_hidden():
            self.set_awareness("searching")
            self.ai_search()
            return

        self.evaluate_combat_state(target)

    def evaluate_combat_state(self, target):
        hp = self.db.hp or 0
        max_hp = self.db.max_hp or 0
        hp_ratio = hp / max_hp if max_hp else 1

        if not self.is_engaged_with(target):
            self.ai_advance(target)
            return

        if hp_ratio < 0.2:
            self.msg("The creature panics!")
            self.ai_retreat(target)
            return

        if hp_ratio < 0.3:
            self.ai_retreat(target)
        else:
            self.ai_attack(target)

    def ai_attack(self, target):
        self.set_state("last_seen_target", target.id)
        self.execute_cmd(f"attack {target.key}")

    def ai_advance(self, target):
        self.execute_cmd(f"advance {target.key}")

    def ai_search(self):
        self.execute_cmd("search")

    def ai_retreat(self, target):
        if random.random() < 0.6:
            self.execute_cmd("retreat")
            if target and target.db.in_combat:
                npc_hp = self.db.hp or 0
                npc_max_hp = self.db.max_hp or 1
                target_hp = target.db.hp or 0
                target_max_hp = target.db.max_hp or 1
                npc_hp_ratio = npc_hp / npc_max_hp if npc_max_hp else 1
                target_hp_ratio = target_hp / target_max_hp if target_max_hp else 1
                follow_chance = 60
                if npc_hp_ratio > target_hp_ratio:
                    follow_chance -= 10
                else:
                    follow_chance += 10
                if random.randint(1, 100) <= follow_chance:
                    target.execute_cmd(f"advance {self.key}")
        else:
            self.msg("You fail to break away!")

    def npc_combat_tick(self):
        self.ai_tick()

    def is_winning(self, target):
        return (self.db.hp or 0) > (target.db.hp or 0)

    def attempt_pursue(self, target):
        if not target or self.get_range(target) == "melee" or not self.is_winning(target):
            return False
        if random.randint(1, 100) >= 70:
            return False

        self.set_range(target, "near" if self.get_range(target) == "far" else "melee")
        self.set_roundtime(1.5)
        if self.location:
            self.location.msg_contents(f"{self.key} rushes forward to keep {target.key} engaged!")
        return True

    def attempt_retreat(self, target):
        if not target:
            return False
        if (self.db.hp or 0) >= ((self.db.max_hp or 1) * 0.3):
            return False
        if random.randint(1, 100) >= 30:
            return False

        self.set_range(target, "far")
        self.set_roundtime(1.5)
        if self.location:
            self.location.msg_contents(f"{self.key} attempts to flee!")
        return True