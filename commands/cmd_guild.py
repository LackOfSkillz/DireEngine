from evennia import Command

from typeclasses.characters import VALID_GUILDS


class CmdGuild(Command):
    key = "guild"
    aliases = ["profession"]
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if not args:
            current = caller.get_guild() if hasattr(caller, "get_guild") else None
            if not current:
                caller.msg("You do not currently belong to a guild.")
                return
            caller.msg(f"You currently belong to the {current.replace('_', ' ').title()} guild.")
            return

        normalized = str(args).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized not in VALID_GUILDS:
            options = ", ".join(guild.replace("_", " ") for guild in VALID_GUILDS)
            caller.msg(f"Valid guilds: {options}")
            return

        if not caller.set_guild(normalized):
            caller.msg("You cannot join that guild.")
            return

        caller.msg(f"You align yourself with the {normalized.replace('_', ' ').title()} guild.")