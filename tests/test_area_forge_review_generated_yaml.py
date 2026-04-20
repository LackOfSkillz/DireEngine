from pathlib import Path

import yaml

from world.area_forge.review import review_generated_zone
from world.area_forge.review.review_generated_yaml import _normalize_source_positions

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


def test_review_generated_zone_corrects_layout_and_connectivity(tmp_path):
    if Image is None:
        return

    root = tmp_path
    worlddata_dir = root / "worlddata" / "zones"
    build_dir = root / "build" / "sample_zone"
    worlddata_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    source_image = root / "sample_zone.png"
    Image.new("RGB", (40, 40), color=(255, 255, 255)).save(source_image)

    yaml_path = worlddata_dir / "sample_zone.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "v1",
                "zone_id": "sample_zone",
                "name": "sample_zone",
                "rooms": [
                    {
                        "id": "room_a",
                        "name": "room_a_10_10",
                        "zone_id": "sample_zone",
                        "map": {"x": 0, "y": 0, "layer": 0},
                        "exits": {
                            "south": {"target": "room_b", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0},
                            "west": {"target": "room_c", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0},
                        },
                        "special_exits": {"go gatc": {"target": "room_c", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                    },
                    {
                        "id": "room_b",
                        "name": "room_b_20_10",
                        "zone_id": "sample_zone",
                        "map": {"x": 0, "y": 40, "layer": 0},
                        "exits": {},
                        "special_exits": {},
                    },
                    {
                        "id": "room_c",
                        "name": "room_c_30_10",
                        "zone_id": "sample_zone",
                        "map": {"x": -40, "y": 0, "layer": 0},
                        "exits": {},
                        "special_exits": {},
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    (build_dir / "review_graph.json").write_text(
        yaml.safe_dump(
            {
                "zone_id": "sample_zone",
                "nodes": [
                    {"id": "room_a", "x": 10, "y": 10, "name": "North Gate"},
                    {"id": "room_b", "x": 20, "y": 10, "name": "Market Street"},
                    {"id": "room_c", "x": 30, "y": 10, "name": "South Gate"},
                ],
                "edges": [
                    {"source": "room_a", "target": "room_b", "type": "spatial"},
                    {"source": "room_b", "target": "room_c", "type": "spatial"},
                ],
                "special_edges": [
                    {"source": "room_a", "target": "room_c", "label": "go gate"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    result = review_generated_zone(str(source_image), str(yaml_path))

    reviewed = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    room_a = next(room for room in reviewed["rooms"] if room["id"] == "room_a")
    room_b = next(room for room in reviewed["rooms"] if room["id"] == "room_b")
    room_c = next(room for room in reviewed["rooms"] if room["id"] == "room_c")

    assert yaml_path.with_suffix(".raw.yaml").exists()
    assert Path(result["report_path"]).exists()
    assert room_a["name"] == "North Gate"
    assert room_b["map"]["x"] == 0
    assert room_b["map"]["y"] == 0
    assert room_a["exits"]["east"]["target"] == "room_b"
    assert room_b["exits"]["west"]["target"] == "room_a"
    assert room_b["exits"]["east"]["target"] == "room_c"
    assert "west" not in room_a["exits"]
    assert "go gate" in room_a["special_exits"]


def test_normalize_source_positions_compacts_noisy_ocr_lines():
    positions = _normalize_source_positions(
        [
            {"id": "room_a", "x": 10, "y": 10},
            {"id": "room_b", "x": 11, "y": 10},
            {"id": "room_c", "x": 28, "y": 10},
            {"id": "room_d", "x": 29, "y": 10},
            {"id": "room_e", "x": 29, "y": 22},
        ]
    )

    xs = sorted({coord[0] for coord in positions.values()})
    ys = sorted({coord[1] for coord in positions.values()})

    assert positions["room_a"][0] == positions["room_b"][0]
    assert positions["room_c"][0] == positions["room_d"][0]
    assert len(xs) == 2
    assert len(ys) == 2
    assert max(xs) - min(xs) <= 20
    assert max(ys) - min(ys) <= 20


def test_review_generated_zone_rebuilds_loop_cluster_into_rectangle(tmp_path):
    if Image is None:
        return

    root = tmp_path
    worlddata_dir = root / "worlddata" / "zones"
    build_dir = root / "build" / "loop_zone"
    worlddata_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    source_image = root / "loop_zone.png"
    Image.new("RGB", (80, 80), color=(255, 255, 255)).save(source_image)

    yaml_path = worlddata_dir / "loop_zone.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "v1",
                "zone_id": "loop_zone",
                "name": "loop_zone",
                "rooms": [
                    {
                        "id": "room_a",
                        "name": "room_a_0_0",
                        "zone_id": "loop_zone",
                        "map": {"x": 0, "y": 0, "layer": 0},
                        "exits": {"east": {"target": "room_b", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "south": {"target": "room_d", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                    {
                        "id": "room_b",
                        "name": "room_b_1_0",
                        "zone_id": "loop_zone",
                        "map": {"x": 120, "y": 40, "layer": 0},
                        "exits": {"south": {"target": "room_c", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "west": {"target": "room_a", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                    {
                        "id": "room_c",
                        "name": "room_c_1_1",
                        "zone_id": "loop_zone",
                        "map": {"x": 40, "y": 140, "layer": 0},
                        "exits": {"west": {"target": "room_d", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "north": {"target": "room_b", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                    {
                        "id": "room_d",
                        "name": "room_d_0_1",
                        "zone_id": "loop_zone",
                        "map": {"x": -80, "y": 60, "layer": 0},
                        "exits": {"north": {"target": "room_a", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "east": {"target": "room_c", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    (build_dir / "review_graph.json").write_text(
        yaml.safe_dump(
            {
                "zone_id": "loop_zone",
                "nodes": [
                    {"id": "room_a", "x": 10, "y": 10},
                    {"id": "room_b", "x": 31, "y": 9},
                    {"id": "room_c", "x": 29, "y": 30},
                    {"id": "room_d", "x": 8, "y": 28},
                ],
                "edges": [
                    {"source": "room_a", "target": "room_b", "type": "spatial"},
                    {"source": "room_b", "target": "room_c", "type": "spatial"},
                    {"source": "room_c", "target": "room_d", "type": "spatial"},
                    {"source": "room_d", "target": "room_a", "type": "spatial"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    review_generated_zone(str(source_image), str(yaml_path))

    reviewed = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    coords = {room["id"]: (room["map"]["x"], room["map"]["y"]) for room in reviewed["rooms"]}
    xs = {coord[0] for coord in coords.values()}
    ys = {coord[1] for coord in coords.values()}

    assert len(xs) == 2
    assert len(ys) == 2
    assert coords["room_a"][1] == coords["room_b"][1]
    assert coords["room_b"][0] == coords["room_c"][0]
    assert coords["room_c"][1] == coords["room_d"][1]
    assert coords["room_d"][0] == coords["room_a"][0]


def test_review_generated_zone_rebuilds_hub_spoke_cluster_cardinally(tmp_path):
    if Image is None:
        return

    root = tmp_path
    worlddata_dir = root / "worlddata" / "zones"
    build_dir = root / "build" / "hub_zone"
    worlddata_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    source_image = root / "hub_zone.png"
    Image.new("RGB", (80, 80), color=(255, 255, 255)).save(source_image)

    yaml_path = worlddata_dir / "hub_zone.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "v1",
                "zone_id": "hub_zone",
                "name": "hub_zone",
                "rooms": [
                    {
                        "id": "hub",
                        "name": "hub_0_0",
                        "zone_id": "hub_zone",
                        "map": {"x": 120, "y": 120, "layer": 0},
                        "exits": {
                            "north": {"target": "north", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0},
                            "south": {"target": "south", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0},
                            "east": {"target": "east", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0},
                            "west": {"target": "west", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0},
                        },
                        "special_exits": {},
                    },
                    {
                        "id": "north",
                        "name": "north_0_-1",
                        "zone_id": "hub_zone",
                        "map": {"x": 100, "y": 40, "layer": 0},
                        "exits": {"south": {"target": "hub", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                    {
                        "id": "east",
                        "name": "east_1_0",
                        "zone_id": "hub_zone",
                        "map": {"x": 200, "y": 100, "layer": 0},
                        "exits": {"west": {"target": "hub", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                    {
                        "id": "south",
                        "name": "south_0_1",
                        "zone_id": "hub_zone",
                        "map": {"x": 140, "y": 220, "layer": 0},
                        "exits": {"north": {"target": "hub", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                    {
                        "id": "west",
                        "name": "west_-1_0",
                        "zone_id": "hub_zone",
                        "map": {"x": 40, "y": 160, "layer": 0},
                        "exits": {"east": {"target": "hub", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}},
                        "special_exits": {},
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    (build_dir / "review_graph.json").write_text(
        yaml.safe_dump(
            {
                "zone_id": "hub_zone",
                "nodes": [
                    {"id": "hub", "x": 21, "y": 20, "name": "Crossroads Hub"},
                    {"id": "north", "x": 20, "y": 8},
                    {"id": "east", "x": 33, "y": 19},
                    {"id": "south", "x": 22, "y": 32},
                    {"id": "west", "x": 9, "y": 21},
                ],
                "edges": [
                    {"source": "hub", "target": "north", "type": "spatial"},
                    {"source": "hub", "target": "east", "type": "spatial"},
                    {"source": "hub", "target": "south", "type": "spatial"},
                    {"source": "hub", "target": "west", "type": "spatial"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    review_generated_zone(str(source_image), str(yaml_path))

    reviewed = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    coords = {room["id"]: (room["map"]["x"], room["map"]["y"]) for room in reviewed["rooms"]}
    hub_coord = coords["hub"]

    directions = set()
    for room_id in ("north", "east", "south", "west"):
        room_coord = coords[room_id]
        assert room_coord != hub_coord
        assert room_coord[0] == hub_coord[0] or room_coord[1] == hub_coord[1]
        if room_coord[0] > hub_coord[0]:
            directions.add("east")
        elif room_coord[0] < hub_coord[0]:
            directions.add("west")
        elif room_coord[1] > hub_coord[1]:
            directions.add("south")
        elif room_coord[1] < hub_coord[1]:
            directions.add("north")

    assert directions == {"north", "south", "east", "west"}


def test_review_generated_zone_rebuilds_block_cluster_into_grid(tmp_path):
    if Image is None:
        return

    root = tmp_path
    worlddata_dir = root / "worlddata" / "zones"
    build_dir = root / "build" / "block_zone"
    worlddata_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    source_image = root / "block_zone.png"
    Image.new("RGB", (80, 80), color=(255, 255, 255)).save(source_image)

    yaml_path = worlddata_dir / "block_zone.yaml"
    yaml_path.write_text(
        yaml.safe_dump(
            {
                "schema_version": "v1",
                "zone_id": "block_zone",
                "name": "block_zone",
                "rooms": [
                    {"id": "a", "name": "a", "zone_id": "block_zone", "map": {"x": 0, "y": 0, "layer": 0}, "exits": {"east": {"target": "b", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "south": {"target": "d", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}}, "special_exits": {}},
                    {"id": "b", "name": "b", "zone_id": "block_zone", "map": {"x": 90, "y": 15, "layer": 0}, "exits": {"west": {"target": "a", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "east": {"target": "c", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "south": {"target": "e", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}}, "special_exits": {}},
                    {"id": "c", "name": "c", "zone_id": "block_zone", "map": {"x": 210, "y": 25, "layer": 0}, "exits": {"west": {"target": "b", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "south": {"target": "f", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}}, "special_exits": {}},
                    {"id": "d", "name": "d", "zone_id": "block_zone", "map": {"x": -10, "y": 120, "layer": 0}, "exits": {"north": {"target": "a", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "east": {"target": "e", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}}, "special_exits": {}},
                    {"id": "e", "name": "e", "zone_id": "block_zone", "map": {"x": 105, "y": 130, "layer": 0}, "exits": {"north": {"target": "b", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "west": {"target": "d", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "east": {"target": "f", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}}, "special_exits": {}},
                    {"id": "f", "name": "f", "zone_id": "block_zone", "map": {"x": 215, "y": 140, "layer": 0}, "exits": {"north": {"target": "c", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}, "west": {"target": "e", "typeclass": "typeclasses.exits.Exit", "speed": "", "travel_time": 0}}, "special_exits": {}},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    (build_dir / "review_graph.json").write_text(
        yaml.safe_dump(
            {
                "zone_id": "block_zone",
                "nodes": [
                    {"id": "a", "x": 11, "y": 10},
                    {"id": "b", "x": 21, "y": 9},
                    {"id": "c", "x": 31, "y": 10},
                    {"id": "d", "x": 10, "y": 22},
                    {"id": "e", "x": 22, "y": 21},
                    {"id": "f", "x": 32, "y": 22},
                ],
                "edges": [
                    {"source": "a", "target": "b", "type": "spatial"},
                    {"source": "b", "target": "c", "type": "spatial"},
                    {"source": "d", "target": "e", "type": "spatial"},
                    {"source": "e", "target": "f", "type": "spatial"},
                    {"source": "a", "target": "d", "type": "spatial"},
                    {"source": "b", "target": "e", "type": "spatial"},
                    {"source": "c", "target": "f", "type": "spatial"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    review_generated_zone(str(source_image), str(yaml_path))

    reviewed = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    coords = {room["id"]: (room["map"]["x"], room["map"]["y"]) for room in reviewed["rooms"]}
    xs = sorted({coord[0] for coord in coords.values()})
    ys = sorted({coord[1] for coord in coords.values()})

    assert len(xs) == 3
    assert len(ys) == 2
    assert coords["a"][1] == coords["b"][1] == coords["c"][1]
    assert coords["d"][1] == coords["e"][1] == coords["f"][1]
    assert coords["a"][0] == coords["d"][0]
    assert coords["b"][0] == coords["e"][0]
    assert coords["c"][0] == coords["f"][0]
