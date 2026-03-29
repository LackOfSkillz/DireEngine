from typeclasses.abilities import Ability, register_ability
from utils.contests import run_contest
from utils.survival_messaging import msg_actor, msg_detecting_observers, react_or_message_target


class HideAbility(Ability):
    key = "hide"
    roundtime = 2.0
    category = "stealth"
    required = {
        "skill": "stealth",
        "rank": 0,
    }
    visible_if = {
        "skill": "stealth",
        "min_rank": 0,
    }

    def can_use(self, user, target=None):
        return True, ""

    def execute(self, user, target=None):
        observers = user.get_room_observers()

        if not observers:
            user.set_state("hidden", {"strength": 50, "source": "hide"})
            msg_actor(user, "You slip into hiding.")
            user.use_skill("stealth", apply_roundtime=False, emit_placeholder=False)
            return

        stealth_bonus = 10 if user.is_stalking() else 0
        outcome_rank = {"fail": 0, "partial": 1, "success": 2, "strong": 3}
        best_outcome = "strong"
        partial_detectors = []
        strong_detectors = []

        for observer in observers:
            result = run_contest(
                user.get_stealth_total() + stealth_bonus,
                observer.get_perception_total(),
            )
            outcome = result["outcome"]
            if outcome_rank[outcome] < outcome_rank[best_outcome]:
                best_outcome = outcome
            if outcome == "fail":
                strong_detectors.append(observer)
            elif outcome == "partial":
                partial_detectors.append(observer)

        msg_detecting_observers(
            user,
            lambda observer: f"You notice {user.key} trying to hide.",
            strong_detectors,
        )
        msg_detecting_observers(
            user,
            lambda observer: "You notice suspicious movement nearby.",
            partial_detectors,
        )

        if best_outcome == "fail":
            user.break_stealth()
            msg_actor(user, "You fail to find concealment.")
            user.use_skill("stealth", apply_roundtime=False, emit_placeholder=False)
            return

        strength_map = {
            "partial": 10,
            "success": 25,
            "strong": 40,
        }
        user.set_state(
            "hidden",
            {"strength": strength_map.get(best_outcome, 10), "source": "hide"},
        )
        if best_outcome == "partial":
            msg_actor(user, "You struggle to conceal yourself.")
        else:
            msg_actor(user, "You slip into hiding.")
        user.use_skill("stealth", apply_roundtime=False, emit_placeholder=False)


class SneakAbility(Ability):
    key = "sneak"
    roundtime = 2.0
    category = "stealth"
    required = {
        "skill": "stealth",
        "rank": 5,
    }
    visible_if = {
        "skill": "stealth",
        "min_rank": 5,
    }

    def can_use(self, user, target=None):
        if not user.is_hidden():
            return False, "You must be hidden before you can sneak."
        return True, ""

    def execute(self, user, target=None):
        msg_actor(user, "You prepare to move quietly.")
        user.set_state("sneaking", True)


class StalkAbility(Ability):
    key = "stalk"
    roundtime = 2.0
    category = "stealth"
    required = {
        "skill": "stealth",
        "rank": 10,
    }
    visible_if = {
        "skill": "stealth",
        "min_rank": 10,
    }

    def can_use(self, user, target=None):
        if not user.is_hidden():
            return False, "You must be hidden before you can stalk."
        if not target:
            return False, "Stalk whom?"
        if target.location != user.location:
            return False, "You need to be near them to stalk them."
        return True, ""

    def execute(self, user, target=None):
        user.set_state("stalking", target.id)
        msg_actor(user, f"You begin stalking {target.key}.")
        defender_total = target.get_perception_total() if hasattr(target, "get_perception_total") else 0
        result = run_contest(user.get_stealth_total(), defender_total)
        if result["outcome"] == "fail":
            react_or_message_target(target, player_text=f"You spot {user.key} shadowing you.", awareness="alert")
        elif result["outcome"] == "partial":
            react_or_message_target(target, player_text="You sense someone following you.", awareness="alert")
        user.use_skill("stealth", apply_roundtime=False, emit_placeholder=False)


class AmbushAbility(Ability):
    key = "ambush"
    roundtime = 3.0
    category = "stealth"
    required = {
        "skill": "stealth",
        "rank": 10,
    }
    visible_if = {
        "skill": "stealth",
        "min_rank": 10,
    }

    def can_use(self, user, target=None):
        if not user.is_hidden():
            return False, "You must be hidden before you can ambush."
        if user.is_ambushing():
            return False, "You are already preparing an ambush."
        if not target:
            return False, "Ambush whom?"
        if target.location != user.location:
            return False, "You need to be near them to ambush them."
        return True, ""

    def execute(self, user, target=None):
        user.set_state("ambush_target", target.id)
        msg_actor(user, f"You prepare to ambush {target.key}.")
        user.use_skill("stealth", apply_roundtime=False, emit_placeholder=False)


register_ability(HideAbility())
register_ability(SneakAbility())
register_ability(StalkAbility())
register_ability(AmbushAbility())