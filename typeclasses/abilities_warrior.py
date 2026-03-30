import time

from typeclasses.abilities import Ability, register_ability


class WarriorAbility(Ability):
    guilds = {"warrior"}
    required = {"skill": "attack", "rank": 0}
    visible_if = {"skill": "attack", "min_rank": 0}
    exhaustion_cost = 0

    def can_pay_tempo(self, user, amount):
        if not hasattr(user, "get_war_tempo"):
            return False, "You have no feel for battle rhythm yet."
        if user.get_war_tempo() < amount:
            return False, "You are not yet worked into a battle state."
        return True, ""

    def apply_exhaustion_cost(self, user):
        amount = int(getattr(self, "exhaustion_cost", 0) or 0)
        if amount > 0 and hasattr(user, "add_exhaustion"):
            user.add_exhaustion(amount)


class SurgeAbility(WarriorAbility):
    key = "surge"
    roundtime = 2.0
    category = "strikes"
    exhaustion_cost = 4

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 15)

    def execute(self, user, target=None):
        user.spend_war_tempo(15)
        user.set_state("warrior_surge", {"bonus": 10, "damage": 2, "expires_at": time.time() + 10})
        self.apply_exhaustion_cost(user)
        user.msg("You surge forward on the rhythm of battle.")


class IntimidateAbility(WarriorAbility):
    key = "intimidate"
    roundtime = 2.0
    category = "roars"
    exhaustion_cost = 3

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 20)

    def execute(self, user, target=None):
        target_name = getattr(target, "key", "") if target else ""
        ok, message = user.activate_warrior_roar("intimidate", target_name=target_name)
        if not ok:
            user.msg(message)
            return
        self.apply_exhaustion_cost(user)


class RallyAbility(WarriorAbility):
    key = "rally"
    roundtime = 2.0
    category = "roars"
    exhaustion_cost = 4

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 20)

    def execute(self, user, target=None):
        ok, message = user.activate_warrior_roar("rally")
        if not ok:
            user.msg(message)
            return
        self.apply_exhaustion_cost(user)


class CrushingBlowAbility(WarriorAbility):
    key = "crush"
    roundtime = 3.0
    category = "strikes"
    exhaustion_cost = 10

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 25)

    def execute(self, user, target=None):
        user.spend_war_tempo(25)
        user.set_state("warrior_crush", {"damage_multiplier": 1.25, "expires_at": time.time() + 10})
        self.apply_exhaustion_cost(user)
        user.msg("You gather yourself for a crushing blow.")


class PressAdvantageAbility(WarriorAbility):
    key = "press"
    roundtime = 2.0
    category = "strikes"
    exhaustion_cost = 6

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 20)

    def execute(self, user, target=None):
        user.spend_war_tempo(20)
        user.set_state("warrior_press", {"accuracy": 10, "expires_at": time.time() + 12})
        self.apply_exhaustion_cost(user)
        user.msg("You press your advantage and look for the opening to widen.")


class SweepAbility(WarriorAbility):
    key = "sweep"
    roundtime = 3.0
    category = "strikes"
    exhaustion_cost = 8

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 30)

    def execute(self, user, target=None):
        user.spend_war_tempo(30)
        user.set_state("warrior_sweep", {"expires_at": time.time() + 10})
        self.apply_exhaustion_cost(user)
        user.msg("You shift your stance, ready to sweep an enemy off balance.")


class SecondWindAbility(WarriorAbility):
    key = "secondwind"
    roundtime = 2.0
    category = "survival"
    exhaustion_cost = 5

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 25)

    def execute(self, user, target=None):
        user.spend_war_tempo(25)
        user.set_fatigue(max(0, int(user.db.fatigue or 0) - 20))
        user.set_balance(min(int(user.db.max_balance or 100), int(user.db.balance or 0) + 15))
        self.apply_exhaustion_cost(user)
        user.msg("You draw a second wind and steady yourself.")


class WhirlAbility(WarriorAbility):
    key = "whirl"
    roundtime = 3.0
    category = "strikes"
    exhaustion_cost = 14

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 35)

    def execute(self, user, target=None):
        user.spend_war_tempo(35)
        user.set_state("warrior_whirl", {"expires_at": time.time() + 8})
        self.apply_exhaustion_cost(user)
        user.msg("You widen your footing and prepare to whirl through nearby threats.")


class HoldGroundAbility(WarriorAbility):
    key = "hold"
    roundtime = 2.0
    category = "survival"
    exhaustion_cost = 5

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 30)

    def execute(self, user, target=None):
        user.spend_war_tempo(30)
        user.set_state("warrior_hold", {"defense": 10, "expires_at": time.time() + 15})
        self.apply_exhaustion_cost(user)
        user.msg("You plant yourself and refuse to be moved.")


class FrenzyAbility(WarriorAbility):
    key = "frenzy"
    roundtime = 3.0
    category = "survival"
    exhaustion_cost = 16

    def can_use(self, user, target=None):
        return self.can_pay_tempo(user, 40)

    def execute(self, user, target=None):
        user.spend_war_tempo(40)
        user.set_state("warrior_frenzy", {"damage_multiplier": 1.2, "accuracy": 10, "expires_at": time.time() + 15})
        self.apply_exhaustion_cost(user)
        user.msg("You give yourself over to the violence of the moment.")


register_ability(SurgeAbility())
register_ability(IntimidateAbility())
register_ability(RallyAbility())
register_ability(CrushingBlowAbility())
register_ability(PressAdvantageAbility())
register_ability(SweepAbility())
register_ability(SecondWindAbility())
register_ability(WhirlAbility())
register_ability(HoldGroundAbility())
register_ability(FrenzyAbility())
