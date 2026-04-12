from typeclasses.abilities import Ability, register_ability
from engine.services.skill_service import SkillService
from utils.contests import run_contest
from utils.survival_messaging import msg_actor, msg_room, react_or_message_target
from world.systems.scheduler import schedule_event


class SearchAbility(Ability):
    key = "search"
    roundtime = 2.0
    category = "perception"
    required = {"skill": "perception", "rank": 0}
    visible_if = {"skill": "perception", "min_rank": 0}

    def execute(self, user, target=None):
        msg_actor(user, "You carefully search your surroundings.")
        user.set_awareness("searching")

        highest_difficulty = 10

        for obj in user.get_room_observers():
            if not hasattr(obj, "is_hidden") or not obj.is_hidden():
                continue

            defense_total = obj.get_stealth_total() + obj.get_hidden_strength()
            highest_difficulty = max(highest_difficulty, int(defense_total or 0))
            result = run_contest(
                user.get_perception_total(),
                defense_total,
                attacker=user,
                defender=obj,
            )

            if result["outcome"] in ["success", "strong"]:
                msg_actor(user, f"You spot {obj.key}!")
                react_or_message_target(obj, player_text="You have been spotted!", awareness="alert")
                obj.break_stealth()

        if hasattr(user, "detect_traps_in_room"):
            user.detect_traps_in_room()

        SkillService.award_xp(user, "perception", highest_difficulty, source={"mode": "difficulty"})


class ObserveAbility(Ability):
    key = "observe"
    roundtime = 1.5
    category = "perception"
    required = {"skill": "perception", "rank": 5}
    visible_if = {"skill": "perception", "min_rank": 5}

    def execute(self, user, target=None):
        msg_actor(user, "You study your surroundings carefully.")
        msg_room(user, f"{user.key} pauses to study the area.", exclude=[user])
        user.set_awareness("alert")
        user.set_state("observing", True)
        if hasattr(user, "detect_traps_in_room"):
            user.detect_traps_in_room()

        schedule_event(
            key="observe_reset",
            owner=user,
            delay=10,
            callback="perception:clear_observe",
            metadata={"system": "perception", "type": "cooldown"},
        )
        SkillService.award_xp(user, "perception", 10, source={"mode": "difficulty"})


register_ability(SearchAbility())
register_ability(ObserveAbility())