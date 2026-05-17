from domain.abilities.dances.shared import build_dance_definition


EagleDance = build_dance_definition(bit_index=4, name="eagle", canonical_display_name="Eagle", required_level=22, canonical_pit_master="Calenra", canonical_pit_room=1017303, offense_bonuses={"missile_accuracy": 10, "missile_damage": 10}, skill_modifiers={"perception": 12}, engagement_speed_bonus=8, roar_power_modifiers={"inspiration": 110})