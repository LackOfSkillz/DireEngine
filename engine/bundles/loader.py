from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

from engine.bundles.manifest import BundleManifest, parse_bundle_manifest


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_required: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass(slots=True)
class LoadReport:
    discovered: list[str] = field(default_factory=list)
    loaded: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BundleContext:
    manifest: BundleManifest
    registries: object


def _parse_version(version: str) -> tuple[int, ...]:
    parts = []
    for part in str(version or "0").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def _satisfies_version(version: str, spec: str) -> bool:
    normalized_spec = str(spec or "").strip()
    if not normalized_spec:
        return True
    normalized_version = _parse_version(version)
    for clause in [item.strip() for item in normalized_spec.split(",") if item.strip()]:
        if clause.startswith(">="):
            if normalized_version < _parse_version(clause[2:]):
                return False
        elif clause.startswith("<="):
            if normalized_version > _parse_version(clause[2:]):
                return False
        elif clause.startswith(">"):
            if normalized_version <= _parse_version(clause[1:]):
                return False
        elif clause.startswith("<"):
            if normalized_version >= _parse_version(clause[1:]):
                return False
        elif clause.startswith("=="):
            if normalized_version != _parse_version(clause[2:]):
                return False
        else:
            if normalized_version != _parse_version(clause):
                return False
    return True


class BundleLoader:
    def __init__(self, *, registries, engine_version: str = "1.0.0", search_paths: list[str] | None = None):
        self.registries = registries
        self.engine_version = str(engine_version or "1.0.0")
        self.search_paths = [str(path) for path in (search_paths or []) if str(path).strip()]

    def discover(self) -> list[BundleManifest]:
        manifests: list[BundleManifest] = []
        seen_paths: set[str] = set()
        for raw_path in self.search_paths:
            root = Path(raw_path)
            if not root.exists():
                continue
            for manifest_path in sorted(root.glob("**/bundle.toml")):
                normalized = str(manifest_path.resolve())
                if normalized in seen_paths:
                    continue
                manifests.append(parse_bundle_manifest(manifest_path))
                seen_paths.add(normalized)
        return manifests

    def validate_dependencies(self, manifests: list[BundleManifest]) -> ValidationResult:
        result = ValidationResult()
        manifest_map: dict[str, BundleManifest] = {}
        provide_owners: dict[tuple[str, str], str] = {}
        for manifest in manifests:
            if manifest.bundle_id in manifest_map:
                result.errors.append(f"Duplicate bundle ID detected: {manifest.bundle_id}")
                continue
            manifest_map[manifest.bundle_id] = manifest
            if not _satisfies_version(self.engine_version, manifest.engine_spec):
                result.errors.append(
                    f"Bundle {manifest.bundle_id} requires engine {manifest.engine_spec}, current engine is {self.engine_version}."
                )
            for provide_type, values in manifest.provides.items():
                for value in values:
                    key = (provide_type, str(value or "").strip().lower())
                    owner = provide_owners.get(key)
                    if owner is not None and owner != manifest.bundle_id:
                        result.errors.append(
                            f"Bundle {manifest.bundle_id} conflicts with {owner} for {provide_type}:{value}."
                        )
                    else:
                        provide_owners[key] = manifest.bundle_id

        for manifest in manifests:
            missing = [bundle_id for bundle_id in manifest.required_bundles if bundle_id not in manifest_map]
            if missing:
                result.missing_required[manifest.bundle_id] = missing

        graph = {
            manifest.bundle_id: [dependency for dependency in manifest.required_bundles if dependency in manifest_map]
            for manifest in manifests
            if manifest.bundle_id in manifest_map
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str):
            if node in visited:
                return
            if node in visiting:
                result.errors.append(f"Bundle dependency cycle detected involving {node}.")
                return
            visiting.add(node)
            for dependency in graph.get(node, []):
                visit(dependency)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)
        return result

    def order(self, manifests: list[BundleManifest]) -> list[BundleManifest]:
        manifest_map = {manifest.bundle_id: manifest for manifest in manifests}
        graph = {
            manifest.bundle_id: [dependency for dependency in manifest.required_bundles if dependency in manifest_map]
            for manifest in manifests
        }
        indegree = {bundle_id: len(dependencies) for bundle_id, dependencies in graph.items()}
        ready = sorted(bundle_id for bundle_id, value in indegree.items() if value == 0)
        ordered: list[BundleManifest] = []
        while ready:
            current = ready.pop(0)
            ordered.append(manifest_map[current])
            for bundle_id, dependencies in graph.items():
                if current in dependencies:
                    indegree[bundle_id] -= 1
                    if indegree[bundle_id] == 0:
                        ready.append(bundle_id)
                        ready.sort()
        return ordered

    def load_all(self, manifests: list[BundleManifest]) -> LoadReport:
        report = LoadReport(discovered=[manifest.bundle_id for manifest in manifests])
        validation = self.validate_dependencies(manifests)
        report.warnings.extend(validation.warnings)
        report.failed.update({f"validation:{index}": error for index, error in enumerate(validation.errors, start=1)})
        valid_manifest_map = {
            manifest.bundle_id: manifest
            for manifest in manifests
            if manifest.bundle_id not in validation.missing_required
        }
        if validation.errors:
            invalid_ids = set()
            for message in validation.errors:
                for manifest in manifests:
                    if manifest.bundle_id in message:
                        invalid_ids.add(manifest.bundle_id)
            for bundle_id in invalid_ids:
                valid_manifest_map.pop(bundle_id, None)
                report.skipped[bundle_id] = "validation_error"
        for bundle_id, missing in validation.missing_required.items():
            report.skipped[bundle_id] = f"missing_required_dependencies: {', '.join(missing)}"

        ordered = self.order(list(valid_manifest_map.values()))
        loaded_bundle_ids: set[str] = set()
        for manifest in ordered:
            unmet_runtime = [dependency for dependency in manifest.required_bundles if dependency not in loaded_bundle_ids]
            if unmet_runtime:
                report.skipped[manifest.bundle_id] = f"dependency_failed_to_load: {', '.join(unmet_runtime)}"
                continue
            try:
                register_callable = self._resolve_callable(manifest.register_callable)
                register_callable(BundleContext(manifest=manifest, registries=self.registries))
                loaded_bundle_ids.add(manifest.bundle_id)
                report.loaded.append(manifest.bundle_id)
            except Exception as exc:
                report.failed[manifest.bundle_id] = str(exc)
        return report

    @staticmethod
    def _resolve_callable(path: str):
        module_path, attribute_name = str(path or "").rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, attribute_name)