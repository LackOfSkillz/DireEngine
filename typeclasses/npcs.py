import random

from typeclasses.characters import Character


class NPC(Character):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_npc = True
        self.db.is_trainer = False
        self.db.trains_profession = None
        self.db.is_shopkeeper = False
        self.db.witnessed_crime = False

    def is_shopkeeper(self):
        return bool(getattr(self.db, "is_shopkeeper", False))

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

        combat_timer = int(self.get_state("combat_timer") or 0)
        if self.get_target():
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

        self.set_range(target, "melee")
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

        self.set_range(target, "missile")
        self.set_roundtime(1.5)
        if self.location:
            self.location.msg_contents(f"{self.key} attempts to flee!")
        return True