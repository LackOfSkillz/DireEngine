from commands.command import Command
from engine.services.circle_service import commit_advancement, find_guild_leader_for_profession, project_advancement
from engine.services.messaging import send_untargeted_action
from engine.services.stat_training_service import StatTrainingService


class CmdTrain(Command):
    """
    Train with an instructor or training source.

    Examples:
        train tactics
    """

    key = "train"
    locks = "cmd:all()"
    help_category = "Training & Lore"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()
        args = str(self.args or "").strip().lower()

        trainer = StatTrainingService.find_trainer_in_room(caller)
        if trainer:
            result = StatTrainingService.commit(caller) if args == "commit" else StatTrainingService.consult(caller)
            send_untargeted_action(caller, actor_message=result.message, room_message=result.room_message)
            return

        profession = getattr(caller.db, "profession", "commoner") if getattr(caller, "db", None) else "commoner"
        leader = find_guild_leader_for_profession(caller, profession)
        if leader:
            if args in {"commit", "circle commit"}:
                result = commit_advancement(caller)
                send_untargeted_action(caller, actor_message=result.message, room_message=result.room_message)
            else:
                projection = project_advancement(caller)
                lines = [
                    f"{leader.key} considers your progress toward Circle {int(projection['target_circle'] or 0)}.",
                    f"Guildhall: {projection['guildhall_room_key'] or 'Not yet available'}",
                    f"Skill ranks: {int(projection['skill_rank_total'] or 0)}/{int(projection['requirements']['skill_rank_total_required'] or 0)}",
                    f"Coins: {int(projection['coins'] or 0)}/{int(projection['requirements']['money_coins_required'] or 0)}",
                    f"TDPs on advance: {int(projection['tdp_grant_preview'] or 0)}",
                ]
                if projection.get("missing"):
                    lines.append("Missing:")
                    lines.extend([f"  {entry}" for entry in projection["missing"]])
                    lines.append("Type TRAIN COMMIT once the missing requirements are satisfied.")
                else:
                    lines.append("Type TRAIN COMMIT to advance.")
                send_untargeted_action(caller, actor_message="\n".join(lines), room_message=projection.get("room_message"))
            return

        if not hasattr(caller, "advance_profession"):
            caller.msg("You cannot train that way right now.")
            return

        ok, message = caller.advance_profession()
        caller.msg(message)
        if ok and hasattr(caller, "sync_client_state"):
            caller.sync_client_state()
