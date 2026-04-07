from commands.command import Command

from world.languages import apply_comprehension, apply_language_exposure, get_eavesdrop_level, get_language_display_name


class CmdWhisper(Command):
    """
    Whisper privately to another player.

    Examples:
        whisper kier = keep moving
        wh kier = keep moving
    """

    key = "whisper"
    aliases = ["wh"]
    locks = "cmd:all()"
    help_category = "Communication"

    def parse(self):
        raw_args = str(self.args or "")
        if "=" not in raw_args:
            self.target_name = None
            self.message = None
            return

        target_name, message = raw_args.split("=", 1)
        self.target_name = target_name.strip()
        self.message = message.strip()

    def func(self):
        caller = self.caller

        if not self.target_name or not self.message:
            caller.msg("Usage: whisper <target> = <message>")
            return

        target = caller.search(self.target_name)
        if not target:
            return
        if target == caller:
            caller.msg("Whispering to yourself would be redundant.")
            return
        if not hasattr(target, "perceive_spoken_text"):
            caller.msg("You can only whisper to someone who can understand speech.")
            return

        active_language = caller.get_active_language() if hasattr(caller, "get_active_language") else "common"
        language_name = get_language_display_name(active_language)
        spoken_text = caller.render_spoken_text(self.message) if hasattr(caller, "render_spoken_text") else self.message
        perceived_text = target.perceive_spoken_text(spoken_text, active_language, speaker=caller) if hasattr(target, "perceive_spoken_text") else spoken_text

        caller.msg(f'You whisper to {target.get_display_name(looker=caller)} in {language_name}, "{spoken_text}"')
        target.msg(f'{caller.get_display_name(looker=target)} whispers to you in {language_name}, "{perceived_text}"')
        apply_language_exposure(target, active_language, amount=0.01)

        room = getattr(caller, "location", None)
        if not room:
            return

        for listener in list(room.contents):
            if listener in (caller, target) or not hasattr(listener, "msg"):
                continue
            if not hasattr(listener, "perceive_spoken_text"):
                continue

            leak_level = float(get_eavesdrop_level(listener, caller) or 0.0)
            if leak_level <= 0.0:
                continue

            leak_seed = f"leak:{getattr(caller, 'id', None) or getattr(caller, 'key', 'speaker')}:{getattr(listener, 'id', None) or getattr(listener, 'key', 'listener')}:{active_language}"
            leaked_text = apply_comprehension(spoken_text, leak_level, seed=leak_seed)
            perceived_leak = listener.perceive_spoken_text(leaked_text, active_language, speaker=caller)
            listener.msg(f'You overhear {caller.get_display_name(looker=listener)} whispering in {language_name}, "{perceived_leak}"')
            apply_language_exposure(listener, active_language, amount=0.005)

        # TODO: eavesdrop hooks