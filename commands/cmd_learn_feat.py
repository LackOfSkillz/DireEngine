from __future__ import annotations

from commands.command import Command
from commands.cmd_mindstate import render_mindstate
from engine.services.feat_training_service import FeatTrainerService
from engine.services.messaging import send_untargeted_action


def _run_feat_learning(caller, raw_args):
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


class CmdLearnFeat(Command):
    """Dispatch learn requests to mindstate, feats, or guild spell instruction."""

    key = "learn"
    help_category = "Magic"

    def func(self):
        caller = self.caller
        if hasattr(caller, "ensure_core_defaults"):
            caller.ensure_core_defaults()

        raw_args = str(self.args or "").strip()
        if not raw_args:
            render_mindstate(caller)
            return

        lowered = raw_args.lower()
        if lowered.startswith("feat "):
            _run_feat_learning(caller, raw_args)
            return

        spell_name, separator, trainer_name = raw_args.partition(" from ")
        if not separator:
            caller.msg("Usage: LEARN <spell> FROM <guildmaster>")
            return
        trainer = caller.search(trainer_name.strip(), location=caller.location)
        if not trainer:
            return
        if not hasattr(trainer, "teach_spell"):
            caller.msg(f"{trainer.key} cannot teach spells.")
            return

        result = trainer.teach_spell(caller, spell_name.strip())
        if not result.success:
            detail = next(iter(result.messages or result.errors or []), "You cannot learn that spell right now.")
            caller.msg(f"{trainer.key} says, \"{detail}\"")
            return

        send_untargeted_action(
            caller,
            actor_message=(
                f"{trainer.key} instructs you in {spell_name.strip().title()}. You commit the pattern to memory."
            ),
            room_message=f"{caller.key} studies closely as {trainer.key} guides them through spell instruction.",
        )