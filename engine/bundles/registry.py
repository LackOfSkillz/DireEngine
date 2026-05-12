from __future__ import annotations

from copy import deepcopy

from engine.bundles.exceptions import BundleConflictError, BundleNotLoadedError, BundleOwnershipError, ManifestValidationError


class Registry:
    """Base class for content registries."""

    required_fields: tuple[str, ...] = ("id",)

    def __init__(self, registry_name: str):
        self.registry_name = str(registry_name)
        self._entries: dict[str, dict] = {}
        self._owners: dict[str, str] = {}

    def _normalize_key(self, key: str) -> str:
        normalized = str(key or "").strip().lower()
        if not normalized:
            raise ManifestValidationError(f"{self.registry_name} registration key cannot be empty.")
        return normalized

    def validate_definition(self, key: str, definition: dict) -> dict:
        if not isinstance(definition, dict):
            raise ManifestValidationError(f"{self.registry_name} definition for '{key}' must be a dict.")
        normalized = deepcopy(definition)
        normalized.setdefault("id", key)
        missing = [field_name for field_name in self.required_fields if normalized.get(field_name) in (None, "")]
        if missing:
            raise ManifestValidationError(
                f"{self.registry_name} definition for '{key}' is missing required fields: {', '.join(sorted(missing))}."
            )
        return normalized

    def register(self, key: str, definition: dict, *, source_bundle: str) -> None:
        normalized_key = self._normalize_key(key)
        normalized_source = str(source_bundle or "").strip()
        if not normalized_source:
            raise ManifestValidationError(f"{self.registry_name} registration for '{normalized_key}' requires source_bundle.")
        existing_owner = self._owners.get(normalized_key)
        if existing_owner is not None and existing_owner != normalized_source:
            raise BundleConflictError(
                f"{self.registry_name} key '{normalized_key}' is already owned by bundle '{existing_owner}'."
            )
        normalized = self.validate_definition(normalized_key, definition)
        normalized["source_bundle"] = normalized_source
        self._entries[normalized_key] = normalized
        self._owners[normalized_key] = normalized_source

    def get(self, key: str) -> dict | None:
        normalized_key = self._normalize_key(key)
        payload = self._entries.get(normalized_key)
        return deepcopy(payload) if payload is not None else None

    def require(self, key: str) -> dict:
        payload = self.get(key)
        if payload is None:
            raise BundleNotLoadedError(f"{self.registry_name} key '{self._normalize_key(key)}' is not registered.")
        return payload

    def list_keys(self) -> list[str]:
        return sorted(self._entries.keys())

    def list_by_bundle(self, bundle_id: str) -> list[str]:
        normalized_bundle = str(bundle_id or "").strip()
        return sorted(key for key, owner in self._owners.items() if owner == normalized_bundle)

    def is_registered(self, key: str) -> bool:
        return self._normalize_key(key) in self._entries

    def unregister(self, key: str, *, source_bundle: str) -> None:
        normalized_key = self._normalize_key(key)
        normalized_source = str(source_bundle or "").strip()
        owner = self._owners.get(normalized_key)
        if owner is None:
            return
        if owner != normalized_source:
            raise BundleOwnershipError(
                f"{self.registry_name} key '{normalized_key}' is owned by '{owner}', not '{normalized_source}'."
            )
        self._owners.pop(normalized_key, None)
        self._entries.pop(normalized_key, None)

    def clear(self) -> None:
        self._entries.clear()
        self._owners.clear()