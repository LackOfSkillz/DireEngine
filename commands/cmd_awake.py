from commands.command import Command
from engine.services.messaging import send_untargeted_action


class CmdAwake(Command):
    """
    Return to an awake state from sleep.

    Usage:
        awake
    """

    key = "awake"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        character = self.caller
        if not hasattr(character, "ensure_sleep_defaults"):
            character.msg("You are already awake.")
            return
        character.ensure_sleep_defaults()
        if character.is_awake():
            character.msg("You are already awake.")
            return
        character.db.sleep_state = "awake"
        send_untargeted_action(
            actor=character,
            actor_message="Your mind returns to active awareness. You are ready to train.",
            room_message=f"{character.key} stirs and returns to alertness.",
        )
        if hasattr(character, "sync_client_state"):
            character.sync_client_state()
