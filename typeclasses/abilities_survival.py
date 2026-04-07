from typeclasses.abilities import Ability, register_ability
from utils.contests import run_contest
from utils.survival_loot import create_simple_item
from utils.survival_messaging import msg_actor, msg_room
import random


class ForageAbility(Ability):
    key = "forage"
    roundtime = 3.0
    category = "survival"
    required = {"skill": "outdoorsmanship", "rank": 1}
    visible_if = {"skill": "outdoorsmanship", "min_rank": 1}

    def execute(self, user, target=None):
        msg_room(user, f"{user.key} searches the area carefully.", exclude=[user])

        outdoorsmanship = int(user.get_skill("outdoorsmanship") or 0)
        skill_total = outdoorsmanship + user.get_stat("wisdom") + user.get_stat("intelligence")
        difficulty = int(getattr(getattr(user.location, "db", None), "forage_difficulty", 35) or 35)
        result = run_contest(skill_total, difficulty, attacker=user)
        outcome = result["outcome"]

        if outcome == "fail":
            msg_actor(user, "You find nothing of use.")
            return

        if outcome == "partial":
            quality = "rough"
            yield_amount = 1
            msg_actor(user, "You find a few scraps of usable material.")
        elif outcome == "success":
            quality = "useful"
            yield_amount = 2
            msg_actor(user, "You gather some useful natural materials.")
        else:
            quality = "high-quality"
            yield_amount = 3
            msg_actor(user, "You expertly gather high-quality natural materials.")

        if hasattr(user, "is_profession") and user.is_profession("ranger"):
            yield_amount += 1
        yield_amount += outdoorsmanship // 10

        resource_profiles = (
            {
                "key": "grass tuft",
                "desc": "A tuft of hardy field grass gathered from the surrounding area.",
                "value": 1,
                "weight": 0.2,
                "kind": "grass",
            },
            {
                "key": "stick bundle",
                "desc": "A tidy bundle of dry sticks suitable for kindling, trade, or camp work.",
                "value": 2,
                "weight": 0.5,
                "kind": "stick",
            },
            {
                "key": "wild herb",
                "desc": "A fragrant wild herb with enough quality to interest a careful buyer.",
                "value": 5,
                "weight": 0.1,
                "kind": "wild herb",
            },
        )

        quality_value_multipliers = {
            "rough": 1,
            "useful": 2,
            "high-quality": 3,
        }
        created_items = []
        for _index in range(max(1, int(yield_amount or 1))):
            roll = random.random()
            if roll < 0.7:
                profile = resource_profiles[0]
            elif roll < 0.95:
                profile = resource_profiles[1]
            else:
                profile = resource_profiles[2]

            item_key = f"{quality} {profile['key']}"
            item_value = int(profile["value"] * quality_value_multipliers.get(quality, 1))
            create_simple_item(
                user,
                key=item_key,
                desc=f"A {quality} {profile['desc'].lower()}",
                foraged=True,
                material_quality=quality,
                forage_kind=profile["kind"],
                item_value=item_value,
                value=item_value,
                weight=profile["weight"],
            )
            created_items.append(item_key)

        user.db.forage_uses = int(getattr(user.db, "forage_uses", 0) or 0) + 1
        if created_items:
            summary = ", ".join(created_items[:3])
            if len(created_items) > 3:
                summary = f"{summary}, and {len(created_items) - 3} more"
            msg_actor(user, f"You recover {summary}.")

        user.use_skill(
            "outdoorsmanship",
            apply_roundtime=False,
            emit_placeholder=False,
            require_known=False,
            difficulty=difficulty,
        )


register_ability(ForageAbility())