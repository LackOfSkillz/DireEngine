from domain.abilities.dances.shared import build_dance_definition


CobraDance = build_dance_definition(bit_index=2, name="cobra", canonical_display_name="Cobra", required_level=14, canonical_pit_master="Melcorek", canonical_pit_room=51227, offense_bonuses={"melee_accuracy": 8, "melee_damage": 10}, engagement_speed_bonus=10, roar_power_modifiers={"intimidation": 105})