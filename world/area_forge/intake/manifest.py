from pathlib import Path

import yaml


def create_manifest(map_path, area_id, profile="dr_city"):
    manifest = {
        "area_id": area_id,
        "map_file": str(map_path),
        "profile": profile,
        "generation": {
            "synthesize_street_names": True,
            "synthesize_room_descriptions": True,
            "synthesize_special_exits": True,
        },
    }

    out_path = Path("manifests") / f"{area_id}.yaml"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as file_handle:
        yaml.safe_dump(manifest, file_handle, sort_keys=False)
    return out_path


def load_manifest(path):
    with Path(path).open(encoding="utf-8") as file_handle:
        return yaml.safe_load(file_handle)
