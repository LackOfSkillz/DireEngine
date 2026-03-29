from pathlib import Path


def generate_review_flags(nodes, edges):
    flags = []

    for node in nodes:
        if node.get("ocr_confidence_tier") == "low":
            flags.append(f"Low-confidence label: {node.get('ocr_label') or node.get('final_label')}")
        if node.get("needs_label_review"):
            flags.append(f"Label needs review: {node.get('final_label')}")

    for edge in edges:
        if isinstance(edge, tuple) and len(edge) > 3:
            data = edge[3]
            if data.get("confidence_tier") == "low":
                flags.append(f"Uncertain exit label: {data.get('label') or data.get('final_exit_name') or edge[1]}")
            if data.get("needs_review"):
                flags.append(f"Exit needs review: {data.get('final_exit_name') or edge[1]}")
            if data.get("one_way_warning"):
                flags.append(f"One-way exit warning: {edge[0]} -> {edge[2]}")

    return flags


def save_review_report(path, flags):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        for flag in flags:
            file_handle.write(f"- {flag}\n")
