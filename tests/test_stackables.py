import os
import unittest
from unittest import mock

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from commands.cmd_drop import CmdDrop
from typeclasses import abilities_survival as survival
from typeclasses.characters import Character
from typeclasses.objects import Object
from typeclasses.rooms import Room


def _configure_leaf(item):
    item.db.item_type = "raw_resource"
    item.db.material_quality = "useful"
    item.db.forage_kind = "leaf"
    item.db.catalog_category = "healing_herb"
    item.db.stackable = True
    item.set_stack_quantity(1)
    return item


class StackableIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def _create_object(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def test_container_receive_merges_identical_stackables(self):
        container = self._create_object(Object, "satchel")
        container.db.is_container = True

        first = _configure_leaf(self._create_object(Object, "useful leaf"))
        second = _configure_leaf(self._create_object(Object, "useful leaf"))

        first.move_to(container, quiet=True, use_destination=False)
        second.move_to(container, quiet=True, use_destination=False)

        self.assertEqual(len(container.contents), 1)
        self.assertEqual(container.contents[0].get_stack_quantity(), 2)

    def test_split_stack_preserves_remainder(self):
        room = self._create_object(Room, "Split Test Room")
        stack = _configure_leaf(self._create_object(Object, "useful leaf"))
        stack.set_stack_quantity(7)

        split = stack.split_stack(3, destination=room)

        self.assertIsNotNone(split)
        self.assertEqual(stack.get_stack_quantity(), 4)
        self.assertEqual(split.get_stack_quantity(), 3)
        self.assertEqual(split.location, room)

    def test_room_display_aggregates_duplicate_objects(self):
        room = self._create_object(Room, "Aggregation Test Room")
        first = self._create_object(Object, "dagger")
        second = self._create_object(Object, "dagger")
        first.move_to(room, quiet=True, use_destination=False)
        second.move_to(room, quiet=True, use_destination=False)

        rendered = room.get_display_things(looker=None)
        self.assertIn("daggers (2)", rendered)

    def test_forage_attempt_merges_new_items_into_one_stack(self):
        room = self._create_object(Room, "Forage Test Room")
        room.db.terrain_primary = "forest"
        room.db.terrain_type = "forest"
        room.db.zone_id = "test_zone"
        caller = self._create_object(Character, "Forager", location=room)
        caller.get_skill = lambda key: 80 if key == "outdoorsmanship" else 0
        caller.get_stat = lambda key: 10 if key in {"wisdom", "intelligence"} else 0
        caller.is_profession = lambda key: False
        caller.use_skill = lambda *args, **kwargs: None

        entry = {
            "group": "test",
            "slug": "twig",
            "display_name": "twig",
            "terrain": ["forest"],
            "indoor": False,
            "skill_ranks": 0,
            "seasonal": ["all"],
            "time_of_day": ["all"],
            "category": "wood",
        }

        with (
            mock.patch("typeclasses.abilities_survival.iter_forage_catalog_entries", return_value=(entry,)),
            mock.patch("typeclasses.abilities_survival.get_current_season", return_value="summer"),
            mock.patch("typeclasses.abilities_survival.get_current_time_of_day", return_value="afternoon"),
            mock.patch("typeclasses.abilities_survival.get_current_weather", return_value="clear"),
            mock.patch("typeclasses.abilities_survival.get_current_invasion", return_value="none"),
            mock.patch("typeclasses.abilities_survival._select_catalog_entry", return_value=entry),
            mock.patch("typeclasses.abilities_survival.run_contest", return_value={"outcome": "strong"}),
        ):
            result = survival.forage_attempt(caller, room, create_items=True)

        self.assertEqual(result["status"], "success")
        self.assertEqual(len(caller.contents), 1)
        self.assertEqual(caller.contents[0].key, "high-quality twig")
        self.assertEqual(caller.contents[0].get_stack_quantity(), result["yield_amount"])

    def test_drop_partial_stack_decrements_single_stack(self):
        room = self._create_object(Room, "Drop Test Room")
        caller = self._create_object(Character, "Dropper", location=room)
        stack = self._create_object(Object, "high-quality twig", location=caller)
        stack.db.item_type = "foraged_material"
        stack.db.material_quality = "high-quality"
        stack.db.forage_kind = "twig"
        stack.db.catalog_category = "wood"
        stack.db.stackable = True
        stack.aliases.add("twig")
        stack.aliases.add("twigs")
        stack.set_stack_quantity(18)

        messages = []
        caller.msg = lambda text, **kwargs: messages.append(str(text))
        command = CmdDrop()
        command.caller = caller
        command.args = "1.twig"
        command.func()

        caller = type(caller).objects.get(id=caller.id)
        room = type(room).objects.get(id=room.id)
        carried = [item for item in caller.contents if "twig" in str(getattr(item, "key", "")).lower()]
        dropped = [item for item in room.contents if item != caller and "twig" in str(getattr(item, "key", "")).lower()]
        self.assertEqual(len(carried), 1)
        self.assertEqual(carried[0].get_stack_quantity(), 17)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(dropped[0].get_stack_quantity(), 1)
        self.assertIn("You drop high-quality twig.", messages[-1])

    def test_character_merge_stackable_inventory_collapses_duplicates(self):
        room = self._create_object(Room, "Merge Test Room")
        caller = self._create_object(Character, "Merger", location=room)
        first = self._create_object(Object, "high-quality twig", location=caller)
        second = self._create_object(Object, "high-quality twig", location=caller)
        for item, quantity in ((first, 5), (second, 3)):
            item.db.item_type = "foraged_material"
            item.db.material_quality = "high-quality"
            item.db.forage_kind = "twig"
            item.db.catalog_category = "wood"
            item.db.stackable = True
            item.aliases.add("twig")
            item.set_stack_quantity(quantity)

        caller.merge_stackable_inventory()

        caller = type(caller).objects.get(id=caller.id)
        carried = [item for item in caller.contents if "twig" in str(getattr(item, "key", "")).lower()]
        self.assertEqual(len(carried), 1)
        self.assertEqual(carried[0].get_stack_quantity(), 8)

    def test_drop_ordinal_forms_on_single_stack_do_not_disambiguate(self):
        for query in ("second twig", "third twig", "3.twig"):
            with self.subTest(query=query):
                room = self._create_object(Room, f"Ordinal Drop Room {query}")
                caller = self._create_object(Character, f"OrdinalDropper{query}", location=room)
                stack = self._create_object(Object, "high-quality twig")
                stack.db.item_type = "foraged_material"
                stack.db.material_quality = "high-quality"
                stack.db.forage_kind = "twig"
                stack.db.catalog_category = "wood"
                stack.db.stackable = True
                stack.aliases.add("twig")
                stack.aliases.add("twigs")
                stack.set_stack_quantity(18)
                stack.move_to(caller, quiet=True, use_destination=False)

                messages = []
                caller.msg = lambda text, **kwargs: messages.append(str(text))
                command = CmdDrop()
                command.caller = caller
                command.args = query
                command.func()

                caller = type(caller).objects.get(id=caller.id)
                carried = [item for item in caller.contents if "twig" in str(getattr(item, "key", "")).lower()]
                self.assertEqual(len(carried), 1)
                self.assertEqual(carried[0].get_stack_quantity(), 17)
                self.assertEqual(messages[-1], "You drop high-quality twig.")
                self.assertNotIn("More than one match", "\n".join(messages))


if __name__ == "__main__":
    unittest.main()