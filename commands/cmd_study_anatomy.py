from commands.command import Command
from world.helpers.skill_attempts import attempt_with_failure_learning


class CmdStudyAnatomy(Command):
    """
    Study anatomy from a chart, text, or subject.

    Examples:
        study anatomy chart
        study anatomy patient
    """

    key = "study anatomy"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        caller = self.caller
        target_name = str(self.args or "").strip()
        if not target_name:
            caller.msg("Study anatomy on what?")
            return
        target, matches, base_query, index, _scope = self.resolve_target(
            target_name,
            scopes=("characters", "room", "inventory"),
            default_first=True,
        )
        if not target and matches and index is not None:
            self.msg_target_matches(base_query, matches)
            return
        if not target:
            target = caller.search(target_name)
        if not target:
            return
        if getattr(target.db, "is_study_item", False):
            caller.study_item(target)
            return
        if hasattr(caller, "_is_anatomy_study_item") and caller._is_anatomy_study_item(target):
            caller.study_item(target)
            return
        if hasattr(target, "get_body_part"):
            caller.msg(f"You study {target.key}'s anatomy with careful attention.")
            if hasattr(caller, "award_skill_experience"):
                caller.award_skill_experience("scholarship", 10, success=True, outcome="success", event_key="study_anatomy", context_multiplier=1.0)
                caller.award_skill_experience("first_aid", 8, success=True, outcome="success", event_key="study_anatomy", context_multiplier=0.5)
                if hasattr(caller, "is_empath") and caller.is_empath():
                    empathy_rank = int(caller.get_skill("empathy") if hasattr(caller, "get_skill") else 0)
                    if empathy_rank >= 6:
                        caller.award_skill_experience("empathy", 6, success=True, outcome="success", event_key="study_anatomy", context_multiplier=0.1)
                    else:
                        attempt_with_failure_learning(
                            caller,
                            "empathy",
                            6,
                            success=False,
                            failure_reason="skill_too_low",
                            event_key="study_anatomy",
                            failure_multiplier=0.25,
                        )
            return
        caller.msg("You cannot make useful anatomical study of that.")
