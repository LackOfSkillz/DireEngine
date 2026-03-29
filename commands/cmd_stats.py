from evennia import Command


class CmdStats(Command):
    """
    Review your condition, attributes, and current learning.

    Examples:
      stats
      health
      hp
    """

    key = "stats"
    aliases = ["health", "hp", "sta"]
    help_category = "Character"

    def func(self):
        char = self.caller
        char.ensure_core_defaults()
        bal, max_bal = char.get_balance()
        fat, max_fat = char.get_fatigue()
        condition = char.get_condition()
        stats = char.db.stats or {}
        learning = char.get_active_learning_entries()
        profession_name = char.get_profession_display_name() if hasattr(char, "get_profession_display_name") else char.get_profession().replace("_", " ").title()
        profession_rank = char.get_profession_rank_label() if hasattr(char, "get_profession_rank_label") else profession_name
        social_standing = char.get_social_standing() if hasattr(char, "get_social_standing") else "Neutral"
        skill_weights = char.get_profession_skill_weights() if hasattr(char, "get_profession_skill_weights") else {}
        lines = [
            f"Profession: {profession_rank}",
            f"Social Standing: {social_standing}",
            f"Condition: {condition}",
            f"HP: {char.db.hp}/{char.db.max_hp}",
            f"Balance: {bal}/{max_bal}",
            f"Fatigue: {fat}/{max_fat}",
            f"Bleeding: {char.get_bleeding_summary()}",
            char.get_engagement_summary(),
            "",
            "Skill Weights:",
        ]

        if skill_weights:
            lines.append(
                "  " + "  ".join(
                    f"{skillset.title()}: x{weight:.2f}"
                    for skillset, weight in sorted(skill_weights.items())
                )
            )
        else:
            lines.append("  Balanced training across all skillsets.")

        lines.extend([
            "",
            "Attributes:",
            "  Strength: {strength}  Stamina: {stamina}  Agility: {agility}  Reflex: {reflex}".format(
                strength=stats.get("strength", 0),
                stamina=stats.get("stamina", 0),
                agility=stats.get("agility", 0),
                reflex=stats.get("reflex", 0),
            ),
            "  Discipline: {discipline}  Intelligence: {intelligence}  Wisdom: {wisdom}  Charisma: {charisma}".format(
                discipline=stats.get("discipline", 0),
                intelligence=stats.get("intelligence", 0),
                wisdom=stats.get("wisdom", 0),
                charisma=stats.get("charisma", 0),
            ),
            "",
        ])

        if learning:
            lines.append("Active Learning:")
            for entry in learning:
                lines.append(
                    f"  {entry['skill']}: rank {entry['rank']}, {entry['label']} [{entry['mindstate']}/{entry['cap']}]"
                )
        else:
            lines.append(f"Active Learning: clear [0/{char.get_mindstate_cap()}]")

        char.msg("\n".join(lines))