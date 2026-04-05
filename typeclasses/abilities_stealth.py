from typeclasses.abilities import Ability, register_ability
from utils.contests import run_contest, run_group_contest_against_best
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
            if hasattr(user, "record_stealth_contest"):
                user.record_stealth_contest(
                    "hide",
                    10,
                    result=None,
                    target=user.location,
                    roundtime=self.roundtime,
                    event_key="stealth",
                    require_hidden=True,
                )
            return

        stealth_bonus = 10 if user.is_stalking() else 0
        partial_detectors = []
        strong_detectors = []
        highest_difficulty = 10
        contest_result = run_group_contest_against_best(
            user.get_stealth_total() + stealth_bonus,
            [observer.get_perception_total() for observer in observers],
            attacker=user,
            defenders=observers,
        )
        best_outcome = str(contest_result.get("outcome", "fail") or "fail")
        final_margin = int(contest_result.get("diff", 0) or 0)

        for observer_entry in list(contest_result.get("individual_results") or []):
            observer = observer_entry.get("defender")
            if observer is None:
                continue
            highest_difficulty = max(highest_difficulty, int(observer.get_perception_total() or 0))
            outcome = str(observer_entry.get("outcome", "success") or "success")
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
            if hasattr(user, "set_position_state"):
                user.set_position_state("exposed")
            msg_actor(user, "You fail to find concealment.")
            if hasattr(user, "record_stealth_contest"):
                user.record_stealth_contest(
                    "hide",
                    highest_difficulty,
                    result=contest_result,
                    target=user.location,
                    roundtime=self.roundtime,
                    event_key="stealth",
                    require_hidden=False,
                )
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
        if hasattr(user, "set_position_state"):
            user.set_position_state("advantaged")
        if best_outcome == "partial":
            msg_actor(user, "You struggle to conceal yourself.")
        else:
            msg_actor(user, "You slip into hiding.")
        if hasattr(user, "record_stealth_contest"):
            user.record_stealth_contest(
                "hide",
                highest_difficulty,
                result=contest_result,
                target=user.location,
                roundtime=self.roundtime,
                event_key="stealth",
                require_hidden=True,
            )


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
        result = run_contest(user.get_stealth_total(), defender_total, attacker=user, defender=target)
        if result["outcome"] == "fail":
            react_or_message_target(target, player_text=f"You spot {user.key} shadowing you.", awareness="alert")
        elif result["outcome"] == "partial":
            react_or_message_target(target, player_text="You sense someone following you.", awareness="alert")
        if hasattr(user, "record_stealth_contest"):
            user.record_stealth_contest(
                "stalk",
                max(10, int(defender_total or 0)),
                result=result,
                target=target,
                roundtime=self.roundtime,
                event_key="stealth",
                require_hidden=True,
            )


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


register_ability(HideAbility())
register_ability(SneakAbility())
register_ability(StalkAbility())
register_ability(AmbushAbility())