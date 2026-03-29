from evennia import Command


class CmdTrain(Command):
    key = "train"
    locks = "cmd:all()"
    help_category = "Training & Lore"

    def func(self):
        caller = self.caller
        if not hasattr(caller, "advance_profession"):
            caller.msg("You cannot train that way right now.")
            return

        ok, message = caller.advance_profession()
        caller.msg(message)
        if ok and hasattr(caller, "sync_client_state"):
            caller.sync_client_state()