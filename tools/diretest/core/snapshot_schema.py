"""Locked snapshot and leak contracts for DireTest v1."""

SNAPSHOT_SCHEMA = {
    "character": dict,
    "room": dict,
    "inventory": list,
    "equipment": list,
    "combat": (dict, type(None)),
    "attributes": dict,
    "object_deltas": {
        "created": list,
        "deleted": list,
    },
}

LEAK_KEY_PREFIX = "TEST_"