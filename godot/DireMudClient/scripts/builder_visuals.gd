extends RefCounted

class_name BuilderVisuals


const ROOM_COLORS := {
	"forest": Color(0.26, 0.64, 0.34, 1.0),
	"river": Color(0.2, 0.52, 0.86, 1.0),
	"city": Color(0.65, 0.67, 0.74, 1.0),
	"home": Color(0.78, 0.56, 0.34, 1.0),
	"coast": Color(0.3, 0.72, 0.74, 1.0),
	"room": Color(0.2, 0.9, 0.2, 1.0),
	"shop": Color(0.6, 0.2, 0.8, 1.0),
	"guild": Color(1.0, 0.9, 0.2, 1.0),
	"training": Color(1.0, 0.4, 0.7, 1.0),
}

const ITEM_COLOR := Color(0.28, 0.48, 0.86, 1.0)
const CONTAINER_COLOR := Color(0.88, 0.72, 0.18, 1.0)
const NPC_COLOR := Color(1.0, 0.2, 0.2, 1.0)
const FALLBACK_OBJECT_COLOR := Color(0.55, 0.55, 0.55, 1.0)

const ROOM_Z_INDEX := 0
const EXIT_Z_INDEX := 1
const ITEM_Z_INDEX := 5
const NPC_Z_INDEX := 10
const SELECTION_Z_INDEX := 20


static func normalize_semantic_tags(tags_value) -> Array[String]:
	var normalized: Array[String] = []
	if not (tags_value is Array):
		return normalized
	for tag_value in tags_value:
		var tag := str(tag_value).strip_edges().to_lower()
		if not tag.is_empty() and not normalized.has(tag):
			normalized.append(tag)
	return normalized


static func resolve_room_type(room_type_value, tags_value = []) -> String:
	var tags := normalize_semantic_tags(tags_value)
	if _tags_match(tags, ["shop", "bank"]):
		return "shop"
	if _has_guild_semantics(tags):
		return "guild"
	if _tags_match(tags, ["training"]):
		return "training"
	var normalized_room_type := str(room_type_value or "").strip_edges().to_lower()
	match normalized_room_type:
		"wilderness":
			normalized_room_type = "forest"
		"coastal":
			normalized_room_type = "coast"
		"room", "shop", "training":
			normalized_room_type = "city"
	if ROOM_COLORS.has(normalized_room_type):
		return normalized_room_type
	return "forest"


static func get_room_color(room_type_value, tags_value = []) -> Color:
	var resolved_type := resolve_room_type(room_type_value, tags_value)
	return ROOM_COLORS.get(resolved_type, ROOM_COLORS["room"])


static func _tags_match(tags: Array[String], semantic_markers: Array[String]) -> bool:
	for tag in tags:
		for marker in semantic_markers:
			if tag == marker or tag.begins_with(marker + "_") or tag.ends_with("_" + marker) or tag.contains("_" + marker + "_"):
				return true
	return false


static func _has_guild_semantics(tags: Array[String]) -> bool:
	for tag in tags:
		if tag == "guild":
			return true
		if tag.begins_with("guild_access_"):
			return true
		if tag.begins_with("guild_"):
			return true
		if tag.begins_with("poi_guild_"):
			return true
		if tag.begins_with("poi_") and tag.ends_with("_guild"):
			return true
		if tag.ends_with("_guildhall"):
			return true
	return false


static func get_object_color(object_type_value: String) -> Color:
	match str(object_type_value).strip_edges().to_lower():
		"npc":
			return NPC_COLOR
		"container":
			return CONTAINER_COLOR
		"item":
			return ITEM_COLOR
		_:
			return FALLBACK_OBJECT_COLOR


static func get_object_z_index(object_type_value: String) -> int:
	match str(object_type_value).strip_edges().to_lower():
		"npc":
			return NPC_Z_INDEX
		_:
			return ITEM_Z_INDEX