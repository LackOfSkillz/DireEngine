class BarbarianSafService:
    """Canonical Barbarian Inner Fire service per S00264 and adjacent guild scripts. provenance: gsl_2004"""

    MIN_SAF = 0

    @staticmethod
    def _normalize_profession(actor) -> str:
        return str(
            getattr(actor, "profession", getattr(getattr(actor, "db", None), "profession", "")) or ""
        ).strip().lower().replace("-", "_").replace(" ", "_")

    @classmethod
    def _is_barbarian(cls, actor) -> bool:
        return cls._normalize_profession(actor) == "barbarian"

    @classmethod
    def get_inner_fire(cls, actor) -> int:
        """Barbarian Inner Fire is a non-negative SAF store in canonical scripts. provenance: gsl_2004"""
        if not cls._is_barbarian(actor):
            return 0
        return max(cls.MIN_SAF, int(getattr(getattr(actor, "db", None), "canonical_saf", 0) or 0))

    @classmethod
    def set_inner_fire(cls, actor, value) -> int:
        if not cls._is_barbarian(actor):
            return 0
        amount = max(cls.MIN_SAF, int(value or 0))
        getattr(actor, "db", None).canonical_saf = amount
        return amount

    @classmethod
    def calculate_berserk_delta(cls, actor) -> int:
        """Canonical Berserk SAF delta is (discipline*3) - stamina - charisma + 75 per S00523 line 215. provenance: gsl_2004"""
        get_stat = getattr(actor, "get_stat", None)
        if callable(get_stat):
            discipline = int(get_stat("discipline") or 0)
            stamina = int(get_stat("stamina") or 0)
            charisma = int(get_stat("charisma") or 0)
        else:
            stats = dict(getattr(getattr(actor, "db", None), "stats", {}) or {})
            discipline = int(stats.get("discipline", 0) or 0)
            stamina = int(stats.get("stamina", 0) or 0)
            charisma = int(stats.get("charisma", 0) or 0)
        return int((discipline * 3) - stamina - charisma + 75)

    @classmethod
    def apply_berserk_cost(cls, actor, *, override_formula: int | None = None) -> int:
        """Apply the canonical Berserk SAF aftermath cost.

        provenance: gsl_2004 — S00523 $GO_BERSERK line 215 uses
        (pdiscipline*3) - pstamina - pcharisma + 75. The earlier flat +115
        repo value was only a rough cached approximation and is corrected here.
        """
        delta = int(override_formula) if override_formula is not None else cls.calculate_berserk_delta(actor)
        return cls.set_inner_fire(actor, cls.get_inner_fire(actor) + delta)

    @classmethod
    def apply_magic_hit_cost(cls, actor, mana) -> int:
        """Magic hits add incoming mana directly to SAF per S00264. provenance: gsl_2004"""
        return cls.set_inner_fire(actor, cls.get_inner_fire(actor) + max(0, int(mana or 0)))

    @classmethod
    def apply_magic_cast_cost(cls, actor, mana) -> int:
        """Casting magic adds mana * 5 SAF per S00264. provenance: gsl_2004"""
        spent = max(0, int(mana or 0))
        return cls.set_inner_fire(actor, cls.get_inner_fire(actor) + (spent * 5))

    @classmethod
    def tick_inner_fire_recovery(cls, actor, amount=1) -> int:
        """Inner Fire recovers downward toward zero one step at a time in the bounded placeholder seam. provenance: directengine_canon"""
        recovered = max(0, int(amount or 0))
        return cls.set_inner_fire(actor, cls.get_inner_fire(actor) - recovered)

    @classmethod
    def praise(cls, actor) -> int:
        """GM praise sets Barbarian SAF to 0 in S12052. provenance: gsl_2004"""
        return cls.set_inner_fire(actor, 0)

    @classmethod
    def curse(cls, actor) -> int:
        """GM curse adds +100 SAF in the canonical /barbar utility. provenance: gsl_2004"""
        return cls.set_inner_fire(actor, cls.get_inner_fire(actor) + 100)

    @classmethod
    def is_berserk_available(cls, actor) -> bool:
        """Canonical Berserk guard resets negative SAF to zero before proceeding in S00523. provenance: gsl_2004"""
        if not cls._is_barbarian(actor):
            return False
        current = cls.get_inner_fire(actor)
        if current < 0:
            cls.set_inner_fire(actor, 0)
            current = 0
        return current >= 0

    @classmethod
    def clear_on_guild_commitment(cls, actor) -> int:
        """Joining the Barbarian guild sets profession 1 and starts with clean SAF state. provenance: gsl_2004"""
        return cls.set_inner_fire(actor, 0)