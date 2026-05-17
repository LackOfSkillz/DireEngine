from enum import Enum


class HowlState(str, Enum):
    NORMAL = "normal"
    ENHANCED = "enhanced"
    TRAPPED = "trapped"


class RangerSafService:
    """Canonical Ranger SAF service per Gap 8 reconciliation. provenance: gsl_2004"""

    MIN_SAF = -100
    MAX_SAF = 150

    @classmethod
    def get_saf(cls, ranger) -> int:
        """Canonical single-value Ranger SAF store per S00264. provenance: gsl_2004"""
        return max(cls.MIN_SAF, min(cls.MAX_SAF, int(getattr(getattr(ranger, "db", None), "canonical_saf", 0) or 0)))

    @classmethod
    def set_saf(cls, ranger, value) -> None:
        """Canonical Ranger SAF is clamped to [-100, +150] per S00264. provenance: gsl_2004"""
        getattr(ranger, "db", None).canonical_saf = max(cls.MIN_SAF, min(cls.MAX_SAF, int(value or 0)))

    @classmethod
    def get_spellcasting_modifier(cls, ranger, spell) -> int:
        """Canonical SAF spellcasting modifier per S03371 Earth Meld reference. provenance: gsl_2004"""
        profession = str(getattr(ranger, "profession", getattr(getattr(ranger, "db", None), "profession", "")) or "").strip().lower()
        allowed_professions = tuple(str(entry or "").strip().lower() for entry in getattr(spell, "allowed_professions", ()) or ())
        spell_profession = str(getattr(spell, "profession", "") or "").strip().lower()
        if profession == "ranger" and cls.get_saf(ranger) == cls.MIN_SAF:
            return -2
        if profession != "ranger" and (spell_profession == "ranger" or "ranger" in allowed_professions):
            return 2
        return 0

    @classmethod
    def get_bow_load_modifier(cls, ranger) -> float:
        """Canonical bow-load SAF modifier per S00076 LOAD verb. provenance: gsl_2004"""
        saf = cls.get_saf(ranger)
        if saf < -50:
            return 1.1
        if saf > 75:
            return 0.9
        return 1.0

    @classmethod
    def apply_forage_harm_cost(cls, ranger) -> None:
        """Decrement Ranger SAF by 1 as directengine_canon Gate 3 machinery.

        DRG-RANGER-FORAGE-CANON-AUDIT-001 verified no canonical Ranger SAF
        authority for forage in the indexed DireLore corpus. The earlier
        S00340 citation was incorrect; that script is hide mechanics with a
        Paladin SAF branch, not forage. This method remains callable and
        tested, but is not GSL-backed and is not wired into live forage code.
        provenance: directengine_canon
        """
        cls.set_saf(ranger, cls.get_saf(ranger) - 1)

    @classmethod
    def clear_on_guild_commitment(cls, ranger) -> None:
        """Ranger guild commitment clears SAF to 0 per S00486 and S03009. provenance: gsl_2004"""
        cls.set_saf(ranger, 0)

    @classmethod
    def is_companion_tease_enabled(cls, ranger) -> bool:
        """Companion teasing requires wilderness plus SAF < -25 per S00682. provenance: gsl_2004"""
        terrain = str(
            getattr(ranger, "get_ranger_terrain_type", lambda: getattr(getattr(ranger, "location", None), "get_terrain_type", lambda: "urban")())()
            or "urban"
        ).strip().lower()
        return terrain != "urban" and cls.get_saf(ranger) < -25

    @classmethod
    def get_howl_state(cls, ranger) -> HowlState:
        """Howl state follows S01034: enhanced in wilderness with wolf and SAF < -25; trapped when stealth-howling with SAF > -1. provenance: gsl_2004"""
        saf = cls.get_saf(ranger)
        hidden = bool(getattr(getattr(ranger, "db", None), "stealthed", False)) or bool(getattr(ranger, "is_hidden", lambda: False)())
        if hidden and saf > -1:
            return HowlState.TRAPPED
        terrain = str(
            getattr(ranger, "get_ranger_terrain_type", lambda: getattr(getattr(ranger, "location", None), "get_terrain_type", lambda: "urban")())()
            or "urban"
        ).strip().lower()
        companion = getattr(ranger, "get_ranger_companion", lambda: getattr(getattr(ranger, "db", None), "ranger_companion", {}))() or {}
        label = str(companion.get("name", companion.get("type", companion.get("species", ""))) or "").strip().lower()
        if terrain != "urban" and saf < -25 and label == "wolf":
            return HowlState.ENHANCED
        return HowlState.NORMAL

    @classmethod
    def get_multi_tier_threshold(cls, ranger) -> int:
        """The verified S02847 threshold splits at SAF >= -33 in current dispatch expectations. provenance: gsl_2004"""
        return 1 if cls.get_saf(ranger) >= -33 else 0

    @classmethod
    def get_display_percent(cls, ranger) -> int:
        """SAF display percent is 0 - saf per S04537. provenance: gsl_2004"""
        return 0 - cls.get_saf(ranger)

    @classmethod
    def get_skin_yield_bonus(cls, ranger, level) -> int:
        """Canonical Ranger skin-yield bonus per S04627. provenance: gsl_2004"""
        saf = cls.get_saf(ranger)
        return int(15 + ((int(level or 0) / 4.0) * ((100 - (saf + 100)) / 100.0)))

    @classmethod
    def tick_drift(cls, ranger, urbanclass) -> None:
        """Ranger SAF drifts +1 urban and -1 wilderness per S00264. provenance: gsl_2004"""
        delta = 1 if int(urbanclass or 0) > 7 else -1
        cls.set_saf(ranger, cls.get_saf(ranger) + delta)