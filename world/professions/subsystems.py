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
            "devotion": "devotion",
            "fire": "inner_fire",
            "focus": "focus",
            "tempo": "war_tempo",
            "transfer_pool": "transfer_pool",
            "attunement": "attunement",
        }[self.resource_key]

    def _db_max_key(self):
        return {
            "max_devotion": "max_devotion",
            "max_fire": "max_inner_fire",
            "max_focus": "max_focus",
            "max_tempo": "max_war_tempo",
            "max_pool": "max_transfer_pool",
            "max_attunement": "max_attunement",
        }[self.max_key]


class ClericSubsystem(ProfessionSubsystem):
    resource_key = "devotion"
    max_key = "max_devotion"
    default_max = 100

    def get_state(self, character):
        state = super().get_state(character)
        if hasattr(character, "get_devotion_state"):
            state["devotion_state"] = character.get_devotion_state()
        return state

    def tick(self, character):
        if hasattr(character, "process_cleric_tick"):
            return character.process_cleric_tick()
        return False


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

    def tick(self, character):
        changed = super().tick(character)
        if hasattr(character, "process_empath_tick"):
            character.process_empath_tick()
        return changed

    def get_state(self, character):
        state = super().get_state(character)
        if hasattr(character, "get_empath_shock"):
            state["empath_shock"] = character.get_empath_shock()
        if hasattr(character, "get_empath_links"):
            links = character.get_empath_links(require_local=False, include_group=False)
            state["links"] = [
                {
                    "target": getattr(entry.get("target"), "key", None),
                    "type": entry.get("type"),
                    "priority": int(entry.get("priority", 0) or 0),
                    "strength": int(entry.get("strength", 0) or 0),
                    "strength_label": entry.get("strength_label"),
                    "deepened": bool(entry.get("deepened", False)),
                    "remaining": int(entry.get("remaining", 0) or 0),
                }
                for entry in links
            ]
            state["active_link"] = state["links"][0]["target"] if state["links"] else None
        if hasattr(character, "is_empath_overdrawn"):
            state["overdraw"] = bool(character.is_empath_overdrawn())
        if hasattr(character, "get_empath_unity_state"):
            unity = character.get_empath_unity_state()
            state["unity"] = [member.key for member in unity.get("members", [])] if unity else []
        if hasattr(character, "get_empath_wounds"):
            state["wounds"] = character.get_empath_wounds()
        return state


class WarriorSubsystem(ProfessionSubsystem):
    resource_key = "tempo"
    max_key = "max_tempo"
    default_max = 100

    def get_state(self, character):
        state = super().get_state(character)
        if hasattr(character, "get_war_tempo_state"):
            state["tempo_state"] = character.get_war_tempo_state()
        if hasattr(character, "get_active_warrior_berserk"):
            berserk = character.get_active_warrior_berserk()
            state["active_berserk"] = berserk.get("key") if berserk else None
        return state

    def tick(self, character):
        current = int(getattr(character.db, self._db_key(), 0) or 0)
        maximum = int(getattr(character.db, self._db_max_key(), self.default_max) or self.default_max)
        if current > maximum:
            if hasattr(character, "set_war_tempo"):
                character.set_war_tempo(maximum)
            else:
                setattr(character.db, self._db_key(), maximum)
            return True
        if getattr(character.db, "active_warrior_berserk", None):
            return False
        if current <= 0 or getattr(character.db, "in_combat", False):
            return False

        decay = 4
        if hasattr(character, "has_warrior_passive") and character.has_warrior_passive("tempo_decay_1"):
            decay = 3
        if hasattr(character, "set_war_tempo"):
            character.set_war_tempo(max(0, current - decay))
        else:
            setattr(character.db, self._db_key(), max(0, current - decay))
        return True


class RangerSubsystem(ProfessionSubsystem):
    def get_state(self, character):
        state = super().get_state(character)
        if hasattr(character, "get_wilderness_bond"):
            state["wilderness_bond"] = character.get_wilderness_bond()
        if hasattr(character, "get_wilderness_bond_state"):
            state["bond_state"] = character.get_wilderness_bond_state()
        if hasattr(character, "get_ranger_instinct"):
            state["instinct"] = character.get_ranger_instinct()
        if hasattr(character, "get_nature_focus"):
            state["nature_focus"] = character.get_nature_focus()
        if hasattr(character, "get_ranger_terrain_type"):
            state["terrain"] = character.get_ranger_terrain_type()
        if hasattr(character, "get_ranger_companion"):
            state["companion"] = character.get_ranger_companion()
        return state

    def tick(self, character):
        if hasattr(character, "tick_ranger_state"):
            return character.tick_ranger_state()
        return False


class MagicSubsystem(ProfessionSubsystem):
    resource_key = "attunement"
    max_key = "max_attunement"
    default_max = 100

    def tick(self, character):
        return False


SUBSYSTEMS = {
    "barbarian": BarbarianSubsystem,
    "cleric": ClericSubsystem,
    "empath": EmpathSubsystem,
    "moon_mage": MagicSubsystem,
    "necromancer": MagicSubsystem,
    "ranger": RangerSubsystem,
    "thief": ThiefSubsystem,
    "warrior": WarriorSubsystem,
    "warrior_mage": MagicSubsystem,
}


def create_subsystem(profession_name):
    profession = resolve_profession_name(profession_name)
    subsystem_class = SUBSYSTEMS.get(profession, ProfessionSubsystem)
    return subsystem_class(profession)