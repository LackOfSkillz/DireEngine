from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "server" / "evennia.db3"
ORPHAN_COUNT_SQL = """
SELECT COUNT(*)
FROM typeclasses_attribute attr
LEFT JOIN objects_objectdb_db_attributes obj ON obj.attribute_id = attr.id
LEFT JOIN accounts_accountdb_db_attributes acc ON acc.attribute_id = attr.id
LEFT JOIN comms_channeldb_db_attributes chan ON chan.attribute_id = attr.id
LEFT JOIN scripts_scriptdb_db_attributes scr ON scr.attribute_id = attr.id
WHERE obj.objectdb_id IS NULL
  AND acc.accountdb_id IS NULL
  AND chan.channeldb_id IS NULL
  AND scr.scriptdb_id IS NULL
"""


def count_orphan_attributes(date_filter=None):
    conn = sqlite3.connect(str(DB_PATH))
    try:
        sql = ORPHAN_COUNT_SQL
        params = []
        if date_filter:
            sql += " AND substr(attr.db_date_created, 1, 10) = ?"
            params.append(str(date_filter))
        row = conn.execute(sql, params).fetchone()
        return int((row or [0])[0] or 0)
    finally:
        conn.close()