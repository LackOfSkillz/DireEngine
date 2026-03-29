from commands.command import Command

from utils.crime import resolve_justice_case


class CmdPlead(Command):
    key = "plead"
    locks = "cmd:all()"
    help_category = "Justice"

    def func(self):
        caller = self.caller
        plea = str(self.args or "").strip().lower()
        if not getattr(caller.db, "awaiting_plea", False):
            caller.msg("No one is asking for your plea.")
            return

        if plea not in {"guilty", "innocent"}:
            caller.msg("Plead guilty or innocent.")
            return

        caller.db.plea = plea
        caller.db.awaiting_plea = False

        if plea == "guilty":
            caller.msg("You admit your guilt. The judge nods.")

        resolve_justice_case(caller)