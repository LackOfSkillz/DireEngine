import time

from commands.command import Command

from utils.crime import call_guards


class CmdThug(Command):
    """
    Use thug-style intimidation or rough tactics.

    Examples:
        thug guard
    """

    key = "thug"
    locks = "cmd:all()"
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        raw_args = (self.args or "").strip()
        if not raw_args:
            caller.msg("Usage: thug <target> or thug rough <target>")
            return

        if caller.is_in_roundtime():
            caller.msg_roundtime_block()
            return

        if caller.is_hidden():
            caller.msg("You cannot do that from the shadows.")
            return

        rough = False
        target_name = raw_args
        if raw_args.lower().startswith("rough "):
            rough = True
            target_name = raw_args[6:].strip()

        if not target_name:
            caller.msg("Who do you want to pressure?")
            return

        target = caller.search(target_name, location=caller.location)
        if not target:
            return

        if target == caller:
            caller.msg("That would be a strange display.")
            return

        if target.location != caller.location:
            caller.msg("They are not here.")
            return

        room = caller.location
        if rough:
            if not caller.is_profession("thief") or caller.get_profession_rank() < 20:
                caller.msg("You lack the experience to do that.")
                return
            if getattr(target.db, "roughed", False):
                caller.msg("They are already reeling from a rough opening.")
                return

        now = time.time()
        caller.db.recent_action = True
        caller.db.recent_action_timer = now
        caller.clear_disguise()
        if hasattr(caller, "set_position_state"):
            caller.set_position_state("exposed")
        caller.reveal()

        if rough:
            target.db.roughed = True
            target.db.rough_timer = now
            if hasattr(target, "set_attention_state"):
                target.set_attention_state("alert")
            if hasattr(caller, "set_target"):
                caller.set_target(target)
            if hasattr(target, "set_target"):
                target.set_target(caller)
            caller.db.in_combat = True
            target.db.in_combat = True
            caller.db.escape_chain = 0
            if hasattr(caller, "add_crime"):
                caller.add_crime(2)
            if room:
                room.db.alert_level = int(getattr(room.db, "alert_level", 0) or 0) + 2
                if not (hasattr(room, "is_lawless") and room.is_lawless()):
                    call_guards(room, caller)
            caller.msg(f"You slam into {target.key}, throwing them off balance!")
            target.msg("You are caught off guard and exposed!")
            caller.apply_thief_roundtime(3)
            return

        if getattr(target.db, "intimidated", False):
            caller.msg("They are already feeling the pressure.")
            return

        target.db.intimidated = True
        target.db.intimidation_timer = now
        if hasattr(target, "set_attention_state"):
            target.set_attention_state("distracted")
        if hasattr(caller, "add_crime"):
            caller.add_crime(1)
        if room:
            room.db.alert_level = int(getattr(room.db, "alert_level", 0) or 0) + 1
        caller.msg(f"You pressure {target.key}, forcing hesitation.")
        target.msg(f"{caller.key} threatens you!")
        caller.apply_thief_roundtime(2)
