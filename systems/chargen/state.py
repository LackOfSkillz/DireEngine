from dataclasses import dataclass, field


CHARGEN_BASE_STATS = {
    "strength": 10,
    "agility": 10,
    "reflex": 10,
    "intelligence": 10,
    "wisdom": 10,
    "stamina": 10,
}

CHARGEN_POINT_POOL = 0


@dataclass(slots=True)
class CharacterBlueprint:
    name: str | None = None
    race: str | None = None
    gender: str | None = None
    profession: str | None = None
    stats: dict = field(default_factory=dict)
    description: str | None = None
    appearance: dict = field(default_factory=dict)
    identity: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "name": self.name,
            "race": self.race,
            "gender": self.gender,
            "profession": self.profession,
            "stats": dict(self.stats or {}),
            "description": self.description,
            "appearance": dict(self.appearance or {}),
            "identity": dict(self.identity or {}),
        }


@dataclass(slots=True)
class ChargenState:
    blueprint: CharacterBlueprint = field(default_factory=CharacterBlueprint)
    current_step: str = "name"
    points_remaining: int = CHARGEN_POINT_POOL
    reserved_name: str | None = None
    base_stats: dict = field(default_factory=lambda: dict(CHARGEN_BASE_STATS))
    allocated_points: dict = field(default_factory=dict)
    appearance: dict = field(default_factory=dict)
    last_validation_error: str | None = None
