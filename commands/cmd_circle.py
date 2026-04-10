from commands.command import Command


class CmdCircle(Command):
    """
    View your current profession circle and advancement progress.

    Examples:
        circle
        circle advance
    """

    key = "circle"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        run_empath_circle_command(self.caller, self.args)


def _build_empath_circle_lines(caller):
    status = caller.get_circle_progression_status() if hasattr(caller, "get_circle_progression_status") else {}
    current_circle = int(status.get("current_circle", 1) or 1)
    empathy_rank = int(caller.get_empath_progression_rank() if hasattr(caller, "get_empath_progression_rank") else 0)
    lines = [f"Empath Circle: {current_circle}", f"Empathy Rank: {empathy_rank}"]
    next_circle = status.get("next_circle")
    requirements = dict(status.get("requirements", {}) or {})
    current_ranks = dict(status.get("current_ranks", {}) or {})
    if next_circle and requirements:
        lines.append(f"Next Circle: {int(next_circle)}")
        for skill_name, required_rank in requirements.items():
            current_rank = int(current_ranks.get(skill_name, 0) or 0)
            lines.append(f"  {caller.format_skill_name(skill_name)}: {current_rank}/{int(required_rank or 0)}")
    else:
        lines.append("Next Circle: You have reached the highest configured Empath circle.")
    next_unlock = caller.get_next_empath_unlock_status() if hasattr(caller, "get_next_empath_unlock_status") else None
    if next_unlock:
        lines.append(f"Next Technique: {next_unlock['label']} (Empathy {int(next_unlock['required_rank'] or 0)})")
    available_unlocks = caller.get_available_empath_unlocks() if hasattr(caller, "get_available_empath_unlocks") else []
    if available_unlocks:
        recent = ", ".join(entry["label"] for entry in available_unlocks[-3:])
        lines.append(f"Unlocked: {recent}")
    return lines


def run_empath_circle_command(caller, raw_args="", force_advance=False):
    args = str(raw_args or "").strip().lower()
    if not hasattr(caller, "is_profession") or not caller.is_profession("empath"):
        caller.msg("Only Empaths can circle this way.")
        return True
    should_advance = force_advance or args in {"advance", "up", "next"}
    if args and not should_advance:
        caller.msg("Usage: circle or circle advance")
        return True
    if should_advance:
        ok, lines, _status = caller.advance_circle() if hasattr(caller, "advance_circle") else (False, ["You cannot circle right now."], None)
        for line in lines if isinstance(lines, list) else [str(lines)]:
            caller.msg(line)
        return True
    for line in _build_empath_circle_lines(caller):
        caller.msg(line)
    return True
