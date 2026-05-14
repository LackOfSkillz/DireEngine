from commands.command import Command
from engine.services.messaging import send_action_messages, send_untargeted_action


class CmdCombatReset(Command):
    """
    Reset a character's combat and wound state.

    Examples:
        combatreset AedanSmoke
    """

    key = "combatreset"
    aliases = ["cmbreset"]
    locks = "cmd:perm(Builder) or perm(Admin) or perm(Developer)"
    help_category = "Admin"

    def func(self):
        caller = self.caller
        query = str(self.args or "").strip()
        if not query:
            caller.msg("Combat reset whom?")
            return

        target = caller.search(query, global_search=True)
        if not target:
            return
        if not hasattr(target, "combat_reset_state"):
            caller.msg(f"You cannot combat reset {target.key}.")
            return

        target.combat_reset_state()
        if target != caller:
            send_action_messages(
                actor=caller,
                target=target,
                room=getattr(target, "location", None) or getattr(caller, "location", None),
                actor_message=f"You reset {target.key}'s combat state.",
                target_message="A restoring force clears your combat state and lingering wounds.",
                room_message=f"{target.key} suddenly looks refreshed and at ease.",
            )
            return
        send_untargeted_action(
            caller,
            actor_message=f"You reset {target.key}'s combat state.",
            room_message=f"{target.key} suddenly looks refreshed and at ease.",
        )
