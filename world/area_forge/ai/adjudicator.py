from world.area_forge.extract.ocr import derive_poi_stub


def log_adjudication(message):
    print(f"[AreaForge AI] {message}")


def _promotable_landmark(node):
    label = node.get("ocr_label")
    if not label:
        return False
    if node.get("ocr_label_type") != "landmark":
        return False
    if node.get("ocr_label_quality", 0) < 0.78:
        return False
    if node.get("ocr_association_score", 0) < 0.78:
        return False
    if len(label.split()) > 4:
        return False
    return True


def assign_landmark_flavor(nodes):
    for node in nodes:
        if _promotable_landmark(node):
            node["landmark_flavor"] = node.get("ocr_label")
            continue

        candidate = node.get("label_candidate")
        candidate_type = node.get("label_candidate_type")
        candidate_quality = node.get("label_candidate_quality", 0)
        if candidate and candidate_type in {"landmark", "place"} and candidate_quality >= 0.6:
            node["landmark_flavor"] = candidate
    return nodes


def _poi_candidate(node):
    label = node.get("ocr_label") or node.get("label_candidate")
    if not label:
        return None

    label_type = node.get("ocr_label_type") or node.get("label_candidate_type")
    quality = node.get("ocr_label_quality", node.get("label_candidate_quality", 0))
    association = node.get("ocr_association_score", 0)
    if label_type != "poi_stub":
        return None
    if quality < 0.58 or association < 0.55:
        return None

    poi = derive_poi_stub(label)
    if not poi:
        return None
    poi["quality"] = quality
    poi["association"] = association
    return poi


def _poi_stub_description(poi_title, poi_exit_name, district):
    descriptions = {
        "academy": f"A provisional academy interior waits here, with chalk boards, spare benches, and enough space to grow into lecture rooms or practice halls around {poi_title}.",
        "bank": f"This stub marks the future interior of {poi_title}, where counters, ledgers, and guarded strongrooms can later be built out behind the public floor.",
        "forge": f"This stub marks the future working space of {poi_title}, ready for hearths, anvils, and a proper smith's floorplan once the area is expanded.",
        "guild": f"This stub marks the future rooms of {poi_title}, suitable for offices, meeting chambers, and the back corridors of a proper guildhall.",
        "hall": f"This stub holds the place of {poi_title}, ready for a larger civic or ceremonial interior to be attached later.",
        "inn": f"This stub marks the future inn interior of {poi_title}, where a taproom, kitchen, and rented rooms can later be built out.",
        "office": f"This stub reserves the interior of {poi_title}, ready for desks, records, and the bureaucracy that belongs behind its door.",
        "prison": f"This stub stands in for the interior of {poi_title}, leaving room for cells, watch stations, and controlled access deeper inside.",
        "shrine": f"This stub marks the future interior of {poi_title}, where altar space, candles, and a devotional chamber can later be shaped with more care.",
        "shop": f"This stub reserves a future shop interior for {poi_title}, where counters, stock rooms, and merchant clutter can be added later.",
        "smithy": f"This stub marks the future smithy interior of {poi_title}, waiting for bellows, iron racks, and blackened worktables.",
        "store": f"This stub holds the future interior of {poi_title}, ready for shelves, counters, and trade goods once the location is built out.",
        "tavern": f"This stub marks the future tavern interior of {poi_title}, where tables, casks, and a louder social space can later take shape.",
        "temple": f"This stub reserves the temple interior of {poi_title}, leaving room for sanctuaries, side chapels, and more formal devotional architecture.",
    }
    base = descriptions.get(
        poi_exit_name,
        f"This is a stubbed interior for {poi_title}, ready for later expansion.",
    )
    if district == "river":
        return f"{base} Even in stub form, the damp riverfront atmosphere seems to follow the threshold inside."
    if district == "market":
        return f"{base} Noise from the surrounding commercial streets still seems close behind the doorway."
    return base


def synthesize_poi_stubs(nodes, edges):
    existing_ids = {node["id"] for node in nodes}
    chosen = []
    for node in sorted(
        nodes,
        key=lambda item: (
            -(item.get("ocr_association_score", 0) + item.get("ocr_label_quality", 0)),
            item["y"],
            item["x"],
        ),
    ):
        poi = _poi_candidate(node)
        if not poi:
            continue

        duplicate = False
        for selected in chosen:
            if selected["exit_name"] != poi["exit_name"]:
                continue
            dx = selected["x"] - node["x"]
            dy = selected["y"] - node["y"]
            if (dx * dx + dy * dy) ** 0.5 <= 90:
                duplicate = True
                break
        if duplicate:
            continue

        stub_id = f"{node['id']}__poi_{poi['exit_name']}"
        if stub_id in existing_ids:
            continue

        node["landmark_flavor"] = poi["title"]
        district = node.get("prose_seed", {}).get("district", "")
        stub_node = {
            "id": stub_id,
            "x": node["x"],
            "y": node["y"],
            "kind": "poi_stub",
            "area_name": node.get("area_name"),
            "generated_name": poi["title"],
            "final_label": poi["title"],
            "generated_desc": _poi_stub_description(poi["title"], poi["exit_name"], district),
            "desc_final": _poi_stub_description(poi["title"], poi["exit_name"], district),
            "road_meta": {"street": None, "lane": None, "alley": []},
            "prose_seed": {"district": district, "marker_kind": "poi_stub"},
            "is_stub": True,
            "poi_anchor": node["id"],
            "poi_exit_name": poi["exit_name"],
        }
        nodes.append(stub_node)
        edges.append(
            (
                node["id"],
                poi["exit_name"],
                stub_id,
                {
                    "exit_type": "special",
                    "final_exit_name": poi["exit_name"],
                    "confidence_tier": "high",
                    "poi_stub": True,
                    "aliases": [f"go {poi['exit_name']}", f"enter {poi['exit_name']}"] + poi.get("aliases", []),
                },
            )
        )
        edges.append(
            (
                stub_id,
                "out",
                node["id"],
                {
                    "exit_type": "special",
                    "final_exit_name": "out",
                    "confidence_tier": "high",
                    "poi_stub": True,
                    "aliases": ["leave"],
                },
            )
        )
        existing_ids.add(stub_id)
        chosen.append({"x": node["x"], "y": node["y"], "exit_name": poi["exit_name"]})

    return nodes, edges


def refine_node_labels(nodes):
    for node in nodes:
        if node.get("ocr_confidence_tier") in ("low", "none") or (
            node.get("ocr_label") and node.get("ocr_label_quality", 0) < 0.6
        ):
            node["needs_label_review"] = True
    return nodes


def enhance_medium_labels(nodes):
    for node in nodes:
        if node.get("ocr_confidence_tier") == "medium":
            node["label_candidate"] = node.get("ocr_label")
            node["label_candidate_type"] = node.get("ocr_label_type")
            node["label_candidate_quality"] = node.get("ocr_label_quality", 0)
    return nodes


def lock_high_confidence_labels(nodes):
    for node in nodes:
        if node.get("ocr_confidence_tier") == "high" and _promotable_landmark(node):
            node["final_label"] = node.get("ocr_label")
    return nodes


def fallback_labels(nodes):
    for node in nodes:
        if not node.get("final_label"):
            node["final_label"] = node.get("generated_name", node["id"])
    return nodes


def _normalize_edge(edge):
    if len(edge) > 3:
        source_id, exit_name, target_id, edge_data = edge[0], edge[1], edge[2], dict(edge[3])
    else:
        source_id, exit_name, target_id = edge
        edge_data = {}
    return (source_id, exit_name, target_id, edge_data)


def flag_uncertain_exits(edges):
    normalized = []
    for edge in edges:
        source_id, exit_name, target_id, edge_data = _normalize_edge(edge)
        if edge_data.get("confidence_tier") in ("low", "none"):
            edge_data["needs_review"] = True
        normalized.append((source_id, exit_name, target_id, edge_data))
    return normalized


def preserve_command_exits(edges):
    normalized = []
    for edge in edges:
        source_id, exit_name, target_id, edge_data = _normalize_edge(edge)
        if edge_data.get("is_command"):
            edge_data["final_exit_name"] = edge_data.get("label")
        normalized.append((source_id, exit_name, target_id, edge_data))
    return normalized


def fallback_exit_names(edges):
    normalized = []
    for edge in edges:
        source_id, exit_name, target_id, edge_data = _normalize_edge(edge)
        if not edge_data.get("final_exit_name"):
            edge_data["final_exit_name"] = exit_name
        normalized.append((source_id, exit_name, target_id, edge_data))
    return normalized


def check_exit_symmetry(edges):
    normalized = [_normalize_edge(edge) for edge in edges]
    pairs = {(source_id, target_id) for source_id, _exit_name, target_id, _edge_data in normalized}
    output = []
    for source_id, exit_name, target_id, edge_data in normalized:
        if (target_id, source_id) not in pairs:
            edge_data["one_way_warning"] = True
        output.append((source_id, exit_name, target_id, edge_data))
    return output


def normalize_prose_seed(nodes):
    for node in nodes:
        node["prose_seed"] = node.get("prose_seed", {})
    return nodes


def assign_atmosphere_tags(nodes):
    for node in nodes:
        seed = node.get("prose_seed", {})
        district = seed.get("district", "")
        if "market" in district:
            node["atmosphere"] = "busy_commercial"
        elif "river" in district:
            node["atmosphere"] = "river_worn"
        elif "north" in district:
            node["atmosphere"] = "ordered_residential"
        elif "south" in district:
            node["atmosphere"] = "weathered_working"
        else:
            node["atmosphere"] = "neutral"
    return nodes


def refine_prose(nodes):
    atmosphere_lines = {
        "busy_commercial": "Trade presses close around the street, with voices, wheels, and hanging signs crowding the space.",
        "river_worn": "Damp air and the smell of rope, tar, and river silt cling to the stones here.",
        "ordered_residential": "The surrounding facades feel more deliberate here, with cleaner stonework and a quieter civic order.",
        "weathered_working": "Patched stone, soot, and hard daily use give the street a rougher but lived-in character.",
        "neutral": "The street feels like a connective seam in the city, shaped by the traffic that passes through it.",
    }
    for node in nodes:
        if not node.get("desc_final"):
            base = node.get("generated_desc") or f"You are at {node.get('final_label')}."
            landmark = node.get("landmark_flavor")
            atmosphere = atmosphere_lines.get(node.get("atmosphere"), atmosphere_lines["neutral"])

            if landmark and landmark != node.get("final_label"):
                node["desc_final"] = f"{base} Nearby, {landmark} gives this stretch of the city a more distinct identity. {atmosphere}"
            else:
                node["desc_final"] = f"{base} {atmosphere}"
    return nodes


def adjudicate_area_spec(area_spec, context=None):
    log_adjudication("Adjudication pass (no-op fallback)")
    if context:
        area_id = context.get("area_id")
        if area_id:
            log_adjudication(f"Context area_id={area_id}")

    nodes = area_spec.get("nodes", [])
    nodes = lock_high_confidence_labels(nodes)
    nodes = enhance_medium_labels(nodes)
    nodes = refine_node_labels(nodes)
    nodes = fallback_labels(nodes)
    nodes = assign_landmark_flavor(nodes)
    nodes = normalize_prose_seed(nodes)
    nodes = assign_atmosphere_tags(nodes)
    nodes = refine_prose(nodes)

    edges = area_spec.get("edges", [])
    edges = preserve_command_exits(edges)
    edges = fallback_exit_names(edges)
    edges = flag_uncertain_exits(edges)
    edges = check_exit_symmetry(edges)
    nodes, edges = synthesize_poi_stubs(nodes, edges)

    area_spec["nodes"] = nodes
    area_spec["edges"] = edges
    area_spec["meta"] = dict(area_spec.get("meta", {}))
    area_spec["meta"]["node_count"] = len(nodes)
    area_spec["meta"]["edge_count"] = len(edges)
    area_spec["meta"]["adjudication_enabled"] = True
    area_spec["meta"]["adjudication_context"] = context or {}
    return area_spec
