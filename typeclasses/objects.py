"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for all entities
with a location in the game world (like Characters, Rooms, Exits).

"""

import logging
import re

from django.utils.text import slugify
from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object

from systems.chargen.mirror import MIRROR_KEY, is_chargen_active, render_mirror
from world.helpers.display_aggregation import format_stack_label
from world.helpers.target_resolver import mark_item_arrival


LOGGER = logging.getLogger(__name__)


class ObjectParent:
    """Shared helpers for all in-world objects."""

    def split_numbered_query(self, query):
        raw_query = (query or "").strip()
        if not raw_query:
            return "", None

        match = re.match(r"^(?P<name>.+?)\s+(?P<index>\d+)$", raw_query)
        if not match:
            return raw_query, None

        return match.group("name").strip(), max(1, int(match.group("index")))

    def get_name_matches(self, query, candidates):
        target = (query or "").strip().lower()
        if not target:
            return []

        exact = []
        partial = []
        contains = []
        for obj in candidates or []:
            if not obj:
                continue

            names = []
            key = str(getattr(obj, "key", "") or "").strip().lower()
            if key:
                names.append(key)

            aliases = getattr(obj, "aliases", None)
            if aliases and hasattr(aliases, "all"):
                try:
                    names.extend(str(alias).strip().lower() for alias in aliases.all())
                except Exception:
                    pass

            if target in names:
                exact.append(obj)
                continue

            if any(name.startswith(target) for name in names if name):
                partial.append(obj)
                continue

            if any(target in name for name in names if name):
                contains.append(obj)

        return exact or partial or contains

    def resolve_numbered_candidate(self, query, candidates, default_first=True):
        base_query, index = self.split_numbered_query(query)
        matches = self.get_name_matches(base_query, candidates)
        if not matches:
            return None, matches, base_query, index

        if index is not None:
            if 1 <= index <= len(matches):
                return matches[index - 1], matches, base_query, index
            return None, matches, base_query, index

        if default_first or len(matches) == 1:
            return matches[0], matches, base_query, index

        return None, matches, base_query, index

    def msg_numbered_matches(self, query, matches):
        base_query = (query or "").strip()
        if not matches:
            return

        lines = [f"More than one match for '{base_query}' (use '{base_query} <number>' to choose one):"]
        for index, match in enumerate(matches, start=1):
            if hasattr(match, "get_display_name"):
                name = match.get_display_name(self)
            else:
                name = getattr(match, "key", str(match))
            lines.append(f" {index}. {name}")

        self.msg("\n".join(lines))

    def at_grave_recovery(self, grave_damage):
        """Hook for future durability systems when an item leaves a grave."""
        return grave_damage


class Object(ObjectParent, DefaultObject):
    """Shared in-world object base for portable items and fixtures."""

    def at_object_creation(self):
        super().at_object_creation()
        if not self.db.world_id:
            self.db.world_id = slugify(self.key)
        self.db.stealable = True
        self.db.burglary_enabled = False
        self.db.lock_difficulty = 0
        self.db.trap_difficulty = 0
        self.db.entry_open = False
        self.db.last_burgled_at = 0
        self.db.burgle_heat = 0
        self.db.stack_quantity = max(1, int(getattr(self.db, "stack_quantity", 1) or 1))

    def get_stack_quantity(self):
        quantity = getattr(self.db, "stack_quantity", None)
        if quantity is None:
            quantity = getattr(self.db, "stack_count", 1)
        try:
            return max(1, int(quantity or 1))
        except (TypeError, ValueError):
            return 1

    def set_stack_quantity(self, quantity):
        normalized = max(1, int(quantity or 1))
        self.db.stack_quantity = normalized
        self.db.stack_count = normalized
        return normalized

    def is_stackable(self):
        explicit = getattr(self.db, "stackable", None)
        if explicit is not None:
            return bool(explicit)
        if bool(getattr(self.db, "is_container", False)):
            return False
        item_type = str(getattr(self.db, "item_type", "") or "").strip().lower()
        return item_type in {"raw_resource", "foraged_material"}

    def get_stack_identity(self):
        explicit = str(getattr(self.db, "stack_identity", "") or "").strip()
        if explicit:
            return explicit.lower()
        parts = [
            str(self.__class__.__module__),
            str(self.__class__.__name__),
            str(self.key or "").strip().lower(),
            str(getattr(self.db, "item_type", "") or "").strip().lower(),
            str(getattr(self.db, "material_quality", "") or "").strip().lower(),
            str(getattr(self.db, "forage_kind", "") or "").strip().lower(),
            str(getattr(self.db, "catalog_category", "") or "").strip().lower(),
        ]
        return "|".join(parts)

    def can_stack_with(self, other):
        if other is None or other == self:
            return False
        if not hasattr(other, "is_stackable") or not hasattr(other, "get_stack_identity"):
            return False
        return self.is_stackable() and other.is_stackable() and self.get_stack_identity() == other.get_stack_identity()

    def merge_stack_from(self, other):
        if not self.can_stack_with(other):
            return False
        self.set_stack_quantity(self.get_stack_quantity() + other.get_stack_quantity())
        other.delete()
        return True

    def split_stack(self, quantity, destination=None):
        requested = max(1, int(quantity or 1))
        total = self.get_stack_quantity()
        if not self.is_stackable() or requested >= total:
            return None
        split_obj = create_object(type(self), key=self.key, location=destination)
        for attr in list(self.db_attributes.all()):
            if str(getattr(attr, "db_key", "") or "") in {"stack_quantity", "stack_count", "mt516_arrived_at"}:
                continue
            split_obj.attributes.add(attr.db_key, attr.value, category=attr.db_category)
        aliases = getattr(self, "aliases", None)
        if aliases and hasattr(aliases, "all"):
            for alias in aliases.all():
                split_obj.aliases.add(alias)
        split_obj.set_stack_quantity(requested)
        self.set_stack_quantity(total - requested)
        return split_obj

    def find_stack_merge_target(self, contents):
        for candidate in list(contents or []):
            if candidate == self:
                continue
            if hasattr(candidate, "can_stack_with") and candidate.can_stack_with(self):
                return candidate
        return None

    def at_object_receive(self, moved_obj, source_location, **kwargs):
        super().at_object_receive(moved_obj, source_location, **kwargs)
        if moved_obj and hasattr(moved_obj, "is_stackable"):
            mark_item_arrival(moved_obj)
            target = moved_obj.find_stack_merge_target(getattr(self, "contents", [])) if hasattr(moved_obj, "find_stack_merge_target") else None
            if target is not None:
                target.merge_stack_from(moved_obj)

    def get_inventory_display_name(self, looker=None, **kwargs):
        label = self.get_display_name(looker, **kwargs)
        if not self.is_stackable():
            return label
        return format_stack_label(label, self.get_stack_quantity())

    def return_appearance(self, looker, **kwargs):
        appearance = super().return_appearance(looker, **kwargs)
        if not self.is_stackable() or self.get_stack_quantity() <= 1:
            return appearance
        return f"{appearance}\nQuantity: {self.get_stack_quantity()}"

    def get_base_weight(self):
        weight = getattr(self.db, "weight", None)
        if weight is None:
            return None
        try:
            return max(0.0, float(weight))
        except (TypeError, ValueError):
            return None

    def get_contents_weight(self, depth=0, max_depth=5, seen=None):
        if depth >= max_depth:
            LOGGER.error("Container weight calculation exceeded max depth for %s", self)
            return 0.0

        seen = set(seen or set())
        object_id = int(getattr(self, "id", 0) or 0)
        if object_id and object_id in seen:
            return 0.0
        if object_id:
            seen.add(object_id)

        total = 0.0
        for item in list(getattr(self, "contents", []) or []):
            if hasattr(item, "get_total_weight"):
                total += float(item.get_total_weight(depth=depth + 1, max_depth=max_depth, seen=seen) or 0.0)
                continue

            weight = getattr(getattr(item, "db", None), "weight", None)
            try:
                total += max(0.0, float(weight))
            except (TypeError, ValueError):
                LOGGER.error("Missing weight on nested item %s", item)
        return total

    def get_total_weight(self, depth=0, max_depth=5, seen=None):
        base_weight = self.get_base_weight()
        if base_weight is None:
            if not getattr(getattr(self, "ndb", None), "missing_weight_logged", False):
                LOGGER.error("Missing weight on object %s", self)
                self.ndb.missing_weight_logged = True
            base_weight = 0.0
        if not bool(getattr(self.db, "is_container", False)) and not getattr(self, "contents", None):
            return base_weight
        return base_weight + self.get_contents_weight(depth=depth, max_depth=max_depth, seen=seen)

    def at_pre_get(self, getter, **kwargs):
        if self.get_base_weight() is None:
            if getter and hasattr(getter, "msg"):
                getter.msg("That cannot be carried right now.")
            return False
        return super().at_pre_get(getter, **kwargs)


class BountyBoard(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = "Names, crude likenesses, and reward notices are nailed here in overlapping layers."
        self.db.stealable = False


class ChargenMirror(Object):
    def at_object_creation(self):
        super().at_object_creation()
        self.db.desc = "A tall mirror in a blackened frame. It reflects more than posture and less than mercy."
        self.db.is_chargen_mirror = True
        self.db.stealable = False
        self.aliases.add("mirror")
        self.aliases.add("glass")
        self.aliases.add("reflection")

    def return_appearance(self, looker, **kwargs):
        if is_chargen_active(looker):
            return render_mirror(looker)
        return super().return_appearance(looker, **kwargs)