from .wearables import Wearable


class WearableContainer(Wearable):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.is_container = True
        self.db.capacity = 1
        self.db.allowed_types = []

    def is_worn(self):
        return getattr(self.db, "worn_by", None) is not None

    def get_stored_items(self):
        return list(self.contents)

    def can_hold_item(self, item):
        owner = getattr(self.db, "worn_by", None)
        if not self.is_worn() or not owner:
            return False, "You must be wearing it to use it."

        if item.location != owner:
            return False, "You must be holding that."

        if getattr(item.db, "worn_by", None) == owner:
            return False, "You must unwield or remove that first."

        if len(self.get_stored_items()) >= (self.db.capacity or 1):
            return False, "It cannot hold anything more."

        allowed = self.db.allowed_types or []
        if allowed and getattr(item.db, "item_type", None) not in allowed:
            return False, "That does not fit."

        return True, None

    def store_item(self, item):
        can_hold, msg = self.can_hold_item(item)
        if not can_hold:
            return False, msg

        owner = self.db.worn_by
        if hasattr(owner, "get_weapon") and owner.get_weapon() == item:
            owner.clear_equipped_weapon()

        if not item.move_to(self, quiet=True, use_destination=False):
            return False, f"You cannot stow {item.key}."

        item.db.stored_in = self
        return True, f"You stow {item.key}."

    def retrieve_item(self, item_name):
        owner = getattr(self.db, "worn_by", None)
        if not owner:
            return False, None, "You do not have that stored."

        item, matches, base_query, index = owner.resolve_numbered_candidate(
            item_name,
            self.get_stored_items(),
            default_first=True,
        )
        if not item:
            if matches and index is not None:
                owner.msg_numbered_matches(base_query, matches)
            return False, None, "You do not have that stored."

        if not item.move_to(owner, quiet=True, use_destination=False):
            return False, None, f"You cannot draw {item.key}."
        item.db.stored_in = None
        return True, item, f"You draw {item.key}."

        return False, None, "You do not have that stored."

    def get_stowed_display(self, looker=None):
        if looker is not None and looker != getattr(self.db, "worn_by", None):
            return None

        stored = self.get_stored_items()
        if not stored:
            return "empty"
        return ", ".join(obj.key for obj in stored)

    def return_appearance(self, looker):
        desc = self.db.desc or "A practical wearable container."
        lines = [self.key, desc]
        if self.is_worn():
            lines.append("It is currently being worn.")

        if looker == getattr(self.db, "worn_by", None):
            stored = self.get_stored_items()
            if stored:
                lines.append("It currently holds:")
                for item in stored:
                    lines.append(f"  {item.key}")
            else:
                lines.append("It currently holds: empty.")

        return "\n".join(lines)