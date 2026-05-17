from domain.abilities.dances.shared import build_dance_definition


SwanDance = build_dance_definition(bit_index=1, name="swan", canonical_display_name="Swan", required_level=10, canonical_pit_master="Nightlark", canonical_pit_room=102021, defense_bonuses={"melee": 10}, balance_bonus=8, roar_power_modifiers={"inspiration": 105})