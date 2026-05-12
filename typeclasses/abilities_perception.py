from typeclasses.abilities import Ability, register_ability
from engine.services.skill_service import SkillService
from utils.contests import run_contest
from utils.survival_messaging import msg_actor, msg_room, react_or_message_target
from world.helpers.skill_attempts import attempt_with_failure_learning
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
        spotted_any = False

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
                spotted_any = True
                msg_actor(user, f"You spot {obj.key}!")
                react_or_message_target(obj, player_text="You have been spotted!", awareness="alert")
                obj.break_stealth()

        detected_traps = []
        if hasattr(user, "detect_traps_in_room"):
            detected_traps = user.detect_traps_in_room() or []

        perception_rank = int(user.get_skill("perception") if hasattr(user, "get_skill") else 0)
        attempt_with_failure_learning(
            user,
            "perception",
            highest_difficulty,
            success=bool(spotted_any or detected_traps or perception_rank >= highest_difficulty),
            failure_reason="skill_too_low",
            event_key="search",
            failure_multiplier=0.25,
        )


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
        detected_traps = []
        if hasattr(user, "detect_traps_in_room"):
            detected_traps = user.detect_traps_in_room() or []

        schedule_event(
            key="observe_reset",
            owner=user,
            delay=10,
            callback="perception:clear_observe",
            metadata={"system": "perception", "type": "cooldown"},
        )
        perception_rank = int(user.get_skill("perception") if hasattr(user, "get_skill") else 0)
        attempt_with_failure_learning(
            user,
            "perception",
            10,
            success=bool(detected_traps or perception_rank >= 10),
            failure_reason="skill_too_low",
            event_key="observe",
            failure_multiplier=0.25,
        )


register_ability(SearchAbility())
register_ability(ObserveAbility())