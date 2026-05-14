"""Feat trainer acquisition, forgetting, and profession grant flow."""

from __future__ import annotations

from dataclasses import dataclass

from domain.feats.feat_definitions import FEAT_REGISTRY, Feat, get_feat
from engine.services.feat_service import FeatService
from engine.services.slot_service import SlotService


FORGET_COST_COINS = 1250


def _normalize_identifier(value) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


@dataclass(slots=True)
class CanLearnResult:
    success: bool
    reason: str | None = None
    missing_skills: dict[str, dict[str, int]] | None = None
    missing_prerequisites: list[str] | None = None
    needed_slots: int = 0
    available_slots: int = 0


@dataclass(slots=True)
class LearnResult:
    success: bool
    feat_id: str | None = None
    slot_cost: int = 0
    reason: str | None = None


@dataclass(slots=True)
class CanForgetResult:
    success: bool
    reason: str | None = None
    dependent_feats: list[str] | None = None
    cost_coins: int = 0


@dataclass(slots=True)
class ForgetResult:
    success: bool
    feat_id: str | None = None
    slots_refunded: int = 0
    cost_paid: int = 0
    reason: str | None = None


class FeatTrainerService:
    @staticmethod
    def resolve_feat_query(query: str) -> Feat | None:
        normalized = _normalize_identifier(query)
        if not normalized:
            return None

        direct = get_feat(normalized)
        if direct is not None:
            return direct

        exact_name = None
        partial_name = None
        for feat in FEAT_REGISTRY.values():
            feat_names = {
                _normalize_identifier(feat.id),
                _normalize_identifier(feat.name),
            }
            if normalized in feat_names:
                exact_name = feat
                break
            if normalized in _normalize_identifier(feat.name) or normalized in _normalize_identifier(feat.id):
                partial_name = partial_name or feat
        return exact_name or partial_name

    @staticmethod
    def find_trainer_in_room(character):
        room = getattr(character, "location", None)
        if room is None:
            return None
        for obj in list(getattr(room, "contents", []) or []):
            if str(getattr(getattr(obj, "db", None), "trainer_kind", "") or "").strip().lower() == "feat":
                return obj
        return None

    @staticmethod
    def _get_profession(character) -> str:
        if character is None:
            return ""
        getter = getattr(character, "get_profession", None)
        if callable(getter):
            return _normalize_identifier(getter())
        db = getattr(character, "db", None)
        return _normalize_identifier(getattr(db, "profession", getattr(character, "profession", "")))

    @staticmethod
    def can_learn_feat(character, feat_id: str) -> CanLearnResult:
        feat = get_feat(feat_id)
        if feat is None:
            return CanLearnResult(False, reason="unknown_feat")
        if SlotService.get_pool(character) is None:
            return CanLearnResult(False, reason="not_magic_user")
        if FeatService.has_feat(character, feat.id):
            return CanLearnResult(False, reason="already_known")

        profession = FeatTrainerService._get_profession(character)
        if feat.allowed_professions is not None:
            allowed = {_normalize_identifier(entry) for entry in (feat.allowed_professions or [])}
            if profession not in allowed:
                return CanLearnResult(False, reason="profession_restricted")

        missing_skills = {}
        for skill_name, required_rank in dict(feat.requirements or {}).items():
            getter = getattr(character, "get_skill_rank", None)
            if callable(getter):
                current = int(getter(skill_name) or 0)
            else:
                current = int(getattr(character, "get_skill", lambda _name: 0)(skill_name) or 0)
            if current < int(required_rank or 0):
                missing_skills[str(skill_name)] = {"required": int(required_rank or 0), "current": current}
        if missing_skills:
            return CanLearnResult(False, reason="insufficient_skills", missing_skills=missing_skills)

        missing_prerequisites = [required_feat_id for required_feat_id in list(feat.prerequisites or []) if not FeatService.has_feat(character, required_feat_id)]
        if missing_prerequisites:
            return CanLearnResult(False, reason="missing_prerequisites", missing_prerequisites=missing_prerequisites)

        available = SlotService.get_available_slots(character)
        if available < int(feat.slot_cost or 0):
            return CanLearnResult(
                False,
                reason="insufficient_slots",
                needed_slots=int(feat.slot_cost or 0),
                available_slots=available,
            )

        return CanLearnResult(True, needed_slots=int(feat.slot_cost or 0), available_slots=available)

    @staticmethod
    def teach_feat(character, feat_id: str) -> LearnResult:
        feat = get_feat(feat_id)
        if feat is None:
            return LearnResult(False, reason="unknown_feat")
        check = FeatTrainerService.can_learn_feat(character, feat.id)
        if not check.success:
            return LearnResult(False, reason=check.reason)

        if not SlotService.allocate(character, "feats", feat.id, feat.slot_cost):
            return LearnResult(False, reason="slot_allocation_failed")

        feats_state = FeatService.ensure_feat_defaults(character)
        learned = list(feats_state.get("learned", []) or [])
        if feat.id not in learned:
            learned.append(feat.id)
        feats_state["learned"] = sorted(set(learned))
        getattr(character, "db").feats = feats_state
        return LearnResult(True, feat_id=feat.id, slot_cost=int(feat.slot_cost or 0))

    @staticmethod
    def can_forget_feat(character, feat_id: str) -> CanForgetResult:
        feat = get_feat(feat_id)
        if feat is None:
            return CanForgetResult(False, reason="unknown_feat")

        feats_state = FeatService.ensure_feat_defaults(character)
        learned = set(feats_state.get("learned", []) or [])
        granted = set(feats_state.get("granted", []) or [])
        if feat.id not in learned:
            if feat.id in granted:
                return CanForgetResult(False, reason="granted_feat_cannot_be_forgotten")
            return CanForgetResult(False, reason="not_learned")

        dependent_feats = []
        for known_id in learned:
            known_feat = get_feat(known_id)
            if known_feat is not None and feat.id in list(known_feat.prerequisites or []):
                dependent_feats.append(known_feat.name)
        if dependent_feats:
            return CanForgetResult(False, reason="has_dependents", dependent_feats=sorted(dependent_feats))
        return CanForgetResult(True, cost_coins=FORGET_COST_COINS)

    @staticmethod
    def forget_feat(character, feat_id: str) -> ForgetResult:
        feat = get_feat(feat_id)
        if feat is None:
            return ForgetResult(False, reason="unknown_feat")
        check = FeatTrainerService.can_forget_feat(character, feat.id)
        if not check.success:
            return ForgetResult(False, reason=check.reason)

        current_coins = int(getattr(getattr(character, "db", None), "coins", 0) or 0)
        if current_coins < int(check.cost_coins or 0):
            return ForgetResult(False, reason="insufficient_kronar")

        character.db.coins = current_coins - int(check.cost_coins or 0)
        refunded = SlotService.deallocate(character, "feats", feat.id)
        feats_state = FeatService.ensure_feat_defaults(character)
        feats_state["learned"] = [entry for entry in list(feats_state.get("learned", []) or []) if entry != feat.id]
        getattr(character, "db").feats = feats_state
        return ForgetResult(True, feat_id=feat.id, slots_refunded=refunded, cost_paid=int(check.cost_coins or 0))

    @staticmethod
    def grant_free_feat(character, feat_id: str) -> bool:
        feat = get_feat(feat_id)
        if feat is None:
            return False
        feats_state = FeatService.ensure_feat_defaults(character)
        learned = set(feats_state.get("learned", []) or [])
        granted = set(feats_state.get("granted", []) or [])
        if feat.id in learned:
            SlotService.deallocate(character, "feats", feat.id)
            learned.remove(feat.id)
        granted.add(feat.id)
        feats_state["learned"] = sorted(learned)
        feats_state["granted"] = sorted(granted)
        getattr(character, "db").feats = feats_state
        return True

    @staticmethod
    def grant_circle_profession_feats(character, new_circle: int) -> list[Feat]:
        profession = FeatTrainerService._get_profession(character)
        granted = []
        for feat in FEAT_REGISTRY.values():
            required_circle = int(dict(feat.granted_by_profession or {}).get(profession, 0) or 0)
            if required_circle != int(new_circle or 0):
                continue
            if FeatTrainerService.grant_free_feat(character, feat.id):
                granted.append(feat)
        return granted