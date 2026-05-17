from domain.abilities.dances.shared import build_dance_definition


BadgerDance = build_dance_definition(bit_index=3, name="badger", canonical_display_name="Badger", required_level=18, canonical_pit_master="Yutwian", canonical_pit_room=2102060, defense_bonuses={"melee": 8, "parry": 10, "shield": 10}, skill_modifiers={"multiple_engaged_opponent": 15}, roar_power_modifiers={"inspiration": 105})