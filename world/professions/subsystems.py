from .professions import get_profession_display_name, get_profession_profile, resolve_profession_name


class ProfessionSubsystem:
    resource_key = None
    max_key = None
    default_max = 0

    def __init__(self, profession_name):
        self.profession = resolve_profession_name(profession_name)
        self.profile = get_profession_profile(self.profession)

    def get_state(self, character):
        state = {
            "key": self.profession,
            "profession": self.profession,
            "guild_tag": self.profile.get("guild_tag"),
            "label": get_profession_display_name(self.profession),
        }
        if self.resource_key and self.max_key:
            state[self.resource_key] = int(getattr(character.db, self._db_key(), 0) or 0)
            state[self.max_key] = int(getattr(character.db, self._db_max_key(), self.default_max) or self.default_max)
        return state

    def tick(self, character):
        if not self.resource_key or not self.max_key:
            return False
        current = int(getattr(character.db, self._db_key(), 0) or 0)
        maximum = int(getattr(character.db, self._db_max_key(), self.default_max) or self.default_max)
        if current >= maximum:
            return False
        setattr(character.db, self._db_key(), min(maximum, current + self.regen_amount(character)))
        return True

    def regen_amount(self, character):
        return 1

    def _db_key(self):
        return {
            "fire": "inner_fire",
            "focus": "focus",
            "transfer_pool": "transfer_pool",
            "attunement": "attunement",
        }[self.resource_key]

    def _db_max_key(self):
        return {
            "max_fire": "max_inner_fire",
            "max_focus": "max_focus",
            "max_pool": "max_transfer_pool",
            "max_attunement": "max_attunement",
        }[self.max_key]


class BarbarianSubsystem(ProfessionSubsystem):
    resource_key = "fire"
    max_key = "max_fire"
    default_max = 10


class ThiefSubsystem(ProfessionSubsystem):
    resource_key = "focus"
    max_key = "max_focus"
    default_max = 10

    def regen_amount(self, character):
        if hasattr(character, "is_hidden") and character.is_hidden():
            return 2
        return 1


class EmpathSubsystem(ProfessionSubsystem):
    resource_key = "transfer_pool"
    max_key = "max_pool"
    default_max = 10


class MagicSubsystem(ProfessionSubsystem):
    resource_key = "attunement"
    max_key = "max_attunement"
    default_max = 100

    def tick(self, character):
        return False


SUBSYSTEMS = {
    "barbarian": BarbarianSubsystem,
    "empath": EmpathSubsystem,
    "moon_mage": MagicSubsystem,
    "necromancer": MagicSubsystem,
    "thief": ThiefSubsystem,
    "warrior_mage": MagicSubsystem,
}


def create_subsystem(profession_name):
    profession = resolve_profession_name(profession_name)
    subsystem_class = SUBSYSTEMS.get(profession, ProfessionSubsystem)
    return subsystem_class(profession)