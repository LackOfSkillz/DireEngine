from django.conf import settings

from evennia.utils import utils


COMMAND_DEFAULT_CLASS = utils.class_from_module(settings.COMMAND_DEFAULT_CLASS)


def _render_result(cmd, result):
    if not result:
        cmd.msg("Character creation did not return a result.")
        return
    if result.get("error"):
        cmd.msg(result["error"])
    if result.get("message"):
        cmd.msg(result["message"])
    if result.get("summary"):
        cmd.msg(result["summary"])
    prompt = result.get("prompt")
    if prompt:
        cmd.msg(prompt)


class _ChargenAccountCommand(COMMAND_DEFAULT_CLASS):
    account_caller = True
    help_category = "General"

    def require_chargen(self):
        if getattr(self.account.ndb, "chargen_state", None) is None:
            self.msg("No active character creation session. Use |wcharcreate|n to begin.")
            return False
        return True


class CmdCharCreate(_ChargenAccountCommand):
    key = "charcreate"
    aliases = ["chargen"]
    locks = "cmd:pperm(Player)"

    def func(self):
        result = self.account.handle_chargen_input("charcreate", args=self.args)
        _render_result(self, result)


class CmdChargenName(_ChargenAccountCommand):
    key = "name"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("name", args=self.args)
        _render_result(self, result)


class CmdChargenRace(_ChargenAccountCommand):
    key = "race"
    locks = "cmd:all()"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("race", args=self.args)
        _render_result(self, result)


class CmdChargenGender(_ChargenAccountCommand):
    key = "gender"
    locks = "cmd:all()"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("gender", args=self.args)
        _render_result(self, result)


class CmdChargenProfession(_ChargenAccountCommand):
    key = "profession"
    locks = "cmd:all()"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("profession", args=self.args)
        _render_result(self, result)


class CmdChargenStat(_ChargenAccountCommand):
    key = "stat"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("stat", args=self.args)
        _render_result(self, result)


class CmdChargenResetStats(_ChargenAccountCommand):
    key = "resetstats"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("resetstats", args=self.args)
        _render_result(self, result)


class CmdChargenBuild(_ChargenAccountCommand):
    key = "build"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("build", args=self.args)
        _render_result(self, result)


class CmdChargenHeight(_ChargenAccountCommand):
    key = "height"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("height", args=self.args)
        _render_result(self, result)


class CmdChargenHair(_ChargenAccountCommand):
    key = "hair"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("hair", args=self.args)
        _render_result(self, result)


class CmdChargenEyes(_ChargenAccountCommand):
    key = "eyes"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("eyes", args=self.args)
        _render_result(self, result)


class CmdChargenSkin(_ChargenAccountCommand):
    key = "skin"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("skin", args=self.args)
        _render_result(self, result)


class CmdChargenNext(_ChargenAccountCommand):
    key = "next"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("next", args=self.args)
        _render_result(self, result)


class CmdChargenBack(_ChargenAccountCommand):
    key = "back"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("back", args=self.args)
        _render_result(self, result)


class CmdChargenCancel(_ChargenAccountCommand):
    key = "cancel"
    aliases = ["chargencancel"]
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("cancel", args=self.args)
        _render_result(self, result)


class CmdChargenConfirm(_ChargenAccountCommand):
    key = "confirm"
    locks = "cmd:pperm(Player)"

    def func(self):
        if not self.require_chargen():
            return
        result = self.account.handle_chargen_input("confirm", args=self.args)
        _render_result(self, result)
        character = result.get("character")
        if character:
            try:
                self.account.puppet_object(self.session, character)
                self.account.db._last_puppet = character
                self.msg(f"You enter the world as {character.key}.")
            except RuntimeError as exc:
                self.msg(f"Character created, but you could not automatically enter the world: {exc}")


class CmdChargenInspect(_ChargenAccountCommand):
    key = "@chargeninspect"
    locks = "cmd:perm(Admin)"
    help_category = "Admin"

    def func(self):
        target_name = self.args.strip()
        if not target_name:
            self.msg("Usage: @chargeninspect <account>")
            return
        target = self.account.search(target_name, quiet=True)
        if not target:
            self.msg("No such account was found.")
            return
        target = target[0]
        state = getattr(target.ndb, "chargen_state", None)
        if not state:
            self.msg(f"{target.key} has no active chargen state.")
            return
        lines = [
            f"Account: {target.key}",
            f"Current step: {state.current_step}",
            f"Reserved name: {state.reserved_name}",
            f"Blueprint: {state.blueprint.to_dict()}",
            f"Appearance: {dict(state.appearance or {})}",
            f"Points remaining: {state.points_remaining}",
            f"Last validation error: {state.last_validation_error}",
        ]
        self.msg("\n".join(lines))