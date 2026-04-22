from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.systems.direlore_npc_import import DEFAULT_IMPORT_LIMIT, import_direlore_npcs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import spawn-ready NPC definitions from DireLore canon tables.")
    parser.add_argument("--limit", type=int, default=DEFAULT_IMPORT_LIMIT, help="Maximum number of NPCs to process.")
    parser.add_argument("--write", action="store_true", help="Write imported NPC YAML files.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing NPC YAML files when writing.")
    parser.add_argument("--indent", type=int, default=2, help="JSON output indentation.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    summary = import_direlore_npcs(limit=args.limit, dry_run=not args.write, overwrite=args.overwrite)
    print(json.dumps(summary, indent=max(0, int(args.indent)), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())