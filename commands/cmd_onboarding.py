from commands.command import Command
from systems import onboarding


class CmdOnboardingGender(Command):
    key = "gender"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        ok, message = onboarding.set_gender(self.caller, self.args)
        self.caller.msg(message)


class CmdOnboardingStand(Command):
    key = "stand"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        raw = str(self.args or "").strip()
        if not raw.lower().startswith("at "):
            self.caller.msg("Usage: stand at <human|elf|dwarf>. You can also just type human, elf, or dwarf.")
            return
        ok, message = onboarding.select_race(self.caller, raw[3:])
        self.caller.msg(message)


class CmdOnboardingSet(Command):
    key = "set"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        raw = str(self.args or "").strip().lower()
        for label, field in {
            "hair style": "hair_style",
            "hair color": "hair_color",
            "build": "build",
            "height": "height",
            "eyes": "eyes",
        }.items():
            prefix = f"{label} "
            if raw.startswith(prefix):
                value = raw[len(prefix):].strip()
                ok, message = onboarding.set_trait(self.caller, field, value)
                self.caller.msg(message)
                return
        self.caller.msg("Usage: set hair style <value>, set hair color <value>, set build <value>, set height <value>, or set eyes <value>. Short forms also work: hair short, hair black, build lean, height tall, eyes green.")


class CmdOnboardingName(Command):
    key = "name"
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        ok, message = onboarding.set_final_name(self.caller, self.args)
        self.caller.msg(message)


class CmdOnboardingIntake(Command):
    key = "intake"
    aliases = ["objective"]
    locks = "cmd:all()"
    help_category = "General"

    def func(self):
        self.caller.msg("\n".join(onboarding.get_status_lines(self.caller)))