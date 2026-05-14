"""Canonical magical feat definitions.

Feats are passive magical capabilities that consume slots from the same
magic_slot_pool used by permanently memorized spells.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Feat:
    id: str
    name: str
    description: str
    category: str
    slot_cost: int = 1
    requirements: dict[str, int] = field(default_factory=dict)
    prerequisites: list[str] = field(default_factory=list)
    allowed_professions: list[str] | None = None
    granted_by_profession: dict[str, int] = field(default_factory=dict)
    modifier_payload: dict[str, float] = field(default_factory=dict)
    unlock_payload: list[str] = field(default_factory=list)


FEAT_REGISTRY: dict[str, Feat] = {}


def _normalize_identifier(value) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def register_feat(feat: Feat) -> Feat:
    FEAT_REGISTRY[_normalize_identifier(feat.id)] = feat
    return feat


def get_feat(feat_id: str) -> Feat | None:
    return FEAT_REGISTRY.get(_normalize_identifier(feat_id))


register_feat(
    Feat(
        id="deep_attunement",
        name="Deep Attunement",
        description="Your innate connection to mana increases your attunement regeneration.",
        category="attunement",
        requirements={"attunement": 100, "arcana": 100},
        modifier_payload={"attunement_regen_multiplier": 1.10},
    )
)

register_feat(
    Feat(
        id="efficient_harnessing",
        name="Efficient Harnessing",
        description="You harness and channel mana with refined economy, reducing the attunement cost of magical actions.",
        category="attunement",
        requirements={"attunement": 100, "arcana": 100},
        modifier_payload={
            "harness_attunement_cost_multiplier": 0.90,
            "spell_attunement_cost_multiplier": 0.90,
        },
    )
)

register_feat(
    Feat(
        id="focused_preparation",
        name="Focused Preparation",
        description="Your concentration extends the time you can hold a prepared spell pattern before it dissipates.",
        category="preparation",
        requirements={"primary_magic": 100, "arcana": 100},
        modifier_payload={"prepared_expiry_bonus_seconds": 15.0},
    )
)

register_feat(
    Feat(
        id="faster_battle_preparations",
        name="Faster Battle Preparations",
        description="Your reflexes accelerate the preparation of battle-mode spells.",
        category="preparation",
        requirements={"primary_magic": 100, "arcana": 100},
        modifier_payload={"battle_prep_time_delta_seconds": -1.0},
    )
)

register_feat(
    Feat(
        id="faster_matrices",
        name="Faster Matrices",
        description="Your mastery of standard spell matrices reduces their preparation time.",
        category="preparation",
        requirements={"primary_magic": 100, "arcana": 100},
        modifier_payload={"standard_prep_time_delta_seconds": -2.0},
    )
)

register_feat(
    Feat(
        id="cautious_casting",
        name="Cautious Casting",
        description="Your careful approach to magical work reduces the injury severity of spell backfires.",
        category="casting",
        requirements={"primary_magic": 50, "arcana": 50},
        modifier_payload={"backlash_injury_multiplier": 0.75},
    )
)

register_feat(
    Feat(
        id="efficient_channeling",
        name="Efficient Channeling",
        description="Your refined channeling reduces the mana cost of sustaining cyclic spells.",
        category="attunement",
        requirements={"attunement": 100, "arcana": 100},
        granted_by_profession={"cleric": 2},
        modifier_payload={"cyclic_drain_multiplier": 0.90},
    )
)

register_feat(
    Feat(
        id="raw_channeling",
        name="Raw Channeling",
        description=(
            "You channel mana directly from your attunement to sustain cyclic spells, "
            "bypassing the need to harness mana into a held pool."
        ),
        category="attunement",
        requirements={"attunement": 100, "arcana": 100},
        granted_by_profession={"bard": 2},
        unlock_payload=["cyclic_attunement_sustain"],
    )
)