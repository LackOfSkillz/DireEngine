from collections.abc import Mapping

from commands.command import Command
from world.systems.skills import MINDSTATE_MAX, base_pool, is_active, rank_cost


DISPLAY_NAME_OVERRIDES = {
    "appraisal": "Appraisal",
    "arcana": "Arcana",
    "athletics": "Athletics",
    "attunement": "Attunement",
    "brawling": "Hand-To-Hand",
    "chain_armor": "Chain Armor",
    "debilitation": "Debilitation",
    "evasion": "Evasion",
    "first_aid": "First Aid",
    "light_armor": "Light Armor",
    "light_edge": "Light-Edged",
    "locksmithing": "Lockpicking",
    "perception": "Perception",
    "plate_armor": "Plate Armor",
    "scholarship": "Scholarship",
    "stealth": "Stealth",
    "targeted_magic": "Targeted Magic",
}


def format_skill_display_name(skill_name):
    normalized = str(skill_name or "").strip().lower().replace(" ", "_")
    if normalized in DISPLAY_NAME_OVERRIDES:
        return DISPLAY_NAME_OVERRIDES[normalized]
    return normalized.replace("_", " ").title()


def calculate_rank_percent(skill, displayed_rank):
    progress_cost = rank_cost(displayed_rank)
    if progress_cost <= 0:
        return 0
    progress = max(0.0, float(getattr(skill, "rank_progress", 0.0) or 0.0))
    return max(0, min(99, int((progress / progress_cost) * 100)))


def calculate_pool_display(skill, displayed_rank, display_skillset):
    live_rank = int(getattr(skill, "rank", 0) or 0)
    if live_rank == displayed_rank:
        current_pool = max(0.0, float(getattr(skill, "pool", 0.0) or 0.0))
        maximum_pool = max(0.0, float(getattr(skill, "max_pool", 0.0) or 0.0))
    else:
        current_pool = 0.0
        maximum_pool = max(0.0, float(base_pool(displayed_rank, display_skillset) or 0.0))
    return int(round(current_pool)), int(round(maximum_pool))


class CmdExperience(Command):
    """
    Show skill learning and ranks.

    Examples:
        experience
        exp
        experience all
        exp all
    """

    key = "experience"
    aliases = ["exp"]
    locks = "cmd:all()"
    help_category = "Training & Lore"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()
        if not hasattr(caller, "exp_skills"):
            caller.msg("You do not expose experience skill data.")
            return

        mode = str(self.args or "").strip().lower()
        if mode and mode != "all":
            caller.msg("Usage: experience [all]")
            return
        show_all = mode == "all"

        legacy_skills = getattr(caller.db, "skills", None) or {}
        if not isinstance(legacy_skills, Mapping):
            legacy_skills = {}

        handler = caller.exp_skills
        skill_names = set(handler.skills.keys())
        if show_all:
            skill_names.update(str(name or "").strip().lower() for name in legacy_skills.keys() if str(name or "").strip())

        skill_rows = []
        for skill_name in sorted(skill_names):
            legacy_entry = legacy_skills.get(skill_name)
            if not isinstance(legacy_entry, Mapping):
                legacy_entry = {}
            if hasattr(caller, "_sync_exp_skill_state"):
                skill = caller._sync_exp_skill_state(skill_name, legacy_entry)
            else:
                skill = handler.get(skill_name)

            displayed_rank = int(skill.rank or 0)
            if displayed_rank <= 0:
                displayed_rank = int(legacy_entry.get("rank", 0) or 0)

            display_skillset = str(getattr(caller, "get_skillset", lambda name: "primary")(skill_name) or "primary")
            display_name = format_skill_display_name(skill_name)
            displayed_percent = calculate_rank_percent(skill, displayed_rank)
            displayed_pool, displayed_max_pool = calculate_pool_display(skill, displayed_rank, display_skillset)

            if not show_all and (int(skill.mindstate or 0) <= 0 or not is_active(skill)):
                continue

            skill_rows.append(
                {
                    "skill_name": skill_name,
                    "skill": skill,
                    "display_name": display_name,
                    "displayed_rank": displayed_rank,
                    "displayed_percent": displayed_percent,
                    "displayed_pool": displayed_pool,
                    "displayed_max_pool": displayed_max_pool,
                }
            )

        if not skill_rows:
            if show_all:
                caller.msg("No skills with field experience to display.")
                return
            caller.msg("No actively training skills to display. Use exp all to see everything.")
            return

        if show_all:
            skill_rows.sort(key=lambda entry: entry["display_name"].lower())
        else:
            skill_rows.sort(key=lambda entry: (-int(entry["skill"].mindstate or 0), entry["display_name"].lower()))

        lines = []
        if show_all:
            lines.extend(["Showing all skills with field experience.", ""])
        lines.append("           Skill        Rank/% -> Mindstate      Bits (pool / max)")
        for entry in skill_rows:
            skill = entry["skill"]
            lines.append(
                f"{entry['display_name']:>20}: "
                f"{entry['displayed_rank']:>4} {entry['displayed_percent']:02d}% "
                f"{skill.mindstate_name():<12} ({int(skill.mindstate or 0)}/{MINDSTATE_MAX})         "
                f"({entry['displayed_pool']}/{entry['displayed_max_pool']})"
            )
        lines.append("")
        lines.append(f"Total Ranks Displayed: {sum(entry['displayed_rank'] for entry in skill_rows)}")
        caller.msg("\n".join(lines))