from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import logging

from django.conf import settings

from engine.bundles.builtin_skills import populate_skill_registry_from_canon
from engine.bundles.loader import BundleLoader, LoadReport
from engine.bundles.stat_registry import populate_stat_registry_from_canon


BUNDLE_API_VERSION = "1.0.0"
_LAST_BOOT_REPORT: LoadReport | None = None
_LAST_STAT_SOURCE = "uninitialized"
_LAST_SKILL_SOURCE = "uninitialized"
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RegistryHub:
    profession_registry: object
    race_registry: object
    zone_registry: object
    trade_registry: object
    content_registry: object
    skill_registry: object
    stat_registry: object
    spell_circle_registry: object


def get_registry_hub() -> RegistryHub:
    from engine.bundles import (
        content_registry,
        profession_registry,
        race_registry,
        skill_registry,
        spell_circle_registry,
        stat_registry,
        trade_registry,
        zone_registry,
    )

    return RegistryHub(
        profession_registry=profession_registry,
        race_registry=race_registry,
        zone_registry=zone_registry,
        trade_registry=trade_registry,
        content_registry=content_registry,
        skill_registry=skill_registry,
        stat_registry=stat_registry,
        spell_circle_registry=spell_circle_registry,
    )


def reset_registries() -> None:
    hub = get_registry_hub()
    for registry in (
        hub.profession_registry,
        hub.race_registry,
        hub.zone_registry,
        hub.trade_registry,
        hub.content_registry,
        hub.skill_registry,
        hub.stat_registry,
        hub.spell_circle_registry,
    ):
        registry.clear()


def get_default_bundle_paths(extra_paths: list[str] | None = None) -> list[str]:
    repo_root = Path(__file__).resolve().parents[2]
    configured = [str(path) for path in list(getattr(settings, "BUNDLE_PATHS", []) or []) if str(path).strip()]
    paths = [repo_root / "world" / "bundles", repo_root / "bundles"]
    paths.extend(Path(path) for path in configured)
    paths.extend(Path(path) for path in (extra_paths or []) if str(path).strip())
    seen: set[str] = set()
    ordered: list[str] = []
    for path in paths:
        normalized = str(path)
        if normalized in seen:
            continue
        ordered.append(normalized)
        seen.add(normalized)
    return ordered


def boot_bundles(*, extra_paths: list[str] | None = None) -> LoadReport:
    global _LAST_BOOT_REPORT, _LAST_STAT_SOURCE, _LAST_SKILL_SOURCE
    reset_registries()
    hub = get_registry_hub()
    _LAST_SKILL_SOURCE = populate_skill_registry_from_canon(registry=hub.skill_registry)
    _LAST_STAT_SOURCE = populate_stat_registry_from_canon(registry=hub.stat_registry)
    loader = BundleLoader(registries=hub, engine_version=BUNDLE_API_VERSION, search_paths=get_default_bundle_paths(extra_paths))
    report = loader.load_all(loader.discover())
    report.warnings.append(f"skill_registry_source={_LAST_SKILL_SOURCE}")
    report.warnings.append(f"stat_registry_source={_LAST_STAT_SOURCE}")
    _LAST_BOOT_REPORT = report
    try:
        from evennia.utils import logger as evennia_logger

        evennia_logger.log_info(
            f"[Bundles] boot complete: loaded={len(report.loaded)} skipped={len(report.skipped)} failed={len(report.failed)} skill_source={_LAST_SKILL_SOURCE} stat_source={_LAST_STAT_SOURCE}"
        )
    except Exception:
        LOGGER.info(
            "[Bundles] boot complete: loaded=%s skipped=%s failed=%s skill_source=%s stat_source=%s",
            len(report.loaded),
            len(report.skipped),
            len(report.failed),
            _LAST_SKILL_SOURCE,
            _LAST_STAT_SOURCE,
        )
    return report


def get_last_boot_report() -> LoadReport | None:
    return _LAST_BOOT_REPORT


def get_last_stat_source() -> str:
    return _LAST_STAT_SOURCE


def get_last_skill_source() -> str:
    return _LAST_SKILL_SOURCE