from commands.command import Command


class CmdDraw(Command):
    """
        Pull an item out of something you are wearing.

        Examples:
            draw dagger
            draw sword from back scabbard
            dra mace from belt sheath
    """

    key = "draw"
    aliases = ["dra"]
    help_category = "Equipment"

    def func(self):
        if not self.args:
            self.caller.msg("What do you want to draw?")
            return

        item_name = self.args.strip()
        container = None
        if " from " in item_name:
            item_name, container_name = [part.strip() for part in item_name.split(" from ", 1)]
            container = self.caller.get_worn_container_by_name(container_name)
            if not container:
                self.caller.msg(f"You are not wearing {container_name}.")
                return

        containers = [container] if container else self.caller.get_worn_containers()
        if not containers:
            self.caller.msg("You do not have anything like that stored.")
            return

        for worn_container in containers:
            success, item, msg = worn_container.retrieve_item(item_name)
            if success:
                self.caller.msg(msg)
                if getattr(item.db, "item_type", None) == "weapon":
                    self.caller.clear_equipped_weapon()
                    self.caller.db.equipped_weapon = item
                    self.caller.msg(f"You wield {item.key}.")
                return

        self.caller.msg("You have nothing like that stored.")