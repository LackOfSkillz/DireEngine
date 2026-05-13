from __future__ import annotations

from commands.command import Command
from engine.presenters.combat_presenter import CombatPresenter
from engine.services.attack_verb_service import AttackVerbService


class _BaseAttackVerbCommand(Command):
    locks = "cmd:all()"
    help_category = "Combat"
    verb_key = ""

    def func(self):
        execution = AttackVerbService.execute(self.caller, self.verb_key, target_arg=self.args)
        if execution.result is None and execution.matches:
            self.msg_target_matches(execution.base_query, execution.matches)
            return
        CombatPresenter.present_attack(execution.result, self.caller, execution.target)


class CmdThrust(_BaseAttackVerbCommand):
    """
    Thrust at a target with your weapon.

    Usage:
        thrust [target]
        thrust at [target]

    Thrust emphasizes puncture damage.
    Roundtime: 5 seconds.
    """

    key = "thrust"
    verb_key = "thrust"


class CmdLunge(_BaseAttackVerbCommand):
    """
    Lunge hard at a target.

    Usage:
        lunge [target]
        lunge at [target]

    Lunge commits to a longer-reaching attack.
    Roundtime: 7 seconds.
    """

    key = "lunge"
    verb_key = "lunge"


class CmdSlice(_BaseAttackVerbCommand):
    """
    Slice through a target.

    Usage:
        slice [target]
        slice at [target]

    Slice emphasizes cutting damage.
    Roundtime: 5 seconds.
    """

    key = "slice"
    verb_key = "slice"


class CmdChop(_BaseAttackVerbCommand):
    """
    Chop at a target.

    Usage:
        chop [target]
        chop at [target]

    Chop preserves the classic tree and vine terrain guard.
    Roundtime: 5 seconds.
    """

    key = "chop"
    verb_key = "chop"


class CmdSweep(_BaseAttackVerbCommand):
    """
    Sweep low at a target.

    Usage:
        sweep [target]
        sweep at [target]

    Sweep biases toward lower-body hits.
    Roundtime: 5 seconds.
    """

    key = "sweep"
    verb_key = "sweep"


class CmdFeint(_BaseAttackVerbCommand):
    """
    Feint against a target.

    Usage:
        feint [target]

    Feint can fall back to your current engagement target.
    Roundtime: 3 seconds.
    """

    key = "feint"
    verb_key = "feint"


class CmdJab(_BaseAttackVerbCommand):
    """
    Jab at a target.

    Usage:
        jab [target]
        jab at [target]

    Jab is the fastest direct attack after feint.
    Roundtime: 4 seconds.
    """

    key = "jab"
    verb_key = "jab"
