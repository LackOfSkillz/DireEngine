from commands.command import Command
from engine.services.circle_service import commit_advancement, find_guild_leader_for_profession, project_advancement
from engine.services.messaging import send_untargeted_action
from engine.services.stat_training_service import StatTrainingService


class CmdStudy(Command):
    """
    Study an item, lesson, or topic source.

    Examples:
        study book
    """

    key = "study"
    locks = "cmd:all()"
    help_category = "Lore"

    def func(self):
        trainer = StatTrainingService.find_trainer_in_room(self.caller)
        if trainer:
            args = str(self.args or "").strip().lower()
            result = StatTrainingService.commit(self.caller) if args == "commit" else StatTrainingService.consult(self.caller)
            send_untargeted_action(self.caller, actor_message=result.message, room_message=result.room_message)
            return

        profession = getattr(self.caller.db, "profession", "commoner") if getattr(self.caller, "db", None) else "commoner"
        leader = find_guild_leader_for_profession(self.caller, profession)
        if leader:
            args = str(self.args or "").strip().lower()
            if args in {"commit", "circle commit"}:
                result = commit_advancement(self.caller)
                send_untargeted_action(self.caller, actor_message=result.message, room_message=result.room_message)
            else:
                projection = project_advancement(self.caller)
                lines = [
                    f"{leader.key} reviews your circle progress toward Circle {int(projection['target_circle'] or 0)}.",
                    f"Guildhall: {projection['guildhall_room_key'] or 'Not yet available'}",
                    f"Skill ranks: {int(projection['skill_rank_total'] or 0)}/{int(projection['requirements']['skill_rank_total_required'] or 0)}",
                    f"Coins: {int(projection['coins'] or 0)}/{int(projection['requirements']['money_coins_required'] or 0)}",
                    f"TDPs on advance: {int(projection['tdp_grant_preview'] or 0)}",
                ]
                if projection.get("missing"):
                    lines.append("Missing:")
                    lines.extend([f"  {entry}" for entry in projection["missing"]])
                else:
                    lines.append("Type STUDY COMMIT to advance.")
                send_untargeted_action(self.caller, actor_message="\n".join(lines), room_message=projection.get("room_message"))
            return

        target_name = (self.args or "").strip()
        if not target_name:
            self.caller.msg("Study what?")
            return

        candidates = list(getattr(self.caller, "contents", []) or [])
        if getattr(self.caller, "location", None):
            candidates.extend(obj for obj in list(getattr(self.caller.location, "contents", []) or []) if obj != self.caller)
        target, matches, base_query, index = self.resolve_item_target(target_name, candidates, default_first=True)
        if not target and matches and index is not None:
            self.msg_item_matches(base_query, matches)
            return
        if not target:
            target = self.caller.search(target_name)
        if not target:
            return

        self.caller.study_item(target)
