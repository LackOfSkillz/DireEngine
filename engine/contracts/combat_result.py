class CombatResult:
    def __init__(self, success, outcome, damage=0, roundtime=0, messages=None):
        self.success = success
        self.outcome = outcome
        self.damage = damage
        self.roundtime = roundtime
        self.messages = messages or []