import os
import time
import unittest

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.utils.create import create_object

from engine.services.ranger_saf_service import RangerSafService
from typeclasses.characters import Character
from typeclasses.objects import Object
from typeclasses.rooms import Room


class RangerCompanionBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        stamp = int(time.time() * 1000)
        self.wild_room = self._create(Room, f"Behavior Wilds {stamp}")
        self.wild_room.set_environment_type("wilderness")
        self.wild_room.set_terrain_type("forest")
        self.city_room = self._create(Room, f"Behavior City {stamp}")
        self.city_room.set_environment_type("urban")
        self.city_room.set_terrain_type("urban")

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def _create(self, typeclass, key, **kwargs):
        obj = create_object(typeclass, key=key, nohome=True, **kwargs)
        self.created.append(obj)
        return obj

    def _create_character(self, key, *, profession, location):
        character = self._create(Character, key, location=location, home=location)
        character.ensure_core_defaults()
        character.ensure_stat_defaults()
        character.db.profession = profession
        return character

    def test_following_companion_moves_with_owner(self):
        ranger = self._create_character("Behavior Ranger Follow", profession="ranger", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="raccoon")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()

        ranger.move_to(self.city_room, quiet=True, move_type="walk")

        self.assertEqual(companion.location, self.city_room)
        self.assertEqual(ranger.get_ranger_companion()["state"], "present")

    def test_stay_blocks_follow_and_whistle_recalls(self):
        ranger = self._create_character("Behavior Ranger Stay", profession="ranger", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()

        ok, message = ranger.command_ranger_companion("stay")
        self.assertTrue(ok)
        self.assertIn("wait", message.lower())

        ranger.move_to(self.city_room, quiet=True, move_type="walk")
        self.assertEqual(companion.location, self.wild_room)

        ok, message = ranger.command_ranger_companion("whistle")
        self.assertTrue(ok)
        self.assertIn("wolf", message.lower())
        self.assertEqual(companion.location, self.city_room)

    def test_owner_attack_notifies_companion_assist(self):
        ranger = self._create_character("Behavior Ranger Attack", profession="ranger", location=self.wild_room)
        foe = self._create_character("Behavior Foe", profession="thief", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()

        ranger.set_target(foe)

        self.assertEqual(companion.get_target(), foe)
        self.assertTrue(bool(companion.db.in_combat))

    def test_owner_attacked_notifies_companion_defense(self):
        ranger = self._create_character("Behavior Ranger Defend", profession="ranger", location=self.wild_room)
        attacker = self._create_character("Behavior Attacker", profession="thief", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="raccoon")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()

        ranger.at_attacked(attacker)

        self.assertEqual(companion.get_target(), attacker)

    def test_owner_death_notifies_companion_search(self):
        ranger = self._create_character("Behavior Ranger Death", profession="ranger", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()

        corpse = ranger.at_death()

        self.assertIsNotNone(corpse)
        self.assertEqual(companion.location, corpse.location)
        self.assertEqual(ranger.get_ranger_companion()["state"], "searching")

    def test_tease_respects_gate5_and_species_bait(self):
        ranger = self._create_character("Behavior Ranger Tease", profession="ranger", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="raccoon")
        self.assertTrue(ok)
        corn = self._create(Object, "corn cob", location=ranger, home=ranger)
        RangerSafService.set_saf(ranger, -30)

        ok, message = ranger.command_ranger_companion("tease")

        self.assertTrue(ok)
        self.assertIn("corn", message.lower())
        self.assertGreaterEqual(ranger.get_ranger_companion()["bond"], 51)

        ok, _message = ranger.dismiss_ranger_companion()
        self.assertTrue(ok)
        ok, _message = ranger.call_ranger_companion(species="wolf")
        self.assertTrue(ok)

        ok, message = ranger.command_ranger_companion("tease")
        self.assertFalse(ok)
        self.assertIn("turns away", message.lower())

    def test_companion_get_drop_and_give_item(self):
        ranger = self._create_character("Behavior Ranger Items", profession="ranger", location=self.wild_room)
        friend = self._create_character("Behavior Friend", profession="cleric", location=self.wild_room)
        ok, _message = ranger.call_ranger_companion(species="raccoon")
        self.assertTrue(ok)
        companion = ranger.get_ranger_companion_entity()
        shiny = self._create(Object, "shiny coin", location=self.wild_room, home=self.wild_room)

        ok, _message = ranger.command_ranger_companion("get", item_name="coin")
        self.assertTrue(ok)
        self.assertEqual(shiny.location, companion)

        ok, _message = ranger.command_ranger_companion("give", item_name="coin", recipient=friend)
        self.assertTrue(ok)
        self.assertEqual(shiny.location, friend)

        shiny.move_to(companion, quiet=True)
        ok, _message = ranger.command_ranger_companion("drop", item_name="coin")
        self.assertTrue(ok)
        self.assertEqual(shiny.location, self.wild_room)