"""
Object

The Object is the class for general items in the game world.

Use the ObjectParent class to implement common features for all entities
with a location in the game world (like Characters, Rooms, Exits).

"""

import logging
import re

from evennia.objects.objects import DefaultObject


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
        self.db.stealable = True

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