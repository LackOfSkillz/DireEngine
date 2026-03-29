from pathlib import Path

from world.area_forge.ai.adjudicator import adjudicate_area_spec
from world.area_forge.build.diff import diff_area_specs
from world.area_forge.build.snapshots import load_snapshot, save_snapshot
from world.area_forge.intake.manifest import create_manifest, load_manifest
from world.area_forge.paths import artifact_paths
from world.area_forge.review import generate_review_flags, save_review_report
from world.area_forge.serializer import load_area_spec, save_area_spec


def _extract_area(area_id, map_path, use_ocr=True, use_ai_adjudication=False, profile=None, style=None):
    if profile != "dr_city":
        raise ValueError(f"Unsupported AreaForge profile: {profile}")

    from world.the_landing import extract_the_landing_area_spec

    return extract_the_landing_area_spec(
        map_path=map_path,
        use_ocr=use_ocr,
        use_ai_adjudication=use_ai_adjudication,
        area_id=area_id,
        profile=profile,
        style_settings=style,
    )


def _build_evennia_area(area_id, area_spec, profile=None):
    if profile != "dr_city":
        raise ValueError(f"Unsupported AreaForge profile: {profile}")

    from world.the_landing import build_the_landing_from_area_spec

    return build_the_landing_from_area_spec(area_spec)


def run_area_forge(map_path, area_id, mode="full", manifest_path=None, use_ocr=True):
    if not manifest_path:
        manifest_path = create_manifest(map_path, area_id)

    print(f"[AreaForge] Using manifest: {manifest_path}")
    manifest = load_manifest(manifest_path)

    map_path = Path(manifest["map_file"])
    area_id = manifest["area_id"]
    profile = manifest.get("profile", "dr_city")
    style = manifest.get("style", {})
    artifacts = artifact_paths(area_id)

    area_spec = None
    build_result = None
    changes = []
    if mode == "build":
        area_spec = load_area_spec(artifacts["areaspec"])
        if not area_spec:
            raise FileNotFoundError("Build mode requires an existing build/areaspec.json artifact.")
    else:
        area_spec = _extract_area(
            area_id,
            map_path,
            use_ocr=use_ocr,
            use_ai_adjudication=(mode == "full"),
            profile=profile,
            style=style,
        )

    if mode == "extract":
        save_area_spec(artifacts["areaspec"], area_spec)
        flags = generate_review_flags(area_spec["nodes"], area_spec["edges"])
        save_review_report(artifacts["review"], flags)
        old_snapshot = load_snapshot(area_id)
        changes = diff_area_specs(old_snapshot, area_spec)
        for change in changes:
            print(f"[DIFF] {change}")
        save_snapshot(area_id, area_spec)
    elif mode == "enrich":
        area_spec = adjudicate_area_spec(
            area_spec,
            context={"profile": profile, "area_id": area_id, "style": style},
        )
        save_area_spec(artifacts["areaspec"], area_spec)
        flags = generate_review_flags(area_spec["nodes"], area_spec["edges"])
        save_review_report(artifacts["review"], flags)
        old_snapshot = load_snapshot(area_id)
        changes = diff_area_specs(old_snapshot, area_spec)
        for change in changes:
            print(f"[DIFF] {change}")
        save_snapshot(area_id, area_spec)
    elif mode == "build":
        old_snapshot = load_snapshot(area_id)
        changes = diff_area_specs(old_snapshot, area_spec)
        for change in changes:
            print(f"[DIFF] {change}")
        flags = generate_review_flags(area_spec["nodes"], area_spec["edges"])
        save_review_report(artifacts["review"], flags)
        build_result = _build_evennia_area(area_id, area_spec, profile=profile)
        save_snapshot(area_id, area_spec)
    elif mode == "full":
        old_snapshot = load_snapshot(area_id)
        changes = diff_area_specs(old_snapshot, area_spec)
        for change in changes:
            print(f"[DIFF] {change}")
        save_area_spec(artifacts["areaspec"], area_spec)
        flags = generate_review_flags(area_spec["nodes"], area_spec["edges"])
        save_review_report(artifacts["review"], flags)
        build_result = _build_evennia_area(area_id, area_spec, profile=profile)
        save_snapshot(area_id, area_spec)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    print(f"Area: {area_id}")
    print(f"Rooms: {len(area_spec['nodes'])}")
    print(f"Exits: {len(area_spec['edges'])}")
    print(f"Review flags: {len(flags)}")
    print("Artifacts:")
    print(f" - {artifacts['manifest']}")
    print(f" - {artifacts['areaspec']}")
    print(f" - {artifacts['review']}")

    return {
        "area_id": area_id,
        "area_spec": area_spec,
        "review_flag_count": len(flags),
        "artifacts": artifacts,
        "changes": changes,
        "build_result": build_result,
    }
