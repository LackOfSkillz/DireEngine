from commands.command import Command
from engine.services.circle_service import commit_advancement, project_advancement
from world.helpers.target_resolver import format_item_matches, resolve_target


class CmdCircle(Command):
    """
    View your current profession circle and advancement progress.

    Examples:
        circle
        circle advance
        circle invite <target>
        circle accept <target>
        circle leave
    """

    key = "circle"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        if hasattr(self.caller, "is_profession") and self.caller.is_profession("empath"):
            run_empath_circle_command(self.caller, self.args)
            return
        run_profession_circle_command(self.caller, self.args)


def run_profession_circle_command(caller, raw_args=""):
    args = str(raw_args or "").strip().lower()
    if args in {"advance", "up", "next"}:
        caller.msg(commit_advancement(caller).message)
        return True
    if args:
        caller.msg("Usage: circle or circle advance")
        return True
    projection = project_advancement(caller)
    caller.msg(f"{projection['profession'].replace('_', ' ').title()} Circle: {int(projection['current_circle'] or 0)}")
    caller.msg(f"Next Circle: {int(projection['target_circle'] or 0)}")
    notes = str(projection["requirements"].get("profession_specific_notes", "") or "").strip()
    if notes:
        caller.msg(notes)
    for line in projection.get("missing", []) or []:
        caller.msg(line)
    return True


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
    raw_text = str(raw_args or "").strip()
    args = raw_text.lower()
    if not hasattr(caller, "is_profession") or not caller.is_profession("empath"):
        caller.msg("Only Empaths can circle this way.")
        return True
    parts = raw_text.split()
    command = parts[0].lower() if parts else ""
    remainder = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
    if command == "invite":
        if not remainder:
            caller.msg("Usage: circle invite <target>")
            return True
        target, matches, base_query, index, _scope = resolve_target(
            remainder,
            caller,
            scopes=("characters",),
            default_first=True,
        )
        if not target and matches and index is not None:
            caller.msg(format_item_matches(base_query, matches, looker=caller))
            return True
        if not target:
            target = caller.search(remainder, location=caller.location)
        if not target:
            return True
        ok, message = caller.invite_empath_circle_member(target) if hasattr(caller, "invite_empath_circle_member") else (False, "You cannot form a shock circle right now.")
        caller.msg(message)
        return True
    if command == "accept":
        if not remainder:
            caller.msg("Usage: circle accept <target>")
            return True
        target, matches, base_query, index, _scope = resolve_target(
            remainder,
            caller,
            scopes=("characters",),
            default_first=True,
        )
        if not target and matches and index is not None:
            caller.msg(format_item_matches(base_query, matches, looker=caller))
            return True
        if not target:
            target = caller.search(remainder, location=caller.location)
        if not target:
            return True
        ok, message = caller.accept_empath_circle_invite(target) if hasattr(caller, "accept_empath_circle_invite") else (False, "You cannot join a shock circle right now.")
        caller.msg(message)
        return True
    if command == "leave":
        ok, message = caller.leave_empath_circle() if hasattr(caller, "leave_empath_circle") else (False, "You are not part of a shock circle.")
        caller.msg(message)
        return True
    should_advance = force_advance or args in {"advance", "up", "next"}
    if args and not should_advance:
        caller.msg("Usage: circle, circle advance, circle invite <target>, circle accept <target>, or circle leave")
        return True
    if should_advance:
        ok, lines, _status = caller.advance_circle() if hasattr(caller, "advance_circle") else (False, ["You cannot circle right now."], None)
        for line in lines if isinstance(lines, list) else [str(lines)]:
            caller.msg(line)
        return True
    for line in _build_empath_circle_lines(caller):
        caller.msg(line)
    for line in caller.get_empath_circle_status_lines() if hasattr(caller, "get_empath_circle_status_lines") else []:
        caller.msg(line)
    return True
