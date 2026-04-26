from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Awaitable, Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


PhraseList = list[tuple[str, int]]
GeneratorCallable = Callable[..., Awaitable[Any]]
EXPLICIT_REPETITION_PHRASES = (
    "in the heart of",
    "the air is",
    "the air is thick with",
)
FABRICATION_FLAG_TERMS = (
    "lantern",
    "tower",
    "staircase",
    "door",
    "window",
    "stairs",
    "hall",
    "chamber",
    "corridor",
    "gate",
    "arch",
    "mist",
    "fog",
    "cobweb",
    "peaks",
    "forest",
    "ruins",
)
GEOMETRY_FLAG_TERMS = (
    "slopes",
    "rises",
    "falls",
    "curves",
    "bends",
    "tilts",
)
SENTENCE_START_PATTERNS = (
    "the room is",
    "the walls are",
    "the floor is",
)
MAX_DESCRIPTION_WORDS = 80
DEAD_OUTPUT_PATTERNS = (
    r"^enclosed room, no exits\.?$",
    r"^no exits\.?$",
    r"^plain space\.?$",
    r"^dead end\.?$",
)


@dataclass(frozen=True)
class SampleDescription:
    zone_id: str
    zone_name: str
    room_id: str
    room_name: str
    text: str | None
    error: str | None
    provenance: dict[str, Any]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate room description samples for manual quality review.")
    parser.add_argument("--zones", required=True, help="Comma-separated zone ids, for example harbor_district,temple_quarter")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of rooms to sample across all zones.")
    parser.add_argument("--max-tokens", type=int, default=140, help="Max tokens per generation call.")
    parser.add_argument("--output", help="Optional explicit export path. Defaults to exports/sample_descriptions_<timestamp>.txt")
    return parser.parse_args(argv)


def setup_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")

    import django

    django.setup()

    import evennia

    if not bool(getattr(evennia, "_LOADED", False)):
        evennia._init()


def _normalize_zone_ids(raw_value: str) -> list[str]:
    seen: set[str] = set()
    zone_ids: list[str] = []
    for item in str(raw_value or "").split(","):
        zone_id = item.strip()
        if not zone_id or zone_id in seen:
            continue
        seen.add(zone_id)
        zone_ids.append(zone_id)
    if not zone_ids:
        raise ValueError("At least one zone id is required.")
    return zone_ids


def prepare_zone_yaml_for_generation(raw_data: dict[str, Any] | None) -> dict[str, Any]:
    normalized = dict(raw_data or {})
    normalized.setdefault("placements", {"npcs": [], "items": []})
    return normalized


def resolve_zone_id(requested_zone_id: str, raw_data: dict[str, Any]) -> str:
    yaml_zone_id = str((raw_data or {}).get("zone_id") or "").strip()
    return yaml_zone_id or str(requested_zone_id or "").strip()


def build_llm_client(llm_config: Any, client_class: Callable[..., Any] | None = None):
    if client_class is None:
        from world.builder.services.llm_client import LocalLLMClient

        client_class = LocalLLMClient

    return client_class(
        base_url=getattr(llm_config, "llm_base_url", None),
        model=getattr(llm_config, "llm_model", None),
    )


def normalize_sampling_llm_config(llm_config: Any) -> Any:
    temperature = float(getattr(llm_config, "llm_temperature", 0.5) or 0.5)
    if temperature > 0.7:
        temperature = 0.4
    values = dict(getattr(llm_config, "__dict__", {}) or {})
    values.update(
        {
            "llm_enabled": bool(getattr(llm_config, "llm_enabled", False)),
            "llm_base_url": getattr(llm_config, "llm_base_url", None),
            "llm_model": getattr(llm_config, "llm_model", None),
            "llm_temperature": temperature,
            "log_llm_calls": bool(getattr(llm_config, "log_llm_calls", True)),
        }
    )
    return SimpleNamespace(**values)


def load_generation_zone(zone_id: str) -> dict[str, Any]:
    from world.builder.schemas.generation_context_schema import normalize_generation_context
    from world.worlddata.services.import_zone_service import _build_import_plan, _load_zone_yaml

    requested_zone_id = str(zone_id or "").strip()
    if not requested_zone_id:
        raise ValueError("zone_id is required.")

    raw_data = prepare_zone_yaml_for_generation(_load_zone_yaml(requested_zone_id))
    normalized_zone_id = resolve_zone_id(requested_zone_id, raw_data)
    plan = _build_import_plan(normalized_zone_id, raw_data)
    return {
        "zone_id": normalized_zone_id,
        "name": str(raw_data.get("name") or plan.get("name") or normalized_zone_id),
        "generation_context": normalize_generation_context(raw_data.get("generation_context")),
        "rooms": list(plan.get("rooms") or []),
        "warnings": list(plan.get("warnings") or []),
    }


def iter_sample_targets(zones: list[dict[str, Any]], limit: int) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    remaining = max(0, int(limit or 0))
    targets: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for zone in zones:
        for room in list(zone.get("rooms") or []):
            if remaining <= 0:
                return targets
            targets.append((zone, room))
            remaining -= 1
    return targets


async def generate_samples(
    zone_ids: list[str],
    *,
    limit: int,
    max_tokens: int = 140,
    zone_loader: Callable[[str], dict[str, Any]] = load_generation_zone,
    config_loader: Callable[[], Any] | None = None,
    client_factory: Callable[[Any], Any] | None = None,
    generator: GeneratorCallable | None = None,
) -> tuple[list[SampleDescription], list[dict[str, Any]]]:
    if limit <= 0:
        return [], []

    if config_loader is None:
        from world.builder.services.llm_client import load_llm_config

        config_loader = load_llm_config
    if client_factory is None:
        client_factory = build_llm_client
    if generator is None:
        from world.builder.prompting.room_description_generation import generate_room_description

        generator = generate_room_description

    zones = [zone_loader(zone_id) for zone_id in zone_ids]
    targets = iter_sample_targets(zones, limit)

    llm_config = normalize_sampling_llm_config(config_loader())
    client = client_factory(llm_config) if client_factory is not None else None

    samples: list[SampleDescription] = []
    for zone, room in targets:
        result = await generator(room, zone, client=client, llm_config=llm_config, max_tokens=max_tokens)
        samples.append(
            SampleDescription(
                zone_id=str(zone.get("zone_id") or ""),
                zone_name=str(zone.get("name") or zone.get("zone_id") or "Unknown Zone"),
                room_id=str(room.get("id") or ""),
                room_name=str(room.get("name") or room.get("id") or "Unnamed Room"),
                text=str(getattr(result, "text", None) or "").strip() or None,
                error=str(getattr(result, "error", None) or "").strip() or None,
                provenance=dict(getattr(result, "provenance", {}) or {}),
            )
        )
    return samples, zones


def prepare_generation_runtime(
    zone_ids: list[str],
    *,
    zone_loader: Callable[[str], dict[str, Any]] = load_generation_zone,
    config_loader: Callable[[], Any] | None = None,
    client_factory: Callable[[Any], Any] | None = None,
) -> tuple[list[dict[str, Any]], Any, Any]:
    if config_loader is None:
        from world.builder.services.llm_client import load_llm_config

        config_loader = load_llm_config
    if client_factory is None:
        client_factory = build_llm_client

    zones = [zone_loader(zone_id) for zone_id in zone_ids]
    llm_config = normalize_sampling_llm_config(config_loader())
    client = client_factory(llm_config) if client_factory is not None else None
    return zones, llm_config, client


async def generate_samples_from_runtime(
    zones: list[dict[str, Any]],
    *,
    llm_config: Any,
    client: Any,
    limit: int,
    max_tokens: int = 140,
    generator: GeneratorCallable | None = None,
) -> list[SampleDescription]:
    if limit <= 0:
        return []

    if generator is None:
        from world.builder.prompting.room_description_generation import generate_room_description

        generator = generate_room_description

    targets = iter_sample_targets(zones, limit)
    samples: list[SampleDescription] = []
    for zone, room in targets:
        result = await generator(room, zone, client=client, llm_config=llm_config, max_tokens=max_tokens)
        samples.append(
            SampleDescription(
                zone_id=str(zone.get("zone_id") or ""),
                zone_name=str(zone.get("name") or zone.get("zone_id") or "Unknown Zone"),
                room_id=str(room.get("id") or ""),
                room_name=str(room.get("name") or room.get("id") or "Unnamed Room"),
                text=str(getattr(result, "text", None) or "").strip() or None,
                error=str(getattr(result, "error", None) or "").strip() or None,
                provenance=dict(getattr(result, "provenance", {}) or {}),
            )
        )
    return samples


def _tokenize_for_phrases(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", str(text or "").lower())


def collect_repeated_phrases(
    texts: list[str],
    *,
    min_words: int = 3,
    max_words: int = 5,
    min_count: int = 2,
    limit: int = 10,
) -> PhraseList:
    counter: Counter[str] = Counter()
    for text in texts:
        tokens = _tokenize_for_phrases(text)
        seen_in_text: set[str] = set()
        for size in range(min_words, max_words + 1):
            if len(tokens) < size:
                continue
            for index in range(0, len(tokens) - size + 1):
                phrase = " ".join(tokens[index:index + size])
                if phrase in seen_in_text:
                    continue
                seen_in_text.add(phrase)
                counter[phrase] += 1

    repeated = [(phrase, count) for phrase, count in counter.items() if count >= min_count]
    repeated.sort(key=lambda item: (-item[1], -len(item[0].split()), item[0]))
    return repeated[: max(0, limit)]


def count_phrase_occurrences(texts: list[str], phrases: tuple[str, ...] = EXPLICIT_REPETITION_PHRASES) -> dict[str, int]:
    counts: dict[str, int] = {}
    normalized_texts = [str(text or "").lower() for text in texts]
    for phrase in phrases:
        counts[phrase] = sum(text.count(phrase) for text in normalized_texts)
    return counts


def count_fabrication_flags(texts: list[str], terms: tuple[str, ...] = FABRICATION_FLAG_TERMS) -> dict[str, int]:
    counts: dict[str, int] = {}
    normalized_texts = [str(text or "").lower() for text in texts]
    for term in terms:
        pattern = re.compile(rf"\b{re.escape(term)}\b")
        counts[term] = sum(len(pattern.findall(text)) for text in normalized_texts)
    return counts


def count_geometry_flags(texts: list[str], terms: tuple[str, ...] = GEOMETRY_FLAG_TERMS) -> dict[str, int]:
    counts: dict[str, int] = {}
    normalized_texts = [str(text or "").lower() for text in texts]
    for term in terms:
        pattern = re.compile(rf"\b{re.escape(term)}\b")
        counts[term] = sum(len(pattern.findall(text)) for text in normalized_texts)
    return counts


def word_count(text: str) -> int:
    return len(_tokenize_for_phrases(text))


def count_length_flags(texts: list[str], max_words: int = MAX_DESCRIPTION_WORDS) -> int:
    return sum(1 for text in texts if word_count(text) > max_words)


def sentence_count(text: str) -> int:
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+", str(text or "").strip()) if chunk.strip()]
    return len(chunks)


def average_sentence_count(texts: list[str]) -> float:
    if not texts:
        return 0.0
    return sum(sentence_count(text) for text in texts) / len(texts)


def count_sentence_flags(texts: list[str], minimum: int = 3, maximum: int = 5) -> int:
    return sum(1 for text in texts if sentence_count(text) < minimum or sentence_count(text) > maximum)


def count_dead_outputs(texts: list[str], patterns: tuple[str, ...] = DEAD_OUTPUT_PATTERNS) -> int:
    total = 0
    for text in texts:
        normalized = str(text or "").strip().lower()
        if any(re.fullmatch(pattern, normalized) for pattern in patterns):
            total += 1
    return total


def count_repeated_sentence_starts(texts: list[str], starts: tuple[str, ...] = SENTENCE_START_PATTERNS) -> dict[str, int]:
    counts = {start: 0 for start in starts}
    for text in texts:
        for chunk in re.split(r"(?<=[.!?])\s+", str(text or "").strip()):
            sentence = chunk.strip().lower()
            if not sentence:
                continue
            for start in starts:
                if sentence.startswith(start):
                    counts[start] += 1
    return counts


def average_word_count(texts: list[str]) -> float:
    if not texts:
        return 0.0
    return sum(word_count(text) for text in texts) / len(texts)


def build_evaluation_counts(samples: list[SampleDescription]) -> dict[str, Any]:
    texts = [sample.text for sample in samples if sample.text]
    fabrication_counts = count_fabrication_flags(texts)
    geometry_counts = count_geometry_flags(texts)
    sentence_start_counts = count_repeated_sentence_starts(texts)
    return {
        "explicit_repetition": count_phrase_occurrences(texts),
        "fabrication_flags": fabrication_counts,
        "noun_violations": sum(fabrication_counts.values()),
        "geometry_flags": geometry_counts,
        "geometry_violations": sum(geometry_counts.values()),
        "over_80_words": count_length_flags(texts),
        "average_words": round(average_word_count(texts), 2),
        "sentence_count_flags": count_sentence_flags(texts),
        "average_sentences": round(average_sentence_count(texts), 2),
        "dead_outputs": count_dead_outputs(texts),
        "repeated_sentence_starts": sentence_start_counts,
        "repeated_sentence_start_total": sum(sentence_start_counts.values()),
    }


def format_stdout_sample(sample: SampleDescription) -> str:
    body = sample.text or f"[ERROR] {sample.error or 'Generation returned no text.'}"
    return f"[Zone: {sample.zone_name} | Room: {sample.room_id}]\n{body}\n\n---"


def format_export(samples: list[SampleDescription], repeated_phrases: PhraseList, evaluation_counts: dict[str, Any] | None = None) -> str:
    evaluation_counts = evaluation_counts or build_evaluation_counts(samples)
    lines: list[str] = []
    current_zone_id: str | None = None
    for sample in samples:
        if sample.zone_id != current_zone_id:
            if lines:
                lines.append("")
            lines.append(f"=== Zone: {sample.zone_name} ===")
            lines.append("")
            current_zone_id = sample.zone_id
        lines.append(f"[Room: {sample.room_id}]")
        lines.append(sample.text or f"[ERROR] {sample.error or 'Generation returned no text.'}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("Repeated phrases:")
    if repeated_phrases:
        for phrase, count in repeated_phrases:
            lines.append(f"- \"{phrase}\" ({count})")
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Evaluation counts:")
    lines.append("Explicit repetition:")
    for phrase, count in dict(evaluation_counts.get("explicit_repetition") or {}).items():
        lines.append(f"- \"{phrase}\": {count}")
    lines.append("Fabrication flags:")
    for term, count in dict(evaluation_counts.get("fabrication_flags") or {}).items():
        lines.append(f"- \"{term}\": {count}")
    lines.append(f"Noun violations: {int(evaluation_counts.get('noun_violations') or 0)}")
    lines.append("Geometry flags:")
    for term, count in dict(evaluation_counts.get("geometry_flags") or {}).items():
        lines.append(f"- \"{term}\": {count}")
    lines.append(f"Geometry violations: {int(evaluation_counts.get('geometry_violations') or 0)}")
    lines.append(f"Over 80 words: {int(evaluation_counts.get('over_80_words') or 0)}")
    lines.append(f"Average words: {float(evaluation_counts.get('average_words') or 0.0):.2f}")
    lines.append(f"Sentence count flags: {int(evaluation_counts.get('sentence_count_flags') or 0)}")
    lines.append(f"Average sentences: {float(evaluation_counts.get('average_sentences') or 0.0):.2f}")
    lines.append(f"Dead outputs: {int(evaluation_counts.get('dead_outputs') or 0)}")
    lines.append("Repeated sentence starts:")
    for start, count in dict(evaluation_counts.get("repeated_sentence_starts") or {}).items():
        lines.append(f"- \"{start}\": {count}")
    lines.append(f"Repeated sentence start total: {int(evaluation_counts.get('repeated_sentence_start_total') or 0)}")
    return "\n".join(lines).rstrip() + "\n"


def default_export_path(now: datetime | None = None) -> Path:
    timestamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / "exports" / f"sample_descriptions_{timestamp}.txt"


def write_export(content: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return output_path


async def _async_main(argv: list[str] | None = None) -> int:
    raise RuntimeError("_async_main is no longer used.")

    for sample in samples:
        print(format_stdout_sample(sample))
        print()

    repeated_phrases = collect_repeated_phrases([sample.text for sample in samples if sample.text])
    print("Repeated phrases:")
    if repeated_phrases:
        for phrase, count in repeated_phrases:
            print(f'- "{phrase}" ({count})')
    else:
        print("- none")

    output_path = Path(args.output) if args.output else default_export_path()
    export_path = write_export(format_export(samples, repeated_phrases), output_path)
    print()
    print(f"Export written to {export_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(argv)
        zone_ids = _normalize_zone_ids(args.zones)
        if args.limit <= 0:
            raise ValueError("--limit must be greater than 0.")

        setup_django()
        zones, llm_config, client = prepare_generation_runtime(zone_ids)
        samples = asyncio.run(
            generate_samples_from_runtime(
                zones,
                llm_config=llm_config,
                client=client,
                limit=args.limit,
                max_tokens=args.max_tokens,
            )
        )

        for sample in samples:
            print(format_stdout_sample(sample))
            print()

        repeated_phrases = collect_repeated_phrases([sample.text for sample in samples if sample.text])
        evaluation_counts = build_evaluation_counts(samples)
        print("Repeated phrases:")
        if repeated_phrases:
            for phrase, count in repeated_phrases:
                print(f'- "{phrase}" ({count})')
        else:
            print("- none")
        print("Evaluation counts:")
        print("Explicit repetition:")
        for phrase, count in dict(evaluation_counts.get("explicit_repetition") or {}).items():
            print(f'- "{phrase}": {count}')
        print("Fabrication flags:")
        for term, count in dict(evaluation_counts.get("fabrication_flags") or {}).items():
            print(f'- "{term}": {count}')
        print(f"Noun violations: {int(evaluation_counts.get('noun_violations') or 0)}")
        print("Geometry flags:")
        for term, count in dict(evaluation_counts.get("geometry_flags") or {}).items():
            print(f'- "{term}": {count}')
        print(f"Geometry violations: {int(evaluation_counts.get('geometry_violations') or 0)}")
        print(f"Over 80 words: {int(evaluation_counts.get('over_80_words') or 0)}")
        print(f"Average words: {float(evaluation_counts.get('average_words') or 0.0):.2f}")
        print(f"Sentence count flags: {int(evaluation_counts.get('sentence_count_flags') or 0)}")
        print(f"Average sentences: {float(evaluation_counts.get('average_sentences') or 0.0):.2f}")
        print(f"Dead outputs: {int(evaluation_counts.get('dead_outputs') or 0)}")
        print("Repeated sentence starts:")
        for start, count in dict(evaluation_counts.get("repeated_sentence_starts") or {}).items():
            print(f'- "{start}": {count}')
        print(f"Repeated sentence start total: {int(evaluation_counts.get('repeated_sentence_start_total') or 0)}")

        output_path = Path(args.output) if args.output else default_export_path()
        export_path = write_export(format_export(samples, repeated_phrases, evaluation_counts), output_path)
        print()
        print(f"Export written to {export_path}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())