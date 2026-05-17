from domain.abilities.dances.badger import BadgerDance
from domain.abilities.dances.bear import BearDance
from domain.abilities.dances.cobra import CobraDance
from domain.abilities.dances.dragon import DragonDance
from domain.abilities.dances.eagle import EagleDance
from domain.abilities.dances.panther import PantherDance
from domain.abilities.dances.swan import SwanDance
from domain.abilities.dances.wolverine import WolverineDance


DANCE_REGISTRY = {
    SwanDance.name: SwanDance,
    CobraDance.name: CobraDance,
    BadgerDance.name: BadgerDance,
    EagleDance.name: EagleDance,
    BearDance.name: BearDance,
    WolverineDance.name: WolverineDance,
    PantherDance.name: PantherDance,
    DragonDance.name: DragonDance,
}

DANCE_BY_BIT = {
    SwanDance.bit_index: SwanDance,
    CobraDance.bit_index: CobraDance,
    BadgerDance.bit_index: BadgerDance,
    EagleDance.bit_index: EagleDance,
    BearDance.bit_index: BearDance,
    WolverineDance.bit_index: WolverineDance,
    PantherDance.bit_index: PantherDance,
    DragonDance.bit_index: DragonDance,
}


def normalize_dance_name(name: str) -> str:
    return str(name or "").strip().lower().replace(" ", "").replace("'", "")


DANCE_ALIASES = {}
for definition in DANCE_REGISTRY.values():
    for alias in tuple(getattr(definition, "aliases", ()) or ()):
        normalized = normalize_dance_name(alias)
        if normalized:
            DANCE_ALIASES[normalized] = definition


def get_dance_definition(name: str):
    return DANCE_ALIASES.get(normalize_dance_name(name))


def get_dance_definition_by_bit(bit_index: int):
    return DANCE_BY_BIT.get(int(bit_index))