import unittest

from domain.abilities.roars.serpent_hiss import SerpentHissRoar
from engine.services.roar_service import RoarService
from tests.domain.roar_test_support import DummyExit, DummyRoom, make_actor_and_target


class SerpentHissTests(unittest.TestCase):
    def test_serpent_hiss_forces_flee_and_sets_return_lock(self):
        actor, target, room = make_actor_and_target()
        destination = DummyRoom(11)
        room.contents.append(DummyExit(destination))

        result = SerpentHissRoar.begin_roar(actor, [target], RoarService, vocal_profile={"modifier": 100}, randomizer=lambda _low, _high: 10)

        self.assertTrue(result.success)
        self.assertEqual(target.location, destination)
        self.assertEqual(RoarService.get_forced_return_block(target)["origin_room_id"], room.id)