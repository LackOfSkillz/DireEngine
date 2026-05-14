from __future__ import annotations

from commands.command import Command
from engine.services.feat_training_service import FeatTrainerService
from engine.services.messaging import send_untargeted_action


class CmdForgetFeat(Command):
    """Forget a magical feat at a feat trainer."""

    key = "forget"
    aliases = ["unlearn"]
    help_category = "Magic"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        raw_args = str(self.args or "").strip()
        lowered = raw_args.lower()
        if not lowered.startswith("feat "):
            caller.msg("Usage: FORGET FEAT <feat name>")
            return
        feat_name = raw_args[5:].strip()
        if not feat_name:
            caller.msg("Usage: FORGET FEAT <feat name>")
            return

        trainer = FeatTrainerService.find_trainer_in_room(caller)
        if trainer is None:
            caller.msg("There is no feat trainer here.")
            return

        feat = trainer.resolve_feat(feat_name)
        if feat is None:
            caller.msg(f"{trainer.key} says, \"I know of no such feat as '{feat_name}'.\"")
            return

        result = FeatTrainerService.forget_feat(caller, feat.id)
        if not result.success:
            caller.msg(f"{trainer.key} says, \"{trainer.describe_forgetting_path(caller, feat)}\"")
            return

        send_untargeted_action(
            caller,
            actor_message=(
                f"{trainer.key} carefully unwinds the patterns of {feat.name} from your mind. "
                f"You feel the slot freed and the kronar leave your purse. "
                f"({int(result.slots_refunded or 0)} slot refunded; {int(result.cost_paid or 0)} kronar paid.)"
            ),
            room_message=f"{trainer.key} performs a complex unbinding gesture on {caller.key}.",
        )