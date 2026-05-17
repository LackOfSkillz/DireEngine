from domain.abilities.dances.shared import build_dance_definition


WolverineDance = build_dance_definition(bit_index=6, name="wolverine", canonical_display_name="Wolverine", required_level=30, canonical_pit_master="Mopeliar", canonical_pit_room=152111, offense_bonuses={"melee_accuracy": 10, "melee_damage": 10}, defense_bonuses={"melee": 8, "parry": 8}, skill_modifiers={"multiple_engaged_opponent": 12}, stat_modifiers={"strength": 4}, balance_bonus=8, engagement_speed_bonus=10, roar_power_modifiers={"intimidation": 110})