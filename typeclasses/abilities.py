class Ability:
    key = "base"
    roundtime = 1.0

    required = {
        "skill": None,
        "rank": 0,
    }

    visible_if = {
        "skill": None,
        "min_rank": 0,
    }

    guilds = None
    category = "general"

    def can_use(self, user, target=None):
        return True, ""

    def execute(self, user, target=None):
        raise NotImplementedError("Ability must implement execute()")


ABILITY_REGISTRY = {}


def register_ability(ability):
    ABILITY_REGISTRY[ability.key] = ability


def get_ability(key):
    return ABILITY_REGISTRY.get(key)


class TestAbility(Ability):
    key = "test"
    category = "general"

    def execute(self, user, target=None):
        user.msg("You perform a test ability.")


register_ability(TestAbility())


import typeclasses.abilities_stealth
import typeclasses.abilities_perception
import typeclasses.abilities_survival