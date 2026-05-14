"""TDP training cost calculations per modern DR canon."""

from world.races.utils import get_racial_tdp_modifier


def tdp_cost_to_raise(current_value, racial_modifier):
    """Calculate TDP cost to raise a stat by 1 point."""
    current = max(0, int(current_value or 0))
    modifier = int(racial_modifier or 0)
    if current <= 0:
        return 0
    cost = (current * 3) + (modifier * (current // 2))
    return max(0, cost)


def tdp_cost_to_project(current_value, target_value, racial_modifier):
    """Calculate total TDP cost to raise a stat from current to target."""
    current = max(0, int(current_value or 0))
    target = max(0, int(target_value or 0))
    modifier = int(racial_modifier or 0)
    if target <= current:
        return 0
    total = 0
    for value in range(current, target):
        total += tdp_cost_to_raise(value, modifier)
    return total


def tdp_cost_for_character(character, stat):
    """Convenience wrapper for calculating a character's next stat cost."""
    if not getattr(character, "db", None):
        return 0
    stats = getattr(character.db, "stats", {}) or {}
    current = int(stats.get(str(stat or "").strip().lower(), 0) or 0)
    race = getattr(character.db, "race", "human") or "human"
    modifier = get_racial_tdp_modifier(race, stat)
    return tdp_cost_to_raise(current, modifier)