from commands.command import Command
from world.systems.skills import MINDSTATE_MAX, award_xp, is_active, pulse, train


class CmdSkillDebug(Command):
    """
    Inspect the Phase 1 experience-model state for a skill.

    Examples:
        skilldebug
        skilldebug evasion
    """

    key = "skilldebug"
    locks = "cmd:all()"
    help_category = "Training & Lore"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()
        if not hasattr(caller, "exp_skills"):
            caller.msg("You do not expose Phase 1 skill state data.")
            return

        raw_args = str(self.args or "").strip()
        tokens = raw_args.split()
        skill_name = "evasion"
        action = None
        action_value = None

        def _parse_number(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        if raw_args:
            first = str(tokens[0] or "").strip()
            first_lower = first.lower()
            if first_lower == "tick":
                from world.systems.exp_pulse import exp_pulse_tick

                exp_pulse_tick()
                caller.msg("Tick executed")
                return
            if first_lower == "reset":
                action = "reset"
            elif first_lower == "pulse":
                action = "pulse"
                action_value = 1
                if len(tokens) >= 2:
                    try:
                        action_value = max(1, int(tokens[1]))
                    except (TypeError, ValueError):
                        caller.msg("Pulse count must be an integer.")
                        return
            elif first_lower == "train":
                action = "train"
                if len(tokens) < 2:
                    caller.msg("Usage: skilldebug [skill] train <difficulty>")
                    return
                action_value = _parse_number(tokens[1])
                if action_value is None:
                    caller.msg("Training difficulty must be numeric.")
                    return
            else:
                numeric_first = _parse_number(first)
                if numeric_first is not None:
                    action = "award"
                    action_value = numeric_first
                else:
                    skill_name = first_lower
                    if len(tokens) >= 2:
                        second = str(tokens[1] or "").strip().lower()
                        if second == "reset":
                            action = "reset"
                        elif second == "pulse":
                            action = "pulse"
                            action_value = 1
                            if len(tokens) >= 3:
                                try:
                                    action_value = max(1, int(tokens[2]))
                                except (TypeError, ValueError):
                                    caller.msg("Pulse count must be an integer.")
                                    return
                        elif second == "train":
                            action = "train"
                            if len(tokens) < 3:
                                caller.msg("Usage: skilldebug [skill] train <difficulty>")
                                return
                            action_value = _parse_number(tokens[2])
                            if action_value is None:
                                caller.msg("Training difficulty must be numeric.")
                                return
                        else:
                            numeric_second = _parse_number(tokens[1])
                            if numeric_second is None:
                                caller.msg("Usage: skilldebug [skill] [amount|train <difficulty>|pulse [count]|reset]")
                                return
                            action = "award"
                            action_value = numeric_second

        skill = caller.exp_skills.get(skill_name)
        if action == "award":
            gained = award_xp(skill, action_value)
            caller.msg(f"Gained: {gained:.1f}")
        elif action == "train":
            gained = train(skill, action_value)
            caller.msg(f"Trained: {gained:.1f}")
        elif action == "pulse":
            total_drained = 0.0
            pulse_count = int(action_value or 1)
            for _ in range(pulse_count):
                total_drained += pulse(skill)
            caller.msg(f"Drained: {total_drained:.1f}")
        elif action == "reset":
            skill.pool = 0.0
            skill.rank_progress = 0.0
            skill.update_mindstate()
            caller.msg("Reset pool and rank progress to 0.0")

        percent = (skill.pool / skill.max_pool) * 100 if skill.max_pool > 0 else 0.0
        caller.msg(
            "\n".join(
                [
                    f"Skill Debug: {skill.name}",
                    f"Rank: {skill.rank}",
                    f"Rank Progress: {skill.rank_progress:.1f}",
                    f"Pool: {skill.pool:.1f}",
                    f"Max Pool: {skill.max_pool:.1f}",
                    f"Percent: {percent:.1f}%",
                    f"Skillset: {skill.skillset}",
                    f"Last Trained: {skill.last_trained}",
                    f"Active: {is_active(skill)}",
                    f"Mindstate: {skill.mindstate}/{MINDSTATE_MAX} ({skill.mindstate_name()})",
                ]
            )
        )
