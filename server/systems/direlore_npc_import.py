from __future__ import annotations

from datetime import date
import math
import re
from collections import defaultdict

from world.systems.canon_seed import connect_direlore

from . import npc_loader


DEFAULT_IMPORT_LIMIT = 200
NOISE_NAME_PATTERNS = (
    re.compile(r"^test\b", re.IGNORECASE),
    re.compile(r"\bdebug\b", re.IGNORECASE),
)
MESSAGE_PREFIX_RE = re.compile(r"^[A-Za-z0-9_ -]+:\s*")
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def normalize_import_npc_id(name: str) -> str:
    text = str(name or "").strip().lower()
    text = NON_ALNUM_RE.sub("_", text)
    return text.strip("_")


def normalize_loot_candidate_id(item_name: str) -> str:
    text = re.sub(r"\s*\(\d+\)\s*$", "", str(item_name or "").strip())
    text = NON_ALNUM_RE.sub("_", text.lower())
    return text.strip("_")


def should_skip_npc_row(row: dict) -> bool:
    name = str((row or {}).get("name") or "").strip()
    if not name:
        return True
    lowered = name.lower()
    if lowered in {"unknown", "placeholder"}:
        return True
    return any(pattern.search(name) for pattern in NOISE_NAME_PATTERNS)


def classify_npc_type(row: dict) -> str:
    npc_type = str((row or {}).get("npc_type") or "").strip().lower()
    if npc_type == "passive":
        return "neutral"
    if npc_type == "humanoid":
        return "neutral"
    return "hostile"


def derive_stats(row: dict) -> dict:
    level = max(1, int((row or {}).get("level") or 1))
    return {
        "level": level,
        "health": max(1, level * 10),
        "attack": max(1, int(math.ceil(level * 0.6))),
        "defense": max(0, int(math.ceil(level * 0.45))),
    }


def _article_for(name: str) -> str:
    stripped = str(name or "").strip().lower()
    if not stripped:
        return "a"
    return "an" if stripped[0] in "aeiou" else "a"


def _clean_message_text(text: str) -> str:
    cleaned = MESSAGE_PREFIX_RE.sub("", str(text or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def build_description(name: str) -> dict:
    lowered = str(name or "").strip().lower()
    article = _article_for(lowered)
    return {
        "short": f"{article} {lowered}".strip(),
        "long": f"{str(name or '').strip()} is here.",
    }


def build_dialogue_payload(messages: list[dict]) -> dict:
    idle_lines = []
    for message in list(messages or []):
        if str(message.get("message_type") or "").strip().lower() != "ambient":
            continue
        cleaned = _clean_message_text(message.get("message_text") or "")
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered.startswith("death") or lowered.startswith("decay") or lowered.startswith("searching"):
            continue
        if cleaned not in idle_lines:
            idle_lines.append(cleaned)
        if len(idle_lines) >= 3:
            break
    return {
        "greeting": "",
        "idle": idle_lines,
    }


def interpret_npc(row: dict, facts: list[dict] | None = None, messaging: list[dict] | None = None) -> dict:
    name = str((row or {}).get("name") or "").strip()
    npc_type = classify_npc_type(row)
    return {
        "id": normalize_import_npc_id(name),
        "name": name,
        "type": npc_type,
        "stats": derive_stats(row),
        "behavior": {
            "aggressive": npc_type == "hostile",
            "roam": False,
            "assist": False,
        },
        "vendor": {
            "enabled": False,
            "inventory": [],
        },
        "dialogue": build_dialogue_payload(messaging or []),
        "description": build_description(name),
        "meta": {
            "source": "direlore",
            "imported_at": date.today().isoformat(),
        },
    }


def build_npc_payload(row: dict, messages: list[dict] | None = None) -> dict:
    return interpret_npc(row, messaging=messages)


def fetch_canon_npcs(limit: int = DEFAULT_IMPORT_LIMIT) -> list[dict]:
    with connect_direlore() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, level, npc_type, attack_range, located, lifecycle_status
                FROM canon_npcs
                WHERE COALESCE(name, '') <> ''
                ORDER BY id
                LIMIT %s
                """,
                (max(1, int(limit or DEFAULT_IMPORT_LIMIT)),),
            )
            return list(cur.fetchall())


def fetch_npc_messages(npc_ids: list[int]) -> dict[int, list[dict]]:
    if not npc_ids:
        return {}
    grouped: dict[int, list[dict]] = defaultdict(list)
    with connect_direlore() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT npc_id, message_type, message_text, confidence
                FROM canon_npc_messaging
                WHERE npc_id = ANY(%s)
                ORDER BY npc_id, id
                """,
                (npc_ids,),
            )
            for row in cur.fetchall():
                grouped[int(row["npc_id"])] .append(dict(row))
    return dict(grouped)


def fetch_npc_loot_candidates(npc_ids: list[int]) -> dict[int, list[str]]:
    if not npc_ids:
        return {}
    grouped: dict[int, list[str]] = defaultdict(list)
    with connect_direlore() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT npc_id, item_name
                FROM canon_npc_loot
                WHERE npc_id = ANY(%s)
                ORDER BY npc_id, id
                """,
                (npc_ids,),
            )
            for row in cur.fetchall():
                normalized = normalize_loot_candidate_id(row["item_name"])
                if normalized and normalized not in grouped[int(row["npc_id"])]:
                    grouped[int(row["npc_id"])] .append(normalized)
    return dict(grouped)


def import_direlore_npcs(*, limit: int = DEFAULT_IMPORT_LIMIT, dry_run: bool = True, overwrite: bool = False) -> dict:
    rows = fetch_canon_npcs(limit=limit)
    messages_by_npc = fetch_npc_messages([int(row["id"]) for row in rows])
    loot_by_npc = fetch_npc_loot_candidates([int(row["id"]) for row in rows])
    existing_ids = set(npc_loader.load_all_npcs().keys()) if not dry_run else set()

    summary = {
        "selected": len(rows),
        "imported": 0,
        "skipped_existing": 0,
        "skipped_invalid": 0,
        "loot_candidates": 0,
        "missing": {
            "descriptions": 0,
            "aggression_flags": 0,
            "loot": 0,
        },
        "npcs": [],
    }

    for row in rows:
        if should_skip_npc_row(row):
            summary["skipped_invalid"] += 1
            continue

        payload = interpret_npc(row, messaging=messages_by_npc.get(int(row["id"]), []))
        loot_candidates = loot_by_npc.get(int(row["id"]), [])
        summary["loot_candidates"] += len(loot_candidates)
        if not str((row or {}).get("located") or "").strip():
            summary["missing"]["descriptions"] += 1
        if row.get("npc_type") not in {"creature", "passive", "humanoid"}:
            summary["missing"]["aggression_flags"] += 1
        if not loot_candidates:
            summary["missing"]["loot"] += 1

        if not dry_run and payload["id"] in existing_ids and not overwrite:
            summary["skipped_existing"] += 1
            continue

        if not dry_run:
            npc_loader.save_npc_payload(payload)
            existing_ids.add(payload["id"])

        summary["imported"] += 1
        summary["npcs"].append(
            {
                "id": payload["id"],
                "name": payload["name"],
                "type": payload["type"],
                "level": payload["stats"]["level"],
                "source": payload["meta"]["source"],
                "loot_candidates": loot_candidates,
            }
        )

    processed = max(1, summary["imported"] + summary["skipped_existing"])
    summary["missing_percent"] = {
        key: round((value / processed) * 100.0, 1)
        for key, value in summary["missing"].items()
    }

    return summary