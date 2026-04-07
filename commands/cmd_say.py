from commands.command import Command

from world.languages import apply_language_exposure, get_language_display_name


class CmdSay(Command):
    """
    Speak aloud in your active language.

    Examples:
        say Hello there.
        " Hello there.
    """

    key = "say"
    aliases = ['"']
    locks = "cmd:all()"
    help_category = "Communication"

    def func(self):
        caller = self.caller
        speech = str(self.args or "").strip()
        if not speech:
            caller.msg("Say what?")
            return

        spoken_text = caller.render_spoken_text(speech) if hasattr(caller, "render_spoken_text") else speech
        active_language = caller.get_active_language() if hasattr(caller, "get_active_language") else "common"
        language_name = get_language_display_name(active_language)

        caller.msg(f'You say in {language_name}, "{spoken_text}"')
        if not caller.location:
            return

        for listener in list(caller.location.contents):
            if listener == caller or not hasattr(listener, "msg"):
                continue
            perceived_text = listener.perceive_spoken_text(spoken_text, active_language, speaker=caller) if hasattr(listener, "perceive_spoken_text") else spoken_text
            listener.msg(f'{caller.get_display_name(looker=listener)} says in {language_name}, "{perceived_text}"')
            apply_language_exposure(listener, active_language, amount=0.01)