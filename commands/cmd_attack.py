from commands.command import Command
from engine.presenters.combat_presenter import CombatPresenter
from engine.services.combat_service import CombatService


class CmdAttack(Command):
    """
    Attack someone in the room.

    Examples:
      attack goblin
      att corl
    """

    key = "attack"
    aliases = ["att", "hit", "kill", "slice", "bash", "jab"]
    help_category = "Combat"

    def func(self):
        target = self._resolve_target()
        result = CombatService.attack(self.caller, target)
        CombatPresenter.present_attack(result, self.caller, target)

    def _resolve_target(self):
        if not self.args:
            return self.caller.get_target() if hasattr(self.caller, "get_target") else None
        target_name = self.args.strip()
        target, matches, base_query, index, _scope = self.resolve_target(
            target_name,
            scopes=("characters",),
            default_first=True,
        )
        if not target and matches and index is not None:
            self.msg_target_matches(base_query, matches)
        return target