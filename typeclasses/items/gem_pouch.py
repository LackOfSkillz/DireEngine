from typeclasses.objects import Object


class GemPouch(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_container = True
        self.db.is_gem_pouch = True
        self.db.item_value = 25
        self.db.max_capacity_weight = 9999.0
        self.db.value = 25
        self.db.weight = 0.5
        self.db.desc = "A small pouch meant to keep gemstones together and close at hand."

    def return_appearance(self, looker):
        contents_weight = self.get_contents_weight() if hasattr(self, "get_contents_weight") else 0.0
        total_weight = self.get_total_weight() if hasattr(self, "get_total_weight") else float(getattr(self.db, "weight", 0.0) or 0.0)
        lines = [self.key, self.db.desc or "A small pouch meant to keep gemstones together and close at hand."]
        lines.append(f"Weight: {total_weight:.1f} (contents: {contents_weight:.1f})")
        lines.append(f"Capacity: {contents_weight:.1f} / {float(getattr(self.db, 'max_capacity_weight', 0.0) or 0.0):.1f}")
        stored = list(self.contents)
        if stored:
            lines.append("It currently holds:")
            for item in stored:
                lines.append(f"  {item.key}")
        else:
            lines.append("It currently holds: empty.")
        return "\n".join(lines)
