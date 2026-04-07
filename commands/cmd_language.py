from commands.command import Command

from world.languages import get_language_display_name, normalize_language_name


class CmdLanguage(Command):
    """
    View or change your active spoken language.

    Examples:
        language
        language saurathi
    """

    key = "language"
    aliases = ["lang"]
    locks = "cmd:all()"
    help_category = "Communication"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if not args:
            if hasattr(caller, "get_language_proficiencies"):
                profiles = caller.get_language_proficiencies()
            else:
                profiles = {"common": 1.0}
            languages = [
                f"{get_language_display_name(language)} ({int(round(float(proficiency or 0.0) * 100))}%)"
                for language, proficiency in profiles.items()
                if float(proficiency or 0.0) > 0.0
            ]
            known = ", ".join(languages) if languages else "Common (100%)"
            active = caller.get_active_language() if hasattr(caller, "get_active_language") else "common"
            caller.msg(f"Known languages: {known}")
            caller.msg(f"Active language: {get_language_display_name(active)}")
            return

        language_key = normalize_language_name(args, default=None)
        if language_key is None:
            caller.msg("Unknown language.")
            return

        if hasattr(caller, "set_language") and caller.set_language(language_key):
            caller.msg(f"You now speak {get_language_display_name(language_key)}.")
            return

        caller.msg("You do not know that language.")