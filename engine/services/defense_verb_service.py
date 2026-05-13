from __future__ import annotations

import random
from dataclasses import dataclass

from domain.combat.verbs import DEFENSE_VERBS, DefenseVerb
from engine.services.result import ActionResult
from engine.services.skill_service import SkillService


@dataclass(frozen=True)
class DefenseVerbExecution:
    result: ActionResult
    verb: DefenseVerb


class DefenseVerbService:
    @staticmethod
    def execute(defender, verb: str) -> DefenseVerbExecution:
        verb_meta = DEFENSE_VERBS[str(verb or "").strip().lower()]
        current_maneuver = DefenseVerbService._get_last_maneuver(defender)
        if current_maneuver == int(verb_meta.verb_id):
            return DefenseVerbExecution(
                result=ActionResult.fail(data={"error_code": "already_positioned", "block_message": verb_meta.already_message, "outcome": "blocked"}),
                verb=verb_meta,
            )

        broke_stealth = False
        if hasattr(defender, "is_hidden") and defender.is_hidden():
            broke_stealth = True
            if hasattr(defender, "break_stealth"):
                defender.break_stealth()
            else:
                defender.db.stealthed = False
        elif bool(getattr(getattr(defender, "db", None), "stealthed", False)):
            broke_stealth = True
            if hasattr(defender, "break_stealth"):
                defender.break_stealth()
            else:
                defender.db.stealthed = False

        if hasattr(defender, "is_stunned") and defender.is_stunned():
            if hasattr(defender, "consume_stun"):
                defender.consume_stun()
            return DefenseVerbExecution(
                result=ActionResult.fail(data={"error_code": "stunned", "block_message": "You are too stunned to maneuver.", "outcome": "blocked", "broke_stealth": broke_stealth}),
                verb=verb_meta,
            )

        if hasattr(defender, "is_in_roundtime") and defender.is_in_roundtime():
            return DefenseVerbExecution(
                result=ActionResult.fail(data={"error_code": "roundtime", "outcome": "blocked", "broke_stealth": broke_stealth}),
                verb=verb_meta,
            )

        if hasattr(defender, "set_last_maneuver"):
            defender.set_last_maneuver(verb_meta.verb_id)
        else:
            defender.db.last_maneuver = int(verb_meta.verb_id)

        if verb_meta.key == "parry":
            DefenseVerbService._award_remedial_parry_xp(defender)

        roundtime = random.randint(3, 4)
        if hasattr(defender, "set_roundtime"):
            defender.set_roundtime(roundtime)

        return DefenseVerbExecution(
            result=ActionResult.ok(
                data={
                    "outcome": "positioned",
                    "verb": verb_meta.key,
                    "roundtime": roundtime,
                    "message": verb_meta.enter_message,
                    "broke_stealth": broke_stealth,
                }
            ),
            verb=verb_meta,
        )

    @staticmethod
    def get_verb(verb: str) -> DefenseVerb:
        return DEFENSE_VERBS[str(verb or "").strip().lower()]

    @staticmethod
    def _get_last_maneuver(defender) -> int:
        getter = getattr(defender, "get_last_maneuver", None)
        if callable(getter):
            return int(getter() or 0)
        return int(getattr(getattr(defender, "db", None), "last_maneuver", 0) or 0)

    @staticmethod
    def _award_remedial_parry_xp(defender):
        get_skill = getattr(defender, "get_skill", None)
        if not callable(get_skill):
            return
        if not all(
            hasattr(defender, attr)
            for attr in ("_sync_exp_skill_state", "_persist_exp_skill_state", "get_exp_skillset_tier")
        ):
            return
        skill_name = DefenseVerbService._get_parry_skill_name(defender)
        current_rank = int(get_skill(skill_name) or 0)
        get_circle = getattr(defender, "get_circle", None)
        circle = int(get_circle() if callable(get_circle) else getattr(getattr(defender, "db", None), "circle", 1) or 1)
        if current_rank >= circle:
            return
        difficulty = random.randint(1, max(2, circle + 5))
        SkillService.award_xp(
            defender,
            skill_name,
            difficulty,
            source={"mode": "difficulty"},
            success=True,
            context_multiplier=0.5,
        )

    @staticmethod
    def _get_parry_skill_name(defender) -> str:
        if hasattr(defender, "get_weapon_profile"):
            profile = dict(defender.get_weapon_profile() or {})
            skill_name = str(profile.get("skill") or "").strip().lower()
            if skill_name:
                return skill_name
        return "combat"