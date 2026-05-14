"""Magical feat lookup and modifier aggregation service."""

from __future__ import annotations

from collections.abc import Mapping

from domain.feats.feat_definitions import FEAT_REGISTRY, Feat, get_feat


def _normalize_identifier(value) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


class FeatService:
    @staticmethod
    def ensure_feat_defaults(character):
        if character is None:
            return {"learned": [], "granted": []}

        db = getattr(character, "db", None)
        if db is None:
            return {"learned": [], "granted": []}

        raw = getattr(db, "feats", None)
        if not isinstance(raw, Mapping):
            raw = {}

        learned = raw.get("learned") if isinstance(raw, Mapping) else None
        granted = raw.get("granted") if isinstance(raw, Mapping) else None
        normalized = {
            "learned": [_normalize_identifier(value) for value in list(learned or []) if str(value or "").strip()],
            "granted": [_normalize_identifier(value) for value in list(granted or []) if str(value or "").strip()],
        }
        db.feats = normalized
        return normalized

    @staticmethod
    def get_known_feats(character) -> list[str]:
        feats_state = FeatService.ensure_feat_defaults(character)
        return sorted(set(feats_state["learned"]) | set(feats_state["granted"]))

    @staticmethod
    def has_feat(character, feat_id: str) -> bool:
        normalized = _normalize_identifier(feat_id)
        return normalized in FeatService.get_known_feats(character)

    @staticmethod
    def get_active_feat_objects(character) -> list[Feat]:
        return [FEAT_REGISTRY[feat_id] for feat_id in FeatService.get_known_feats(character) if feat_id in FEAT_REGISTRY]

    @staticmethod
    def get_feat(character, feat_id: str) -> Feat | None:
        if not FeatService.has_feat(character, feat_id):
            return None
        return get_feat(feat_id)

    @staticmethod
    def get_modifier(character, key: str) -> float:
        normalized_key = str(key or "").strip().lower().replace("-", "_").replace(" ", "_")
        is_multiplier = normalized_key.endswith("_multiplier")
        value = 1.0 if is_multiplier else 0.0

        for feat in FeatService.get_active_feat_objects(character):
            payload = dict(getattr(feat, "modifier_payload", {}) or {})
            if normalized_key not in payload:
                continue
            modifier = float(payload.get(normalized_key) or 0.0)
            if is_multiplier:
                value *= modifier
            else:
                value += modifier

        return value

    @staticmethod
    def get_unlock(character, key: str) -> bool:
        normalized_key = str(key or "").strip().lower().replace("-", "_").replace(" ", "_")
        for feat in FeatService.get_active_feat_objects(character):
            unlocks = {str(value).strip().lower().replace("-", "_").replace(" ", "_") for value in (feat.unlock_payload or [])}
            if normalized_key in unlocks:
                return True
        return False