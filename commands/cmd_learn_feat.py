from __future__ import annotations

from commands.command import Command
from engine.services.feat_training_service import FeatTrainerService
from engine.services.messaging import send_untargeted_action


class CmdLearnFeat(Command):
    """Learn a magical feat from a feat trainer."""

    key = "learn"
    help_category = "Magic"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        raw_args = str(self.args or "").strip()
        lowered = raw_args.lower()
        if not lowered.startswith("feat "):
            caller.msg("Usage: LEARN FEAT <feat name>")
            return
        feat_name = raw_args[5:].strip()
        if not feat_name:
            caller.msg("Usage: LEARN FEAT <feat name>")
            return

        trainer = FeatTrainerService.find_trainer_in_room(caller)
        if trainer is None:
            caller.msg("There is no feat trainer here.")
            return

        feat = trainer.resolve_feat(feat_name)
        if feat is None:
            caller.msg(f"{trainer.key} says, \"I know of no such feat as '{feat_name}'.\"")
            return

        result = FeatTrainerService.teach_feat(caller, feat.id)
        if not result.success:
            caller.msg(f"{trainer.key} says, \"{trainer.describe_learning_path(caller, feat)}\"")
            return

        send_untargeted_action(
            caller,
            actor_message=(
                f"{trainer.key} guides you through the principles of {feat.name}. "
                f"You feel your magical understanding deepen. ({int(result.slot_cost or 0)} slot consumed.)"
            ),
            room_message=f"{caller.key} concentrates as {trainer.key} guides them through magical instruction.",
        )