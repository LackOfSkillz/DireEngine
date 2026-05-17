from domain.abilities.dances.shared import build_dance_definition


PantherDance = build_dance_definition(bit_index=7, name="panther", canonical_display_name="Panther", required_level=40, canonical_pit_master="Sathralor", canonical_pit_room=2030953, offense_bonuses={"missile_accuracy": 10}, defense_bonuses={"missile": 12}, stat_modifiers={"agility": 4, "reflex": 4}, skill_modifiers={"stealth": 12, "hiding": 12, "stalking": 12}, engagement_speed_bonus=10, roar_power_modifiers={"intimidation": 105})