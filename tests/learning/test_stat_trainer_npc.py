import os
import unittest
from types import SimpleNamespace

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from typeclasses.npcs import ClericGuildmaster, EmpathGuildleader, GuildLeaderNPC, NPC, StatTrainerNPC
from world.areas.the_landing.stat_trainers import ensure_the_landing_stat_trainers


class StatTrainerNpcTests(unittest.TestCase):
    def setUp(self):
        self.created = []

    def tearDown(self):
        for obj in reversed(self.created):
            try:
                obj.delete()
            except Exception:
                pass

    def _create(self, typeclass, key):
        obj = create_object(typeclass, key=key, nohome=True)
        self.created.append(obj)
        return obj

    def _tagged_rooms(self, tag_name):
        return [obj for obj in ObjectDB.objects.get_by_tag(tag_name) if getattr(obj, "db_typeclass_path", "") == "typeclasses.rooms.Room"]

    def test_stat_trainer_npc_initializes_required_attributes(self):
        npc = self._create(StatTrainerNPC, "Trainer Test")
        self.assertTrue(npc.db.is_trainer)
        self.assertIsNone(npc.db.trains_stat)
        self.assertTrue(str(npc.db.greeting or "").strip())

    def test_stat_trainer_handle_inquiry_returns_greeting_without_topic(self):
        npc = self._create(StatTrainerNPC, "Greeting Trainer")
        response = npc.handle_inquiry(SimpleNamespace(), None)
        self.assertEqual(response, npc.db.greeting)

    def test_stat_trainer_handle_inquiry_returns_placeholder_for_topic(self):
        npc = self._create(StatTrainerNPC, "Placeholder Trainer")
        response = npc.handle_inquiry(SimpleNamespace(), "training")
        self.assertIn("nothing in response", response)

    def test_guild_leader_npc_initializes_required_attributes(self):
        npc = self._create(GuildLeaderNPC, "Leader Test")
        self.assertTrue(npc.db.is_guild_leader)
        self.assertEqual(npc.db.guild_role, "leader")
        self.assertIsNone(npc.db.leads_profession)
        self.assertTrue(str(npc.db.greeting or "").strip())

    def test_guild_leader_handle_inquiry_returns_greeting_without_topic(self):
        npc = self._create(GuildLeaderNPC, "Leader Greeting")
        response = npc.handle_inquiry(SimpleNamespace(), None)
        self.assertEqual(response, npc.db.greeting)

    def test_existing_guildleaders_remain_direct_npc_subclasses(self):
        self.assertEqual(EmpathGuildleader.__bases__, (NPC,))
        self.assertEqual(ClericGuildmaster.__bases__, (NPC,))

    def test_all_eight_stat_trainer_rooms_exist(self):
        rooms = ensure_the_landing_stat_trainers()
        self.assertEqual(len(rooms), 8)
        for stat_name in rooms:
            self.assertEqual(len(self._tagged_rooms(f"stat_trainer:{stat_name}")), 1)

    def test_all_eight_trainer_rooms_are_tagged_for_the_landing(self):
        rooms = ensure_the_landing_stat_trainers()
        for room in rooms.values():
            self.assertEqual(room.db.region_name, "The Landing")

    def test_each_trainer_room_has_exactly_one_matching_stat_trainer(self):
        rooms = ensure_the_landing_stat_trainers()
        for stat_name, room in rooms.items():
            trainers = [obj for obj in room.contents if isinstance(obj, StatTrainerNPC)]
            self.assertEqual(len(trainers), 1)
            self.assertEqual(trainers[0].db.trains_stat, stat_name)
