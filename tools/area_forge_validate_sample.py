from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import re
import statistics
from collections import deque
from pathlib import Path
import sys
import time

import cv2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build" / "area_forge_validation_summary.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from world.area_forge.extract.yaml_graph import extract_yaml_graph_area_spec_v2


def _component_metrics(area_spec: dict[str, object]) -> dict[str, object]:
    nodes = [node for node in list(area_spec.get("nodes") or []) if isinstance(node, dict) and node.get("id")]
    node_ids = {str(node["id"]) for node in nodes}
    adjacency = {node_id: set() for node_id in node_ids}
    for raw_edge in list(area_spec.get("edges") or []):
        if not isinstance(raw_edge, (list, tuple)) or len(raw_edge) < 3:
            continue
        source = str(raw_edge[0] or "")
        target = str(raw_edge[2] or "")
        if source not in adjacency or target not in adjacency:
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)

    components = []
    seen = set()
    for node_id in sorted(adjacency):
        if node_id in seen:
            continue
        queue = deque([node_id])
        seen.add(node_id)
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    components.sort(key=len, reverse=True)

    room_count = len(nodes)
    isolated_room_count = sum(1 for component in components if len(component) == 1)
    largest_component = len(components[0]) if components else 0
    connected_rooms = room_count - isolated_room_count
    connected_pct = (connected_rooms / room_count * 100.0) if room_count else 0.0
    return {
        "rooms": room_count,
        "isolated_rooms": isolated_room_count,
        "largest_component": largest_component,
        "connected_rooms": connected_rooms,
        "connected_pct": round(connected_pct, 1),
        "component_count": len(components),
    }


def _image_metrics(map_path: Path) -> dict[str, object]:
    image = cv2.imread(str(map_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"OpenCV could not read map image: {map_path}")
    dark_ratio = float((image < 220).mean())
    return {
        "file_size_bytes": map_path.stat().st_size,
        "dark_ratio": round(dark_ratio, 4),
        "image_width": int(image.shape[1]),
        "image_height": int(image.shape[0]),
    }


def _evaluate_map(map_path: Path, area_id: str, use_ocr: bool) -> dict[str, object]:
    area_spec = extract_yaml_graph_area_spec_v2(
        map_path=map_path,
        area_id=area_id,
        use_ocr=use_ocr,
        use_ai_adjudication=False,
        profile="yaml_graph",
        style_settings={},
    )
    metrics = _component_metrics(area_spec)
    image_metrics = _image_metrics(map_path)
    return {
        "map_name": map_path.name,
        "area_id": area_id,
        "map_path": str(map_path),
        "ocr_used": bool(area_spec.get("meta", {}).get("ocr_used")),
        **image_metrics,
        **metrics,
    }


def _evaluate_map_worker(map_path_str: str, area_id: str, use_ocr: bool, queue) -> None:
    try:
        result = _evaluate_map(Path(map_path_str), area_id, use_ocr)
    except Exception as exc:  # pragma: no cover - surfaced in parent process
        queue.put({"ok": False, "error": repr(exc)})
        return
    queue.put({"ok": True, "result": result})


def _evaluate_map_with_timeout(map_path: Path, area_id: str, use_ocr: bool, timeout_seconds: float | None) -> dict[str, object]:
    if not timeout_seconds or timeout_seconds <= 0:
        started = time.perf_counter()
        result = _evaluate_map(map_path, area_id, use_ocr)
        result["status"] = "ok"
        result["elapsed_seconds"] = round(time.perf_counter() - started, 1)
        return result

    context = mp.get_context("spawn")
    queue = context.Queue()
    process = context.Process(
        target=_evaluate_map_worker,
        args=(str(map_path), area_id, use_ocr, queue),
    )
    started = time.perf_counter()
    process.start()
    process.join(timeout_seconds)
    elapsed_seconds = round(time.perf_counter() - started, 1)
    if process.is_alive():
        process.terminate()
        process.join()
        return {
            "map_name": map_path.name,
            "map_path": str(map_path),
            "status": "timeout",
            "elapsed_seconds": elapsed_seconds,
        }
    payload = queue.get() if not queue.empty() else {"ok": False, "error": "worker exited without payload"}
    queue.close()
    if not payload.get("ok"):
        return {
            "map_name": map_path.name,
            "map_path": str(map_path),
            "status": "error",
            "elapsed_seconds": elapsed_seconds,
            "error": payload.get("error", "unknown error"),
        }
    result = payload["result"]
    result["status"] = "ok"
    result["elapsed_seconds"] = elapsed_seconds
    return result


def _decision_gate(results: list[dict[str, object]]) -> dict[str, object]:
    if not results:
        return {
            "sample_size": 0,
            "median_connectivity": 0.0,
            "mean_connectivity": 0.0,
            "decision": "no_data",
        }
    connectivity = [float(item["connected_pct"]) for item in results]
    median_connectivity = round(statistics.median(connectivity), 1)
    mean_connectivity = round(sum(connectivity) / len(connectivity), 1)
    if median_connectivity >= 95.0:
        decision = "ready_for_batch"
    elif median_connectivity >= 85.0:
        decision = "one_more_fix_round"
    else:
        decision = "investigate_broader_failures"
    return {
        "sample_size": len(results),
        "median_connectivity": median_connectivity,
        "mean_connectivity": mean_connectivity,
        "minimum_connectivity": round(min(connectivity), 1),
        "maximum_connectivity": round(max(connectivity), 1),
        "decision": decision,
    }


def _connectivity_histogram(results: list[dict[str, object]]) -> dict[str, int]:
    bins = {f"{lower}-{lower + 5}": 0 for lower in range(0, 100, 5)}
    for item in results:
        value = float(item["connected_pct"])
        bucket_floor = min(95, max(0, int(math.floor(value / 5.0) * 5)))
        label = f"{bucket_floor}-{bucket_floor + 5}"
        bins[label] += 1
    return bins


def _pearson_correlation(results: list[dict[str, object]], key: str) -> float | None:
    if len(results) < 2:
        return None
    xs = [float(item[key]) for item in results]
    ys = [float(item["connected_pct"]) for item in results]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return round(numerator / (denom_x * denom_y), 3)


def _summary_payload(results: list[dict[str, object]], skipped: list[dict[str, object]]) -> dict[str, object]:
    summary = _decision_gate(results)
    summary["processed_count"] = len(results)
    summary["skipped_count"] = len(skipped)
    summary["timeout_count"] = sum(1 for item in skipped if item.get("status") == "timeout")
    summary["error_count"] = sum(1 for item in skipped if item.get("status") == "error")
    summary["connectivity_histogram"] = _connectivity_histogram(results)
    summary["correlations"] = {
        "rooms_vs_connectivity": _pearson_correlation(results, "rooms"),
        "file_size_vs_connectivity": _pearson_correlation(results, "file_size_bytes"),
        "dark_ratio_vs_connectivity": _pearson_correlation(results, "dark_ratio"),
    }
    return summary


def _default_area_id(map_path: Path) -> str:
    stem = map_path.stem.lower().replace(" ", "_").replace("-", "_")
    return f"validation_{stem}"


def _resolve_map_paths(args: argparse.Namespace) -> list[Path]:
    explicit_paths = [Path(item).expanduser() for item in args.maps]
    resolved = explicit_paths if explicit_paths else (sorted(ROOT.glob(args.glob)) if args.glob else [])
    if not args.name_regex:
        return resolved
    pattern = re.compile(args.name_regex, re.IGNORECASE)
    return [path for path in resolved if pattern.fullmatch(path.name)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AreaForge V2 connectivity validation across a map sample.")
    parser.add_argument("maps", nargs="*", help="Explicit map paths to evaluate.")
    parser.add_argument("--glob", default="", help="Workspace-relative glob for sample maps, for example maps/ranik/*.{gif,png}.")
    parser.add_argument("--name-regex", default="", help="Optional case-insensitive filename regex filter applied after glob/path resolution.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Path to write the JSON summary report.")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR during extraction.")
    parser.add_argument("--timeout-seconds", type=float, default=0.0, help="Optional per-map timeout. Timed out maps are skipped and reported.")
    args = parser.parse_args()

    map_paths = _resolve_map_paths(args)
    if not map_paths:
        print("No map paths resolved. Provide explicit paths or --glob.")
        return 1

    results = []
    skipped = []
    for map_path in map_paths:
        if not map_path.is_absolute():
            map_path = (ROOT / map_path).resolve()
        if not map_path.exists():
            print(f"Missing map: {map_path}")
            return 1
        result = _evaluate_map_with_timeout(
            map_path,
            _default_area_id(map_path),
            use_ocr=not args.no_ocr,
            timeout_seconds=args.timeout_seconds,
        )
        if result.get("status") == "ok":
            results.append(result)
            print(
                f"{result['map_path']}: rooms={result['rooms']} isolated={result['isolated_rooms']} "
                f"largest_component={result['largest_component']} connected={result['connected_pct']}% "
                f"elapsed={result['elapsed_seconds']}s"
            )
            continue
        skipped.append(result)
        if result.get("status") == "timeout":
            print(f"{result['map_path']}: timed out after {result['elapsed_seconds']}s")
        else:
            print(f"{result['map_path']}: failed after {result['elapsed_seconds']}s error={result.get('error')}")

    summary = {
        "results": results,
        "skipped": skipped,
        "summary": _summary_payload(results, skipped),
    }
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["summary"], indent=2))
    print(f"Wrote report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())