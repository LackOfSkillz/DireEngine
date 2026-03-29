from evennia import Command

from typeclasses.characters import VALID_GUILDS


class CmdProfession(Command):
    key = "profession"
    locks = "cmd:all()"
    help_category = "Character"

    def func(self):
        caller = self.caller
        args = (self.args or "").strip()

        if not args:
            current = caller.get_profession() if hasattr(caller, "get_profession") else "commoner"
            rank = caller.get_profession_rank_label() if hasattr(caller, "get_profession_rank_label") else current.replace("_", " ").title()
            description = ""
            if hasattr(caller, "get_profession_profile"):
                description = caller.get_profession_profile().get("description", "")
            social = caller.get_social_standing() if hasattr(caller, "get_social_standing") else "Neutral"
            lines = [f"Profession: {rank}"]
            if description:
                lines.append(description)
            lines.append(f"Social Standing: {social}")
            caller.msg("\n".join(lines))
            return

        normalized = str(args).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized not in VALID_GUILDS:
            options = ", ".join(profession.replace("_", " ") for profession in VALID_GUILDS)
            caller.msg(f"Valid professions: {options}")
            return

        if not hasattr(caller, "set_profession") or not caller.set_profession(normalized):
            caller.msg("You cannot take on that profession.")
            return

        if hasattr(caller, "sync_client_state"):
            caller.sync_client_state()
        caller.msg(f"You take on the {normalized.replace('_', ' ').title()} profession.")