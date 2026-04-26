import os
from pathlib import Path

from world.area_forge.ai.adjudicator import adjudicate_area_spec
from world.area_forge.build.diff import diff_area_specs
from world.area_forge.build.review_graph import area_spec_to_review_graph
from world.area_forge.build.review_normalization import generate_normalization_report
from world.area_forge.build.snapshots import load_snapshot, save_snapshot
from world.area_forge.build.zone_yaml_export import write_zone_yaml_from_review_graph
from world.area_forge.extract.yaml_graph import extract_yaml_graph_area_spec_v2
from world.area_forge.intake.manifest import create_manifest, load_manifest
from world.area_forge.paths import artifact_paths
from world.area_forge.review import generate_review_flags, save_review_report
from world.area_forge.serializer import load_area_spec, load_review_graph, save_area_spec, save_review_graph


def _extract_area(area_id, map_path, use_ocr=True, use_ai_adjudication=False, profile=None, style=None):
    if profile == "yaml_graph":
        return extract_yaml_graph_area_spec_v2(
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
        if not review_graph:
            raise FileNotFoundError("yaml_graph builds require an existing review_graph artifact.")
        generate_normalization_report(review_graph, output_path=artifacts["normalization_report"])
        yaml_path = write_zone_yaml_from_review_graph(review_graph, output_path=artifacts["zone_yaml"])
        return {
            "zone_yaml": str(yaml_path),
        }

    if profile != "dr_city":
        raise ValueError(f"Unsupported AreaForge profile: {profile}")

    from world.the_landing import build_the_landing_from_area_spec

    return build_the_landing_from_area_spec(area_spec)


def _ensure_evennia_django():
    from django.conf import settings

    if settings.configured:
        return

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

    import django

    django.setup()


def _spawn_zone(area_id, *, dry_run=False):
    _ensure_evennia_django()
    from world.worlddata.services.import_zone_service import load_zone

    return load_zone(area_id, dry_run=dry_run)


def _summarize_extraction(area_spec, normalization_report=None):
    meta = area_spec.get("meta") if isinstance(area_spec.get("meta"), dict) else {}
    print("Extraction summary:")
    print(f" - Pixel clusters: {meta.get('raw_cluster_count', 0)}")
    print(f" - Markers: {meta.get('node_count', len(area_spec.get('nodes') or []))}")
    print(f" - Missing markers: {meta.get('missing_marker_count', 0)}")
    print(f" - Marker coverage: {meta.get('marker_coverage', 0.0)}")
    print(f" - Weak marker candidates: {meta.get('weak_marker_candidate_count', 0)}")
    print(f" - Weak marker promoted: {meta.get('weak_marker_promoted_count', 0)}")
    print(f" - Forced marker promoted: {meta.get('forced_marker_promoted_count', 0)}")
    print(f" - Corridor segments: {meta.get('corridor_segment_count', 0)}")
    print(f" - Spatial exits: {meta.get('edge_count', len(area_spec.get('edges') or []))}")
    print(f" - Special-exit candidates: {meta.get('special_exit_candidate_count', 0)}")
    print(f" - Unnamed rooms: {meta.get('unnamed_room_count', 0)}")
    if bool(meta.get('under_detected')):
        print(" - WARNING: UNDER-DETECTED MAP")
    if normalization_report:
        normalized_nodes = list(normalization_report.get('normalized_nodes') or [])
        print(f" - Unique X lanes: {len({node.get('map_x', 0) for node in normalized_nodes})}")
        print(f" - Unique Y lanes: {len({node.get('map_y', 0) for node in normalized_nodes})}")
        print(f" - Isolated rooms: {normalization_report.get('isolated_room_count', 0)}")
        print(f" - Normalization overlaps: {normalization_report.get('overlap_count', 0)}")


def run_area_forge(
    map_path,
    area_id,
    mode="full",
    manifest_path=None,
    use_ocr=True,
    profile=None,
    spawn=False,
    dry_run_spawn=False,
):
    if spawn and dry_run_spawn:
        raise ValueError("Choose either spawn or dry_run_spawn, not both.")
    if (spawn or dry_run_spawn) and mode not in {"build", "full"}:
        raise ValueError("Spawn options are only supported in build or full mode.")

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
    spawn_result = None
    changes = []
    normalization_report = None
    if mode == "build":
        area_spec = load_area_spec(artifacts["areaspec"])
        if not area_spec:
            raise FileNotFoundError("Build mode requires an existing build/areaspec.json artifact.")
        review_graph = load_review_graph(artifacts["review_graph"]) if profile == "yaml_graph" else None
        if profile == "yaml_graph" and not review_graph:
            raise FileNotFoundError("Build mode requires an existing build/review_graph.json artifact.")
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
        normalization_report = generate_normalization_report(review_graph, output_path=artifacts["normalization_report"])
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
            normalization_report = generate_normalization_report(review_graph, output_path=artifacts["normalization_report"])
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
            review_graph = area_spec_to_review_graph(area_spec, source_image=str(map_path))
            save_review_graph(artifacts["review_graph"], review_graph)
            normalization_report = generate_normalization_report(review_graph, output_path=artifacts["normalization_report"])
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
            normalization_report = generate_normalization_report(review_graph, output_path=artifacts["normalization_report"])
        build_result = _build_evennia_area(area_id, area_spec, profile=profile)
        if spawn or dry_run_spawn:
            spawn_result = _spawn_zone(area_id, dry_run=dry_run_spawn)
        save_snapshot(area_id, area_spec)
    elif mode == "full":
        old_snapshot = load_snapshot(area_id)
        changes = diff_area_specs(old_snapshot, area_spec)
        for change in changes:
            print(f"[DIFF] {change}")
        save_area_spec(artifacts["areaspec"], area_spec)
        if review_graph:
            save_review_graph(artifacts["review_graph"], review_graph)
            normalization_report = generate_normalization_report(review_graph, output_path=artifacts["normalization_report"])
        flags = generate_review_flags(area_spec["nodes"], area_spec["edges"])
        save_review_report(artifacts["review"], flags)
        build_result = _build_evennia_area(area_id, area_spec, profile=profile)
        if spawn or dry_run_spawn:
            spawn_result = _spawn_zone(area_id, dry_run=dry_run_spawn)
        save_snapshot(area_id, area_spec)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    print(f"Area: {area_id}")
    print(f"Rooms: {len(area_spec['nodes'])}")
    print(f"Exits: {len(area_spec['edges'])}")
    print(f"Review flags: {len(flags)}")
    _summarize_extraction(area_spec, normalization_report=normalization_report)
    print("Artifacts:")
    print(f" - {artifacts['manifest']}")
    print(f" - {artifacts['areaspec']}")
    if profile == "yaml_graph":
        print(f" - {artifacts['marker_recovery_report']}")
    print(f" - {artifacts['review']}")
    if review_graph:
        print(f" - {artifacts['review_graph']}")
        print(f" - {artifacts['normalization_report']}")
    if build_result and build_result.get("zone_yaml"):
        print(f" - {build_result['zone_yaml']}")
    if spawn_result:
        if spawn_result.get("dry_run"):
            print("Spawn dry run:")
        else:
            print("Spawn result:")
        print(f" - Zone: {spawn_result['zone_id']}")
        print(f" - Rooms: {spawn_result['rooms']}")
        print(f" - Exits: {spawn_result['exits']}")
        print(f" - NPCs: {spawn_result['npcs']}")
        print(f" - Items: {spawn_result['items']}")
        for warning in list(spawn_result.get("warnings") or []):
            print(f" - Warning: {warning}")

    return {
        "area_id": area_id,
        "area_spec": area_spec,
        "review_flag_count": len(flags),
        "artifacts": artifacts,
        "changes": changes,
        "build_result": build_result,
        "spawn_result": spawn_result,
    }
