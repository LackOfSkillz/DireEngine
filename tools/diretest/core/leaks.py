"""Leak detection for DireTest teardown."""

from __future__ import annotations

from .snapshot_schema import LEAK_KEY_PREFIX


def detect_leaks() -> list:
    """Return surviving test-created objects after teardown."""

    from evennia.objects.models import ObjectDB

    leaked_objects = []
    for obj in ObjectDB.objects.filter(db_key__startswith=LEAK_KEY_PREFIX):
        leaked_objects.append(
            {
                "id": int(getattr(obj, "id", 0) or 0),
                "key": str(getattr(obj, "key", "") or ""),
                "type": str(getattr(obj, "typeclass_path", "") or ""),
            }
        )
    return leaked_objects