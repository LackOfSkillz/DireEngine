from commands.command import Command
from engine.services.messaging import send_untargeted_action


class CmdSleep(Command):
    """
    Enter a meditative rest state to drain experience pools.

    Usage:
        sleep
    """

    key = "sleep"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        character = self.caller
        if not hasattr(character, "ensure_sleep_defaults"):
            character.msg("You cannot sleep.")
            return
        character.ensure_sleep_defaults()
        current = str(getattr(character.db, "sleep_state", "awake") or "awake")
        if current == "awake":
            character.db.sleep_state = "light_sleep"
            send_untargeted_action(
                actor=character,
                actor_message=(
                    "You settle into a meditative posture and allow your mind to enter a state of rest. "
                    "You will no longer gain new experience until you awaken, but you will continue to absorb experience into new ranks."
                ),
                room_message=f"{character.key} settles into a meditative posture and grows still.",
            )
        elif current == "light_sleep":
            character.db.sleep_state = "deep_sleep"
            send_untargeted_action(
                actor=character,
                actor_message=(
                    "You sink deeper into rest. Your mind slows to a still point - you no longer absorb experience, "
                    "but your Rested Experience grows."
                ),
                room_message=f"{character.key}'s breath slows further as they enter a deeper sleep.",
            )
        else:
            character.msg("You are already in deep sleep.")
            return
        if hasattr(character, "sync_client_state"):
            character.sync_client_state()
