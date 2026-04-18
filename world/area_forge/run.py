from pathlib import Path

from world.area_forge.ai.adjudicator import adjudicate_area_spec
from world.area_forge.build.diff import diff_area_specs
from world.area_forge.build.review_graph import area_spec_to_review_graph
from world.area_forge.build.snapshots import load_snapshot, save_snapshot
from world.area_forge.build.zone_yaml_export import write_zone_yaml_from_review_graph
from world.area_forge.extract.yaml_graph import extract_yaml_graph_area_spec
from world.area_forge.intake.manifest import create_manifest, load_manifest
from world.area_forge.paths import artifact_paths
from world.area_forge.review import generate_review_flags, save_review_report
from world.area_forge.serializer import load_area_spec, load_review_graph, save_area_spec, save_review_graph


def _extract_area(area_id, map_path, use_ocr=True, use_ai_adjudication=False, profile=None, style=None):
    if profile == "yaml_graph":
        return extract_yaml_graph_area_spec(
            map_path=map_path,
            use_ocr=use_ocr,
            use_ai_adjudication=use_ai_adjudication,
            area_id=area_id,
            profile=profile,
            style_settings=style,
        )

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
    if profile == "yaml_graph":
        artifacts = artifact_paths(area_id)
        review_graph = load_review_graph(artifacts["review_graph"])
        yaml_path = write_zone_yaml_from_review_graph(review_graph or area_spec, output_path=artifacts["zone_yaml"])
        return {
            "zone_yaml": str(yaml_path),
        }

    if profile != "dr_city":
        raise ValueError(f"Unsupported AreaForge profile: {profile}")

    from world.the_landing import build_the_landing_from_area_spec

    return build_the_landing_from_area_spec(area_spec)


def run_area_forge(map_path, area_id, mode="full", manifest_path=None, use_ocr=True, profile=None):
    if not manifest_path:
        manifest_path = create_manifest(map_path, area_id, profile=profile or "yaml_graph")

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

    review_graph = area_spec_to_review_graph(area_spec, source_image=str(map_path)) if profile == "yaml_graph" else None

    if mode == "review":
        if not review_graph:
            raise ValueError("Review mode is only supported for the yaml_graph profile.")
        save_review_graph(artifacts["review_graph"], review_graph)
        print(f"Area: {area_id}")
        print(f"Review graph: {artifacts['review_graph']}")
        return {
            "area_id": area_id,
            "area_spec": area_spec,
            "review_graph": review_graph,
            "review_flag_count": 0,
            "artifacts": artifacts,
            "changes": [],
            "build_result": None,
        }

    if mode == "extract":
        save_area_spec(artifacts["areaspec"], area_spec)
        if review_graph:
            save_review_graph(artifacts["review_graph"], review_graph)
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
        if profile == "yaml_graph":
            save_review_graph(artifacts["review_graph"], area_spec_to_review_graph(area_spec, source_image=str(map_path)))
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
        if review_graph:
            save_review_graph(artifacts["review_graph"], review_graph)
        build_result = _build_evennia_area(area_id, area_spec, profile=profile)
        save_snapshot(area_id, area_spec)
    elif mode == "full":
        old_snapshot = load_snapshot(area_id)
        changes = diff_area_specs(old_snapshot, area_spec)
        for change in changes:
            print(f"[DIFF] {change}")
        save_area_spec(artifacts["areaspec"], area_spec)
        if review_graph:
            save_review_graph(artifacts["review_graph"], review_graph)
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
    if review_graph:
        print(f" - {artifacts['review_graph']}")
    if build_result and build_result.get("zone_yaml"):
        print(f" - {build_result['zone_yaml']}")

    return {
        "area_id": area_id,
        "area_spec": area_spec,
        "review_flag_count": len(flags),
        "artifacts": artifacts,
        "changes": changes,
        "build_result": build_result,
    }
