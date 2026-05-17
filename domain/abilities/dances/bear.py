from domain.abilities.dances.shared import build_dance_definition


BearDance = build_dance_definition(bit_index=5, name="bear", canonical_display_name="Bear", required_level=26, canonical_pit_master="Drathrok", canonical_pit_room=225061, offense_bonuses={"melee_damage": 12}, stat_modifiers={"strength": 6, "stamina": 6})