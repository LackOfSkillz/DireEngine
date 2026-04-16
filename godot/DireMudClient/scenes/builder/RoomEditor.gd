extends PanelContainer


signal save_requested(room_id, updates)
signal draft_changed(room_id, updates)
signal close_requested()
signal add_npc_requested()
signal add_item_requested()
signal exit_selected(exit_id)
signal exit_save_requested(room_id, exit_id, fields)
signal exit_delete_requested(room_id, exit_id)


var room_id: String = ""
var current_area_id: String = ""
var is_loading := false
var current_exits: Dictionary = {}
var current_exit_rows: Array[Dictionary] = []
var available_zones: Dictionary = {}
var target_zone_ids: Array[String] = []
var target_room_ids: Array[String] = []
var selected_exit_id := ""
var selected_direction := ""

const EXIT_DIRECTIONS := ["north", "south", "east", "west", "up", "down", "northeast", "northwest", "southeast", "southwest", "in", "out"]


@onready var empty_state: Label = $Margin/VBoxContainer/EmptyState
@onready var content_block: VBoxContainer = $Margin/VBoxContainer/ContentBlock
@onready var room_id_label: Label = $Margin/VBoxContainer/InfoPanel/Margin/InfoGrid/RoomIdValue
@onready var type_label: Label = $Margin/VBoxContainer/InfoPanel/Margin/InfoGrid/TypeValue
@onready var coord_label: Label = $Margin/VBoxContainer/InfoPanel/Margin/InfoGrid/CoordValue
@onready var exits_label: Label = $Margin/VBoxContainer/InfoPanel/Margin/InfoGrid/ExitsValue
@onready var objects_label: Label = $Margin/VBoxContainer/InfoPanel/Margin/InfoGrid/ObjectValue
@onready var exits_empty_label: Label = $Margin/VBoxContainer/ExitsSection/Margin/VBox/Empty
@onready var exit_list: ItemList = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitList
@onready var exit_editor: PanelContainer = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor
@onready var exit_id_value: Label = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/SelectedExitId
@onready var exit_direction_value: Label = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionRow/DirectionValue
@onready var exit_target_zone_input: OptionButton = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/TargetZone
@onready var exit_target_input: OptionButton = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/TargetRoom
@onready var exit_label_input: LineEdit = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/LabelInput
@onready var exit_aliases_input: LineEdit = $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/AliasesInput
@onready var name_input: LineEdit = $Margin/VBoxContainer/ContentBlock/Name
@onready var description_input: TextEdit = $Margin/VBoxContainer/ContentBlock/DescriptionPanel/Margin/Description
@onready var tags_input: LineEdit = $Margin/VBoxContainer/ContentBlock/Tags
@onready var direction_buttons := {
	"north": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/North,
	"south": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/South,
	"east": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/East,
	"west": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/West,
	"up": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/Up,
	"down": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/Down,
	"northeast": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/Northeast,
	"northwest": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/Northwest,
	"southeast": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/Southeast,
	"southwest": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/Southwest,
	"in": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/In,
	"out": $Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/DirectionGrid/Out,
}


func _ready() -> void:
	$Margin/VBoxContainer/ContentBlock/ButtonRow/Save.pressed.connect(_on_save_pressed)
	$Margin/VBoxContainer/ContentBlock/ButtonRow/Close.pressed.connect(_on_close_pressed)
	$Margin/VBoxContainer/ContentBlock/SpawnRow/AddNpc.pressed.connect(_on_add_npc_pressed)
	$Margin/VBoxContainer/ContentBlock/SpawnRow/AddItem.pressed.connect(_on_add_item_pressed)
	exit_list.item_selected.connect(_on_exit_selected)
	exit_target_zone_input.item_selected.connect(_on_target_zone_selected)
	$Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/ButtonRow/Save.pressed.connect(_on_exit_save_pressed)
	$Margin/VBoxContainer/ExitsSection/Margin/VBox/ExitEditor/Margin/VBox/ButtonRow/Delete.pressed.connect(_on_exit_delete_pressed)
	name_input.text_changed.connect(_on_field_changed)
	description_input.text_changed.connect(_on_field_changed)
	tags_input.text_changed.connect(_on_field_changed)
	description_input.wrap_mode = TextEdit.LINE_WRAPPING_BOUNDARY
	for direction in direction_buttons.keys():
		(direction_buttons[direction] as BaseButton).toggled.connect(_on_direction_button_toggled.bind(direction))
	clear_room()


func load_room(data: Dictionary, area_id: String = "", preferred_exit_id: String = "", zone_options: Dictionary = {}) -> void:
	is_loading = true
	room_id = str(data.get("id", ""))
	current_area_id = area_id.strip_edges()
	available_zones = zone_options.duplicate(true)
	room_id_label.text = room_id
	type_label.text = _format_room_type(str(data.get("room_type", "room")))
	coord_label.text = "(%d, %d, %d)" % [
		int(data.get("map_x", 0)),
		int(data.get("map_y", 0)),
		int(data.get("map_layer", 0)),
	]
	current_exits = (data.get("exits", {}) as Dictionary).duplicate(true)
	current_exit_rows = _build_exit_rows(data)
	exits_label.text = str(int(current_exits.size()))
	objects_label.text = str(int((data.get("contents", []) as Array).size()))
	name_input.text = str(data.get("name", ""))
	description_input.text = str(data.get("description", ""))
	var tags: Array[String] = []
	for tag in data.get("tags", []):
		tags.append(str(tag))
	tags_input.text = ", ".join(tags)
	_rebuild_target_zone_options(current_area_id)
	_rebuild_exit_list(preferred_exit_id)
	empty_state.visible = false
	content_block.visible = true
	visible = true
	is_loading = false


func clear_room() -> void:
	room_id = ""
	current_area_id = ""
	room_id_label.text = "-"
	type_label.text = "-"
	coord_label.text = "-"
	current_exits.clear()
	current_exit_rows.clear()
	available_zones.clear()
	target_zone_ids.clear()
	target_room_ids.clear()
	selected_exit_id = ""
	selected_direction = ""
	exits_label.text = "0"
	objects_label.text = "0"
	name_input.text = ""
	description_input.text = ""
	tags_input.text = ""
	exit_list.clear()
	exits_empty_label.visible = true
	exit_editor.visible = false
	exit_id_value.text = "-"
	exit_direction_value.text = "-"
	_set_selected_direction("")
	exit_target_zone_input.clear()
	exit_target_input.clear()
	exit_label_input.text = ""
	exit_aliases_input.text = ""
	empty_state.visible = true
	content_block.visible = false
	visible = true


func get_room_updates() -> Dictionary:
	var parsed_tags: Array[String] = []
	for raw_tag in tags_input.text.split(","):
		var normalized_tag := raw_tag.strip_edges()
		if not normalized_tag.is_empty():
			parsed_tags.append(normalized_tag)
	return {
		"name": name_input.text.strip_edges(),
		"description": description_input.text,
		"tags": parsed_tags,
	}


func set_room_type(room_type: String) -> void:
	type_label.text = _format_room_type(room_type)


func _build_exit_rows(data: Dictionary) -> Array[Dictionary]:
	var rows: Array[Dictionary] = []
	var detailed_rows = data.get("exit_details", [])
	if detailed_rows is Array and not detailed_rows.is_empty():
		for raw_row in detailed_rows:
			if raw_row is Dictionary:
				var row: Dictionary = (raw_row as Dictionary).duplicate(true)
				row["id"] = str(row.get("id", "")).strip_edges()
				row["direction"] = str(row.get("direction", "")).strip_edges().to_lower()
				row["target"] = _normalize_target(row.get("target", row.get("target_room_id", "")))
				row["label"] = str(row.get("label", ""))
				row["aliases"] = (row.get("aliases", []) as Array).duplicate(true)
				rows.append(row)
		return rows
	var fallback_exits: Dictionary = (data.get("exits", {}) as Dictionary).duplicate(true)
	for direction in fallback_exits.keys():
		var target := _normalize_target(fallback_exits.get(direction, ""))
		rows.append(
			{
				"id": "legacy:%s:%s" % [room_id, str(direction).strip_edges().to_lower()],
				"direction": str(direction).strip_edges().to_lower(),
				"target": target,
				"label": "",
				"aliases": [],
			}
		)
	return rows


func _normalize_target(raw_target: Variant) -> Dictionary:
	if raw_target is Dictionary:
		return {
			"zone_id": str((raw_target as Dictionary).get("zone_id", current_area_id)).strip_edges(),
			"room_id": str((raw_target as Dictionary).get("room_id", "")).strip_edges(),
		}
	return {
		"zone_id": current_area_id,
		"room_id": str(raw_target).strip_edges(),
	}


func _rebuild_target_zone_options(preferred_zone_id: String = "") -> void:
	target_zone_ids.clear()
	exit_target_zone_input.clear()
	var zone_ids: Array[String] = []
	for zone_id in available_zones.keys():
		zone_ids.append(str(zone_id))
	zone_ids.sort()
	for zone_id in zone_ids:
		target_zone_ids.append(zone_id)
		var zone_payload: Dictionary = (available_zones.get(zone_id, {}) as Dictionary).duplicate(true)
		var zone_name := str(zone_payload.get("name", zone_id)).strip_edges()
		exit_target_zone_input.add_item("%s (%s)" % [zone_name if not zone_name.is_empty() else zone_id, zone_id])
	var selected_zone_id := preferred_zone_id.strip_edges()
	if selected_zone_id.is_empty() and not current_area_id.is_empty():
		selected_zone_id = current_area_id
	var selected_zone_index := _find_target_zone_option_index(selected_zone_id)
	if selected_zone_index >= 0:
		exit_target_zone_input.select(selected_zone_index)
	_rebuild_target_room_options(selected_zone_id if selected_zone_index >= 0 else current_area_id)


func _rebuild_target_room_options(zone_id: String) -> void:
	target_room_ids.clear()
	exit_target_input.clear()
	var normalized_zone_id := zone_id.strip_edges()
	var zone_payload: Dictionary = (available_zones.get(normalized_zone_id, {}) as Dictionary).duplicate(true)
	var rooms_payload: Dictionary = (zone_payload.get("rooms", {}) as Dictionary).duplicate(true)
	var room_options: Array[String] = []
	for option_id in rooms_payload.keys():
		room_options.append(str(option_id))
	room_options.sort()
	for option_id in room_options:
		if option_id.is_empty() or (normalized_zone_id == current_area_id and option_id == room_id):
			continue
		var room_payload: Dictionary = (rooms_payload.get(option_id, {}) as Dictionary).duplicate(true)
		var option_name := str(room_payload.get("name", option_id)).strip_edges()
		target_room_ids.append(option_id)
		exit_target_input.add_item("%s (%s)" % [option_name if not option_name.is_empty() else option_id, option_id])


func _rebuild_exit_list(preferred_exit_id: String = "") -> void:
	exit_list.clear()
	selected_exit_id = ""
	exit_editor.visible = false
	exit_id_value.text = "-"
	exit_direction_value.text = "-"
	_set_selected_direction("")
	exit_target_input.select(-1)
	exit_label_input.text = ""
	exit_aliases_input.text = ""
	current_exit_rows.sort_custom(func(a: Dictionary, b: Dictionary): return str(a.get("direction", "")) < str(b.get("direction", "")))
	for row in current_exit_rows:
		var direction := str(row.get("direction", "")).strip_edges().to_lower()
		var target: Dictionary = _normalize_target(row.get("target", {}))
		var target_zone_id := str(target.get("zone_id", current_area_id)).strip_edges()
		var target_room_id := str(target.get("room_id", "")).strip_edges()
		var label := str(row.get("label", "")).strip_edges()
		var item_text := "[%s] -> %s/%s" % [_format_exit_direction(direction), target_zone_id if not target_zone_id.is_empty() else current_area_id, target_room_id if not target_room_id.is_empty() else "-"]
		if not label.is_empty():
			item_text += " | %s" % label
		exit_list.add_item(item_text)
	exits_empty_label.visible = current_exit_rows.is_empty()
	if not preferred_exit_id.strip_edges().is_empty():
		select_exit_by_id(preferred_exit_id)
	elif not current_exit_rows.is_empty():
		select_exit_by_id(str(current_exit_rows[0].get("id", "")).strip_edges())


func _format_exit_direction(direction: String) -> String:
	return direction.strip_edges().to_upper()


func _format_room_type(room_type: String) -> String:
	var normalized := room_type.strip_edges().replace("_", " ")
	if normalized.is_empty():
		return "-"
	return normalized.capitalize()


func _on_field_changed() -> void:
	if is_loading or room_id.is_empty():
		return
	emit_signal("draft_changed", room_id, get_room_updates())


func _find_exit_row_index(exit_id: String) -> int:
	var normalized_exit_id := exit_id.strip_edges()
	for index in range(current_exit_rows.size()):
		if str(current_exit_rows[index].get("id", "")).strip_edges() == normalized_exit_id:
			return index
	return -1


func _find_direction_option_index(direction: String) -> int:
	var normalized_direction := direction.strip_edges().to_lower()
	for index in range(EXIT_DIRECTIONS.size()):
		if EXIT_DIRECTIONS[index] == normalized_direction:
			return index
	return -1


func _find_target_zone_option_index(target_zone_id: String) -> int:
	var normalized_target_zone_id := target_zone_id.strip_edges()
	for index in range(target_zone_ids.size()):
		if target_zone_ids[index] == normalized_target_zone_id:
			return index
	return -1


func _find_target_room_option_index(target_room_id: String) -> int:
	var normalized_target_room_id := target_room_id.strip_edges()
	for index in range(target_room_ids.size()):
		if target_room_ids[index] == normalized_target_room_id:
			return index
	return -1


func select_exit_by_id(exit_id: String) -> void:
	var row_index := _find_exit_row_index(exit_id)
	if row_index < 0:
		return
	exit_list.select(row_index)
	_on_exit_selected(row_index)


func _on_exit_selected(index: int) -> void:
	if index < 0 or index >= current_exit_rows.size():
		selected_exit_id = ""
		exit_editor.visible = false
		return
	var row: Dictionary = (current_exit_rows[index] as Dictionary).duplicate(true)
	selected_exit_id = str(row.get("id", "")).strip_edges()
	exit_id_value.text = selected_exit_id
	var direction := str(row.get("direction", "")).strip_edges().to_lower()
	_set_selected_direction(direction)
	var target := _normalize_target(row.get("target", {}))
	var target_zone_id := str(target.get("zone_id", current_area_id)).strip_edges()
	var target_room_id := str(target.get("room_id", "")).strip_edges()
	var target_zone_index := _find_target_zone_option_index(target_zone_id)
	if target_zone_index >= 0:
		exit_target_zone_input.select(target_zone_index)
	_rebuild_target_room_options(target_zone_id)
	exit_target_input.select(_find_target_room_option_index(target_room_id))
	exit_label_input.text = str(row.get("label", ""))
	var aliases: Array[String] = []
	for alias in row.get("aliases", []):
		aliases.append(str(alias))
	exit_aliases_input.text = ", ".join(aliases)
	exit_editor.visible = true
	emit_signal("exit_selected", selected_exit_id)


func _on_exit_save_pressed() -> void:
	if room_id.is_empty() or selected_exit_id.is_empty():
		return
	var target_zone_index := exit_target_zone_input.get_selected_id()
	var target_index := exit_target_input.get_selected_id()
	if selected_direction.is_empty():
		return
	if target_zone_index < 0 or target_zone_index >= target_zone_ids.size():
		return
	if target_index < 0 or target_index >= target_room_ids.size():
		return
	var aliases: Array[String] = []
	for raw_alias in exit_aliases_input.text.split(","):
		var normalized_alias := raw_alias.strip_edges()
		if not normalized_alias.is_empty() and not aliases.has(normalized_alias):
			aliases.append(normalized_alias)
	var fields := {
		"direction": selected_direction,
		"target_zone_id": target_zone_ids[target_zone_index],
		"target_room_id": target_room_ids[target_index],
		"label": exit_label_input.text.strip_edges(),
		"aliases": aliases,
	}
	emit_signal("exit_save_requested", room_id, selected_exit_id, fields)


func _on_exit_delete_pressed() -> void:
	if room_id.is_empty() or selected_exit_id.is_empty():
		return
	emit_signal("exit_delete_requested", room_id, selected_exit_id)


func _on_save_pressed() -> void:
	if room_id == "":
		return
	if name_input.text.strip_edges() == "":
		return
	var updates := get_room_updates()
	emit_signal("draft_changed", room_id, updates)
	emit_signal("save_requested", room_id, updates)


func _on_close_pressed() -> void:
	visible = false
	emit_signal("close_requested")


func _on_add_npc_pressed() -> void:
	if room_id == "":
		return
	emit_signal("add_npc_requested")


func _on_add_item_pressed() -> void:
	if room_id == "":
		return
	emit_signal("add_item_requested")


func _set_selected_direction(direction: String) -> void:
	selected_direction = direction.strip_edges().to_lower()
	exit_direction_value.text = _format_exit_direction(selected_direction) if not selected_direction.is_empty() else "-"
	for button_direction in direction_buttons.keys():
		(direction_buttons[button_direction] as BaseButton).set_pressed_no_signal(button_direction == selected_direction)


func _on_direction_button_toggled(pressed: bool, direction: String) -> void:
	if not pressed:
		if selected_direction == direction:
			(direction_buttons[direction] as BaseButton).set_pressed_no_signal(true)
		return
	_set_selected_direction(direction)


func _on_target_zone_selected(index: int) -> void:
	if index < 0 or index >= target_zone_ids.size():
		return
	_rebuild_target_room_options(target_zone_ids[index])