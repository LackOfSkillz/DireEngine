from typeclasses.wearable_containers import WearableContainer

from world.systems import fishing_economy


class FishString(WearableContainer):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_fish_string = True
        self.db.slot = "belt"
        self.db.capacity = 12
        self.db.max_capacity_weight = 60.0
        self.db.allowed_types = ["fish"]
        self.db.weight = 0.4
        self.db.item_type = "container"
        self.db.item_value = 8
        self.db.value = 8
        self.db.desc = "A looped cord and hooks meant for carrying a day's catch without filling your hands."
        self.aliases.add("string")
        self.aliases.add("fish string")

    def can_hold_item(self, item):
        if not fishing_economy.is_fish_item(item):
            return False, "Only fish belong on a fish string."
        if item.location != self.db.worn_by and item.location != getattr(self, "location", None):
            return False, "You must be holding that."
        if len(self.get_stored_items()) >= int(getattr(self.db, "capacity", 1) or 1):
            return False, "The string is already heavy with fish."
        current_contents_weight = self.get_contents_weight() if hasattr(self, "get_contents_weight") else 0.0
        item_weight = float(getattr(getattr(item, "db", None), "weight", 0.0) or 0.0)
        max_capacity_weight = float(getattr(self.db, "max_capacity_weight", 0.0) or 0.0)
        if max_capacity_weight > 0 and (current_contents_weight + item_weight) > max_capacity_weight:
            return False, "The string cannot take that much more weight."
        return True, None

    def store_item(self, item):
        can_hold, msg = self.can_hold_item(item)
        if not can_hold:
            return False, msg
        if not item.move_to(self, quiet=True, use_destination=False):
            return False, f"You cannot secure {item.key} to the string."
        item.db.stored_in = self
        return True, f"You secure {item.key} to the fish string."

    def return_appearance(self, looker):
        desc = self.db.desc or "A practical fish string."
        lines = [self.key, desc]
        lines.append(f"Weight: {float(self.get_total_weight() or 0.0):.1f}")
        lines.append(f"Capacity: {len(self.get_stored_items())}/{int(getattr(self.db, 'capacity', 0) or 0)} fish")
        stored = self.get_stored_items()
        if stored:
            lines.append("It currently holds:")
            for item in stored:
                lines.append(f"  {item.key}")
        else:
            lines.append("It currently holds: empty.")
        return "\n".join(lines)