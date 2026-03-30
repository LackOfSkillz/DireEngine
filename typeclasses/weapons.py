from collections.abc import Mapping

from evennia import DefaultObject


WEAPON_SKILLS = [
    "brawling",
    "light_edge",
    "heavy_edge",
    "blunt",
    "polearm",
]


class Weapon(DefaultObject):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.item_type = "weapon"
        self.db.weapon_type = "brawling"
        self.db.damage = 5
        self.db.speed = 2.0
        self.db.damage_min = 1
        self.db.damage_max = 4
        self.db.roundtime = 3
        self.db.balance_cost = 10
        self.db.fatigue_cost = 5
        self.db.skill = "brawling"
        self.db.damage_type = "impact"
        self.db.weapon_profile = {
            "type": "brawling",
            "skill": "brawling",
            "damage": 5,
            "balance": 50,
            "speed": 2.0,
            "damage_min": 1,
            "damage_max": 4,
            "roundtime": 2.0,
        }
        self.db.damage_types = {"slice": 0, "impact": 1, "puncture": 0}
        self.db.balance = 50
        self.db.skill_scaling = {}
        self.db.unlocks = {
            20: {"damage_bonus": 2},
            40: {"flavor": True},
        }
        self.db.is_ranged = False
        self.db.weapon_range_type = None
        self.db.range_band = "melee"
        self.db.ammo_loaded = False
        self.db.ammo_type = "arrow"
        self.db.roundtime = 2.0
        self.normalize_damage_types()
        self.sync_profile_fields()

    def get_weapon_skill(self):
        profile = self.get_weapon_profile()
        return profile.get("skill") or self.db.skill or self.db.weapon_type or "brawling"

    def get_weapon_profile(self):
        profile = dict(self.db.weapon_profile or {})
        profile.setdefault("type", self.db.weapon_type or self.db.skill or "brawling")
        profile.setdefault("skill", self.db.skill or self.db.weapon_type or "brawling")
        profile.setdefault("damage", self.db.damage if self.db.damage is not None else 5)
        profile.setdefault("balance", self.db.balance if self.db.balance is not None else 50)
        profile.setdefault("speed", self.db.speed if self.db.speed is not None else self.db.roundtime if self.db.roundtime is not None else 2.0)
        profile.setdefault("damage_min", self.db.damage_min if self.db.damage_min is not None else 1)
        profile.setdefault("damage_max", self.db.damage_max if self.db.damage_max is not None else 4)
        profile.setdefault("roundtime", self.db.roundtime if self.db.roundtime is not None else 2.0)
        profile.setdefault("weapon_range_type", self.db.weapon_range_type)
        profile.setdefault("range_band", self.db.range_band if self.db.range_band is not None else "melee")
        return profile

    def sync_profile_fields(self):
        profile = self.get_weapon_profile()
        self.db.weapon_profile = profile
        self.db.weapon_type = profile.get("type", self.db.weapon_type or profile.get("skill", "brawling"))
        self.db.skill = profile.get("skill", self.db.skill or "brawling")
        self.db.damage = profile.get("damage", self.db.damage)
        self.db.balance = profile.get("balance", self.db.balance)
        self.db.speed = profile.get("speed", self.db.speed or self.db.roundtime)
        self.db.damage_min = profile.get("damage_min", self.db.damage_min)
        self.db.damage_max = profile.get("damage_max", self.db.damage_max)
        self.db.roundtime = profile.get("roundtime", self.db.roundtime)
        self.db.weapon_range_type = profile.get("weapon_range_type", self.db.weapon_range_type)
        self.db.range_band = profile.get("range_band", self.db.range_band)

    def normalize_damage_types(self):
        damage_types = dict(self.db.damage_types or {})
        total = sum(damage_types.values())
        if total <= 0:
            return

        for key in damage_types:
            damage_types[key] /= total

        self.db.damage_types = damage_types

    def get_weapon_suitability(self, character):
        skill_name = self.get_weapon_profile().get("skill", "brawling")
        skill = character.get_skill(skill_name)
        return (skill - 30) * 0.5

    def get_weapon_effects(self, character):
        effects = {}
        skill_name = self.get_weapon_profile().get("skill", "brawling")
        rank = character.get_skill(skill_name)

        for tier in (self.db.skill_scaling or {}).get(skill_name, []):
            if rank >= tier.get("rank", 0):
                effects.update(tier.get("effects", {}))

        for threshold, effect in sorted((self.db.unlocks or {}).items()):
            try:
                threshold_rank = int(threshold)
            except (TypeError, ValueError):
                continue
            if rank >= threshold_rank and isinstance(effect, Mapping):
                if effect.get("damage_bonus") is not None:
                    effects["damage_bonus"] = effects.get("damage_bonus", 0) + effect.get("damage_bonus", 0)
                if effect.get("flavor"):
                    effects["flavor"] = True

        return effects

    def _clear_wielder_reference(self, wielder):
        if not wielder or not hasattr(wielder, "db"):
            return
        if getattr(wielder.db, "equipped_weapon", None) == self:
            wielder.db.equipped_weapon = None
        if getattr(self.db, "stored_in", None):
            self.db.stored_in = None

    def at_drop(self, dropper, **kwargs):
        super().at_drop(dropper, **kwargs)
        self._clear_wielder_reference(dropper)

    def at_give(self, giver, getter, **kwargs):
        super().at_give(giver, getter, **kwargs)
        self._clear_wielder_reference(giver)