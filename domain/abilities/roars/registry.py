from domain.abilities.roars.anger_the_earth import AngerTheEarthRoar
from domain.abilities.roars.banshees_wail import BansheesWailRoar
from domain.abilities.roars.caution_of_the_spider import CautionOfTheSpiderRoar
from domain.abilities.roars.honor import HonorRoar
from domain.abilities.roars.vengeance import VengeanceRoar
from domain.abilities.roars.steadfastness import SteadfastnessRoar
from domain.abilities.roars.pride import PrideRoar
from domain.abilities.roars.nobility import NobilityRoar
from domain.abilities.roars.bravery import BraveryRoar
from domain.abilities.roars.bloodthirst import BloodthirstRoar
from domain.abilities.roars.superiority import SuperiorityRoar
from domain.abilities.roars.everild_rage import EverildRageRoar
from domain.abilities.roars.deaths_embrace import DeathsEmbraceRoar
from domain.abilities.roars.deaths_lullaby import DeathsLullabyRoar
from domain.abilities.roars.deaths_shriek import DeathsShriekRoar
from domain.abilities.roars.insane_laughter import InsaneLaughterRoar
from domain.abilities.roars.kuniyo_spirit import KuniyoSpiritRoar
from domain.abilities.roars.lash_of_torment import LashOfTormentRoar
from domain.abilities.roars.magics_bane import MagicsBaneRoar
from domain.abilities.roars.mage_lament import MagesLamentRoar
from domain.abilities.roars.screech_of_madness import ScreechOfMadnessRoar
from domain.abilities.roars.serpent_hiss import SerpentHissRoar
from domain.abilities.roars.slash_the_shadows import SlashTheShadowsRoar
from domain.abilities.roars.tempestuous_fury import TempestuousFuryRoar
from domain.abilities.roars.trothfang_butchery import TrothfangButcheryRoar
from domain.abilities.roars.weighted_justice import WeightedJusticeRoar


ROAR_REGISTRY = {
    KuniyoSpiritRoar.name: KuniyoSpiritRoar,
    EverildRageRoar.name: EverildRageRoar,
    TrothfangButcheryRoar.name: TrothfangButcheryRoar,
    TempestuousFuryRoar.name: TempestuousFuryRoar,
    DeathsEmbraceRoar.name: DeathsEmbraceRoar,
    DeathsLullabyRoar.name: DeathsLullabyRoar,
    DeathsShriekRoar.name: DeathsShriekRoar,
    MagicsBaneRoar.name: MagicsBaneRoar,
    MagesLamentRoar.name: MagesLamentRoar,
    CautionOfTheSpiderRoar.name: CautionOfTheSpiderRoar,
    SerpentHissRoar.name: SerpentHissRoar,
    LashOfTormentRoar.name: LashOfTormentRoar,
    ScreechOfMadnessRoar.name: ScreechOfMadnessRoar,
    BansheesWailRoar.name: BansheesWailRoar,
    InsaneLaughterRoar.name: InsaneLaughterRoar,
    WeightedJusticeRoar.name: WeightedJusticeRoar,
    AngerTheEarthRoar.name: AngerTheEarthRoar,
    SlashTheShadowsRoar.name: SlashTheShadowsRoar,
    HonorRoar.name: HonorRoar,
    VengeanceRoar.name: VengeanceRoar,
    SteadfastnessRoar.name: SteadfastnessRoar,
    PrideRoar.name: PrideRoar,
    NobilityRoar.name: NobilityRoar,
    BraveryRoar.name: BraveryRoar,
    BloodthirstRoar.name: BloodthirstRoar,
    SuperiorityRoar.name: SuperiorityRoar,
}

ROAR_BY_BIT = {
    KuniyoSpiritRoar.bit_index: KuniyoSpiritRoar,
    EverildRageRoar.bit_index: EverildRageRoar,
    TrothfangButcheryRoar.bit_index: TrothfangButcheryRoar,
    TempestuousFuryRoar.bit_index: TempestuousFuryRoar,
    DeathsEmbraceRoar.bit_index: DeathsEmbraceRoar,
    DeathsLullabyRoar.bit_index: DeathsLullabyRoar,
    DeathsShriekRoar.bit_index: DeathsShriekRoar,
    MagicsBaneRoar.bit_index: MagicsBaneRoar,
    MagesLamentRoar.bit_index: MagesLamentRoar,
    CautionOfTheSpiderRoar.bit_index: CautionOfTheSpiderRoar,
    SerpentHissRoar.bit_index: SerpentHissRoar,
    LashOfTormentRoar.bit_index: LashOfTormentRoar,
    ScreechOfMadnessRoar.bit_index: ScreechOfMadnessRoar,
    BansheesWailRoar.bit_index: BansheesWailRoar,
    InsaneLaughterRoar.bit_index: InsaneLaughterRoar,
    WeightedJusticeRoar.bit_index: WeightedJusticeRoar,
    AngerTheEarthRoar.bit_index: AngerTheEarthRoar,
    SlashTheShadowsRoar.bit_index: SlashTheShadowsRoar,
    HonorRoar.bit_index: HonorRoar,
    VengeanceRoar.bit_index: VengeanceRoar,
    SteadfastnessRoar.bit_index: SteadfastnessRoar,
    PrideRoar.bit_index: PrideRoar,
    NobilityRoar.bit_index: NobilityRoar,
    BraveryRoar.bit_index: BraveryRoar,
    BloodthirstRoar.bit_index: BloodthirstRoar,
    SuperiorityRoar.bit_index: SuperiorityRoar,
}


def normalize_roar_name(name: str) -> str:
    return str(name or "").strip().lower().replace(" ", "").replace("'", "")

ROAR_ALIASES = {}
for definition in ROAR_REGISTRY.values():
    for alias in tuple(getattr(definition, "aliases", ()) or ()):
        normalized = normalize_roar_name(alias)
        if normalized:
            ROAR_ALIASES[normalized] = definition


def get_roar_definition(name: str):
    normalized = normalize_roar_name(name)
    return ROAR_ALIASES.get(normalized)


def get_roar_definition_by_bit(bit_index: int):
    return ROAR_BY_BIT.get(int(bit_index))