from pathlib import Path

import yaml


def create_manifest(map_path, area_id, profile="yaml_graph"):
    manifest = {
        "area_id": area_id,
        "map_file": str(map_path),
        "profile": profile,
        "generation": {
            "synthesize_street_names": profile == "dr_city",
            "synthesize_room_descriptions": profile == "dr_city",
            "synthesize_special_exits": profile == "dr_city",
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
