from commands.command import Command
from world.systems.fishing import attach_bait, find_bait_item, resolve_pull, rig_fishing_pole, start_fishing_cast, untangle_fishing_pole


class CmdFish(Command):
    """
    Cast a line into fishable water.

    Examples:
        fish
    """

    key = "fish"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        start_fishing_cast(self.caller)


class CmdBait(Command):
    """
    Prepare bait for fishing.

    Examples:
        bait worm
    """

    key = "bait"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        query = str(self.args or "").strip()
        if not query:
            caller.msg("Bait what?")
            return

        bait_item, matches, base_query, index, invalid_selection = find_bait_item(caller, query=query)
        if bait_item is None:
            if invalid_selection:
                caller.msg("You can't use that as bait.")
                return
            if matches and index is None:
                caller.msg_numbered_matches(base_query, matches)
            else:
                caller.msg("You are not carrying that bait.")
            return

        _ok, message, _session = attach_bait(caller, bait_item)
        caller.msg(message)


class CmdPull(Command):
    """
    React to a bite or keep tension on a hooked fish.

    Examples:
        pull
    """

    key = "pull"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        resolve_pull(self.caller)


class CmdRig(Command):
    """
    Re-rig a fishing pole.

    Examples:
        rig pole
    """

    key = "rig"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        query = str(self.args or "pole").strip().lower()
        if query not in {"pole", "rod", "fishing pole", "line", "hook"}:
            caller.msg("Rig what? Try 'rig pole'.")
            return
        _ok, message = rig_fishing_pole(caller)
        caller.msg(message)


class CmdUntangle(Command):
    """
    Untangle a fishing pole.

    Examples:
        untangle pole
    """

    key = "untangle"
    locks = "cmd:all()"
    help_category = "Survival"

    def func(self):
        caller = self.caller
        query = str(self.args or "pole").strip().lower()
        if query not in {"pole", "rod", "fishing pole", "line"}:
            caller.msg("Untangle what? Try 'untangle pole'.")
            return
        _ok, message = untangle_fishing_pole(caller)
        caller.msg(message)