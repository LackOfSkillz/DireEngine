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
            f"Life State: {str(getattr(char.db, 'life_state', 'ALIVE') or 'ALIVE').title()}",
            f"Condition: {condition}",
            f"HP: {char.db.hp}/{char.db.max_hp}",
            f"Balance: {bal}/{max_bal}",
            f"Fatigue: {fat}/{max_fat}",
            f"Favor: {char.get_favor() if hasattr(char, 'get_favor') else 0} ({char.get_favor_state().title() if hasattr(char, 'get_favor_state') else 'Unprepared'})",
            f"Unabsorbed XP: {char.get_unabsorbed_xp() if hasattr(char, 'get_unabsorbed_xp') else 0}",
            f"Bleeding: {char.get_bleeding_summary()}",
            char.get_engagement_summary(),
            "",
            "Skill Weights:",
        ]

        if hasattr(char, "is_dead") and char.is_dead() and hasattr(char, "get_depart_mode"):
            corpse = char.get_death_corpse() if hasattr(char, "get_death_corpse") else None
            lines.insert(8, f"Depart Path: {char.get_depart_mode(corpse=corpse).title()}")

        if hasattr(char, "is_profession") and char.is_profession("warrior"):
            lines.insert(2, f"Warrior Circle: {char.get_warrior_circle()}")
            lines.insert(3, f"War Tempo: {char.get_war_tempo()}/{char.get_max_war_tempo()}")
            lines.insert(4, f"Tempo State: {char.get_war_tempo_state().title()}")
            lines.insert(5, f"Exhaustion: {char.get_exhaustion()}/100 ({char.get_exhaustion_profile().get('label', 'Fresh')})")
            lines.insert(6, f"Pressure: {char.get_pressure_level()}")
            lines.insert(7, f"Combat Rhythm: {char.get_combat_rhythm_state().title()}")
            active_berserk = char.get_active_warrior_berserk() if hasattr(char, "get_active_warrior_berserk") else None
            if active_berserk:
                lines.insert(8, f"Active Berserk: {str(active_berserk.get('name') or active_berserk.get('key') or '').title()}")
        elif hasattr(char, "is_profession") and char.is_profession("ranger"):
            lines.insert(2, f"Wilderness Bond: {char.get_wilderness_bond()}/100 ({char.get_wilderness_bond_profile().get('label', 'Attuned')})")
            lines.insert(3, f"Instinct: {char.get_ranger_instinct()}")
            if hasattr(char, "get_nature_focus"):
                lines.insert(4, f"Nature Focus: {char.get_nature_focus()}/100")
            if getattr(char, "location", None) and hasattr(char.location, "get_environment_type"):
                lines.insert(5, f"Environment: {char.location.get_environment_type().title()}")
            if getattr(char, "location", None) and hasattr(char.location, "get_terrain_type"):
                lines.insert(6, f"Terrain: {char.location.get_terrain_type().title()}")
            if hasattr(char, "get_ranger_companion"):
                companion = char.get_ranger_companion()
                lines.insert(7, f"Companion: {char.get_ranger_companion_label()} [{companion.get('state', 'inactive')}] {int(companion.get('bond', 0) or 0)}/100")
        elif hasattr(char, "is_profession") and char.is_profession("empath"):
            lines.insert(2, f"Empathic Shock: {char.get_empath_shock()}/100")
            if hasattr(char, "is_empath_overdrawn") and char.is_empath_overdrawn():
                lines.insert(3, "Overdraw: Active")
            if hasattr(char, "get_empath_links"):
                links = char.get_empath_links(require_local=False, include_group=False)
                if links:
                    primary = links[0]
                    detail = " deep" if primary.get("deepened") else ""
                    lines.insert(4, f"Active Link: {primary['target'].key} [{str(primary.get('type', 'touch')).title()} {primary.get('strength_label', 'Weak')}{detail}] (+{max(0, len(links) - 1)} more)")
                else:
                    lines.insert(4, "Active Link: None")
            if hasattr(char, "get_empath_unity_state"):
                unity = char.get_empath_unity_state()
                if unity:
                    lines.insert(5, f"Unity: {', '.join(member.key for member in unity.get('members', []))}")
            if hasattr(char, "get_empath_wounds"):
                wounds = char.get_empath_wounds()
                lines.insert(6, f"Wounds: V {int(wounds.get('vitality', 0) or 0)}  B {int(wounds.get('bleeding', 0) or 0)}  F {int(wounds.get('fatigue', 0) or 0)}  T {int(wounds.get('trauma', 0) or 0)}  P {int(wounds.get('poison', 0) or 0)}  D {int(wounds.get('disease', 0) or 0)}")

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