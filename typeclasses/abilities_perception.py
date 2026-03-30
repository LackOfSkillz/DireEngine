from evennia.utils import delay

from typeclasses.abilities import Ability, register_ability
from utils.contests import run_contest
from utils.survival_messaging import msg_actor, msg_room, react_or_message_target


class SearchAbility(Ability):
    key = "search"
    roundtime = 2.0
    category = "perception"
    required = {"skill": "perception", "rank": 0}
    visible_if = {"skill": "perception", "min_rank": 0}

    def execute(self, user, target=None):
        msg_actor(user, "You carefully search your surroundings.")
        user.set_awareness("searching")

        for obj in user.get_room_observers():
            if not hasattr(obj, "is_hidden") or not obj.is_hidden():
                continue

            result = run_contest(
                user.get_perception_total(),
                obj.get_stealth_total() + obj.get_hidden_strength(),
                attacker=user,
                defender=obj,
            )

            if result["outcome"] in ["success", "strong"]:
                msg_actor(user, f"You spot {obj.key}!")
                react_or_message_target(obj, player_text="You have been spotted!", awareness="alert")
                obj.break_stealth()

        if hasattr(user, "detect_traps_in_room"):
            user.detect_traps_in_room()

        user.use_skill("perception", apply_roundtime=False, emit_placeholder=False)


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

        def clear_observe():
            if not getattr(user, "pk", None):
                return
            user.set_awareness("normal")
            user.clear_state("observing")

        delay(10, clear_observe)
        user.use_skill("perception", apply_roundtime=False, emit_placeholder=False)


register_ability(SearchAbility())
register_ability(ObserveAbility())