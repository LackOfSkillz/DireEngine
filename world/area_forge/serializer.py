import json
from pathlib import Path


def save_area_spec(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2)


def load_area_spec(path):
    path = Path(path)
    try:
        with path.open(encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except FileNotFoundError:
        return None
