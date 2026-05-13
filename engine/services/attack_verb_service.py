from __future__ import annotations

from dataclasses import dataclass

from domain.combat.verbs import ATTACK_VERBS, AttackVerb
from engine.services.combat_service import CombatService
from engine.services.result import ActionResult
from world.helpers.target_resolver import resolve_target


EMPATH_ATTACK_BLOCK_MESSAGE = "Thinking about attacking something? You feel sick to your stomach!"


@dataclass(frozen=True)
class AttackVerbExecution:
    result: ActionResult | None
    target: object | None = None
    matches: tuple[object, ...] = ()
    base_query: str = ""


class AttackVerbService:
    @staticmethod
    def execute(attacker, verb: str, *, target_arg: str = "") -> AttackVerbExecution:
        verb_meta = ATTACK_VERBS[str(verb or "").strip().lower()]
        query = AttackVerbService._normalize_target_arg(target_arg)

        blocked_message = AttackVerbService._get_empath_block_message(attacker)
        if blocked_message:
            return AttackVerbExecution(
                result=ActionResult.fail(data={"error_code": "blocked", "block_message": blocked_message, "outcome": "blocked"}),
            )

        terrain_message = AttackVerbService._get_terrain_guard_message(attacker, verb_meta, query)
        if terrain_message:
            return AttackVerbExecution(
                result=ActionResult.fail(data={"error_code": "blocked", "block_message": terrain_message, "outcome": "blocked"}),
            )

        target, matches, base_query = AttackVerbService._resolve_target(attacker, query, verb_meta)
        if target is None and matches:
            return AttackVerbExecution(result=None, matches=tuple(matches), base_query=base_query)
        if target is None:
            error_code = "target_not_found" if query else "no_target"
            return AttackVerbExecution(result=ActionResult.fail(data={"error_code": error_code, "outcome": "blocked"}))

        slice_result = AttackVerbService._run_slice_defender_hook(attacker, target, verb_meta)
        if slice_result is not None:
            return AttackVerbExecution(result=slice_result, target=target)

        return AttackVerbExecution(
            result=CombatService.attack(
                attacker,
                target,
                verb=verb_meta.key,
                verb_rt=verb_meta.rt_seconds,
                verb_id=verb_meta.verb_id,
            ),
            target=target,
        )

    @staticmethod
    def get_verb(verb: str) -> AttackVerb:
        return ATTACK_VERBS[str(verb or "").strip().lower()]

    @staticmethod
    def _normalize_target_arg(target_arg: str) -> str:
        text = str(target_arg or "").strip()
        lowered = text.lower()
        if lowered.startswith("at "):
            return text[3:].strip()
        return text

    @staticmethod
    def _resolve_target(attacker, query: str, verb_meta: AttackVerb) -> tuple[object | None, list[object], str]:
        if not query:
            current_target = attacker.get_target() if hasattr(attacker, "get_target") else None
            return current_target, [], ""

        target, matches, base_query, _index, _scope = resolve_target(
            query,
            attacker,
            scopes=("characters", "room"),
            default_first=True,
        )
        if target is not None or matches:
            return target, list(matches), base_query

        if verb_meta.uses_engagement_target:
            current_target = attacker.get_target() if hasattr(attacker, "get_target") else None
            if current_target is not None:
                return current_target, [], base_query
        return None, [], base_query

    @staticmethod
    def _get_empath_block_message(attacker) -> str | None:
        if hasattr(attacker, "is_profession") and attacker.is_profession("empath"):
            return EMPATH_ATTACK_BLOCK_MESSAGE
        if hasattr(attacker, "get_profession") and str(attacker.get_profession() or "").strip().lower() == "empath":
            return EMPATH_ATTACK_BLOCK_MESSAGE
        return None

    @staticmethod
    def _get_terrain_guard_message(attacker, verb_meta: AttackVerb, query: str) -> str | None:
        if not verb_meta.has_terrain_guard:
            return None
        normalized = str(query or "").strip().lower()
        if normalized not in {"tree", "trees", "vine", "vines"}:
            return None

        wanted = "trees" if normalized.startswith("tree") else "vines"
        room = getattr(attacker, "location", None)
        contents = list(getattr(room, "contents", []) or []) if room is not None else []
        for obj in contents:
            if not bool(getattr(obj, "is_choppable", False)):
                continue
            return None
        return f"There are no {wanted} around here you really want to chop."

    @staticmethod
    def _run_slice_defender_hook(attacker, target, verb_meta: AttackVerb) -> ActionResult | None:
        if not verb_meta.triggers_defender_script:
            return None
        hook = getattr(target, "on_attack_attempt", None)
        if not callable(hook):
            return None

        hook_result = hook(attacker, verb=verb_meta.key)
        if isinstance(hook_result, str):
            return ActionResult.fail(data={"error_code": "blocked", "block_message": hook_result, "outcome": "blocked"})
        if isinstance(hook_result, dict) and hook_result.get("break"):
            message = str(hook_result.get("message", "") or "")
            if message:
                return ActionResult.fail(data={"error_code": "blocked", "block_message": message, "outcome": "blocked"})
            return ActionResult.ok(data={"outcome": "handled"})
        if hook_result is False:
            return ActionResult.ok(data={"outcome": "handled"})
        return None
