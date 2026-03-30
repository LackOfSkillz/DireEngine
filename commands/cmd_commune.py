from commands.command import Command


class CmdCommune(Command):
    """
    Call upon a cleric commune.

    Examples:
        commune solace
        commune ward
        commune vigil corpse
    """

    key = "commune"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "is_profession") or not caller.is_profession("cleric"):
            caller.msg("Only a cleric can call upon a commune.")
            return

        args = str(self.args or "").strip()
        if not args:
            caller.msg("Commune what? Try solace, ward, or vigil.")
            return

        parts = args.split(None, 1)
        commune_name = parts[0].lower()
        target = None
        if len(parts) > 1:
            target = caller.search(parts[1], location=caller.location)
            if not target:
                return

        ok, message = caller.commune_with_divine(commune_name, target=target) if hasattr(caller, "commune_with_divine") else (False, "You cannot do that.")
        caller.msg(message)
