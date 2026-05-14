from collections.abc import Mapping

from commands.command import Command
from domain.learning.mindstate import get_mindstate_name
from domain.learning.skill_aliases import resolve_skill_alias
from engine.services.circle_service import project_advancement
from engine.services.rexp_service import get_rexp_display
from world.systems.skills import MINDSTATE_MAX, base_pool, get_skill_display_name, is_active, rank_cost


def format_skill_display_name(skill_name):
    normalized = str(skill_name or "").strip().lower().replace(" ", "_")
    return get_skill_display_name(normalized)


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
        exp le
        exp circle
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
        if mode == "help":
            caller.msg(self.__doc__)
            return
        if mode == "circle":
            self._show_circle_progress(caller)
            return
        if mode and mode != "all":
            self._show_skill_detail(caller, mode)
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
        lines.append(f"Time Development Points: {int(getattr(caller.db, 'tdp', 0) or 0)}")
        rexp = get_rexp_display(caller)
        lines.append(
            f"Rested EXP Stored: {rexp['banked']}    Usable This Cycle: {rexp['usable_this_cycle']}    Cycle Refreshes: {rexp['cycle_refreshes_in']}"
        )
        lines.append(f"Current State: {rexp['sleep_state']}")
        caller.msg("\n".join(lines))

    def _show_skill_detail(self, caller, query):
        skill_id = resolve_skill_alias(query) or str(query or "").strip().lower().replace("-", "_").replace(" ", "_")
        detail = caller.get_skill_detail_entry(skill_id) if hasattr(caller, "get_skill_detail_entry") else None
        if not detail:
            caller.msg(f"Unknown skill: '{query}'. Try 'exp help' for syntax.")
            return

        exp_skill = caller._sync_exp_skill_state(skill_id, ((caller.db.skills or {}) if isinstance(caller.db.skills, Mapping) else {}).get(skill_id, {})) if hasattr(caller, "_sync_exp_skill_state") else None
        display_name = format_skill_display_name(skill_id)
        displayed_rank = int(detail.get("rank", 0) or 0)
        displayed_pool = int(round(float(getattr(exp_skill, "pool", 0.0) or 0.0))) if exp_skill else 0
        displayed_max_pool = int(round(float(getattr(exp_skill, "max_pool", 0.0) or 0.0))) if exp_skill else int(round(float(base_pool(displayed_rank, str(getattr(exp_skill, 'skillset', 'primary') if exp_skill else 'primary') or 'primary') or 0.0)))
        lines = [
            display_name,
            f"  Current rank: {displayed_rank}",
            f"  Learning: {displayed_pool}/{displayed_max_pool}",
            f"  Mindstate: {get_mindstate_name(int(detail.get('mindstate', 0) or 0))} ({int(detail.get('mindstate', 0) or 0)}/{int(detail.get('cap', MINDSTATE_MAX) or MINDSTATE_MAX)})",
            f"  Bits to next rank: {max(0, displayed_max_pool - displayed_pool)}",
            f"  Skill group: {str(detail.get('category', 'general') or 'general').title()}",
        ]
        caller.msg("\n".join(lines))

    def _show_circle_progress(self, caller):
        projection = project_advancement(caller)
        lines = [
            f"Profession: {str(projection['profession'] or 'commoner').replace('_', ' ').title()}",
            f"Current Circle: {int(projection['current_circle'] or 0)}",
            f"Next Circle: {int(projection['target_circle'] or 0)}",
            f"Guildhall: {projection['guildhall_room_key'] or 'Not yet available'}",
            f"Required Skill Ranks: {int(projection['skill_rank_total'] or 0)}/{int(projection['requirements']['skill_rank_total_required'] or 0)}",
            f"Required Coins: {int(projection['coins'] or 0)}/{int(projection['requirements']['money_coins_required'] or 0)}",
            f"TDP Grant On Advance: {int(projection['tdp_grant_preview'] or 0)}",
        ]
        if projection.get("missing"):
            lines.append("Missing:")
            lines.extend([f"  {entry}" for entry in projection["missing"]])
        else:
            lines.append("You meet the current placeholder requirements for advancement.")
        caller.msg("\n".join(lines))