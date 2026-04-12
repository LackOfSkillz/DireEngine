import json
import re
from collections import Counter, defaultdict

import psycopg
from psycopg.rows import dict_row

from django.db import connection

from world.systems import canon_normalize


DIRELORE_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "user",
    "password": "pass",
    "dbname": "direlore",
}

ITEM_CATEGORIES = ("weapon", "armor", "container", "clothing")
ACTOR_CATEGORIES = ("shopkeeper", "guard", "civilian", "hostile_creature", "docile_creature")
ALL_CATEGORIES = (*ITEM_CATEGORIES, *ACTOR_CATEGORIES)

NOISE_PREFIXES = (
    "post:",
    "pages that link to",
    "category:",
    "[[post",
    "weapon:",
    "armor:",
)

AUDIT_RULES = {
    "weapon": {
        "critical": ("name",),
        "important": ("damage_profile",),
        "optional": ("value_text",),
    },
    "armor": {
        "critical": ("name",),
        "important": ("protection_profile", "weight"),
        "optional": (),
    },
    "container": {
        "critical": ("name",),
        "important": ("capacity",),
        "optional": ("slot",),
    },
    "clothing": {
        "critical": ("name",),
        "important": ("allowed_slots",),
        "optional": ("value_text",),
    },
    "shopkeeper": {
        "critical": ("name", "role"),
        "important": ("shop_name",),
        "optional": (),
    },
    "guard": {
        "critical": ("name", "role", "aggression_type"),
        "important": (),
        "optional": ("base_health",),
    },
    "civilian": {
        "critical": ("name", "role"),
        "important": (),
        "optional": ("base_health",),
    },
    "hostile_creature": {
        "critical": ("name", "aggression_type"),
        "important": (),
        "optional": ("base_health",),
    },
    "docile_creature": {
        "critical": ("name", "aggression_type"),
        "important": ("flee_behavior",),
        "optional": ("base_health",),
    },
}

FETCHERS = {}


def connect_direlore():
    return psycopg.connect(**DIRELORE_CONFIG, row_factory=dict_row)


def ensure_canon_tables(reset=False):
    statements = (
        """
        CREATE TABLE IF NOT EXISTS canon_items (
            canonical_key TEXT PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            source_entity_id INTEGER,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            item_type TEXT,
            tags_json TEXT NOT NULL,
            value_text TEXT,
            value_num INTEGER,
            weight INTEGER,
            damage_profile_json TEXT,
            protection_profile_json TEXT,
            slot TEXT,
            capacity_json TEXT,
            restrictions_json TEXT,
            normalized_fields_json TEXT,
            raw_json TEXT NOT NULL,
            source_origin TEXT NOT NULL,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS canon_actors (
            canonical_key TEXT PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_entity_id INTEGER,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            actor_type TEXT,
            npc_type TEXT,
            aggression_type TEXT,
            flee_behavior TEXT,
            base_health INTEGER,
            level INTEGER,
            location_text TEXT,
            shop_name TEXT,
            tags_json TEXT NOT NULL,
            normalized_fields_json TEXT,
            raw_json TEXT NOT NULL,
            source_origin TEXT NOT NULL,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS canon_shops (
            canonical_key TEXT PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            source_entity_id INTEGER,
            name TEXT NOT NULL,
            shop_type TEXT,
            owner_name TEXT,
            tags_json TEXT NOT NULL,
            normalized_fields_json TEXT,
            raw_json TEXT NOT NULL,
            source_origin TEXT NOT NULL,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS canon_import_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            canonical_key TEXT NOT NULL,
            entity_category TEXT NOT NULL,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            passed INTEGER NOT NULL,
            missing_fields_json TEXT NOT NULL,
            warnings_json TEXT NOT NULL,
            applied_defaults_json TEXT NOT NULL,
            normalized_fields_json TEXT NOT NULL,
            raw_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
    )
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)

    _ensure_sqlite_column("canon_items", "normalized_fields_json", "TEXT")
    _ensure_sqlite_column("canon_actors", "normalized_fields_json", "TEXT")
    _ensure_sqlite_column("canon_shops", "normalized_fields_json", "TEXT")
    _ensure_sqlite_column("canon_import_audit", "applied_defaults_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_sqlite_column("canon_import_audit", "normalized_fields_json", "TEXT NOT NULL DEFAULT '{}' ")

    if reset:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM canon_import_audit")
            cursor.execute("DELETE FROM canon_shops")
            cursor.execute("DELETE FROM canon_actors")
            cursor.execute("DELETE FROM canon_items")


def fetch_direlore_entities(entity_type, limit, filters=None):
    fetcher = FETCHERS.get(str(entity_type or "").strip().lower())
    if fetcher is None:
        raise ValueError(f"Unsupported DireLore entity type: {entity_type}")
    with connect_direlore() as conn:
        return fetcher(conn, int(limit or 20), dict(filters or {}))


def get_required_fields_by_type(entity_category):
    rules = AUDIT_RULES.get(str(entity_category or "").strip().lower(), {})
    fields = []
    for severity in ("critical", "important", "optional"):
        fields.extend(list(rules.get(severity, ())))
    return tuple(fields)


def audit_entity(entity):
    category = str((entity or {}).get("category") or "").strip().lower()
    rules = AUDIT_RULES.get(category, {})
    merged = _merge_normalized(entity)
    missing_fields = {}
    for severity in ("critical", "important", "optional"):
        missing_fields[severity] = [
            field_name
            for field_name in rules.get(severity, ())
            if _is_missing(merged.get(field_name))
        ]

    warnings = list(entity.get("normalization_warnings") or [])
    if _normalized_value(entity, "classification_confidence") is not None and _normalized_value(entity, "classification_confidence") < 0.5:
        warnings.append("low_classification_confidence")
    warnings = list(dict.fromkeys(warnings))
    return {
        "missing_fields": missing_fields,
        "warnings": warnings,
        "applied_defaults": list(entity.get("applied_defaults") or []),
        "normalized_fields": dict(entity.get("normalized_fields") or {}),
        "passed": len(missing_fields.get("critical") or []) == 0,
    }


def import_controlled_dataset(limit_per_category=20, reset=False):
    ensure_canon_tables(reset=reset)
    imported = {}
    audits = []
    normalization_counts = Counter()

    for category in ALL_CATEGORIES:
        raw_rows = fetch_direlore_entities(category, limit_per_category)
        if category in ITEM_CATEGORIES:
            records = [_apply_item_normalization(_normalize_item_record(category, row)) for row in raw_rows]
            for record in records:
                _upsert_item_record(record)
        elif category == "shopkeeper":
            shop_records = []
            actor_records = []
            for row in raw_rows:
                shop_record, actor_record = _normalize_shopkeeper_records(row)
                shop_record = _apply_shop_normalization(shop_record)
                actor_record = _apply_actor_normalization(actor_record)
                shop_records.append(shop_record)
                actor_records.append(actor_record)
            for record in shop_records:
                _upsert_shop_record(record)
            for record in actor_records:
                _upsert_actor_record(record)
            records = actor_records
        else:
            records = [_apply_actor_normalization(_normalize_actor_record(category, row)) for row in raw_rows]
            for record in records:
                _upsert_actor_record(record)

        imported[category] = len(records)
        for record in records:
            audit = audit_entity(record)
            audits.append({"category": category, "record": record, "audit": audit})
            for field_name in audit.get("applied_defaults") or []:
                normalization_counts[f"{category}.{field_name}"] += 1
            _store_audit(
                table_name=_table_name_for_category(category),
                canonical_key=record["canonical_key"],
                entity_category=category,
                source_table=str(record.get("source_table") or "unknown"),
                source_id=str(record.get("source_id") or "unknown"),
                audit=audit,
                raw_json=record.get("raw_json") or "{}",
            )

    summary = _build_summary(imported, audits, normalization_counts)
    return {
        "imported": imported,
        "summary": summary,
        "sample_failures": sample_broken_entries(limit_per_category=5),
        "audit_count": len(audits),
        "normalization_metrics": {
            "default_usage_counts": dict(sorted(normalization_counts.items())),
            "normalized_records": len(audits),
        },
    }


def generate_summary_report():
    counts = {}
    missing_counter = Counter()
    default_counter = Counter()
    with connection.cursor() as cursor:
        for table_name in ("canon_items", "canon_actors", "canon_shops", "canon_import_audit"):
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            counts[table_name] = int(cursor.fetchone()[0] or 0)

        cursor.execute(
            """
            SELECT entity_category, missing_fields_json, applied_defaults_json
            FROM canon_import_audit
            """
        )
        audit_rows = cursor.fetchall()

    for category, missing_json, defaults_json in audit_rows:
        missing_fields = _parse_json(missing_json, {})
        for severity, field_names in dict(missing_fields or {}).items():
            for field_name in field_names or []:
                missing_counter[(category, severity, field_name)] += 1
        for field_name in _parse_json(defaults_json, []):
            default_counter[(category, field_name)] += 1

    lines = [
        f"canon_items: {counts.get('canon_items', 0)}",
        f"canon_actors: {counts.get('canon_actors', 0)}",
        f"canon_shops: {counts.get('canon_shops', 0)}",
        f"canon_import_audit: {counts.get('canon_import_audit', 0)}",
    ]
    for (category, severity, field_name), total in sorted(missing_counter.items()):
        lines.append(f"{category}: {total} {severity} missing {field_name}")
    for (category, field_name), total in sorted(default_counter.items()):
        lines.append(f"{category}: {total} defaulted {field_name}")
    return lines


def sample_broken_entries(limit_per_category=5):
    samples = defaultdict(list)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT entity_category, canonical_key, missing_fields_json, warnings_json,
                   applied_defaults_json, normalized_fields_json, raw_json
            FROM canon_import_audit
            WHERE passed = 0
            ORDER BY entity_category, id
            """
        )
        for category, canonical_key, missing_json, warnings_json, defaults_json, normalized_json, raw_json in cursor.fetchall():
            if len(samples[category]) >= int(limit_per_category or 5):
                continue
            payload = _parse_json(raw_json, {})
            samples[category].append(
                {
                    "canonical_key": canonical_key,
                    "missing_fields": _parse_json(missing_json, {}),
                    "warnings": _parse_json(warnings_json, []),
                    "applied_defaults": _parse_json(defaults_json, []),
                    "normalized_fields": _parse_json(normalized_json, {}),
                    "name": payload.get("name"),
                    "source_id": payload.get("source_id"),
                }
            )
    return dict(samples)


def get_items_by_type(item_type):
    requested = str(item_type or "").strip().lower()
    items = _load_all_items()
    return [
        item
        for item in items
        if str(_normalized_value(item, "item_type") or item.get("item_type") or item.get("category") or "").strip().lower() == requested
        or str(item.get("category") or "").strip().lower() == requested
    ]


def get_actors_by_role(role):
    requested = str(role or "").strip().lower()
    actors = _load_all_actors()
    return [actor for actor in actors if str(_normalized_value(actor, "role") or actor.get("role") or "").strip().lower() == requested]


def get_creatures_by_aggression(aggression_type):
    requested = str(aggression_type or "").strip().lower()
    actors = _load_all_actors()
    return [
        actor
        for actor in actors
        if str(_normalized_value(actor, "role") or actor.get("role") or "").strip().lower() == "creature"
        and str(_normalized_value(actor, "aggression_type") or actor.get("aggression_type") or "").strip().lower() == requested
    ]


def get_guards():
    return get_actors_by_role("guard")


def get_shopkeepers():
    return get_actors_by_role("shopkeeper")


def get_hostile_creatures():
    return get_creatures_by_aggression("aggressive")


def get_docile_creatures():
    return get_creatures_by_aggression("docile")


def _ensure_sqlite_column(table_name, column_name, column_definition):
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def _fetch_rows(conn, query, params=None):
    with conn.cursor() as cursor:
        cursor.execute(query, params or [])
        return list(cursor.fetchall())


def _safe_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    return str(value)


def _extract_int(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"-?\d+", str(value))
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def _dump_json(value):
    return json.dumps(value, default=str, sort_keys=True)


def _parse_json(value, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _clean_name(name):
    text = str(name or "").strip()
    if ":" in text and text.split(":", 1)[0].lower() in {"weapon", "armor", "item"}:
        return text.split(":", 1)[1].strip()
    return text


def _is_noise_name(name):
    lowered = str(name or "").strip().lower()
    if not lowered:
        return True
    return lowered.startswith(NOISE_PREFIXES)


def _table_name_for_category(category):
    if category in ITEM_CATEGORIES:
        return "canon_items"
    return "canon_actors"


def _normalize_item_record(category, row):
    row = dict(row or {})
    damage_profile = None
    protection_profile = None
    capacity_json = row.get("capacity_json")
    restrictions_json = row.get("restrictions_json")
    slot = row.get("slot") or row.get("worn_location") or row.get("equip_slot")
    item_type = row.get("item_type")

    if category == "weapon":
        item_type = row.get("weapon_type") or item_type or "weapon"
        damage_profile = {
            "weapon_type": row.get("weapon_type"),
            "damage_type": row.get("damage_type"),
            "range": row.get("range"),
            "handedness": row.get("handedness"),
            "skill_type": row.get("skill_type"),
        }
    elif category == "armor":
        item_type = row.get("armor_type") or item_type or "armor"
        protection_profile = row.get("protection_profile") or {
            "armor_type": row.get("armor_type"),
            "hindrance": row.get("hindrance"),
            "coverage": row.get("coverage"),
        }
    elif category == "container":
        item_type = row.get("item_type") or "container"
    elif category == "clothing":
        item_type = row.get("item_type") or "clothing"

    return {
        "canonical_key": f"{category}:{row['source_table']}:{row['source_id']}",
        "category": category,
        "source_table": row["source_table"],
        "source_id": row["source_id"],
        "source_entity_id": row.get("source_entity_id"),
        "name": _clean_name(row.get("name")),
        "item_type": item_type,
        "tags": [category],
        "value_text": _safe_text(row.get("appraised_cost")),
        "value_num": _extract_int(row.get("appraised_cost")),
        "weight": row.get("weight"),
        "damage_profile": damage_profile,
        "protection_profile": protection_profile,
        "slot": _safe_text(slot),
        "capacity_json": capacity_json,
        "restrictions_json": restrictions_json,
        "raw_json": _dump_json(row),
        "source_origin": "direlore",
    }


def _normalize_shopkeeper_records(row):
    row = dict(row or {})
    shop_name = _safe_text(row.get("shop_name") or row.get("entity_name"))
    owner_name = _safe_text(row.get("shop_owner") or "Unknown Shopkeeper")
    shop_record = {
        "canonical_key": f"shop:entity:{row['shop_id']}",
        "source_table": row["source_table"],
        "source_id": row["shop_id"],
        "source_entity_id": row["shop_id"],
        "name": shop_name,
        "shop_type": _safe_text(row.get("shop_type")),
        "owner_name": owner_name,
        "tags": ["shop"],
        "raw_json": _dump_json(row),
        "source_origin": "direlore",
    }
    actor_record = {
        "canonical_key": f"shopkeeper:shop:{row['shop_id']}",
        "category": "shopkeeper",
        "source_table": row["source_table"],
        "source_id": str(row["shop_id"]),
        "source_entity_id": row["shop_id"],
        "name": owner_name,
        "role": "shopkeeper",
        "actor_type": "npc",
        "npc_type": "shopkeeper",
        "aggression_type": None,
        "flee_behavior": None,
        "base_health": None,
        "level": None,
        "location_text": shop_name,
        "shop_name": shop_name,
        "shop_owner": owner_name,
        "tags": ["shopkeeper"],
        "raw_json": _dump_json(row),
        "source_origin": "direlore",
    }
    return shop_record, actor_record


def _normalize_actor_record(category, row):
    row = dict(row or {})
    role = "civilian" if category == "civilian" else "guard" if category == "guard" else "creature"
    aggression_type = None
    flee_behavior = None
    if category == "hostile_creature":
        aggression_type = "aggressive"
    elif category == "docile_creature":
        aggression_type = "docile"
        flee_behavior = _safe_text(row.get("flee_behavior"))

    return {
        "canonical_key": f"{category}:{row['source_table']}:{row['source_id']}",
        "category": category,
        "source_table": row["source_table"],
        "source_id": str(row["source_id"]),
        "source_entity_id": row.get("source_entity_id"),
        "name": _clean_name(row.get("name")),
        "role": role,
        "actor_type": row.get("actor_type") or row.get("entity_type") or "npc",
        "npc_type": row.get("npc_type"),
        "aggression_type": aggression_type,
        "flee_behavior": flee_behavior,
        "base_health": row.get("base_health"),
        "level": row.get("level"),
        "location_text": _safe_text(row.get("located") or row.get("location_text")),
        "occupation": _safe_text(row.get("occupation")),
        "role_fact": _safe_text(row.get("role_fact")),
        "shop_name": None,
        "tags": _actor_tags_for_category(category),
        "raw_json": _dump_json(row),
        "source_origin": "direlore",
    }


def _actor_tags_for_category(category):
    if category == "guard":
        return ["guard"]
    if category == "civilian":
        return ["civilian"]
    if category == "hostile_creature":
        return ["creature", "hostile"]
    if category == "docile_creature":
        return ["creature", "docile"]
    return [str(category or "npc")]


def _apply_item_normalization(record):
    normalized = canon_normalize.normalize_item(record)
    record["normalized_fields"] = normalized["fields"]
    record["normalization_warnings"] = normalized["warnings"]
    record["applied_defaults"] = normalized["applied_defaults"]
    return record


def _apply_actor_normalization(record):
    normalized = canon_normalize.normalize_actor(record)
    record["normalized_fields"] = normalized["fields"]
    record["normalization_warnings"] = normalized["warnings"]
    record["applied_defaults"] = normalized["applied_defaults"]
    return record


def _apply_shop_normalization(record):
    normalized = canon_normalize.normalize_shop(record)
    record["normalized_fields"] = normalized["fields"]
    record["normalization_warnings"] = normalized["warnings"]
    record["applied_defaults"] = normalized["applied_defaults"]
    return record


def _upsert_item_record(record):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT OR REPLACE INTO canon_items (
                canonical_key, source_table, source_id, source_entity_id, category, name, item_type,
                tags_json, value_text, value_num, weight, damage_profile_json, protection_profile_json,
                slot, capacity_json, restrictions_json, normalized_fields_json, raw_json, source_origin
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                record["canonical_key"],
                record["source_table"],
                record["source_id"],
                record.get("source_entity_id"),
                record["category"],
                record["name"],
                record.get("item_type"),
                _dump_json(record.get("tags") or []),
                record.get("value_text"),
                record.get("value_num"),
                record.get("weight"),
                _dump_json(record.get("damage_profile")) if record.get("damage_profile") is not None else None,
                _dump_json(record.get("protection_profile")) if record.get("protection_profile") is not None else None,
                record.get("slot"),
                _dump_json(record.get("capacity_json")) if record.get("capacity_json") is not None else None,
                _dump_json(record.get("restrictions_json")) if record.get("restrictions_json") is not None else None,
                _dump_json(record.get("normalized_fields") or {}),
                record["raw_json"],
                record["source_origin"],
            ],
        )


def _upsert_actor_record(record):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT OR REPLACE INTO canon_actors (
                canonical_key, source_table, source_id, source_entity_id, name, role, actor_type,
                npc_type, aggression_type, flee_behavior, base_health, level, location_text,
                shop_name, tags_json, normalized_fields_json, raw_json, source_origin
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                record["canonical_key"],
                record["source_table"],
                record["source_id"],
                record.get("source_entity_id"),
                record["name"],
                record["role"],
                record.get("actor_type"),
                record.get("npc_type"),
                record.get("aggression_type"),
                _dump_json(record.get("flee_behavior")) if isinstance(record.get("flee_behavior"), (dict, list)) else record.get("flee_behavior"),
                record.get("base_health"),
                record.get("level"),
                record.get("location_text"),
                record.get("shop_name"),
                _dump_json(record.get("tags") or []),
                _dump_json(record.get("normalized_fields") or {}),
                record["raw_json"],
                record["source_origin"],
            ],
        )


def _upsert_shop_record(record):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT OR REPLACE INTO canon_shops (
                canonical_key, source_table, source_id, source_entity_id, name, shop_type,
                owner_name, tags_json, normalized_fields_json, raw_json, source_origin
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                record["canonical_key"],
                record["source_table"],
                record["source_id"],
                record.get("source_entity_id"),
                record["name"],
                record.get("shop_type"),
                record.get("owner_name"),
                _dump_json(record.get("tags") or []),
                _dump_json(record.get("normalized_fields") or {}),
                record["raw_json"],
                record["source_origin"],
            ],
        )


def _store_audit(table_name, canonical_key, entity_category, source_table, source_id, audit, raw_json):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO canon_import_audit (
                table_name, canonical_key, entity_category, source_table, source_id,
                passed, missing_fields_json, warnings_json, applied_defaults_json,
                normalized_fields_json, raw_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                table_name,
                canonical_key,
                entity_category,
                source_table,
                source_id,
                1 if audit.get("passed") else 0,
                _dump_json(audit.get("missing_fields") or {}),
                _dump_json(audit.get("warnings") or []),
                _dump_json(audit.get("applied_defaults") or []),
                _dump_json(audit.get("normalized_fields") or {}),
                raw_json,
            ],
        )


def _load_all_items():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT canonical_key, category, name, item_type, tags_json, value_text, value_num, weight,
                   damage_profile_json, protection_profile_json, slot, capacity_json, restrictions_json,
                   normalized_fields_json, source_table, source_id, source_entity_id, raw_json
            FROM canon_items
            ORDER BY name
            """
        )
        return [_deserialize_item_row(row) for row in cursor.fetchall()]


def _load_all_actors():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT canonical_key, name, role, actor_type, npc_type, aggression_type, flee_behavior,
                   base_health, level, location_text, shop_name, tags_json, normalized_fields_json,
                   source_table, source_id, source_entity_id, raw_json
            FROM canon_actors
            ORDER BY name
            """
        )
        return [_deserialize_actor_row(row) for row in cursor.fetchall()]


def _deserialize_item_row(row):
    return {
        "canonical_key": row[0],
        "category": row[1],
        "name": row[2],
        "item_type": row[3],
        "tags": _parse_json(row[4], []),
        "value_text": row[5],
        "value_num": row[6],
        "weight": row[7],
        "damage_profile": _parse_json(row[8], None),
        "protection_profile": _parse_json(row[9], None),
        "slot": row[10],
        "capacity_json": _parse_json(row[11], None),
        "restrictions_json": _parse_json(row[12], None),
        "normalized_fields": _parse_json(row[13], {}),
        "source_table": row[14],
        "source_id": row[15],
        "source_entity_id": row[16],
        "raw_json": _parse_json(row[17], {}),
    }


def _deserialize_actor_row(row):
    return {
        "canonical_key": row[0],
        "name": row[1],
        "role": row[2],
        "actor_type": row[3],
        "npc_type": row[4],
        "aggression_type": _parse_json(row[5], row[5]) if isinstance(row[5], str) and str(row[5]).startswith("{") else row[5],
        "flee_behavior": _parse_json(row[6], row[6]) if row[6] else None,
        "base_health": row[7],
        "level": row[8],
        "location_text": row[9],
        "shop_name": row[10],
        "tags": _parse_json(row[11], []),
        "normalized_fields": _parse_json(row[12], {}),
        "source_table": row[13],
        "source_id": row[14],
        "source_entity_id": row[15],
        "raw_json": _parse_json(row[16], {}),
    }


def _normalized_value(record, field_name):
    normalized_fields = dict(record.get("normalized_fields") or {})
    if field_name in normalized_fields:
        return normalized_fields.get(field_name)
    return record.get(field_name)


def _merge_normalized(record):
    merged = dict(record or {})
    merged.update(dict(record.get("normalized_fields") or {}))
    return merged


def _build_summary(imported, audits, normalization_counts):
    missing_counter = Counter()
    failed_counter = Counter()
    coverage_counter = Counter()
    for entry in audits:
        category = entry["category"]
        audit = entry["audit"]
        coverage_counter[category] += 1
        if not audit.get("passed"):
            failed_counter[category] += 1
        for severity, field_names in dict(audit.get("missing_fields") or {}).items():
            for field_name in field_names or []:
                missing_counter[(category, severity, field_name)] += 1
    return {
        "imported": dict(imported),
        "failed": dict(failed_counter),
        "normalization_coverage": {
            category: f"{coverage_counter[category]}/{imported.get(category, 0)}"
            for category in imported
        },
        "default_usage_counts": dict(sorted(normalization_counts.items())),
        "missing_fields": {
            f"{category}.{severity}.{field_name}": total
            for (category, severity, field_name), total in sorted(missing_counter.items())
        },
    }


def _fetch_weapons(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT cw.id AS source_id, 'canon_weapons' AS source_table, cw.source_entity_id, ci.name,
               ci.item_type, ci.weight, ci.appraised_cost, cw.weapon_type, cw.damage_type,
               cw.range, cw.handedness, cw.skill_type
        FROM canon_weapons cw
        JOIN canon_items ci ON ci.id = cw.item_id
        ORDER BY cw.id
        LIMIT %s
        """,
        [limit],
    )


def _fetch_armor(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT ca.id AS source_id, 'canon_armor' AS source_table, ca.source_entity_id, ci.name,
               ci.item_type, ci.weight, ci.appraised_cost, ca.armor_type, ca.protection_profile,
               ca.hindrance, ca.coverage
        FROM canon_armor ca
        JOIN canon_items ci ON ci.id = ca.item_id
        ORDER BY ca.id
        LIMIT %s
        """,
        [limit],
    )


def _fetch_containers(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT cc.id AS source_id, 'canon_containers' AS source_table, cc.source_entity_id,
               ci.name, ci.item_type, ci.weight, ci.appraised_cost, cc.slot,
               cc.restrictions_json, cc.capacity_json
        FROM canon_containers cc
        JOIN canon_items ci ON ci.id = cc.item_id
        ORDER BY cc.id
        LIMIT %s
        """,
        [limit],
    )


def _fetch_clothing(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT ci.id AS source_id, 'canon_items' AS source_table, ci.source_entity_id, ci.name,
               ci.item_type, ci.weight, ci.appraised_cost,
               MAX(CASE WHEN f.key = 'worn_location' THEN TRIM(BOTH '"' FROM f.value::text) END) AS worn_location,
               MAX(CASE WHEN f.key = 'equip_slot' THEN TRIM(BOTH '"' FROM f.value::text) END) AS equip_slot
        FROM canon_items ci
        LEFT JOIN canon_weapons cw ON cw.item_id = ci.id
        LEFT JOIN canon_armor ca ON ca.item_id = ci.id
        LEFT JOIN canon_containers cc ON cc.item_id = ci.id
        LEFT JOIN facts f ON f.entity_id = ci.source_entity_id AND f.key IN ('worn_location', 'equip_slot')
        WHERE cw.item_id IS NULL
          AND ca.item_id IS NULL
          AND cc.item_id IS NULL
          AND ci.source_entity_id IS NOT NULL
          AND f.entity_id IS NOT NULL
          AND LOWER(ci.name) NOT LIKE 'weapon:%%'
          AND LOWER(ci.name) NOT LIKE 'armor:%%'
        GROUP BY ci.id, ci.source_entity_id, ci.name, ci.item_type, ci.weight, ci.appraised_cost
        ORDER BY ci.id
        LIMIT %s
        """,
        [limit],
    )


def _fetch_shopkeepers(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT e.id AS shop_id, 'entities' AS source_table, e.name AS entity_name,
               MAX(CASE WHEN f.key = 'shop_name' THEN TRIM(BOTH '"' FROM f.value::text) END) AS shop_name,
               MIN(CASE WHEN f.key = 'shop_type' THEN TRIM(BOTH '"' FROM f.value::text) END) AS shop_type,
               MAX(CASE WHEN f.key = 'shop_owner' THEN TRIM(BOTH '"' FROM f.value::text) END) AS shop_owner
        FROM entities e
        JOIN facts f ON f.entity_id = e.id
        WHERE e.entity_type = 'shop'
          AND f.key IN ('shop_name', 'shop_type', 'shop_owner')
        GROUP BY e.id, e.name
        HAVING MAX(CASE WHEN f.key = 'shop_owner' THEN 1 ELSE 0 END) = 1
        ORDER BY e.id
        LIMIT %s
        """,
        [limit],
    )


def _fetch_guards(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT e.id AS source_id, 'entities' AS source_table, e.id AS source_entity_id,
               e.name, e.entity_type, e.entity_subtype, NULL::INTEGER AS level,
               NULL::TEXT AS located, NULL::TEXT AS base_health,
               MAX(CASE WHEN f.key = 'occupation' THEN TRIM(BOTH '"' FROM f.value::text) END) AS occupation,
               MAX(CASE WHEN f.key = 'role' THEN TRIM(BOTH '"' FROM f.value::text) END) AS role_fact
        FROM entities e
        LEFT JOIN facts f ON f.entity_id = e.id AND f.key IN ('occupation', 'role')
        WHERE LOWER(e.name) SIMILAR TO '%%(guard|guardian|sentry|watchman|watchwoman|constable|marshal|patrol|soldier|captain)%%'
          AND LOWER(e.name) NOT LIKE 'post:%%'
          AND LOWER(e.name) NOT LIKE 'pages that link to%%'
          AND LOWER(e.name) NOT LIKE 'weapon:%%'
          AND LOWER(e.name) NOT LIKE 'category:%%'
        GROUP BY e.id, e.name, e.entity_type, e.entity_subtype
        ORDER BY e.id
        LIMIT %s
        """,
        [limit],
    )


def _fetch_civilians(conn, limit, filters):
    rows = _fetch_rows(
        conn,
        """
        SELECT e.id AS source_id, 'entities' AS source_table, e.id AS source_entity_id,
               e.name, e.entity_type, e.entity_subtype, NULL::INTEGER AS level,
               NULL::TEXT AS located, NULL::TEXT AS base_health,
               MAX(CASE WHEN f.key = 'occupation' THEN TRIM(BOTH '"' FROM f.value::text) END) AS occupation,
               MAX(CASE WHEN f.key = 'role' THEN TRIM(BOTH '"' FROM f.value::text) END) AS role_fact
        FROM entities e
        LEFT JOIN facts f ON f.entity_id = e.id AND f.key IN ('occupation', 'role')
        WHERE LOWER(e.name) SIMILAR TO '%%(innkeeper|bartender|barkeep|proprietor|merchant|trader|clerk|beggar|sailor|farmer|villager|citizen)%%'
          AND LOWER(e.name) NOT LIKE 'post:%%'
          AND LOWER(e.name) NOT LIKE 'pages that link to%%'
          AND LOWER(e.name) NOT LIKE 'category:%%'
          AND LOWER(e.name) NOT LIKE '%%guild%%'
          AND LOWER(e.name) NOT LIKE '%%outpost%%'
        GROUP BY e.id, e.name, e.entity_type, e.entity_subtype
        ORDER BY e.id
        LIMIT %s
        """,
        [limit],
    )
    cleaned = [row for row in rows if not _is_noise_name(row.get("name"))]
    return cleaned[:limit]


def _fetch_hostile_creatures(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT id AS source_id, 'canon_npcs' AS source_table, id AS source_entity_id,
               name, npc_type, level, located, level AS base_health
        FROM canon_npcs
        WHERE npc_type = 'creature'
        ORDER BY id
        LIMIT %s
        """,
        [limit],
    )


def _fetch_docile_creatures(conn, limit, filters):
    return _fetch_rows(
        conn,
        """
        SELECT id AS source_id, 'canon_npcs' AS source_table, id AS source_entity_id,
               name, npc_type, level, located, level AS base_health,
               NULL::TEXT AS flee_behavior
        FROM canon_npcs
        WHERE npc_type = 'passive'
        ORDER BY id
        LIMIT %s
        """,
        [limit],
    )


FETCHERS.update(
    {
        "weapon": _fetch_weapons,
        "armor": _fetch_armor,
        "container": _fetch_containers,
        "clothing": _fetch_clothing,
        "shopkeeper": _fetch_shopkeepers,
        "guard": _fetch_guards,
        "civilian": _fetch_civilians,
        "hostile_creature": _fetch_hostile_creatures,
        "docile_creature": _fetch_docile_creatures,
        "random_npc": _fetch_civilians,
    }
)