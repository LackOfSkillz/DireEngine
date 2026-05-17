def build_dance_definition(
    *,
    bit_index: int,
    name: str,
    canonical_display_name: str,
    required_level: int,
    canonical_pit_master: str,
    canonical_pit_room: int,
    stat_modifiers=None,
    skill_modifiers=None,
    offense_bonuses=None,
    defense_bonuses=None,
    balance_bonus: int = 0,
    engagement_speed_bonus: int = 0,
    roar_power_modifiers=None,
):
    class _DanceDefinition:
        category = "dance"
        @classmethod
        def build_payload(cls, actor, dance_service):
            return {
                "stat_modifiers": dict(cls._stat_modifiers),
                "skill_modifiers": dict(cls._skill_modifiers),
                "offense_bonuses": dict(cls._offense_bonuses),
                "defense_bonuses": dict(cls._defense_bonuses),
                "balance_bonus": int(cls._balance_bonus),
                "engagement_speed_bonus": int(cls._engagement_speed_bonus),
                "roar_power_modifiers": dict(cls._roar_power_modifiers),
            }

    _DanceDefinition.bit_index = int(bit_index)
    _DanceDefinition.name = str(name)
    _DanceDefinition.canonical_display_name = str(canonical_display_name)
    _DanceDefinition.required_level = int(required_level)
    _DanceDefinition.canonical_pit_master = str(canonical_pit_master)
    _DanceDefinition.canonical_pit_room = int(canonical_pit_room)
    _DanceDefinition.aliases = (str(name), canonical_display_name)
    _DanceDefinition._stat_modifiers = dict(stat_modifiers or {})
    _DanceDefinition._skill_modifiers = dict(skill_modifiers or {})
    _DanceDefinition._offense_bonuses = dict(offense_bonuses or {})
    _DanceDefinition._defense_bonuses = dict(defense_bonuses or {})
    _DanceDefinition._balance_bonus = int(balance_bonus or 0)
    _DanceDefinition._engagement_speed_bonus = int(engagement_speed_bonus or 0)
    _DanceDefinition._roar_power_modifiers = dict(roar_power_modifiers or {})
    return _DanceDefinition