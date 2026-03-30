class Ability:
    key = "base"
    roundtime = 1.0
    cooldown = 0.0

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
PROFESSION_ABILITY_MAP = {}


def register_ability(ability):
    ABILITY_REGISTRY[ability.key] = ability


def get_ability_map(character=None):
    ability_map = dict(ABILITY_REGISTRY)
    if hasattr(character, "get_profession"):
        # profession abilities extend here
        for ability_key, ability in PROFESSION_ABILITY_MAP.items():
            ability_map.setdefault(ability_key, ability)
    return ability_map


def get_ability(key, character=None):
    ability_map = get_ability_map(character)
    return ability_map.get(key)


class TestAbility(Ability):
    key = "test"
    category = "general"

    def execute(self, user, target=None):
        user.msg("You perform a test ability.")


register_ability(TestAbility())


import typeclasses.abilities_stealth
import typeclasses.abilities_perception
import typeclasses.abilities_survival
import typeclasses.abilities_warrior