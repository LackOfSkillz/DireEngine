from commands.command import Command
from world.helpers.target_resolver import split_quantity_target


class CmdDrop(Command):
    """
        Put down something you are carrying or wearing.

        Examples:
            drop sword
            drop cloak
    """

    key = "drop"
    help_category = "Equipment"

    def func(self):
        if not self.args:
            self.caller.msg("What do you want to drop?")
            return

        if hasattr(self.caller, "merge_stackable_inventory"):
            try:
                self.caller.merge_stackable_inventory()
            except Exception:
                pass

        requested_quantity, target_query = split_quantity_target(self.args)
        target_query = target_query or self.args

        candidates = [
            item for item in list(getattr(self.caller, "contents", []) or [])
            if getattr(getattr(item, "db", None), "worn_by", None) != self.caller
        ]

        item, matches, base_query, index = self.resolve_item_target(
            target_query,
            candidates,
            default_first=True,
        )
        if not item:
            item = self.caller.find_worn_item(self.args)
            if not item:
                if matches and index is not None:
                    self.msg_item_matches(base_query, matches)
                else:
                    self.caller.search(base_query or target_query)
                return
            self.caller.unequip_item(item)

        if self.caller.get_weapon() == item:
            self.caller.clear_equipped_weapon()

        if not self.caller.location:
            self.caller.msg("There is nowhere here to drop that.")
            return

        if requested_quantity is None and index is not None and hasattr(item, "is_stackable") and item.is_stackable():
            requested_quantity = 1

        if requested_quantity is not None and hasattr(item, "is_stackable") and item.is_stackable():
            total_quantity = item.get_stack_quantity() if hasattr(item, "get_stack_quantity") else 1
            if requested_quantity > total_quantity:
                self.caller.msg(f"You only have {total_quantity} of {item.key}.")
                return
            if requested_quantity < total_quantity and hasattr(item, "split_stack"):
                split_item = item.split_stack(requested_quantity, destination=self.caller.location)
                if split_item is None:
                    self.caller.msg("You cannot separate that stack right now.")
                    return
                if requested_quantity == 1:
                    self.caller.msg(f"You drop {item.key}.")
                else:
                    self.caller.msg(f"You drop {requested_quantity} {item.key}.")
                return

        item.move_to(self.caller.location, quiet=True, use_destination=False)
        self.caller.msg(f"You drop {item.key}.")