from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib

from engine.bundles.exceptions import ManifestValidationError


def _coerce_string_list(value) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ManifestValidationError("Manifest list fields must be TOML arrays.")
    return [str(item or "").strip() for item in value if str(item or "").strip()]


@dataclass(frozen=True, slots=True)
class BundleManifest:
    bundle_id: str
    display_name: str
    version: str
    tier: int
    engine_spec: str = ">=1.0.0"
    required_bundles: tuple[str, ...] = field(default_factory=tuple)
    optional_bundles: tuple[str, ...] = field(default_factory=tuple)
    provides: dict[str, tuple[str, ...]] = field(default_factory=dict)
    register_callable: str = ""
    manifest_path: str = ""

    @property
    def manifest_dir(self) -> str:
        return str(Path(self.manifest_path).parent)


def parse_bundle_manifest(path: str | Path) -> BundleManifest:
    manifest_path = Path(path)
    try:
        payload = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ManifestValidationError(f"Unable to read manifest '{manifest_path}': {exc}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ManifestValidationError(f"Invalid TOML in manifest '{manifest_path}': {exc}") from exc

    bundle = dict(payload.get("bundle") or {})
    requires = dict(payload.get("requires") or {})
    provides = dict(payload.get("provides") or {})
    entrypoint = dict(payload.get("entrypoint") or {})

    bundle_id = str(bundle.get("id") or "").strip()
    display_name = str(bundle.get("display_name") or "").strip()
    version = str(bundle.get("version") or "").strip()
    register_callable = str(entrypoint.get("register_callable") or "").strip()
    if not bundle_id or not display_name or not version or not register_callable:
        raise ManifestValidationError(
            f"Manifest '{manifest_path}' must define bundle.id, bundle.display_name, bundle.version, and entrypoint.register_callable."
        )

    normalized_provides = {
        str(key or "").strip(): tuple(_coerce_string_list(value))
        for key, value in provides.items()
        if str(key or "").strip()
    }

    required_bundles = tuple(_coerce_string_list(requires.get("free_bundles")) + _coerce_string_list(requires.get("paid_bundles")))
    optional_bundles = tuple(_coerce_string_list(requires.get("optional_bundles")))
    tier = int(bundle.get("tier") or 0)

    return BundleManifest(
        bundle_id=bundle_id,
        display_name=display_name,
        version=version,
        tier=tier,
        engine_spec=str(requires.get("engine") or ">=1.0.0").strip() or ">=1.0.0",
        required_bundles=required_bundles,
        optional_bundles=optional_bundles,
        provides=normalized_provides,
        register_callable=register_callable,
        manifest_path=str(manifest_path),
    )