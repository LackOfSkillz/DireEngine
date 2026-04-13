from dataclasses import dataclass


@dataclass(slots=True)
class AttunementState:
    current: float
    maximum: float


@dataclass(slots=True)
class PreparedManaState:
    realm: str
    mana_input: int
    prep_cost: int
    held_mana: int = 0


@dataclass(slots=True)
class ManaContext:
    room_mana: float
    global_modifier: float
    profession_modifier: float