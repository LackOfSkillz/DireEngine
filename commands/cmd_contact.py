from commands.command import Command
from world.systems.theft import get_contact_info, request_contact_service


class CmdContact(Command):
    """
    Review a thief contact scaffold.

    Examples:
        contact
        contact list
        contact fence
        contact fence info
        contact fence heat
    """

    key = "contact"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        raw = (self.args or "").strip().lower()
        contacts = dict(getattr(getattr(caller, "db", None), "contacts", None) or {})
        if not raw or raw == "list":
            if not contacts:
                caller.msg("You have no criminal contacts established yet.")
                return
            lines = ["Known contacts:"]
            for name, info in sorted(contacts.items()):
                role = str((dict(info or {})).get("role", "unknown") or "unknown")
                lines.append(f"{name}: {role}")
            caller.msg("\n".join(lines))
            return

        tokens = raw.split()
        contact_name = tokens[0]
        request_type = tokens[1] if len(tokens) > 1 else None

        info = get_contact_info(caller, contact_name)
        if not info:
            caller.msg("You have not cultivated that contact yet.")
            return

        if request_type in {"info", "heat"}:
            outcome = request_contact_service(caller, contact_name, request_type=request_type)
            caller.msg(str(outcome.get("message") or "No answer comes back."))
            return

        role = str(info.get("role", "unknown") or "unknown")
        disposition = int(info.get("disposition", 0) or 0)
        caller.msg(f"{contact_name}: role={role}, disposition={disposition}")