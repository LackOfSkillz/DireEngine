from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_FAILURE = 2
EXIT_COST_ABORT = 3
DEFAULT_COST_CEILING_USD = 5.0
OBSERVED_GENERATION_COST_CEILING_USD = 0.018


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run live orchestrator phase verification against a fixture zone.")
    parser.add_argument("--fixture", required=True, help="Path to the fixture YAML relative to repo root or absolute.")
    parser.add_argument("--phase", required=True, type=int, help="Target orchestrator phase to run (currently 1-4).")
    parser.add_argument("--cost-ceiling", type=float, default=DEFAULT_COST_CEILING_USD, help="Abort if projected cost exceeds this USD ceiling.")
    parser.add_argument("--output", default="exports", help="Directory for markdown validation reports.")
    parser.add_argument("--write-back", action="store_true", help="Write successful phase results back into the source YAML.")
    return parser.parse_args()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return (_repo_root() / candidate).resolve()


def _bootstrap_django() -> None:
    repo_root = str(_repo_root())
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()


def _ensure_api_key() -> None:
    if not str(os.getenv("ANTHROPIC_API_KEY") or "").strip():
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Live verification requires a real Anthropic key in the environment.")


def _phase_method_name(phase: int) -> str:
    mapping = {
        1: "run_phase_1_zone_type_setup",
        2: "run_phase_2_geographic_structure",
        3: "run_phase_3_room_descriptions",
        4: "run_phase_4_stateful_descriptions",
    }
    if phase not in mapping:
        raise ValueError(f"Unsupported phase {phase}. Supported phases are: {', '.join(str(key) for key in sorted(mapping))}.")
    return mapping[phase]


def _estimate_phase_cost(orchestrator: Any, phase: int) -> tuple[int, float, str]:
    orchestrator.load_zone()
    if phase == 1:
        return 0, 0.0, "Phase 1 has no AI generation cost."
    orchestrator.run_phase_1_zone_type_setup()
    if phase == 2:
        return 0, 0.0, "Phase 2 has no AI generation cost."
    orchestrator.run_phase_2_geographic_structure()
    if phase == 3:
        plans = orchestrator.dry_run_plan()
        phase_plan = next((plan for plan in plans if int(plan.phase_number) == 3), None)
        actions = int(getattr(phase_plan, "estimated_actions", 0) or 0)
        cost = float(getattr(phase_plan, "estimated_cost_usd", 0.0) or 0.0)
        return actions, cost, "Projected from orchestrator dry-run Phase 3 estimate."

    stateful_variants = 0
    for room in list(orchestrator.working_state.get("rooms") or []):
        if not isinstance(room, dict):
            continue
        pending = [
            target
            for target in orchestrator._phase_4_target_states(room)
            if not str(dict(room.get("stateful_descs") or {}).get(target["state_key"]) or "").strip()
        ]
        stateful_variants += len(pending)
    projected_cost = round(stateful_variants * OBSERVED_GENERATION_COST_CEILING_USD, 6)
    return stateful_variants, projected_cost, "Projected conservatively from pending Phase 4 variants at $0.018 per generation."


def _collect_generated_content(phase: int, working_state: dict[str, Any]) -> list[dict[str, Any]]:
    rooms = [room for room in list(working_state.get("rooms") or []) if isinstance(room, dict)]
    content: list[dict[str, Any]] = []
    for room in rooms:
        room_id = str(room.get("id") or room.get("name") or "").strip()
        if not room_id:
            continue
        if phase == 3:
            description = str(room.get("desc") or "").strip()
            if not description:
                continue
            content.append({"room_id": room_id, "name": room.get("name"), "desc": description})
        elif phase == 4:
            stateful_descs = {
                str(key or "").strip(): str(value or "")
                for key, value in dict(room.get("stateful_descs") or {}).items()
                if str(key or "").strip() and str(value or "").strip()
            }
            if not stateful_descs:
                continue
            content.append({"room_id": room_id, "name": room.get("name"), "stateful_descs": stateful_descs})
    return content


def _write_report(
    *,
    output_dir: Path,
    phase: int,
    fixture_path: Path,
    phase_result: Any,
    generated_content: list[dict[str, Any]],
    projected_actions: int,
    projected_cost_usd: float,
    projection_note: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"orchestrator_live_verify_phase_{phase}_{timestamp}.md"

    changes = dict(getattr(phase_result, "changes", {}) or {})
    report_lines = [
        f"# Orchestrator Live Verify Phase {phase}",
        "",
        f"Generated at: `{timestamp}`",
        f"Fixture: `{fixture_path}`",
        f"Phase name: `{getattr(phase_result, 'phase_name', '')}`",
        f"Status: `{getattr(phase_result, 'status', '')}`",
        "",
        "## Projection",
        "",
        f"- Projected actions: `{projected_actions}`",
        f"- Projected cost ceiling estimate: `${projected_cost_usd:.6f}`",
        f"- Projection note: {projection_note}",
        "",
        "## Result",
        "",
        f"- rooms_succeeded: `{json.dumps(list(getattr(phase_result, 'rooms_succeeded', []) or []))}`",
        f"- rooms_failed: `{json.dumps(list(getattr(phase_result, 'rooms_failed', []) or []))}`",
        f"- states_succeeded: `{json.dumps(list(getattr(phase_result, 'states_succeeded', []) or []))}`",
        f"- duration_ms: `{int(getattr(phase_result, 'duration_ms', 0) or 0)}`",
        f"- actual_cost_usd: `{changes.get('approximate_cost_usd', 0.0)}`",
        f"- input_tokens: `{changes.get('input_tokens', 0)}`",
        f"- output_tokens: `{changes.get('output_tokens', 0)}`",
        f"- checkpoint_path: `{getattr(phase_result, 'checkpoint_path', '')}`",
        "",
        "## Prompt Contexts",
        "",
        "```json",
        json.dumps(changes.get("prompt_contexts", []), indent=2, sort_keys=True),
        "```",
        "",
        "## Generated Outputs",
        "",
        "```json",
        json.dumps(changes.get("generated_outputs", []), indent=2, sort_keys=True),
        "```",
        "",
        "## Full Generated Content Per Room",
        "",
        "```json",
        json.dumps(generated_content, indent=2, sort_keys=True),
        "```",
        "",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    return report_path


def _run_to_phase(orchestrator: Any, phase: int) -> Any:
    orchestrator.load_zone()
    result = None
    for current in range(1, phase + 1):
        method_name = _phase_method_name(current)
        result = getattr(orchestrator, method_name)()
    if result is None:
        raise RuntimeError(f"No phase result returned for phase {phase}.")
    return result


def _exit_code_for_status(status: str) -> int:
    normalized = str(status or "").strip().lower()
    if normalized == "success":
        return EXIT_SUCCESS
    if normalized == "partial-success":
        return EXIT_PARTIAL
    return EXIT_FAILURE


def _write_back_working_state(orchestrator: Any, fixture_path: Path, phase_result: Any) -> Path:
    working_state = dict(getattr(orchestrator, "working_state", {}) or {})
    if working_state:
        fixture_path.write_text(yaml.safe_dump(working_state, sort_keys=False), encoding="utf-8")
        return fixture_path

    checkpoint_path = Path(str(getattr(phase_result, "checkpoint_path", "") or "").strip())
    if checkpoint_path.exists():
        fixture_path.write_text(checkpoint_path.read_text(encoding="utf-8"), encoding="utf-8")
        return checkpoint_path

    raise RuntimeError("Write-back requested, but neither orchestrator working_state nor checkpoint content was available.")


def main() -> int:
    args = _parse_args()
    fixture_path = _resolve_path(args.fixture)
    output_dir = _resolve_path(args.output)
    if not fixture_path.exists():
        print(f"ERROR: Fixture not found: {fixture_path}", file=sys.stderr)
        return EXIT_FAILURE

    try:
        _ensure_api_key()
        _bootstrap_django()
        from world.builder.orchestration.zone_orchestrator import ZoneOrchestrator

        probe = ZoneOrchestrator(fixture_path, checkpoint_dir=output_dir / "orchestrator_live_verify_checkpoints")
        projected_actions, projected_cost_usd, projection_note = _estimate_phase_cost(probe, args.phase)
        print(f"Projected actions: {projected_actions}")
        print(f"Projected cost estimate: ${projected_cost_usd:.6f}")
        print(f"Projection note: {projection_note}")
        if projected_cost_usd > float(args.cost_ceiling):
            print(
                f"ABORT: projected cost ${projected_cost_usd:.6f} exceeds ceiling ${float(args.cost_ceiling):.6f}",
                file=sys.stderr,
            )
            return EXIT_COST_ABORT

        checkpoint_dir = output_dir / "orchestrator_live_verify_checkpoints"
        orchestrator = ZoneOrchestrator(fixture_path, checkpoint_dir=checkpoint_dir)
        phase_result = _run_to_phase(orchestrator, args.phase)
        generated_content = _collect_generated_content(args.phase, orchestrator.working_state or {})
        report_path = _write_report(
            output_dir=output_dir,
            phase=args.phase,
            fixture_path=fixture_path,
            phase_result=phase_result,
            generated_content=generated_content,
            projected_actions=projected_actions,
            projected_cost_usd=projected_cost_usd,
            projection_note=projection_note,
        )
        if args.write_back and str(getattr(phase_result, "status", "")).strip().lower() == "success":
            write_back_source = _write_back_working_state(orchestrator, fixture_path, phase_result)
            print(f"Write-back completed: {fixture_path}")
            if write_back_source != fixture_path:
                print(f"Write-back source: {write_back_source}")
        print(f"Report written: {report_path}")
        print(f"Status: {phase_result.status}")
        return _exit_code_for_status(getattr(phase_result, "status", "failure"))
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return EXIT_FAILURE


if __name__ == "__main__":
    raise SystemExit(main())