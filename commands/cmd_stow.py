from commands.command import Command

from world.systems import fishing_economy


class CmdStow(Command):
    """
    Put a carried item into something you are wearing.

    Examples:
      stow dagger
      stow dagger in belt sheath
      sto mace in back scabbard
    """

    key = "stow"
    aliases = ["sto"]
    help_category = "Equipment"

    def func(self):
        if not self.args:
            self.caller.msg("What do you want to stow?")
            return

        item_name = self.args.strip()
        container = None
        if " in " in item_name:
            item_name, container_name = [part.strip() for part in item_name.split(" in ", 1)]
            container = self.caller.get_worn_container_by_name(container_name)
            if not container:
                fish_strings = [obj for obj in list(getattr(self.caller, "contents", []) or []) if fishing_economy.is_fish_string(obj)]
                container, matches, base_query, index = self.caller.resolve_numbered_candidate(container_name, fish_strings, default_first=True)
                if not container and matches and index is not None:
                    self.caller.msg_numbered_matches(base_query, matches)
                    return
            if not container:
                self.caller.msg(f"You are not wearing {container_name}.")
                return

        item, matches, base_query, index = self.caller.resolve_numbered_candidate(
            item_name,
            self.caller.get_visible_carried_items(),
            default_first=True,
        )
        if not item:
            if matches and index is not None:
                self.caller.msg_numbered_matches(base_query, matches)
            else:
                self.caller.search(base_query or item_name)
            return

        if not container:
            containers = self.caller.get_worn_containers()
            if not containers:
                containers = [obj for obj in list(getattr(self.caller, "contents", []) or []) if fishing_economy.is_fish_string(obj)]
            if not containers:
                self.caller.msg("You are not wearing anything you can stow that in.")
                return
            if len(containers) > 1:
                self.caller.msg("You are wearing more than one container. Name which one you want to use.")
                return
            container = containers[0]

        success, msg = container.store_item(item)
        self.caller.msg(msg)