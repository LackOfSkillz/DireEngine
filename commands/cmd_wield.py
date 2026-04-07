from evennia import Command


class CmdWield(Command):
    """
    Ready an item for fighting.

    Examples:
      wield sword
      wield dagger
      wie spear
    """

    key = "wield"
    aliases = ["wie"]
    help_category = "Equipment"

    def func(self):
        if self.caller.is_stunned():
            self.caller.msg("You are too stunned to ready a weapon.")
            self.caller.consume_stun()
            return

        if not self.args:
            self.caller.msg("What do you want to wield?")
            return

        obj, matches, base_query, index = self.caller.resolve_numbered_candidate(
            self.args,
            self.caller.get_visible_carried_items(),
            default_first=True,
        )

        if not obj:
            obj, sheath = self.caller.get_stowed_weapon(self.args)
            if not obj:
                if matches and index is not None:
                    self.caller.msg_numbered_matches(base_query, matches)
                else:
                    self.caller.search(base_query or self.args)
                return
            if not obj.move_to(self.caller, quiet=True, use_destination=False):
                self.caller.msg(f"You cannot draw {obj.key} from {sheath.key} right now.")
                return
            self.caller.set_preferred_sheath(sheath)
            self.caller.msg(f"You draw {obj.key} from {sheath.key}.")

        if obj.location != self.caller:
            self.caller.msg(f"You need to be carrying {obj.key} before you can wield it.")
            return

        self.caller.clear_equipped_weapon()
        self.caller.db.equipped_weapon = obj
        message = f"You wield {obj.key}."
        try:
            from systems import onboarding

            completed, override_message = onboarding.note_weapon_action(self.caller, obj)
            if completed and override_message:
                message = override_message
        except Exception:
            pass
        self.caller.msg(message)