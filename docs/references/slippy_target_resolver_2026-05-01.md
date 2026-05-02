# Slippy Target Resolver Reference

User-provided architectural reference captured on 2026-05-01 for MT-516.

## Context Notes

- Slippy described this as a shared target-resolution mixin adapted from earlier code.
- The reference is architectural inspiration for DireEngine, not drop-in code.
- Additional notes from the user conversation:
  - Sort candidates by grouped scopes and recency.
  - Support ordinals like `third dagger`.
  - Default to first/newest sensible match.
  - Consider nested inventory/container traversal.

## Reference Snippet

```python
# game/mygame/helpers/target_resolver.py
"""
Shared target resolution mixin.

This centralizes how commands resolve a named target across different
'nearby' scopes, with ordered priority.

Current supported scopes:
    - "worn"  : items the caller is wearing (via wearables engine)
    - "hands" : items the caller is holding in hands (subset of caller.contents)
    - "room"  : objects in the caller's current location

This is deliberately *not* global and does not consider a generic
'inventory' beyond hands + worn. That matches current game design:
you only reference hands explicitly, and worn items via wearables.

Usage:

    from world.helpers.target_resolver import TargetResolverMixin

    class CmdLook(TargetResolverMixin, BaseRoleCommand):
        ...

    obj, n, base = self.resolve_target("backpack")
    container, n, base = self.resolve_container("backpack")

The mixin also supports ordinal phrases like "second backpack" using
your shared ordinal helpers, and possessive phrases like "my backpack"
by way of the `possessive` flag.
"""

from __future__ import annotations

from typing import Iterable, Literal, Optional, Tuple, List
from evennia.utils import logger
from world.helpers.ordinals import parse_ordinal_and_name, pick_nth, name_matches


def _sort_by_creation(items: list) -> list:
    """Sort objects newest-first by db.creation_time, falling back to db_date_created."""
    return sorted(
        items,
        key=lambda o: (
            getattr(getattr(o, "db", None), "creation_time", None)
            or getattr(o, "db_date_created", None)
        ),
        reverse=True,
    )


# Scope → priority bucket (lower = higher priority in the final pool)
_SCOPE_TIER = {"hands": 0, "worn": 0, "room": 1, "player": 2}

ScopeLiteral = Literal["worn", "hands", "room", "player"]


def normalize_scopes(scopes: Iterable[str] | None) -> Tuple[ScopeLiteral, ...]:
    """
    Normalize incoming scope names to TargetResolver scopes.

    - Ignores non-resolvable markers like "self" and "here".
    - Preserves order and removes duplicates.

    If scopes is None, defaults to TargetResolverMixin.DEFAULT_SCOPES.
    """
    if scopes is None:
        return TargetResolverMixin.DEFAULT_SCOPES

    ordered: list[ScopeLiteral] = []
    seen: set[ScopeLiteral] = set()

    for scope in scopes:
        if not scope:
            continue

        key = str(scope).lower()
        if key in ("self", "here"):
            continue

        if key in ("worn", "hands", "room"):
            expanded = (key,)  # type: ignore[assignment]
        else:
            continue

        for item in expanded:
            if item not in seen:
                ordered.append(item)
                seen.add(item)

    return tuple(ordered)


def _strip_articles(text: str) -> str:
    """
    Remove leading determiners for looser matching ("the satchel" -> "satchel").
    """
    s = (text or "").strip()
    lower = s.lower()
    for art in ("the ", "a ", "an "):
        if lower.startswith(art):
            return s[len(art):].lstrip()
    return s


class TargetResolverMixin:
    """
    Mixin for Evennia Command subclasses that need consistent target
    resolution with well-defined priority.

    Default priority:
        1) Worn items
        2) Items in hands
        3) Objects in the room
    """

    EXCLUDED_EXIT_NAMES = {
        "north", "south", "east", "west",
        "northeast", "northwest", "southeast", "southwest",
        "up", "down", "in", "out"
    }

    DEFAULT_SCOPES = ("hands", "player", "room")

    # -----------------------------
    # Matching / filtering helpers
    # -----------------------------

    def _valid_room_object(self, obj) -> bool:
        """
        Similar spirit to InventoryCommandMixin.valid_object:
        - exclude exits (by type/destination)
        - exclude common directional exit names
        - exclude props (scene dressing, not interactable)
        """
        try:
            if self._is_exit(obj):
                return False
        except Exception:
            pass

        try:
            key = (getattr(obj, "key", "") or "").lower()
            if key in self.EXCLUDED_EXIT_NAMES:
                return False
        except Exception:
            pass

        try:
            if getattr(obj.db, "category", None) == "prop":
                return False
        except Exception:
            pass

        return True

    def _name_matches_loose(self, obj, search: str) -> bool:
        """
        Article-insensitive, practical name matching.

        Tries your shared name_matches first, then falls back to comparing
        against stripped key/noun/aliases.
        """
        if not obj or not search:
            return False

        s = _strip_articles(search).lower().strip()
        if not s:
            return False

        # 1) Use your existing helper if it works
        try:
            if name_matches(obj, s):
                return True
        except Exception:
            pass

        # 2) Compare against object's key (article-stripped)
        try:
            key = getattr(obj, "key", "") or ""
            if _strip_articles(key).lower().strip() == s:
                return True
        except Exception:
            pass

        # 3) Compare against db.noun (if you use it)
        try:
            noun = getattr(getattr(obj, "db", None), "noun", "") or ""
            if noun.lower().strip() == s:
                return True
        except Exception:
            pass

        # 4) Compare against aliases (common in Evennia)
        try:
            aliases = []
            if hasattr(obj, "aliases") and hasattr(obj.aliases, "all"):
                aliases = obj.aliases.all() or []
            for alias in aliases:
                if _strip_articles(str(alias)).lower().strip() == s:
                    return True
        except Exception:
            pass

        # 5) Token prefix matching — noun required.
        #    All input tokens must prefix-match some word in the name, AND at
        #    least one token must match a noun word (or a key word when db.noun
        #    is unset).  This mirrors name_matches() in ordinals.py and prevents
        #    "coin" from hitting "coin purse" (noun=purse) or "mithryl" from
        #    hitting "mithryl coin" (noun=coin, mithryl is only attr_adj).
        try:
            if len(s) >= 2:
                input_tokens = s.split()

                noun = (getattr(getattr(obj, "db", None), "noun", "") or "").strip().lower()
                key  = _strip_articles(getattr(obj, "key", "") or "").lower().strip()
                attr_adj = (getattr(getattr(obj, "db", None), "attr_adj", "") or "").strip().lower()

                # Words the noun-check runs against
                noun_words = noun.split() if noun else key.split()
                # All words available for general token matching
                all_words  = (attr_adj + " " + " ".join(noun_words)).split()

                noun_hit = any(
                    any(nw.startswith(t) for nw in noun_words)
                    for t in input_tokens
                )
                if noun_hit and all(
                    any(w.startswith(t) for w in all_words)
                    for t in input_tokens
                ):
                    return True
        except Exception:
            pass

        return False

    # -----------------------------
    # Scope collection helpers
    # -----------------------------

    @staticmethod
    def _normalize_dbref_token(token) -> Optional[str]:
        """
        Normalize a hands mapping token into a canonical dbref string.

        We expect values like '#341', but are defensive:
        - None/empty -> None
        - int or digit string -> '#<int>'
        - '#123' -> '#123'
        Anything else is ignored.
        """
        if token is None:
            return None

        s = str(token).strip()
        if not s:
            return None

        if s.startswith("#") and s[1:].isdigit():
            return s

        if s.isdigit():
            return f"#{s}"

        # Unknown format (e.g. a name) — we don't try to be clever here.
        return None

    def _get_hand_objects(self, caller) -> List[object]:
        """
        Return objects currently held in the caller's hands.

        We *don't* do a separate lookup; we trust caller.contents as the
        canonical inventory source (same model as CmdGet), and intersect
        that with the dbrefs in caller.db.hands.
        """
        mapping = getattr(caller.db, "hands", None)
        if not mapping:
            return []

        # Normalize all hand tokens into dbref strings.
        hand_dbrefs = {
            dbref
            for dbref in (
                self._normalize_dbref_token(token) for token in mapping.values()
            )
            if dbref is not None
        }

        if not hand_dbrefs:
            return []

        # Now filter caller.contents (which is what CmdGet uses as 'inv')
        # to only those whose dbref is in the hands set.
        contents = list(getattr(caller, "contents", []) or [])
        objs: List[object] = []

        for obj in contents:
            try:
                obj_dbref = getattr(obj, "dbref", None)
                if obj_dbref and str(obj_dbref) in hand_dbrefs:
                    objs.append(obj)
            except Exception:
                continue

        return objs

    def _get_room_objects(self, caller) -> List[object]:
        """
        Return visible objects in the caller's location (excluding caller),
        plus visible contents of *open* containers in the room.

        Ordering matches command_mixins priority:
            1) room top-level contents
            2) room container contents (one level deep)
        """
        here = getattr(caller, "location", None)
        if not here:
            return []

        def can_view(o) -> bool:
            try:
                if o is caller or not hasattr(o, "access"):
                    return False
                return o.access(caller, "view") or o.access(caller, "touch")
            except Exception:
                return False

        # --- Priority 1: room contents ---
        room_contents = [
            o for o in (getattr(here, "contents", []) or [])
            if can_view(o) and self._valid_room_object(o)
        ]

        # --- Priority 2: contents of open containers in the room (one level deep) ---
        room_container_contents: List[object] = []
        for container in room_contents:
            try:
                if not self._is_container(container):
                    continue
                if not bool(getattr(container.db, "is_open", True)):
                    continue
                if hasattr(container, "is_typeclass") and container.is_typeclass(
                    "typeclasses.characters.Character", exact=False
                ):
                    continue
            except Exception:
                continue

            for o in (getattr(container, "contents", []) or []):
                if can_view(o) and self._valid_room_object(o):
                    room_container_contents.append(o)

        return room_contents + room_container_contents

    def _get_player_objects(self, caller) -> List[object]:
        """
        Return visible objects carried by the caller,
        plus visible contents of open containers in inventory (one level deep).
        """
        contents = list(getattr(caller, "contents", []) or [])

        def can_view(o) -> bool:
            try:
                return hasattr(o, "access") and o.access(caller, "view")
            except Exception:
                return False

        # Top-level inventory
        player_contents = [
            o for o in contents
            if can_view(o)
        ]

        # Contents of open containers in inventory
        player_container_contents: List[object] = []

        for container in player_contents:
            try:
                if not self._is_container(container):
                    continue
                if not bool(getattr(container.db, "is_open", True)):
                    continue
            except Exception:
                continue

            for o in (getattr(container, "contents", []) or []):
                if can_view(o):
                    player_container_contents.append(o)

        return player_contents + player_container_contents

    def _collect_scope_candidates(
        self, caller, scopes: Iterable[ScopeLiteral]
    ) -> list[tuple[str, list[object]]]:
        ordered: list[tuple[str, list[object]]] = []

        for scope in scopes:
            if scope == "hands":
                cands = self._get_hand_objects(caller)
            elif scope == "player":
                cands = self._get_player_objects(caller)
            elif scope == "room":
                cands = self._get_room_objects(caller)
            else:
                continue

            ordered.append((scope, _sort_by_creation(cands)))

        return ordered
    
    # -----------------------------
    # Container detection helpers
    # -----------------------------

    def _is_container(self, obj) -> bool:
        """
        Determine if an object behaves as a container.

        Supports both:
            - obj.is_container() method
            - obj.is_container attribute / obj.db.is_container flag
        """
        if hasattr(obj, "is_container"):
            attr = getattr(obj, "is_container")
            try:
                return attr() if callable(attr) else bool(attr)
            except Exception:
                return False

        try:
            return bool(getattr(obj.db, "is_container", False))
        except Exception:
            return False

    def _filter_containers(self, objects: list[object]) -> list[object]:
        return [o for o in objects if self._is_container(o)]

    def is_nested_container(self, obj) -> bool:
        """
        True if `obj` is located inside another container.
        """
        loc = getattr(obj, "location", None)
        return bool(loc and self._is_container(loc))

    def _is_exit(self, obj) -> bool:
        """
        Lightweight exit detection so we can deprioritize exits when matching names.
        """
        try:
            if hasattr(obj, "is_typeclass") and obj.is_typeclass(
                "typeclasses.exits.Exit", exact=False
            ):
                return True
        except Exception:
            pass

        try:
            return getattr(obj, "destination", None) is not None
        except Exception:
            return False

    # -----------------------------
    # Main resolution API
    # -----------------------------

    def resolve_target(
        self,
        phrase: str,
        *,
        scopes: Iterable[ScopeLiteral] | None = None,
        require_container: bool = False,
        possessive: Optional[bool] = None,
        allow_embedded: bool = True,
    ):
        """
        Resolve a phrase like 'backpack' or 'second backpack' to an object,
        respecting global scope ordering and ownership rules.
        """
        caller = getattr(self, "caller", None)
        if not caller:
            logger.log_err("[TargetResolver] resolve_target called without a caller.")
            return None, 1, "", "none"

        raw_phrase = (phrase or "").strip()
        if not raw_phrase:
            return None, 1, "", "none"

        lower = raw_phrase.lower()

        # 1. Detect possessives ("my backpack")
        inferred_possessive = lower.startswith("my ")
        is_possessive = bool(possessive) or inferred_possessive
        cleaned = raw_phrase[3:].lstrip() if inferred_possessive else raw_phrase

        # 2. Handle "other <name>" as an ordinal alias
        cleaned_lower = cleaned.lower()
        is_other = False

        if cleaned_lower.startswith("other "):
            base_name = cleaned[6:].lstrip()
            n = 2
            is_other = True
        else:
            n, base_name = parse_ordinal_and_name(cleaned)

        base_name = _strip_articles(base_name)

        if not base_name:
            logger.log_info(
                f"[TargetResolver] MISS caller='{caller.key}' "
                f"phrase='{raw_phrase}' cleaned='{cleaned}' reason='no-base-name'"
            )
            return None, n, base_name, "none"

        # 3. Embedded container phrases ("X in/inside/from Y")
        if allow_embedded and not require_container:
            for prep in (" in ", " inside ", " from "):
                idx = cleaned_lower.find(prep)
                if idx == -1:
                    continue
                head = cleaned[:idx].strip()
                tail = cleaned[idx + len(prep):].strip()
                if not head or not tail:
                    continue

                container, _cn, _cbase = self.resolve_container(
                    tail,
                    scopes=scopes,
                    possessive=is_possessive,
                    allow_embedded=False,
                )
                if not container:
                    continue

                n_head, base_head = parse_ordinal_and_name(head)
                contents = [
                    o
                    for o in getattr(container, "contents", []) or []
                    if hasattr(o, "access") and o.access(caller, "view")
                ]
                obj_inside = pick_nth(contents, base_head, n_head)
                if obj_inside:
                    return obj_inside, n_head, base_head, "embedded"

        # 4. Determine effective scopes
        raw_scopes = tuple(scopes or self.DEFAULT_SCOPES)
        if is_possessive:
            owned_scopes = tuple(s for s in raw_scopes if s in ("worn", "hands", "player"))
            scopes_eff: Tuple[ScopeLiteral, ...] = owned_scopes or raw_scopes
        else:
            scopes_eff = raw_scopes

        # 5. Build one global candidate list in scope order
        ordered_scopes = self._collect_scope_candidates(caller, scopes_eff)
        all_cands: list[tuple[object, str, bool]] = []

        for scope_name, cands in ordered_scopes:
            if require_container:
                cands = self._filter_containers(cands)
            if not cands:
                continue
            for o in cands:
                all_cands.append((o, scope_name, self._is_exit(o)))

        if not all_cands:
            logger.log_info(
                f"[TargetResolver] MISS caller='{caller.key}' "
                f"phrase='{raw_phrase}' cleaned='{cleaned}' base='{base_name}' "
                f"scopes={scopes_eff} require_container={require_container} "
                f"possessive={is_possessive} is_other={is_other}"
            )
            return None, n, base_name, "none"

        # 6. Build the ordinal pool with tiered priority.
        #    Tier order: hands/worn (0) → room (1) → player bags (2).
        #    Within each tier, items are sorted newest-first by _sort_by_creation.
        #    This mirrors _find_item_anywhere in inv_cmds so that `l coin` and
        #    `get coin` always resolve the same ordinal-1 item.
        def _tiered_pool(cands, *, exclude_exits: bool):
            buckets: dict[int, list] = {0: [], 1: [], 2: []}
            for o, scope, is_exit in cands:
                if exclude_exits and is_exit:
                    continue
                if not self._name_matches_loose(o, base_name):
                    continue
                tier = _SCOPE_TIER.get(scope, 2)
                buckets[tier].append(o)
            return (
                _sort_by_creation(buckets[0])
                + _sort_by_creation(buckets[1])
                + _sort_by_creation(buckets[2])
            )

        primary_pool  = _tiered_pool(all_cands, exclude_exits=True)
        fallback_pool = _tiered_pool(all_cands, exclude_exits=False)

        pool = primary_pool or fallback_pool
        obj = pool[n - 1] if 1 <= n <= len(pool) else None

        if not obj:
            logger.log_info(
                f"[TargetResolver] MISS caller='{caller.key}' "
                f"phrase='{raw_phrase}' cleaned='{cleaned}' base='{base_name}' "
                f"scopes={scopes_eff} require_container={require_container} "
                f"possessive={is_possessive} is_other={is_other}"
            )
            return None, n, base_name, "none"

        # Find the first scope where this object appeared
        scope_name = next(
            (scope for (o, scope, _is_exit) in all_cands if o is obj),
            "unknown",
        )

        return obj, n, base_name, scope_name

    def resolve_container(
        self,
        phrase: str,
        *,
        scopes: Iterable[ScopeLiteral] | None = None,
        possessive: bool = False,
        allow_embedded: bool = True,
    ):
        """
        Convenience wrapper to resolve only containers.
        """
        return self.resolve_target(
            phrase,
            scopes=scopes,
            require_container=True,
            possessive=possessive,
            allow_embedded=allow_embedded,
        )
```