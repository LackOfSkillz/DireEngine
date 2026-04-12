from commands.command import Command


def _bond_flavor(profile_label):
    tones = {
        "Wildbound": "deeply rooted",
        "Attuned": "in step with the land",
        "Distant": "the pull is faint",
        "Disconnected": "no connection yet",
    }
    return tones.get(str(profile_label or "").strip(), str(profile_label or "").strip().lower())


def _environment_flavor(value):
    tones = {
        "urban": "you feel out of place",
        "wild": "the land answers easily",
        "forest": "the trees feel close",
        "outdoors": "the air sits better on you",
        "indoor": "walls blunt your edge",
    }
    normalized = str(value or "").strip().lower()
    tone = tones.get(normalized)
    return f"{str(value or '').title()} ({tone})" if tone else str(value or "").title()


def _terrain_flavor(value):
    tones = {
        "urban": "stone underfoot, little give",
        "forest": "cover comes naturally",
        "plains": "nothing hides you for long",
        "hills": "the ground rises to meet you",
        "swamp": "every step drags",
    }
    normalized = str(value or "").strip().lower()
    tone = tones.get(normalized)
    return f"{str(value or '').title()} ({tone})" if tone else str(value or "").title()


def _nature_focus_flavor(value):
    amount = max(0, int(value or 0))
    if amount >= 75:
        return "ready"
    if amount >= 35:
        return "gathering"
    if amount > 0:
        return "faint"
    return "quiet"


def _companion_flavor(companion):
    state = str((companion or {}).get("state", "inactive") or "inactive").strip().lower()
    bond = int((companion or {}).get("bond", 0) or 0)
    if state != "active" and bond <= 0:
        return "not yet bonded"
    if state != "active":
        return f"bond {bond}/100"
    return f"active, bond {bond}/100"


class CmdStats(Command):
    """
    Review your condition, attributes, and current learning.

    Examples:
      stats
      health
      hp
    """

    key = "stats"
    aliases = ["health", "hp", "sta", "score"]
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
            f"Race: {char.get_race_display_name() if hasattr(char, 'get_race_display_name') else str(getattr(char.db, 'race', 'human') or 'human').replace('_', ' ').title()}",
            f"Profession: {profession_rank}",
            f"Social Standing: {social_standing}",
            f"Life State: {str(getattr(char.db, 'life_state', 'ALIVE') or 'ALIVE').title()}",
            f"Condition: {condition}",
            f"HP: {char.db.hp}/{char.db.max_hp}",
            f"Balance: {bal}/{max_bal}",
            f"Fatigue: {fat}/{max_fat}",
            f"Favor: {(char.get_favor() if hasattr(char, 'get_favor') else 0)} / {(char.get_favor_max() if hasattr(char, 'get_favor_max') else (char.get_favor() if hasattr(char, 'get_favor') else 0))}",
            f"Unabsorbed XP: {char.get_unabsorbed_xp() if hasattr(char, 'get_unabsorbed_xp') else 0}",
            f"Experience Debt: {char.get_exp_debt() if hasattr(char, 'get_exp_debt') else 0}",
            f"Bleeding: {char.get_bleeding_summary()}",
            f"Carry Capacity: {char.get_max_carry_weight():.1f}" if hasattr(char, 'get_max_carry_weight') else "Carry Capacity: 100.0",
            char.get_engagement_summary(),
            "",
            "Skill Weights:",
        ]

        if hasattr(char, "is_profession") and char.is_profession("cleric"):
            lines.insert(9, f"Devotion: {char.get_devotion() if hasattr(char, 'get_devotion') else 0} / {char.get_devotion_max() if hasattr(char, 'get_devotion_max') else 0}")
            lines.insert(10, f"Specialization: {char.get_cleric_specialization_label() if hasattr(char, 'get_cleric_specialization_label') else 'None'}")

        if hasattr(char, "get_death_status_lines"):
            death_lines = char.get_death_status_lines()
            if death_lines:
                insert_at = len(lines) - 2
                for offset, line in enumerate(death_lines):
                    lines.insert(insert_at + offset, line)

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
            bond_profile = char.get_wilderness_bond_profile().get('label', 'Attuned')
            nature_focus = char.get_nature_focus() if hasattr(char, "get_nature_focus") else 0
            lines.insert(2, f"Circle: {char.get_circle()}")
            lines.insert(3, f"Wilderness Bond: {char.get_wilderness_bond()}/100 ({_bond_flavor(bond_profile)})")
            lines.insert(4, f"Instinct: {char.get_ranger_instinct()}")
            if hasattr(char, "get_nature_focus"):
                lines.insert(5, f"Nature Focus: {nature_focus}/100 ({_nature_focus_flavor(nature_focus)})")
            if getattr(char, "location", None) and hasattr(char.location, "get_environment_type"):
                lines.insert(6, f"Environment: {_environment_flavor(char.location.get_environment_type())}")
            if getattr(char, "location", None) and hasattr(char.location, "get_terrain_type"):
                lines.insert(7, f"Terrain: {_terrain_flavor(char.location.get_terrain_type())}")
            if hasattr(char, "get_ranger_companion"):
                companion = char.get_ranger_companion()
                lines.insert(8, f"Companion: {char.get_ranger_companion_label()} ({_companion_flavor(companion)})")
        elif hasattr(char, "is_profession") and char.is_profession("empath"):
            lines.insert(2, f"Empathic Shock: {char.get_empath_shock()}/100")
            if hasattr(char, "is_empath_overdrawn") and char.is_empath_overdrawn():
                lines.insert(3, "Overdraw: Active")
            if hasattr(char, "get_empath_links"):
                links = char.get_empath_links(require_local=False, include_group=False)
                if links:
                    primary = links[0]
                    lines.insert(4, f"Active Link: {primary['target'].key} [{str(primary.get('type', 'touch')).title()} {primary.get('condition', 'steady').title()} S{int(primary.get('stability', 0) or 0)}]")
                else:
                    lines.insert(4, "Active Link: None")
            if hasattr(char, "get_empath_unity_state"):
                unity = char.get_empath_unity_state()
                if unity:
                    lines.insert(5, f"Unity: {unity['primary_target'].key} <-> {unity['secondary_target'].key} [{unity.get('condition', 'steady').title()} S{int(unity.get('stability', 0) or 0)}]")
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
        try:
            from systems import onboarding

            onboarding.note_stats_action(char)
        except Exception:
            pass