from evennia.utils.create import create_object

from typeclasses.abilities import Ability, register_ability
from typeclasses.objects import Object
from utils.contests import run_contest
from utils.survival_messaging import msg_actor, msg_room


class ForageAbility(Ability):
    key = "forage"
    roundtime = 3.0
    category = "survival"
    required = {"skill": "outdoorsmanship", "rank": 1}
    visible_if = {"skill": "outdoorsmanship", "min_rank": 1}

    def execute(self, user, target=None):
        msg_room(user, f"{user.key} searches the area carefully.", exclude=[user])

        skill_total = user.get_skill("outdoorsmanship") + user.get_stat("wisdom") + user.get_stat("intelligence")
        difficulty = int(getattr(getattr(user.location, "db", None), "forage_difficulty", 35) or 35)
        result = run_contest(skill_total, difficulty, attacker=user)
        outcome = result["outcome"]

        if outcome == "fail":
            msg_actor(user, "You find nothing of use.")
            return

        if outcome == "partial":
            quality = "rough"
            msg_actor(user, "You find a few scraps of usable material.")
        elif outcome == "success":
            quality = "useful"
            msg_actor(user, "You gather some useful natural materials.")
        else:
            quality = "high-quality"
            msg_actor(user, "You expertly gather high-quality natural materials.")

        bundle = create_object(Object, key=f"{quality} foraged bundle", location=user)
        bundle.db.desc = "A simple bundle of natural materials gathered from the surrounding area."
        bundle.db.foraged = True
        bundle.db.material_quality = quality

        user.use_skill(
            "outdoorsmanship",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
        )


register_ability(ForageAbility())