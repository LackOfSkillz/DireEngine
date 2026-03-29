from pathlib import Path


def slugify_area_id(area_id):
    cleaned = str(area_id).strip().lower().replace("-", "_").replace(" ", "_")
    return "_".join(part for part in cleaned.split("_") if part)


def area_display_name(area_id):
    words = slugify_area_id(area_id).split("_")
    return " ".join(word.capitalize() for word in words if word)


def artifact_paths(area_id):
    area_slug = slugify_area_id(area_id)
    base = Path("build") / area_slug
    return {
        "manifest": f"manifests/{area_slug}.yaml",
        "areaspec": str(base / "areaspec.json"),
        "review": str(base / "review.txt"),
        "snapshot": str(Path("build") / "snapshots" / f"{area_slug}.json"),
    }


def area_namespace(area_id):
    area_slug = slugify_area_id(area_id)
    return {
        "area_id": area_id,
        "area_slug": area_slug,
        "area_name": area_display_name(area_id),
        "area_tag": (area_slug, "build"),
        "area_version_tag": (f"{area_slug}_v2", "build_version"),
        "node_category": f"{area_slug}_node",
        "exit_category": f"{area_slug}_exit",
        "node_alias_prefix": area_slug,
    }
