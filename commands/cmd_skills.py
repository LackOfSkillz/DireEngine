from evennia import Command


class CmdSkills(Command):
    """
        Review your skills in a compact list.

    Examples:
      skills
            skills all
      ski
    """

    key = "skills"
    aliases = ["ski"]
    help_category = "Character"

    def func(self):
        self.caller.ensure_core_defaults()
        query = (self.args or "").strip().lower()

        if query and query != "all":
            detail = self.caller.get_skill_detail_entry(query)
            if not detail:
                self.caller.msg("You do not know of that skill.")
                return

            mindstate = f"{detail['label']} [{detail['mindstate']}/{detail['cap']}]"
            lines = [
                detail["display"],
                f"Category: {str(detail['category']).title()}",
                f"Rank: {detail['rank']}",
                f"Mindstate: {mindstate}",
                f"Description: {detail['description']}",
            ]
            self.caller.msg("\n".join(lines))
            return

        show_all = query == "all"
        entries = self.caller.get_skill_entries(include_zero=show_all)

        if not entries:
            self.caller.msg("You do not know any skills yet.")
            return

        if show_all:
            category_order = []
            grouped = {}
            for entry in entries:
                category = str(entry.get("category", "general")).title()
                if category not in grouped:
                    grouped[category] = []
                    category_order.append(category)
                grouped[category].append(entry)

            lines = []
            for category in category_order:
                category_entries = grouped[category]
                skill_width = max(len("Skill"), max(len(entry["display"]) for entry in category_entries))
                rank_width = max(len("Rank"), max(len(str(entry["rank"])) for entry in category_entries))
                if lines:
                    lines.append("")
                lines.extend(
                    [
                        category,
                        f"{'Skill'.ljust(skill_width)}  {'Rank'.rjust(rank_width)}  Mindstate",
                        f"{'-' * skill_width}  {'-' * rank_width}  {'-' * 18}",
                    ]
                )
                for entry in category_entries:
                    mindstate = f"{entry['label']} [{entry['mindstate']}/{entry['cap']}]"
                    lines.append(
                        f"{entry['display'].ljust(skill_width)}  {str(entry['rank']).rjust(rank_width)}  {mindstate}"
                    )
            self.caller.msg("\n".join(lines))
            return

        skill_width = max(len("Skill"), max(len(entry["display"]) for entry in entries))
        rank_width = max(len("Rank"), max(len(str(entry["rank"])) for entry in entries))
        lines = [
            f"{'Skill'.ljust(skill_width)}  {'Rank'.rjust(rank_width)}  Mindstate",
            f"{'-' * skill_width}  {'-' * rank_width}  {'-' * 18}",
        ]

        for entry in entries:
            mindstate = f"{entry['label']} [{entry['mindstate']}/{entry['cap']}]"
            lines.append(
                f"{entry['display'].ljust(skill_width)}  {str(entry['rank']).rjust(rank_width)}  {mindstate}"
            )

        self.caller.msg("\n".join(lines))