import os
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from commands.cmd_look import CmdLook
from world.helpers.target_resolver import format_item_matches, resolve_item_target, resolve_target, split_quantity_target


class _DummyAliases:
    def __init__(self, values=None):
        self._values = list(values or [])

    def all(self):
        return list(self._values)


class _DummyItem:
    def __init__(self, key, arrived_at=0, aliases=None, stack_quantity=1, stackable=False, identity=None):
        self.key = key
        self.id = int(arrived_at or 0)
        self.db = type("DB", (), {"mt516_arrived_at": float(arrived_at)})()
        self.aliases = _DummyAliases(aliases)
        self._stack_quantity = int(stack_quantity or 1)
        self._stackable = bool(stackable)
        self._stack_identity = identity or key.lower()

    def get_display_name(self, looker=None, **kwargs):
        return self.key

    def is_stackable(self):
        return self._stackable

    def get_stack_quantity(self):
        return self._stack_quantity

    def get_stack_identity(self):
        return self._stack_identity


class _DummyTypeclassObject(_DummyItem):
    def __init__(self, key, arrived_at=0, aliases=None, typeclass="object", is_npc=False):
        super().__init__(key, arrived_at=arrived_at, aliases=aliases)
        self._typeclass = typeclass
        self.db = type("DB", (), {"mt516_arrived_at": float(arrived_at), "is_npc": bool(is_npc)})()
        self.location = None

    def is_typeclass(self, path, exact=False):
        if self._typeclass == "character":
            return path == "typeclasses.characters.Character"
        if self._typeclass == "exit":
            return path == "typeclasses.exits.Exit"
        return False


class _DummyCaller(_DummyTypeclassObject):
    def __init__(self, key="jekar"):
        super().__init__(key, typeclass="character")
        self.contents = []
        self.location = type("Room", (), {"contents": []})()
        self._hidden = set()
        self.messages = []
        self.search_calls = []

    def can_detect(self, obj):
        return obj not in self._hidden

    def get_visible_carried_items(self):
        return list(self.contents)

    def at_look(self, target):
        return f"LOOK:{target.key}"

    def msg(self, text):
        self.messages.append(text)

    def search(self, query):
        self.search_calls.append(query)
        return None


class TargetResolverTests(unittest.TestCase):
    def test_prefers_newest_matching_item(self):
        older = _DummyItem("leaf", arrived_at=10)
        newer = _DummyItem("leaf", arrived_at=20)
        match, matches, base_query, index = resolve_item_target("leaf", [older, newer], default_first=True)
        self.assertIs(match, newer)
        self.assertEqual(matches, [newer, older])
        self.assertEqual(base_query, "leaf")
        self.assertIsNone(index)

    def test_supports_other_alias(self):
        older = _DummyItem("leaf", arrived_at=10)
        newer = _DummyItem("leaf", arrived_at=20)
        match, _matches, _base_query, index = resolve_item_target("other leaf", [older, newer], default_first=True)
        self.assertIs(match, older)
        self.assertEqual(index, 2)

    def test_ordinal_resolves_against_single_stack_quantity(self):
        stack = _DummyItem("high-quality twig", arrived_at=20, aliases=["twig", "twigs"], stack_quantity=18, stackable=True, identity="twig")
        match, matches, base_query, index = resolve_item_target("third twig", [stack], default_first=True)
        self.assertIs(match, stack)
        self.assertEqual(matches, [stack])
        self.assertEqual(base_query, "twig")
        self.assertEqual(index, 3)

    def test_ordinal_out_of_range_on_single_stack_returns_no_match(self):
        stack = _DummyItem("high-quality twig", arrived_at=20, aliases=["twig", "twigs"], stack_quantity=2, stackable=True, identity="twig")
        match, matches, base_query, index = resolve_item_target("third twig", [stack], default_first=True)
        self.assertIsNone(match)
        self.assertEqual(matches, [stack])
        self.assertEqual(base_query, "twig")
        self.assertEqual(index, 3)

    def test_formats_guidance_without_number_suffix(self):
        message = format_item_matches("leaf", [_DummyItem("leaf", 1), _DummyItem("leaf", 2)])
        self.assertIn("first leaf", message)
        self.assertIn("2.leaf", message)

    def test_splits_quantity_targets_without_touching_positional_form(self):
        self.assertEqual(split_quantity_target("5 leaves"), (5, "leaves"))
        self.assertEqual(split_quantity_target("2.leaf"), (None, "2.leaf"))

    def test_resolve_character_in_room(self):
        caller = _DummyCaller()
        goblin = _DummyTypeclassObject("goblin", arrived_at=5, typeclass="character", is_npc=True)
        goblin.location = caller.location
        caller.location.contents = [caller, goblin]

        match, _matches, _base_query, _index, scope = resolve_target("goblin", caller, scopes=("characters",))
        self.assertIs(match, goblin)
        self.assertEqual(scope, "characters")

    def test_resolve_multiple_characters_with_ordinals(self):
        caller = _DummyCaller()
        older = _DummyTypeclassObject("goblin", arrived_at=10, typeclass="character", is_npc=True)
        middle = _DummyTypeclassObject("goblin", arrived_at=20, typeclass="character", is_npc=True)
        newer = _DummyTypeclassObject("goblin", arrived_at=30, typeclass="character", is_npc=True)
        caller.location.contents = [caller, older, middle, newer]

        match, _matches, _base_query, _index, _scope = resolve_target("second goblin", caller, scopes=("characters",))
        self.assertIs(match, middle)

    def test_mixed_scope_returns_either(self):
        caller = _DummyCaller()
        goblin = _DummyTypeclassObject("goblin", arrived_at=30, typeclass="character", is_npc=True)
        dagger = _DummyTypeclassObject("dagger", arrived_at=10, typeclass="object")
        caller.location.contents = [caller, goblin, dagger]

        goblin_match, _matches, _base_query, _index, goblin_scope = resolve_target("goblin", caller, scopes=("characters", "room"))
        dagger_match, _matches, _base_query, _index, dagger_scope = resolve_target("dagger", caller, scopes=("characters", "room"))
        self.assertIs(goblin_match, goblin)
        self.assertEqual(goblin_scope, "characters")
        self.assertIs(dagger_match, dagger)
        self.assertEqual(dagger_scope, "room")

    def test_caller_excluded_from_character_scope(self):
        caller = _DummyCaller()
        caller.location.contents = [caller]

        match, matches, _base_query, _index, scope = resolve_target("jekar", caller, scopes=("characters",))
        self.assertIsNone(match)
        self.assertEqual(matches, [])
        self.assertIsNone(scope)

    def test_character_scope_respects_visibility(self):
        caller = _DummyCaller()
        hidden = _DummyTypeclassObject("goblin", arrived_at=5, typeclass="character", is_npc=True)
        caller._hidden.add(hidden)
        caller.location.contents = [caller, hidden]

        match, matches, _base_query, _index, scope = resolve_target("goblin", caller, scopes=("characters",))
        self.assertIsNone(match)
        self.assertEqual(matches, [])
        self.assertIsNone(scope)

    def test_npc_scope_filters_out_non_npcs(self):
        caller = _DummyCaller()
        player = _DummyTypeclassObject("guard", arrived_at=5, typeclass="character", is_npc=False)
        npc = _DummyTypeclassObject("guard", arrived_at=10, typeclass="character", is_npc=True)
        caller.location.contents = [caller, player, npc]

        match, _matches, _base_query, _index, scope = resolve_target("guard", caller, scopes=("npcs",))
        self.assertIs(match, npc)
        self.assertEqual(scope, "npcs")

    def test_look_command_uses_centralized_resolver_for_stack_aliases_and_ordinals(self):
        caller = _DummyCaller()
        twig = _DummyTypeclassObject("high-quality twig", arrived_at=10, aliases=["twig", "twigs"])
        caller.contents = [twig]

        outputs = []
        for query in ("twig", "first twig", "1.twig", "1st twig", "twigs"):
            command = CmdLook()
            command.caller = caller
            command.args = query
            command.msg = lambda text=None, options=None, _outputs=outputs: _outputs.append(text)
            command.func()

        self.assertEqual([payload[0] for payload in outputs], ["LOOK:high-quality twig"] * 5)
        self.assertEqual(caller.search_calls, [])


if __name__ == "__main__":
    unittest.main()