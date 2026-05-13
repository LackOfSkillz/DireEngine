from commands.command import Command
from engine.presenters.combat_presenter import CombatPresenter
from engine.services.attack_verb_service import AttackVerbService


class CmdAttack(Command):
    """
    Attack someone in the room.

    Examples:
      attack goblin
      att corl
    """

    key = "attack"
    aliases = ["att", "hit", "kill", "bash"]
    help_category = "Combat"

    def func(self):
        execution = AttackVerbService.execute(self.caller, "thrust", target_arg=self.args)
        if execution.result is None and execution.matches:
            self.msg_target_matches(execution.base_query, execution.matches)
            return
        CombatPresenter.present_attack(execution.result, self.caller, execution.target)